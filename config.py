TOKEN = '*****'

DB_CONFIG = {
    "dbname": "testdb",
    "user": "admin",
    "password": "adminadmin",
    "host": "localhost",
    "port": "5432"
}

table_metadata_string_DDL_statements = '''
CREATE TABLE public.listings (
	id serial4 NOT NULL,
	author text NULL,
	author_type text NULL,
	url text NULL,
	"location" text NULL,
	deal_type text NULL,
	accommodation_type text NULL,
	floor int4 NULL,
	floors_count int4 NULL,
	rooms_count int4 NULL,
	total_meters float8 NULL,
	price int8 NULL,
	district text NULL, (Район)
	street text NULL,
	house_number text NULL,
	underground text NULL, (Метро)
	residential_complex text NULL,
	CONSTRAINT listings_pkey PRIMARY KEY (id)
);
'''


MODEL_PATH = "/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"