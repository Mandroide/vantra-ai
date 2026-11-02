"""Telemetría de llamadas sin grabaciones, contenido ni teléfonos.

La latencia STT es aproximada desde el último paquete de media recibido
hasta el evento final de transcripción, NO mide WER ni latencia integral.
"""
from __future__ import annotations

from contextlib import closing
import math
import re
import sqlite3
import time

from src.storage import DB

STAGES = {'twilio', 'stream', 'tts', 'stt_approx', 'agent', 'consent', 'policy', 'call'}
EVENTS = {'queued', 'initiated', 'ringing', 'in-progress', 'completed', 'busy',
          'failed', 'no-answer', 'canceled', 'started', 'ended', 'closing',
          'ok', 'error', 'accepted', 'denied', 'not_confirmed',
          'fraud', 'human', 'complaint'}


def record_call_event(call_id: str, stage: str, event: str, duration_ms: float | None = None) -> bool:
    """Solo registra valores enumerados. Los fallos de telemetría no interrumpen llamadas."""
    if not re.fullmatch(r'[0-9a-f]{32}', call_id or '') or stage not in STAGES or event not in EVENTS:
        return False
    if duration_ms is not None and (not math.isfinite(duration_ms) or not 0 <= duration_ms <= 3600000):
        return False
    try:
        DB.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(DB, timeout=5)) as conn:
            with conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS call_events (
                    id INTEGER PRIMARY KEY, call_id TEXT NOT NULL, at_utc INTEGER NOT NULL,
                    stage TEXT NOT NULL, event TEXT NOT NULL, duration_ms REAL
                )""")
                conn.execute('INSERT INTO call_events (call_id,at_utc,stage,event,duration_ms) VALUES (?,?,?,?,?)',
                             (call_id, int(time.time()), stage, event, duration_ms))
        return True
    except (sqlite3.Error, OSError):
        return False


def call_telemetry_summary() -> dict:
    """Métricas observadas por etapa; ausencia de datos se expresa con None."""
    import numpy as np
    output = {'events': 0, 'stages': {}}
    try:
        with closing(sqlite3.connect(DB, timeout=5)) as conn:
            rows = conn.execute('SELECT stage,event,duration_ms FROM call_events').fetchall()
    except (sqlite3.Error, OSError):
        return output
    output['events'] = len(rows)
    for stage in sorted(STAGES):
        values = [float(ms) for stage_name, event, ms in rows
                  if stage_name == stage and event == 'ok' and ms is not None]
        output['stages'][stage] = {
            'count': len(values),
            'p50_ms': round(float(np.percentile(values, 50)), 2) if values else None,
            'p95_ms': round(float(np.percentile(values, 95)), 2) if values else None,
        }
    output['call_status_events'] = {
        status: sum(1 for stage, event, _ in rows if stage == 'twilio' and event == status)
        for status in ('completed', 'busy', 'failed', 'no-answer')
    }
    return output


USAGE_PROVIDERS = {'anthropic_input_tokens', 'anthropic_output_tokens',
                   'azure_tts_characters', 'deepgram_audio_seconds'}


def record_provider_usage(call_id: str, provider: str, units: float,
                          estimated_usd: float | None = None) -> bool:
    """Consumo OBSERVADO; el costo es solo estimado si se ingresó tarifa > 0.

    Nunca incluye facturación PSTN/Twilio, impuestos, infraestructura ni mínimos.
    """
    if (not re.fullmatch(r'[0-9a-f]{32}', call_id or '') or provider not in USAGE_PROVIDERS
        or not math.isfinite(units) or units < 0
        or (estimated_usd is not None and (not math.isfinite(estimated_usd) or estimated_usd < 0))):
        return False
    try:
        DB.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(DB, timeout=5)) as conn:
            with conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS call_usage (
                    id INTEGER PRIMARY KEY, call_id TEXT NOT NULL, at_utc INTEGER NOT NULL,
                    provider TEXT NOT NULL, units REAL NOT NULL, estimated_usd REAL
                )''')
                conn.execute('INSERT INTO call_usage(call_id,at_utc,provider,units,estimated_usd) VALUES (?,?,?,?,?)',
                             (call_id, int(time.time()), provider, units, estimated_usd))
        return True
    except (sqlite3.Error, OSError):
        return False


def usage_summary() -> dict:
    """Unidades observadas y subtotal estimado solo donde hay tarifa configurada."""
    output = {'records': 0, 'units_by_provider': {}, 'partial_estimated_usd': None,
              'priced_records': 0, 'unpriced_records': 0,
              'complete_bill': False}
    try:
        with closing(sqlite3.connect(DB, timeout=5)) as conn:
            rows = conn.execute('SELECT provider,units,estimated_usd FROM call_usage').fetchall()
    except (sqlite3.Error, OSError):
        return output
    output['records'] = len(rows)
    for provider in USAGE_PROVIDERS:
        selected = [r for r in rows if r[0] == provider]
        output['units_by_provider'][provider] = round(sum(r[1] for r in selected), 3)
    priced = [r[2] for r in rows if r[2] is not None]
    output['priced_records'] = len(priced)
    output['unpriced_records'] = len(rows) - len(priced)
    output['partial_estimated_usd'] = round(sum(priced), 6) if priced else None
    return output


def configured_tariff(name: str) -> float | None:
    """Tarifa informada por operador; inválida/ausente significa costo desconocido."""
    from src.config import env
    try:
        value = float(env(name, '0') or '0')
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) and value > 0 else None
