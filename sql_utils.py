import sqlparse
import re
from psycopg2 import connect, sql
from config import DB_CONFIG
from psycopg2.extras import DictCursor


def clean_sql_query(query, city=None):
    query_match = re.search(r"(SELECT\s+.+?(?:;|$))", query, re.IGNORECASE | re.DOTALL)
    if query_match:
        sql_query = query_match.group(1).strip()
        cleaned_query = re.sub(r'\s*\n\s*', ' ', sql_query)
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        return cleaned_query.lower()
    else:
        return None



def execute_sql_query(query):
    try:
        conn = connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        return f"Ошибка выполнения SQL: {e}"
    
def validate_sql(query):
    try:
        sqlparse.parse(query)
        return True
    except Exception:
        return False