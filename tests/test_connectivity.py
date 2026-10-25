"""Pruebas offline: configuración, despliegue opcional y webhook seguro."""
import base64
import hashlib
import hmac
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from scripts.connectivity import OVERLAYS, compose_cmd, validate_settings
from src.telephony_server import app
import src.telephony as tel

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = 'https://voice.pruebas.com'


def test_provider_modes_have_overlays_and_single_base():
    base = yaml.safe_load((ROOT / 'compose.yaml').read_text())
    assert {'vantra', 'twilio-webhook'} <= set(base['services'])
    assert base['services']['vantra']['ports'][0].startswith('127.0.0.1:')
    assert base['services']['twilio-webhook']['ports'][0].startswith('127.0.0.1:')
    for provider, filename in OVERLAYS.items():
        overlay = yaml.safe_load((ROOT / filename).read_text())
        assert len(overlay['services']) == 1
        assert (ROOT / filename).exists()
        assert compose_cmd(provider, 'up')[:4] == ['docker', 'compose', '-f', 'compose.yaml']
        assert '--remove-orphans' in compose_cmd(provider, 'up')
    assert 'twilio-webhook:8000' in (ROOT / 'infra/Caddyfile').read_text()
    for svc in ('vantra', 'twilio-webhook'):
        assert 'healthcheck' in base['services'][svc]
    assert 'vantra:7860' not in (ROOT / 'infra/Caddyfile').read_text()


@pytest.mark.parametrize('provider,expected', [
    ('ngrok', []),
    ('cloudflare', []),
    ('direct', []),
])
def test_each_provider_config_valid(provider, expected):
    values = {
        'TWILIO_PUBLIC_BASE_URL': PUBLIC,
        'NGROK_AUTHTOKEN': 'test-token',
        'CLOUDFLARE_TUNNEL_TOKEN': 'test-cloudflare-token',
        'VANTRA_PUBLIC_HOST': 'voice.pruebas.com',
        'CADDY_EMAIL': 'sistemas@pruebas.com',
    }
    assert validate_settings(values, provider) == expected


@pytest.mark.parametrize('base', [
    'http://voice.pruebas.com',
    'https://127.0.0.1:8000',
    'https://voice.pruebas.com/twilio/status',
    'https://voice.pruebas.com:443',
    'https://voice.pruebas.com?x=1',
    'https://ejemplo.tudominio.com',
])
def test_bad_base_rejected(base):
    issues = validate_settings({'TWILIO_PUBLIC_BASE_URL': base, 'NGROK_AUTHTOKEN': 'test'}, 'ngrok')
    assert issues, base


def test_missing_provider_token_and_host_mismatch():
    assert any('CLOUDFLARE' in problem for problem in validate_settings(
        {'TWILIO_PUBLIC_BASE_URL': PUBLIC}, 'cloudflare'))
    assert any('coincidir' in problem for problem in validate_settings(
        {'TWILIO_PUBLIC_BASE_URL': PUBLIC, 'VANTRA_PUBLIC_HOST': 'otro.com',
         'CADDY_EMAIL': 'ops@pruebas.com'}, 'direct'))
    assert validate_settings({'TWILIO_PUBLIC_BASE_URL': 'https://algo.trycloudflare.com',
                              'CLOUDFLARE_TUNNEL_TOKEN': 'test'}, 'cloudflare')


def test_endpoints_and_signature_do_not_require_tunnel_type(monkeypatch):
    monkeypatch.setenv('TWILIO_PUBLIC_BASE_URL', PUBLIC)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'token-de-prueba')
    monkeypatch.setenv('TWILIO_CALLS_ENABLED', 'true')
    with TestClient(app) as client:
        health = client.get('/healthz')
        assert health.status_code == 200 and health.json()['ok'] is True
        ready = client.get('/readyz')
        assert ready.status_code == 200
        assert 'token-de-prueba' not in ready.text
        assert client.post('/twilio/status', data={'CallSid': 'CA'+'a'*32}).status_code == 403
        payload = {'CallSid': 'CA'+'a'*32, 'CallStatus': 'queued'}
        url = PUBLIC+'/twilio/status'
        signed = url + ''.join(k+v for k,v in sorted(payload.items()))
        signature = base64.b64encode(hmac.new(b'token-de-prueba', signed.encode(), hashlib.sha1).digest()).decode()
        assert tel.twilio_valid_signature(url, signature, payload)
        assert client.post('/twilio/status', data=payload, headers={'X-Twilio-Signature':signature}).status_code == 200


def test_no_secret_print_in_cli_source():
    source = (ROOT / 'scripts/connectivity.py').read_text()
    assert 'print(values)' not in source
    assert 'print(data)' not in source
    assert 'read_settings' in source


def test_daily_limit_is_preserved(monkeypatch):
    monkeypatch.setenv('TWILIO_DAILY_CALL_LIMIT', '8')
    assert tel._daily_call_limit() == 8
    for invalid in ('0', '11', 'abc'):
        monkeypatch.setenv('TWILIO_DAILY_CALL_LIMIT', invalid)
        with pytest.raises(tel.CallPolicyError):
            tel._daily_call_limit()
