"""Piloto saliente REAL solo a destinatarios dominicanos preautorizados.

Controles: lista positiva en entorno + consentimiento verificable externamente,
exclusión permanente, horario local, una llamada simultánea y límite diario.
Los números nunca se guardan en SQLite (solo HMAC irreversible).
"""
from __future__ import annotations

import base64
from contextlib import closing
from datetime import datetime
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from src.config import env, key
from src.storage import DB

DO_NUMBER = re.compile(r'^\+1(?:809|829|849)\d{7}$')
CALL_SID = re.compile(r'^CA[a-zA-Z0-9]{32}$')
TZ = ZoneInfo('America/Santo_Domingo')
TERMINAL = {'completed', 'busy', 'failed', 'no-answer', 'canceled', 'rejected', 'error'}
ACTIVE = {'reserved', 'queued', 'initiated', 'ringing', 'in-progress'}
TWILIO_ACTIVE = {'queued', 'initiated', 'ringing', 'in-progress'}
TWILIO_TERMINAL = {'completed', 'busy', 'failed', 'no-answer', 'canceled'}


class CallPolicyError(ValueError):
    pass


class ActiveCallError(CallPolicyError):
    """Una reserva concurrente activa bloquea nuevos intentos."""


def normalize_do_phone(phone: str) -> str:
    """Solo +1809/+1829/+1849 seguido de 7 dígitos; no normalizar entradas ambiguas."""
    candidate = (phone or '').strip()
    if not DO_NUMBER.fullmatch(candidate):
        raise CallPolicyError('Número inválido: use E.164 dominicano (+1809, +1829 o +1849 y 7 dígitos).')
    return candidate


def _phone_hash(phone: str) -> str:
    return hmac.new(key('TWILIO_AUTH_TOKEN').encode(), phone.encode(), hashlib.sha256).hexdigest()


def _conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=20, isolation_level=None)
    c.execute('PRAGMA busy_timeout=20000')
    c.execute('''CREATE TABLE IF NOT EXISTS phone_calls
                 (
                     id
                     TEXT
                     PRIMARY
                     KEY,
                     nonce
                     TEXT
                     NOT
                     NULL,
                     phone_hash
                     TEXT
                     NOT
                     NULL,
                     call_sid
                     TEXT
                     UNIQUE,
                     status
                     TEXT
                     NOT
                     NULL,
                     created_utc
                     INTEGER
                     NOT
                     NULL,
                     updated_utc
                     INTEGER
                     NOT
                     NULL
                 )''')
    c.execute('CREATE INDEX IF NOT EXISTS calls_when ON phone_calls(created_utc)')
    c.execute('CREATE TABLE IF NOT EXISTS phone_dnc(phone_hash TEXT PRIMARY KEY, added_utc INTEGER NOT NULL)')
    return c


def get_call(call_id: str) -> dict | None:
    if not re.fullmatch('[0-9a-f]{32}', call_id or ''):
        return None
    with closing(_conn()) as c:
        r = c.execute('SELECT id,call_sid,status,created_utc FROM phone_calls WHERE id=?', (call_id,)).fetchone()
    return dict(zip(('id', 'call_sid', 'status', 'created_utc'), r)) if r else None


def _active_calls() -> list[dict]:
    """Instantánea de llamadas locales activas sin números ni datos personales."""
    with closing(_conn()) as c:
        rows = c.execute("SELECT id,call_sid,status FROM phone_calls WHERE status IN "
                         "('reserved','queued','initiated','ringing','in-progress')"
                         " ORDER BY created_utc").fetchall()
    return [dict(zip(('id', 'call_sid', 'status'), row)) for row in rows]


def get_call_by_sid(sid: str) -> dict | None:
    if not CALL_SID.fullmatch(sid or ''):
        return None
    with closing(_conn()) as c:
        r = c.execute('SELECT id,call_sid,status FROM phone_calls WHERE call_sid=?', (sid,)).fetchone()
    return dict(zip(('id', 'call_sid', 'status'), r)) if r else None


def _allowed_now() -> bool:
    local = datetime.now(TZ)
    # Lunes a viernes, 09:00-17:59 local. No sustituye cumplimiento regulatorio.
    return local.weekday() < 5 and 9 <= local.hour < 18


def _preflight(phone: str, confirmed: bool, *, check_time: bool = True) -> str:
    number = normalize_do_phone(phone)
    if env('TWILIO_CALLS_ENABLED', 'false').lower() != 'true':
        raise CallPolicyError('Llamadas reales desactivadas; TWILIO_CALLS_ENABLED=false.')
    if env('VANTRA_MODE', 'DEMO').upper() != 'LIVE':
        raise CallPolicyError('Active VANTRA_MODE=LIVE para llamadas reales.')
    if confirmed is not True:
        raise CallPolicyError('Confirme el consentimiento previo documentado para este número.')
    allowlist = {p.strip() for p in env('TWILIO_TEST_NUMBERS').split(',') if p.strip()}
    if number not in allowlist:
        raise CallPolicyError('Número no autorizado: agréguelo a TWILIO_TEST_NUMBERS tras obtener consentimiento.')
    # Excepción opt-in exclusivamente para pruebas manuales con teléfonos autorizados.
    # Se conservan consentimiento, allowlist, DNC y límites de volumen.
    allow_after_hours = env('TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS', 'false').lower() == 'true'
    if check_time and not allow_after_hours and not _allowed_now():
        raise CallPolicyError('Fuera del horario de pruebas: lunes a viernes, 09:00–17:59 (Santo Domingo).')
    for field in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER',
                  'TWILIO_PUBLIC_BASE_URL', 'DEEPGRAM_API_KEY', 'AZURE_SPEECH_KEY',
                  'AZURE_SPEECH_REGION', 'ANTHROPIC_API_KEY'):
        key(field)
    if not re.fullmatch(r'AC[a-zA-Z0-9]{32}', env('TWILIO_ACCOUNT_SID')):
        raise CallPolicyError('TWILIO_ACCOUNT_SID no tiene un formato válido.')
    base = env('TWILIO_PUBLIC_BASE_URL')
    parsed = urlparse(base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.query or parsed.fragment
        or parsed.path not in ('', '/') or parsed.username or parsed.password):
        raise CallPolicyError('TWILIO_PUBLIC_BASE_URL debe ser una URL HTTPS pública, sin ruta.')
    if not re.fullmatch(r'\+[1-9]\d{6,14}', env('TWILIO_FROM_NUMBER')):
        raise CallPolicyError('TWILIO_FROM_NUMBER debe ser E.164 válido y autorizado en Twilio.')
    return number


def _daily_call_limit() -> int:
    """Máximo diario de intentos de piloto (1 a 10); nunca ilimitado."""
    setting = env('TWILIO_DAILY_CALL_LIMIT', '3').strip()
    try:
        maximum = int(setting)
    except ValueError as exc:
        raise CallPolicyError('TWILIO_DAILY_CALL_LIMIT debe ser un entero entre 1 y 10.') from exc
    if not 1 <= maximum <= 10:
        raise CallPolicyError('TWILIO_DAILY_CALL_LIMIT debe estar entre 1 y 10.')
    return maximum


def _reserve(phone: str) -> tuple[str, str]:
    now = int(time.time())
    today = datetime.now(TZ).date()
    # Medianoche dominicana traducida a timestamp UTC.
    start_today = int(datetime.combine(today, datetime.min.time(), tzinfo=TZ).timestamp())
    number_hash = _phone_hash(phone)
    with closing(_conn()) as c:
        try:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM phone_dnc WHERE phone_hash=?', (number_hash,)).fetchone():
                raise CallPolicyError('Este número pidió no recibir más llamadas (DNC).')
            active = c.execute(
                "SELECT COUNT(*) FROM phone_calls WHERE status IN ('reserved','queued','initiated','ringing','in-progress')").fetchone()[
                0]
            if active >= 1:
                raise ActiveCallError('Existe otra llamada en curso. Solo se permite una simultánea.')
            n = c.execute('SELECT COUNT(*) FROM phone_calls WHERE created_utc>=?', (start_today,)).fetchone()[0]
            daily_limit = _daily_call_limit()
            if n >= daily_limit:
                raise CallPolicyError(f'Límite diario de piloto alcanzado ({daily_limit} intentos).')
            call_id, nonce = uuid4().hex, secrets.token_urlsafe(32)
            c.execute('INSERT INTO phone_calls VALUES (?,?,?,?,?,?,?)',
                      (call_id, nonce, number_hash, None, 'reserved', now, now))
            c.execute('COMMIT')
            return call_id, nonce
        except BaseException:
            c.execute('ROLLBACK')
            raise


def update_call(call_id: str, status: str, sid: str | None = None) -> None:
    if status not in TERMINAL | ACTIVE:
        raise ValueError('Estado telefónico inválido')
    # BEGIN IMMEDIATE serializa comparación y escritura: un callback tardío
    # no puede revivir una llamada que otra conexión acaba de finalizar.
    with closing(_conn()) as c:
        try:
            c.execute('BEGIN IMMEDIATE')
            current = c.execute('SELECT status FROM phone_calls WHERE id=?', (call_id,)).fetchone()
            progression = {'reserved': 0, 'queued': 1, 'initiated': 2, 'ringing': 3, 'in-progress': 4}
            if (current and current[0] not in TERMINAL and
                progression.get(status, 10) >= progression.get(current[0], 10)):
                if sid is None:
                    c.execute('UPDATE phone_calls SET status=?, updated_utc=? WHERE id=?',
                              (status, int(time.time()), call_id))
                else:
                    if not CALL_SID.fullmatch(sid):
                        raise ValueError('Call SID inválido')
                    # No se sobrescribe SID; race webhook-media y creación puede ocurrir.
                    c.execute('''UPDATE phone_calls
                                 SET status=?,
                                     call_sid=COALESCE(call_sid, ?),
                                     updated_utc=?
                                 WHERE id = ?
                                   AND (call_sid IS NULL OR call_sid = ?)''',
                              (status, sid, int(time.time()), call_id, sid))
            c.execute('COMMIT')
        except BaseException:
            c.execute('ROLLBACK')
            raise


def claim_stream(call_id: str, nonce: str, sid: str) -> bool:
    if not re.fullmatch('[0-9a-f]{32}', call_id or '') or not CALL_SID.fullmatch(sid or ''):
        return False
    with closing(_conn()) as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT nonce,status,call_sid FROM phone_calls WHERE id=?', (call_id,)).fetchone()
        valid = bool(row and hmac.compare_digest(row[0], nonce or '')
                     and row[1] not in TERMINAL and (row[2] is None or row[2] == sid))
        if valid:
            c.execute("UPDATE phone_calls SET status='in-progress', call_sid=?, updated_utc=? WHERE id=?",
                      (sid, int(time.time()), call_id))
        c.execute('COMMIT')
        return valid


def add_do_not_call(phone: str) -> None:
    """Permite a un operador excluir un número autorizado sin realizar llamadas."""
    number = normalize_do_phone(phone)
    with closing(_conn()) as c:
        with c:
            c.execute('INSERT OR IGNORE INTO phone_dnc(phone_hash,added_utc) VALUES (?,?)',
                      (_phone_hash(number), int(time.time())))


def mark_do_not_call(call_id: str) -> None:
    with closing(_conn()) as c:
        with c:
            c.execute('''INSERT
            OR IGNORE INTO phone_dnc(phone_hash,added_utc)
            SELECT phone_hash, ?
            FROM phone_calls
            WHERE id = ?''',
                      (int(time.time()), call_id))


def twilio_valid_signature(url: str, signature: str, params: dict[str, str] | None = None) -> bool:
    """Implementación del HMAC-SHA1 documentado por Twilio (comparación segura)."""
    if not signature:
        return False
    suffix = ''.join(str(k) + str(v) for k, v in sorted((params or {}).items()))
    content = (url + suffix).encode()
    expected = base64.b64encode(hmac.new(key('TWILIO_AUTH_TOKEN').encode(), content,
                                         hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, signature)


def public_url(path: str) -> str:
    return env('TWILIO_PUBLIC_BASE_URL').rstrip('/') + path


def twiml_for_stream(call_id: str, nonce: str) -> str:
    from xml.sax.saxutils import escape
    stream_url = public_url('/twilio/media').replace('https://', 'wss://', 1)
    return (f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Connect><Stream url="{escape(stream_url)}">'
            f'<Parameter name="call_id" value="{escape(call_id)}"/>'
            f'<Parameter name="nonce" value="{escape(nonce)}"/>'
            f'</Stream></Connect><Hangup/></Response>')


def summarize_twilio_http_error(exc: requests.exceptions.HTTPError) -> str:
    """Diagnóstico breve sin mostrar teléfonos, tokens ni mensajes sin depurar del proveedor."""
    response = exc.response
    status = response.status_code if response is not None else None
    error_code = None
    if response is not None:
        try:
            payload = response.json()
            candidate = payload.get('code') if isinstance(payload, dict) else None
            if str(candidate).isdigit() and 10000 <= int(candidate) <= 99999:
                error_code = int(candidate)
        except (ValueError, TypeError):
            pass

    advice = {
        10001: 'Compruebe que la cuenta Twilio esté activa.',
        10002: 'La funcionalidad no está disponible para la cuenta Trial.',
        20003: 'Verifique Account SID y Auth Token del mismo proyecto.',
        21203: 'Revise la habilitación de llamadas internacionales.',
        21210: 'El número de origen no está verificado para esta cuenta.',
        21211: 'Twilio considera inválido el número de destino.',
        21212: 'Revise TWILIO_FROM_NUMBER y su autorización para llamadas salientes.',
        21214: 'Twilio no puede completar el enrutamiento hacia ese destino.',
        21215: 'Active República Dominicana en Voice Geographic Permissions si la cuenta lo permite.',
        21216: 'Twilio bloqueó la ruta o la llamada; revise los controles de la cuenta.',
        21217: 'Revise el número telefónico y su formato internacional.',
        21219: 'La cuenta requiere verificar previamente el número de destino.',
    }
    reason = advice.get(error_code)
    if not reason:
        if status == 401:
            reason = 'Revise la autenticación Twilio (Account SID y Auth Token).'
        elif status == 403:
            reason = 'Revise el estado y las restricciones de la cuenta Twilio.'
        else:
            reason = 'Revise el código en Twilio Console > Monitor > Debugger.'

    detail = f'HTTP {status}' if status is not None else 'HTTP desconocido'
    if error_code is not None:
        detail += f', código Twilio {error_code}'
    return f'Twilio rechazó la solicitud ({detail}). {reason} No reintente sin verificar el motivo.'


def refresh_call_status(call_id: str, *, transport=None) -> dict:
    """Consulta un Call SID específico sin originar llamadas ni alterar estados terminales.

    Ante fallo o respuesta incoherente nunca libera el bloqueo local.
    transport permite simular el GET en pruebas sin contactar Twilio.
    """
    current = get_call(call_id)
    if current is None:
        raise CallPolicyError('Llamada local no encontrada.')
    if current['status'] in TERMINAL or not current['call_sid']:
        return current
    sid = current['call_sid']
    account = key('TWILIO_ACCOUNT_SID')
    endpoint = f'https://api.twilio.com/2010-04-01/Accounts/{account}/Calls/{sid}.json'
    fetcher = transport if transport is not None else requests.get
    try:
        response = fetcher(endpoint, auth=(account, key('TWILIO_AUTH_TOKEN')), timeout=7)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get('sid') != sid:
            raise ValueError('Respuesta no corresponde a la llamada solicitada')
        remote_status = payload.get('status')
        if remote_status not in TWILIO_ACTIVE | TWILIO_TERMINAL:
            raise ValueError('Estado no reconocido por Vantra AI')
    except (requests.exceptions.RequestException, ValueError, TypeError, KeyError) as exc:
        raise CallPolicyError(
            'No se pudo verificar el estado en Twilio. Se mantiene el bloqueo por seguridad.'
        ) from exc
    update_call(call_id, remote_status, sid)
    return get_call(call_id)


def reconcile_active_calls(*, transport=None) -> bool:
    """Libera reservas SOLO si Twilio confirmó el estado terminal de cada SID.

    Una reserva sin SID puede ser una solicitud en vuelo o con timeout;
    permanece bloqueada para evitar duplicación accidental de llamadas.
    """
    for call in _active_calls():
        if not call['call_sid']:
            return False
        try:
            refreshed = refresh_call_status(call['id'], transport=transport)
        except CallPolicyError:
            return False
        if refreshed['status'] not in TERMINAL:
            return False
    return not _active_calls()


def start_test_call(phone: str, confirmed: bool, *, transport=None, status_transport=None) -> dict:
    """Realiza UNA llamada real únicamente tras lista positiva, opt-in y controles.

    transport se inyecta únicamente para pruebas sin acceso a Twilio.
    """
    number = _preflight(phone, confirmed)
    try:
        call_id, nonce = _reserve(number)
    except ActiveCallError:
        # transport=... es el modo de prueba con API de creación simulada:
        # no consultar Twilio real salvo que se inyecte también status_transport.
        if transport is not None and status_transport is None:
            raise
        if not reconcile_active_calls(transport=status_transport):
            raise ActiveCallError(
                'Existe otra llamada activa o no verificable en Twilio. '
                'Se mantiene el límite de una simultánea.'
            ) from None
        # Se reevalúan todos los controles dentro de una nueva transacción IMMEDIATE.
        # Otra solicitud concurrente puede haber reservado entretanto; se bloquea.
        call_id, nonce = _reserve(number)
    twiml = twiml_for_stream(call_id, nonce)
    sid = env('TWILIO_ACCOUNT_SID')
    endpoint = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json'
    form = {
        'To': number, 'From': env('TWILIO_FROM_NUMBER'), 'Twiml': twiml,
        'StatusCallback': public_url('/twilio/status') + '?call_id=' + call_id,
        'StatusCallbackMethod': 'POST',
        'StatusCallbackEvent': ['initiated', 'ringing', 'answered', 'completed'],
        'TimeLimit': '180',
    }
    sender = transport or requests.post
    try:
        response = sender(endpoint, data=form, auth=(sid, key('TWILIO_AUTH_TOKEN')), timeout=20)
        response.raise_for_status()
        try:
            result = response.json()
            returned_sid = result['sid']
            if not isinstance(returned_sid, str) or not CALL_SID.fullmatch(returned_sid):
                raise ValueError('SID inválido')
        except (ValueError, KeyError, TypeError) as exc:
            # Twilio respondió 2xx pero el cliente no puede identificar la llamada:
            # no desbloquear hasta una comprobación manual en Twilio Console.
            update_call(call_id, 'initiated')
            raise CallPolicyError(
                'Twilio respondió sin Call SID verificable. NO repita la llamada; '
                'revise Twilio Console antes de liberar la reserva.'
            ) from exc
        update_call(call_id, 'queued', returned_sid)
        return {'id': call_id, 'call_sid': returned_sid,
                'status': (get_call(call_id) or {}).get('status', 'queued'),
                'message': 'Solicitud de llamada enviada a Twilio; aún no confirma que haya contestado.'}
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        # Una solicitud interrumpida pudo haber sido aceptada por Twilio.
        update_call(call_id, 'initiated')
        raise CallPolicyError(
            'No hubo confirmación del intento de llamada. NO repita: '
            'revise primero el historial en Twilio Console.'
        ) from exc
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code >= 500:
            update_call(call_id, 'initiated')  # respuesta ambigua del servidor
        else:
            update_call(call_id, 'error')
        raise
    except Exception:
        update_call(call_id, 'initiated')  # falla inesperada con resultado incierto
        raise


def stop_test_call(call_id: str, *, transport=None) -> dict:
    info = get_call(call_id)
    if not info:
        raise CallPolicyError('Llamada no encontrada')
    if info['status'] in TERMINAL:
        return {'status': info['status'], 'id': call_id}
    if not info['call_sid']:
        update_call(call_id, 'canceled')
        return {'status': 'canceled', 'id': call_id}
    sid = env('TWILIO_ACCOUNT_SID')
    endpoint = (f'https://api.twilio.com/2010-04-01/Accounts/{sid}'
                f'/Calls/{info["call_sid"]}.json')
    sender = transport or requests.post
    response = sender(endpoint, data={'Status': 'completed'},
                      auth=(sid, key('TWILIO_AUTH_TOKEN')), timeout=20)
    response.raise_for_status()
    update_call(call_id, 'completed')
    return {'status': 'completed', 'id': call_id}
