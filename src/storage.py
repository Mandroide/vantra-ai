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


# Telemetría numérica local: no registra voz, texto, números ni datos de clientes.
def _ensure_metrics_table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS interaction_metrics
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
           )"""
    )


def record_interaction_metric(mode: str, status: str, elapsed_ms: float) -> None:
    """Registra únicamente duración y resultado; medición de la aplicación Gradio."""
    import math

    if mode not in {"DEMO", "LIVE"} or not math.isfinite(elapsed_ms) or not 0 <= elapsed_ms <= 3_600_000:
        return
    # Evita que el estado contenga por error contenido de usuario.
    if status not in {"OK", "UNKNOWN", "DENIED", "CONSENT_DENIED", "DNC_REQUESTED",
                      "NEED_CONFIRMATION", "PROVIDER_ERROR", "FALLBACK_HUMAN",
                      "TRANSFER", "ERROR", "PARTIAL"}:
        status = "OTRO"
    with closing(connection()) as conn:
        with conn:
            _ensure_metrics_table(conn)
            conn.execute("INSERT INTO interaction_metrics (mode, status, elapsed_ms) VALUES (?, ?, ?)",
                         (mode, status, float(elapsed_ms)))


def telemetry_summary() -> dict:
    """Conteos y latencia P50/P95 por modo. No representa WER ni éxito de tarea."""
    import numpy as np

    result = {}
    with closing(connection()) as conn:
        _ensure_metrics_table(conn)
        for mode in ("DEMO", "LIVE"):
            values = [row[0] for row in conn.execute(
                "SELECT elapsed_ms FROM interaction_metrics WHERE mode = ?", (mode,))]
            result[mode] = {"interacciones_gradio_observadas": len(values),
                            "latencia_aplicacion_p50_ms": round(float(np.percentile(values, 50)),
                                                                2) if values else None,
                            "latencia_aplicacion_p95_ms": round(float(np.percentile(values, 95)),
                                                                2) if values else None}
    return result
