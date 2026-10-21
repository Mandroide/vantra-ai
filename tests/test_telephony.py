"""No se llama a números reales: pruebas unitarias con Twilio y TTS simulados."""
from __future__ import annotations
import asyncio
from contextlib import closing
import base64
import hashlib
import hmac
import json
import re
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

import src.telephony as phone
import src.telephony_server as server

SID = 'CA' + '1' * 32
ACCOUNT = 'AC' + '2' * 32
ALLOW = '+18091234567'


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setattr(phone, 'DB', tmp_path / 'vantra_calls.sqlite3')
    variables = {
        'VANTRA_MODE': 'LIVE', 'TWILIO_CALLS_ENABLED': 'true',
        'TWILIO_ACCOUNT_SID': ACCOUNT, 'TWILIO_AUTH_TOKEN': 'test-only-auth-token',
        'TWILIO_FROM_NUMBER': '+15551234567',
        'TWILIO_PUBLIC_BASE_URL': 'https://voice-test.example.com',
        'TWILIO_TEST_NUMBERS': ALLOW,
        'DEEPGRAM_API_KEY': 'fake', 'AZURE_SPEECH_KEY': 'fake',
        'AZURE_SPEECH_REGION': 'eastus', 'ANTHROPIC_API_KEY': 'fake',
    }
    for k, v in variables.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(phone, '_allowed_now', lambda: True)
    return variables


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {'sid': SID}


def fake_post(url, **kwargs):
    assert url.startswith('https://api.twilio.com/')
    assert kwargs['auth'] == (ACCOUNT, 'test-only-auth-token')
    assert kwargs['data']['To'] == ALLOW
    assert kwargs['data']['TimeLimit'] == '180'
    root = ElementTree.fromstring(kwargs['data']['Twiml'])
    stream = root.find('./Connect/Stream')
    assert stream.attrib['url'] == 'wss://voice-test.example.com/twilio/media'
    assert root.find('./Hangup') is not None
    assert {'call_id', 'nonce'} == {e.attrib['name'] for e in stream.findall('Parameter')}
    return FakeResponse()


@pytest.mark.parametrize('number', [
    '+1809123456', '+180912345678', '+12025550123', '+18291234A67',
    '8091234567', '+1849000000\n0', '+18091234567;rm -rf /',
])
def test_only_explicit_do_e164(number):
    with pytest.raises(phone.CallPolicyError):
        phone.normalize_do_phone(number)


@pytest.mark.parametrize('number', ['+18091234567', '+18291234567', '+18491234567'])
def test_valid_dominican_prefixes(number):
    assert phone.normalize_do_phone(number) == number


def test_call_requires_consent_allowlist_and_switch(configured, monkeypatch):
    with pytest.raises(phone.CallPolicyError, match='consentimiento'):
        phone.start_test_call(ALLOW, confirmed=False, transport=fake_post)
    with pytest.raises(phone.CallPolicyError, match='no autorizado'):
        phone.start_test_call('+18291234567', confirmed=True, transport=fake_post)
    monkeypatch.setenv('TWILIO_CALLS_ENABLED', 'false')
    with pytest.raises(phone.CallPolicyError, match='desactivadas'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_call_create_and_hangup_offline(configured):
    created = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    assert created['call_sid'] == SID
    assert created['status'] == 'queued'
    assert phone.get_call(created['id'])['status'] == 'queued'
    assert ALLOW not in phone.DB.read_bytes().decode('utf-8', errors='ignore')
    with pytest.raises(phone.CallPolicyError, match='otra llamada'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)

    def fake_stop(url, **kwargs):
        assert url.endswith(SID + '.json')
        assert kwargs['data']['Status'] == 'completed'
        return FakeResponse()

    stopped = phone.stop_test_call(created['id'], transport=fake_stop)
    assert stopped['status'] == 'completed'
    assert phone.get_call(created['id'])['status'] == 'completed'


def test_claim_stream_nonce_and_dnc(configured):
    created = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    with closing(phone._conn()) as db:
        nonce = db.execute('SELECT nonce FROM phone_calls WHERE id=?', (created['id'],)).fetchone()[0]
    assert not phone.claim_stream(created['id'], 'bad', SID)
    assert phone.claim_stream(created['id'], nonce, SID)
    phone.mark_do_not_call(created['id'])
    phone.update_call(created['id'], 'completed')
    with pytest.raises(phone.CallPolicyError, match='DNC'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_status_callback_signature_required(configured):
    client = TestClient(server.app)
    data = {'CallSid': SID, 'CallStatus': 'completed'}
    response = client.post('/twilio/status', data=data)
    assert response.status_code == 403
    response = client.post('/twilio/status', data=data, headers={'X-Twilio-Signature': 'invalid'})
    assert response.status_code == 403
    sig = phone.twilio_valid_signature
    assert not sig(phone.public_url('/twilio/status'), 'random', data)
    source = phone.public_url('/twilio/status') + ''.join(k + v for k, v in sorted(data.items()))
    signature = base64.b64encode(hmac.new(b'test-only-auth-token', source.encode(), hashlib.sha1).digest()).decode()
    assert sig(phone.public_url('/twilio/status'), signature, data)
    valid = client.post('/twilio/status', data=data, headers={'X-Twilio-Signature': signature})
    assert valid.status_code == 200


def test_stream_signature_rejects_missing(configured):
    with TestClient(server.app) as c:
        with pytest.raises(Exception):
            with c.websocket_connect('/twilio/media') as ws:
                ws.receive_json()


def test_raw_mulaw_sent_without_container(configured, monkeypatch):
    class WebSocketMock:
        def __init__(self): self.messages = []

        async def send_json(self, item): self.messages.append(item)

    monkeypatch.setattr(server, 'azure_mulaw_8k', lambda text: b'\xff' * 3200)
    ws = WebSocketMock()
    bridge = server.CallBridge(ws, 'a' * 32, SID, 'MZ' + '9' * 32)
    asyncio.run(bridge._send_audio('Hola'))
    medias = [v for v in ws.messages if v['event'] == 'media']
    assert len(medias) == 2
    assert b''.join(base64.b64decode(p['media']['payload']) for p in medias) == b'\xff' * 3200
    assert ws.messages[-1]['event'] == 'mark'


def test_deepgram_format(configured):
    url = server.deepgram_url()
    assert 'encoding=mulaw' in url and 'sample_rate=8000' in url and 'language=es' in url


def test_websocket_can_claim_valid_session(configured, monkeypatch):
    created = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    with closing(phone._conn()) as db:
        nonce = db.execute('SELECT nonce FROM phone_calls WHERE id=?', (created['id'],)).fetchone()[0]

    async def fake_bridge(self):
        await self.websocket.send_json({'test': 'accepted'})

    monkeypatch.setattr(server.CallBridge, 'run', fake_bridge)
    url = phone.public_url('/twilio/media').replace('https://', 'wss://', 1)
    source = hmac.new(b'test-only-auth-token', url.encode(), hashlib.sha1).digest()
    signature = base64.b64encode(source).decode()
    with TestClient(server.app) as client:
        with client.websocket_connect('/twilio/media', headers={'X-Twilio-Signature': signature}) as ws:
            ws.send_json({'event': 'connected'})
            ws.send_json({'event': 'start', 'start': {
                'callSid': SID, 'streamSid': 'MZ' + '9' * 32,
                'customParameters': {'call_id': created['id'], 'nonce': nonce}}})
            assert ws.receive_json() == {'test': 'accepted'}


def test_manual_dnc_without_dialing(configured):
    phone.add_do_not_call(ALLOW)
    with pytest.raises(phone.CallPolicyError, match='DNC'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_dominican_local_schedule_blocks(configured, monkeypatch):
    monkeypatch.setattr(phone, '_allowed_now', lambda: False)
    with pytest.raises(phone.CallPolicyError, match='Fuera del horario'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_ambiguous_twilio_timeout_fails_closed(configured):
    import requests
    def uncertain(url, **kwargs):
        raise requests.exceptions.ReadTimeout('simulated timeout')

    with pytest.raises(phone.CallPolicyError, match='NO repita'):
        phone.start_test_call(ALLOW, confirmed=True, transport=uncertain)
    with pytest.raises(phone.CallPolicyError, match='otra llamada'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_twilio_http_error_exposes_safe_code(configured):
    import requests
    response = requests.Response()
    response.status_code = 400
    response._content = json.dumps({
        'code': 21215,
        'message': 'Cannot call +18091234567; token=top-secret',
    }).encode()
    error = requests.exceptions.HTTPError('400 Client Error', response=response)
    description = phone.summarize_twilio_http_error(error)
    assert 'HTTP 400' in description
    assert '21215' in description
    assert 'República Dominicana' in description
    assert '+18091234567' not in description
    assert 'top-secret' not in description


def test_twilio_trial_error_hint(configured):
    import requests
    response = requests.Response()
    response.status_code = 400
    response._content = b'{"code": 10002, "message": "Feature not available"}'
    error = requests.exceptions.HTTPError('bad request', response=response)
    assert 'Trial' in phone.summarize_twilio_http_error(error)


def test_twilio_http_error_without_json_or_response(configured):
    import requests
    response = requests.Response()
    response.status_code = 401
    response._content = b'<html>Denied</html>'
    error = requests.exceptions.HTTPError('Denied', response=response)
    msg = phone.summarize_twilio_http_error(error)
    assert 'HTTP 401' in msg
    assert 'autenticación' in msg
    assert 'Denied' not in msg
    no_response = requests.exceptions.HTTPError('denied token abc')
    msg = phone.summarize_twilio_http_error(no_response)
    assert 'desconocido' in msg
    assert 'abc' not in msg
