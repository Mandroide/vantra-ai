"""Únicamente registros sintéticos; nunca se persiste contenido conversacional."""
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

DB=Path(os.getenv('VANTRA_DB_PATH',str(Path(tempfile.gettempdir())/'vantra_demo.sqlite3')))
def connection():
    c=sqlite3.connect(str(DB),timeout=15)
    c.execute('CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, product TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS callbacks (id INTEGER PRIMARY KEY, topic TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS transfers (id INTEGER PRIMARY KEY, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    return c
def insert(table, value):
    if table not in {'leads','callbacks','transfers'}: raise ValueError('Tabla no permitida')
    if len(str(value))>60: raise ValueError('Dato demasiado extenso')
    column={'leads':'product','callbacks':'topic','transfers':'reason'}[table]
    with closing(connection()) as c:
        with c:
            cursor=c.execute(f'INSERT INTO {table}({column}) VALUES (?)',(value,))
        return cursor.lastrowid
def counts():
    with closing(connection()) as c:
        return {t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('leads','callbacks','transfers')}
