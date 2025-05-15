from llama_cpp import Llama
import re
import sqlparse
from config import MODEL_PATH, table_metadata_string_DDL_statements
from sql_utils import clean_sql_query, validate_sql

llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=8, n_gpu_layers=100)


def generate_sql_query(user_query: str, city: str = None) -> str:
    """
    Генерирует SQL-запрос по запросу пользователя. Если задан city,
    добавляет условие location = '<city>' к WHERE или перед LIMIT.
    """
    print(f"Генерируем SQL для запроса: {user_query}")

    prompt = f"""
    Тебе нужно составить sql запрос к таблице на основе запроса пользователя,
    table schema: {table_metadata_string_DDL_statements}
    Примеры:
    user_query: Ищу квартиру около метро Маяковская с площадью не менее 80 квадратных метров
    expected_sql: SELECT url, floor, floors_count, rooms_count, total_meters, price, underground FROM listings WHERE deal_type = 'sale' AND rooms_count = 2 AND underground = 'Маяковская' AND total_meters >= 80 ORDER BY price ASC LIMIT 3;
    user_query: Хочу квартиру рядом с метро Филатов луг не дороже 14000000
    expected_sql: SELECT url, floor, floors_count, rooms_count, total_meters, price, underground FROM listings WHERE deal_type = 'sale' AND underground = 'Филатов луг' AND price <= 14000000 ORDER BY price ASC LIMIT 3;

    Сгенерируй только SQL-запрос для таблицы listings без дополнительных символов или пояснений.
    Запрос обязательно должен начинаться с
    SELECT url, floor, floors_count, rooms_count, total_meters, price, underground
    и заканчиваться "LIMIT 3;"
    Не используй поле district для фильтрации.
    Запрос должен отвечать на вопрос: {user_query}
    SQL:
    """

    try:
        response = llm(prompt, max_tokens=150, stop=[";"])
        raw_text = response["choices"][0]["text"].strip()
        if not raw_text:
            raise ValueError("Пустой ответ от модели")

        cleaned_query = clean_sql_query(raw_text)
        if cleaned_query is None:
            raise ValueError("Не удалось распознать SQL в ответе")

        if not validate_sql(cleaned_query):
            raise ValueError("Сгенерированный SQL некорректен")

        if city:
            if " where " in cleaned_query:
                cleaned_query = cleaned_query.replace(
                    " where ",
                    f" where location = '{city.lower()}' and ",
                    1
                )
            else:
                cleaned_query = cleaned_query.replace(
                    "limit 3;",
                    f"where location = '{city.lower()}' limit 3;"
                )
        print(f"Сгенерированный SQL: {cleaned_query}")
        return cleaned_query

    except Exception as e:
        return f"Ошибка генерации SQL: {e}"  



def generate_listing_description(data):
    """
    Генерирует описание через LLM с использованием расширенного few-shot,
    фильтрацией и дополнительной рандомизацией для разнообразия.
    Всегда добавляет ссылку и корректно обрабатывает None.
    """
    import re, random

    # Подготовка данных
    rooms = data.get("rooms_count")
    total_meters = data.get("total_meters")
    floor = data.get("floor")
    floors_count = data.get("floors_count")
    underground = data.get("underground")
    price_val = data.get("price")
    url = data.get("url") or ""

    attrs = []
    if floor is not None and floors_count is not None:
        attrs.append(f"на {int(floor)}-м этаже {int(floors_count)}-этажного дома")
    elif floor is not None:
        attrs.append(f"на {int(floor)}-м этаже")
    if rooms is not None:
        attrs.append(f"{int(rooms)}-комнатная квартира")
    if total_meters is not None:
        attrs.append(f"площадью {total_meters:.1f} кв. м")
    if underground:
        attrs.append(f"в пешей доступности от метро «{underground.capitalize()}»")
    if price_val is not None:
        attrs.append(f"стоимостью {int(price_val):,} ₽")
    else:
        attrs.append("цена не указана")
    attrs_text = "; ".join(attrs)

    prompt = f"""
Примеры формата:
1) На 7-м этаже 9-этажного дома расположена 2-комнатная квартира площадью 48 кв. м в пешей доступности от метро «Проспект Мира». Стоимость составляет 9 500 000 ₽. Ссылка на объявление: https://example.com/listing/1
2) На 12-м этаже 14-этажного дома представлена 3-комнатная квартира площадью 75 кв. м рядом со станцией «Таганская». Цена — 15 200 000 ₽. Ссылка на объявление: https://example.com/listing/2
3) Квартира с одной спальней площадью 40 кв. м находится на 3-м этаже 5-этажного дома в 5 минутах ходьбы от метро «Черкизовская». Стоимость — 7 300 000 ₽. Ссылка на объявление: https://example.com/listing/3
4) На 18-м этаже 25-этажного дома представлена 4-комнатная квартира площадью 120 кв. м рядом с метро «Киевская». Цена составляет 25 000 000 ₽. Ссылка на объявление: https://example.com/listing/4

Данные объекта: {attrs_text}.

Опиши этот объект недвижимости в том же формате, что и примеры выше.
Не добавляй ничего лишнего, только описание объекта и ссылку на него.
Если метро не указано, не добавляй его в описание.
"""
    try:
        response = llm(prompt, max_tokens=180, temperature=0.9, stop=["Ссылка на объявление:"])
        candidates = [c["text"].strip() for c in response["choices"]]
        def valid(text):
            return bool(re.search(r"\d+-комнат", text)) and bool(re.search(r"\d+[.,]?\d* кв", text)) and "Ссылка на объявление:" in text
        valid_candidates = [t for t in candidates if valid(t)]
        if valid_candidates:
            text = random.choice(valid_candidates)
        else:
            text = random.choice(candidates)
        if "http" not in text:
            text = text.rstrip('.') + f". Ссылка на объявление: {url}"
        return text
    except Exception:
        return f"{attrs_text}. Ссылка на объявление: {url}"
