import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
import os

# Ambil URL database dari environment variable
DATABASE_URL = os.getenv('POSTGRES_URL')

def get_db():
    # Pastikan sslmode=require ada di connection string
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

@contextmanager
def db_connection():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS laporan (
                filename TEXT PRIMARY KEY,
                metadata TEXT,
                tujuan TEXT,
                kesimpulan TEXT,
                referensi TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                section_id TEXT,
                type TEXT,
                title TEXT,
                content TEXT,
                image TEXT,
                parent_section TEXT,
                CONSTRAINT fk_laporan
                    FOREIGN KEY (filename)
                    REFERENCES laporan(filename)
            )
        ''')
        conn.commit()