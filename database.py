import sqlite3
from contextlib import contextmanager

DATABASE = 'laporan.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
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
        # Tabel untuk menyimpan metadata laporan
        conn.execute('''
            CREATE TABLE IF NOT EXISTS laporan (
                filename TEXT PRIMARY KEY,
                metadata TEXT,
                tujuan TEXT,
                kesimpulan TEXT,
                referensi TEXT
            )
        ''')
        # Tabel untuk menyimpan sections (dasar teori, main sections, subsections, dll.)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                section_id TEXT,
                type TEXT,
                title TEXT,
                content TEXT,
                image TEXT,
                parent_section TEXT,
                FOREIGN KEY (filename) REFERENCES laporan(filename)
            )
        ''')
        conn.commit()