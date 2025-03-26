import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
import os
import urllib.parse as urlparse

# Ambil URL database dari environment variable
DATABASE_URL = os.getenv('POSTGRES_URL')

# Bersihkan parameter yang tidak dikenal dari connection string
def clean_dsn(dsn):
    parsed = urlparse.urlparse(dsn)
    query = urlparse.parse_qs(parsed.query)
    # Hanya simpan parameter yang dikenal oleh psycopg2
    allowed_params = {'sslmode', 'dbname', 'user', 'password', 'host', 'port'}
    filtered_query = {k: v for k, v in query.items() if k in allowed_params}
    # Bangun kembali query string
    new_query = '&'.join(f"{k}={v[0]}" for k, v in filtered_query.items())
    # Bangun kembali DSN
    cleaned_dsn = urlparse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    return cleaned_dsn

# Bersihkan DATABASE_URL sebelum digunakan
if DATABASE_URL:
    DATABASE_URL = clean_dsn(DATABASE_URL)
    print(f"Cleaned DATABASE_URL: {DATABASE_URL}")

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