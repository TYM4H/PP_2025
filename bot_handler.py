from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN
from llm_module import generate_sql_query, generate_listing_description
from sql_utils import execute_sql_query, validate_sql, clean_sql_query

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SearchState(StatesGroup):
    city = State()
    property_type = State()
    rooms = State()
    budget = State()

user_listings = {}
user_cities = {}

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! 👋 Я бот-помощник по недвижимости.\n\n"
        "/search – Найти недвижимость пошагово 🏡\n"
        "/help – Помощь и примеры запросов"
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Ты можешь:\n"
        "• Написать запрос текстом (например: «Купить квартиру до 6 млн» )\n"
        "• Использовать пошаговый поиск через /search"
    )

cities_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Москва")],
        [KeyboardButton(text="Сочи")],
        [KeyboardButton(text="Санкт-Петербург")]
    ],
    resize_keyboard=True
)

@dp.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await message.answer("🏙 Выберите город:", reply_markup=cities_kb)
    await state.set_state(SearchState.city)

@dp.message(SearchState.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    user_cities[message.chat.id] = message.text
    types_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Квартира")],
            [KeyboardButton(text="Дом")],
            [KeyboardButton(text="Студия")],
        ],
        resize_keyboard=True
    )
    await message.answer("🏠 Какой тип недвижимости интересует?", reply_markup=types_kb)
    await state.set_state(SearchState.property_type)

@dp.message(SearchState.property_type)
async def process_type(message: Message, state: FSMContext):
    await state.update_data(property_type=message.text)
    rooms_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 комната")],
            [KeyboardButton(text="2 комнаты")],
            [KeyboardButton(text="3 комнаты")],
            [KeyboardButton(text="4+ комнаты")]
        ],
        resize_keyboard=True
    )
    await message.answer("🛏 Сколько комнат ты хочешь?", reply_markup=rooms_kb)
    await state.set_state(SearchState.rooms)

@dp.message(SearchState.rooms)
async def process_rooms(message: Message, state: FSMContext):
    await state.update_data(rooms=message.text)
    await message.answer("💰 Укажи бюджет (например: до 6 млн или до 50 тыс в месяц):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(SearchState.budget)

@dp.message(SearchState.budget)
async def process_budget(message: Message, state: FSMContext):
    await state.update_data(budget=message.text)
    data = await state.get_data()
    user_query = f"{data['property_type']} в {data['city']} {data['rooms']} {data['budget']}"
    await handle_real_estate_search(message, user_query)
    await state.clear()

@dp.message()
async def handle_free_query(message: Message):
    await handle_real_estate_search(message, message.text)

async def handle_real_estate_search(message: Message, user_input: str, offset: int = 0):
    user_query = user_input.lower()
    await message.answer("🔍 Ищу по твоему запросу...")
    
    sql_query = generate_sql_query(user_query, city=user_cities.get(message.chat.id))
    if not sql_query or not validate_sql(sql_query):
        await message.answer("❌ Не удалось обработать запрос. Попробуй снова или используй /search.")
        return
    
    listings = execute_sql_query(sql_query)

    if isinstance(listings, str):
        await message.answer(f"⚠️ Ошибка: {listings}")
        return
    elif not listings:
        await message.answer("😕 Ничего не найдено.")
        return

    chat_id = message.chat.id
    user_listings[chat_id] = listings
    await send_listings(chat_id, listings, offset)

async def send_listings(chat_id: int, listings: list, offset: int = 0):
    chunk = listings[offset:offset + 5]
    for listing in chunk:
        description = generate_listing_description(listing)
        map_link = ""
        await bot.send_message(chat_id, description + map_link, parse_mode="Markdown")

    if offset + 5 < len(listings):
        show_more_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Показать ещё", callback_data=f"more:{offset+5}")]]
        )
        await bot.send_message(chat_id, "🔽 Хочешь ещё варианты?", reply_markup=show_more_kb)

@dp.callback_query(F.data.startswith("more:"))
async def show_more(callback: CallbackQuery):
    offset = int(callback.data.split(":")[1])
    listings = user_listings.get(callback.message.chat.id)
    if listings:
        await send_listings(callback.message.chat.id, listings, offset)
    await callback.answer()
