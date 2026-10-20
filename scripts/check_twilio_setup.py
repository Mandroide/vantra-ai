"""Verifica variables de telefonía de modo LOCAL, jamás realiza llamadas."""
from pathlib import Path
from urllib.parse import urlparse
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import env  # noqa: E402


def main() -> int:
    checks = {
        'modo LIVE': env('VANTRA_MODE').upper() == 'LIVE',
        'TWILIO_CALLS_ENABLED=true': env('TWILIO_CALLS_ENABLED').lower() == 'true',
        'Twilio Account SID': bool(re.fullmatch('AC[a-fA-F0-9]{32}', env('TWILIO_ACCOUNT_SID'))),
        'Twilio Auth Token': bool(env('TWILIO_AUTH_TOKEN')),
        'Número de origen': bool(re.fullmatch(r'\+[1-9]\d{6,14}', env('TWILIO_FROM_NUMBER'))),
        'URL HTTPS pública': urlparse(env('TWILIO_PUBLIC_BASE_URL')).scheme == 'https',
        'Allowlist de destino': bool(env('TWILIO_TEST_NUMBERS')),
        'Deepgram': bool(env('DEEPGRAM_API_KEY')),
        'Anthropic': bool(env('ANTHROPIC_API_KEY')),
        'Azure': bool(env('AZURE_SPEECH_KEY') and env('AZURE_SPEECH_REGION')),
    }
    for item, ok in checks.items():
        print(f"{'OK' if ok else 'FALTA'}  {item}")
    print('No se hizo ninguna llamada ni se verificaron créditos o permisos con Twilio.')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
