"""Opera conectividad pública del piloto, sin iniciar llamadas ni exponer claves.

Ejemplos:
  python scripts/connectivity.py check --provider ngrok
  python scripts/connectivity.py up --provider ngrok
  python scripts/connectivity.py probe
  python scripts/connectivity.py down --provider ngrok
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = {
    'ngrok': 'compose.ngrok.yaml',
    'cloudflare': 'compose.cloudflare.yaml',
    'direct': 'compose.direct.yaml',
}


def read_settings(path: Path | None = None) -> dict[str, str]:
    """Lee .env sin mostrar secretos; entorno de shell prevalece como en Compose."""
    from dotenv import dotenv_values
    data = {k: v or '' for k, v in dotenv_values(path or ROOT / '.env').items()}
    data.update(os.environ)
    return data


def validate_settings(values: dict[str, str], provider: str) -> list[str]:
    problems: list[str] = []
    if provider not in OVERLAYS:
        return ['Proveedor desconocido (ngrok, cloudflare o direct).']
    base = (values.get('TWILIO_PUBLIC_BASE_URL') or '').strip()
    try:
        parsed = urlsplit(base)
        public_port = parsed.port
    except ValueError:
        return ['TWILIO_PUBLIC_BASE_URL: URL o puerto inválidos.']
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment or parsed.path not in ('', '/')
        or public_port is not None or not re.fullmatch(r'[a-zA-Z0-9.-]+', parsed.hostname)
        or '.' not in parsed.hostname or parsed.hostname in ('localhost', '127.0.0.1')
        or any(x in parsed.hostname for x in ('example.com', 'tudominio.com'))):
        problems.append('TWILIO_PUBLIC_BASE_URL: debe ser HTTPS público estable, sin puerto ni ruta.')
    if provider == 'ngrok' and not values.get('NGROK_AUTHTOKEN'):
        problems.append('Falta NGROK_AUTHTOKEN.')
    if provider == 'cloudflare':
        if not values.get('CLOUDFLARE_TUNNEL_TOKEN'):
            problems.append('Falta CLOUDFLARE_TUNNEL_TOKEN.')
        if parsed.hostname and parsed.hostname.endswith('trycloudflare.com'):
            problems.append('Cloudflare Quick Tunnel no da URL estable para la telefonía: use dominio gestionado.')
    if provider == 'direct':
        hostname = (values.get('VANTRA_PUBLIC_HOST') or '').strip().lower()
        if hostname != (parsed.hostname or '').lower():
            problems.append('VANTRA_PUBLIC_HOST debe coincidir con la URL pública sin https://.')
        email = values.get('CADDY_EMAIL', '')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            problems.append('CADDY_EMAIL: indique correo válido para TLS automático.')
    return problems


def compose_cmd(provider: str, verb: str) -> list[str]:
    if provider not in OVERLAYS:
        raise ValueError('Proveedor de conectividad desconocido')
    cmd = ['docker', 'compose', '-f', 'compose.yaml', '-f', OVERLAYS[provider]]
    if verb == 'up':
        return cmd + ['up', '-d', '--build', '--remove-orphans']
    if verb == 'down':
        return cmd + ['down', '--remove-orphans']
    if verb == 'status':
        return cmd + ['ps']
    raise ValueError('Operación no admitida')


def probe_public(base: str, *, timeout: float = 10) -> dict[str, str]:
    """Verifica HTTPS y handshake WSS sin credenciales ni inicio de llamadas.

    Un rechazo 403/401 del WebSocket sin firma es *esperado* y demuestra que
    llegó al endpoint que exige autenticación (no confirma una llamada LIVE).
    """
    from websockets.sync.client import connect
    from websockets.exceptions import InvalidStatus
    url = base.rstrip('/')
    result: dict[str, str] = {}
    with urlopen(Request(url + '/healthz', headers={'User-Agent': 'vantra-connectivity-check'}),
                 timeout=timeout) as response:
        payload = json.loads(response.read(2048))
        if response.status != 200 or payload.get('ok') is not True:
            raise RuntimeError('HTTP healthz no devolvió ok=true')
        result['https'] = 'healthz=200'
    ws_url = 'wss://' + urlsplit(url).netloc + '/twilio/media'
    try:
        with connect(ws_url, open_timeout=timeout):
            raise RuntimeError('Inseguro: WebSocket aceptó conexión sin firma Twilio')
    except InvalidStatus as exc:
        status = exc.response.status_code
        if status not in (401, 403):
            raise RuntimeError(f'WebSocket dio HTTP {status}; se esperaba 403') from exc
        result['websocket'] = f'rechazo seguro HTTP {status}'
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Conectividad segura de Vantra AI')
    parser.add_argument('action', choices=('check', 'up', 'down', 'status', 'probe'))
    parser.add_argument('--provider', choices=OVERLAYS)
    args = parser.parse_args(argv)
    values = read_settings()
    provider = args.provider or values.get('CONNECTIVITY_PROVIDER') or 'ngrok'
    if args.action == 'probe':
        issues = validate_settings(values, provider)
        if issues:
            for item in issues:
                print('ERROR:', item, file=sys.stderr)
            return 2
        try:
            print(json.dumps(probe_public(values['TWILIO_PUBLIC_BASE_URL']), ensure_ascii=False))
        except Exception as exc:
            print('Error de conectividad:', type(exc).__name__, str(exc), file=sys.stderr)
            return 1
        return 0
    if args.action in ('up', 'check'):
        issues = validate_settings(values, provider)
        if issues:
            for item in issues:
                print('ERROR:', item, file=sys.stderr)
            return 2
        print(f'Proveedor: {provider}; destino público: {values["TWILIO_PUBLIC_BASE_URL"]}')
        if values.get('TWILIO_CALLS_ENABLED', 'false').lower() != 'true':
            print('Las llamadas siguen desactivadas (TWILIO_CALLS_ENABLED=false).')
    if args.action == 'check':
        print('Configuración de conectividad coherente (NO verifica acceso externo).')
        return 0
    cmd = compose_cmd(provider, args.action)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
