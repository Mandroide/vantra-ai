"""Únicamente registros sintéticos; nunca se persiste contenido conversacional."""
import os, sqlite3, tempfile
from contextlib import closing
from pathlib import Path

DB = Path(os.getenv('VANTRA_DB_PATH', str(Path(tempfile.gettempdir()) / 'vantra_demo.sqlite3')))


def connection():
    c = sqlite3.connect(str(DB), timeout=15)
    c.execute(
        'CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, product TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS callbacks (id INTEGER PRIMARY KEY, topic TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS transfers (id INTEGER PRIMARY KEY, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    return c


def insert(table, value):
    if table not in {'leads', 'callbacks', 'transfers'}: raise ValueError('Tabla no permitida')
    if len(str(value)) > 60: raise ValueError('Dato demasiado extenso')
    column = {'leads': 'product', 'callbacks': 'topic', 'transfers': 'reason'}[table]
    with closing(connection()) as c:
        with c:
            cursor = c.execute(f'INSERT INTO {table}({column}) VALUES (?)', (value,))
        return cursor.lastrowid


def counts():
    with closing(connection()) as c:
        return {t: c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('leads', 'callbacks', 'transfers')}


def record_interaction_metric(mode: str, status: str, elapsed_ms: float):
    """Guarda ÚNICAMENTE telemetría agregable; sin texto, voz, números ni tokens."""
    if mode not in {'LIVE', 'DEMO'}:
        return
    if not (0 <= elapsed_ms <= 3_600_000):
        return
    with closing(connection()) as c:
        with c:
            c.execute('''CREATE TABLE IF NOT EXISTS interaction_metrics
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY,
                             created_at
                             TEXT
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             mode
                             TEXT
                             NOT
                             NULL,
                             status
                             TEXT
                             NOT
                             NULL,
                             elapsed_ms
                             REAL
                             NOT
                             NULL
                         )''')
            c.execute('INSERT INTO interaction_metrics(mode,status,elapsed_ms) VALUES (?,?,?)',
                      (mode, str(status)[:30], elapsed_ms))


def telemetry_summary():
    """Métricas de la aplicación observadas localmente, NO precisión de tareas."""
    with closing(connection()) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS interaction_metrics
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY,
                         created_at
                         TEXT
                         DEFAULT
                         CURRENT_TIMESTAMP,
                         mode
                         TEXT
                         NOT
                         NULL,
                         status
                         TEXT
                         NOT
                         NULL,
                         elapsed_ms
                         REAL
                         NOT
                         NULL
                     )''')
        result = {}
        for mode in ('DEMO', 'LIVE'):
            rows = c.execute('SELECT elapsed_ms FROM interaction_metrics WHERE mode=? ORDER BY elapsed_ms',
                             (mode,)).fetchall()
            vals = [float(r[0]) for r in rows]
            if vals:
                import numpy as np
                result[mode] = {'interacciones_texto_observadas': len(vals),
                                'latencia_aplicacion_p50_ms': round(float(np.median(vals)), 2),
                                'latencia_aplicacion_p95_ms': round(float(np.percentile(vals, 95)), 2)}
            else:
                result[mode] = {'interacciones_texto_observadas': 0, 'latencias': 'No registradas'}
        return result
