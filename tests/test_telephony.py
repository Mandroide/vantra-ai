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


def test_after_hours_requires_explicit_flag(configured, monkeypatch):
    monkeypatch.setattr(phone, '_allowed_now', lambda: False)
    monkeypatch.setenv('TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS', 'false')
    with pytest.raises(phone.CallPolicyError, match='Fuera del horario'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_after_hours_pilot_allows_only_opted_in_number(configured, monkeypatch):
    monkeypatch.setattr(phone, '_allowed_now', lambda: False)
    monkeypatch.setenv('TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS', 'true')
    with pytest.raises(phone.CallPolicyError, match='consentimiento'):
        phone.start_test_call(ALLOW, confirmed=False, transport=fake_post)
    with pytest.raises(phone.CallPolicyError, match='no autorizado'):
        phone.start_test_call('+18291234567', confirmed=True, transport=fake_post)
    created = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    assert created['status'] == 'queued'
    with pytest.raises(phone.CallPolicyError, match='otra llamada'):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_after_hours_dnc_still_blocks(configured, monkeypatch):
    monkeypatch.setattr(phone, '_allowed_now', lambda: False)
    monkeypatch.setenv('TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS', 'true')
    phone.add_do_not_call(ALLOW)
    with pytest.raises(phone.CallPolicyError, match='DNC'):
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


class FakeCallLookup:
    """Respuesta mínima de consulta GET /Calls/{sid}.json (sin contactar Twilio)."""

    def __init__(self, status: str, sid: str = SID, http_status: int = 200):
        self.status = status
        self.sid = sid
        self.status_code = http_status

    def raise_for_status(self):
        if self.status_code != 200:
            import requests
            raise requests.exceptions.HTTPError('bad response')

    def json(self):
        return {'status': self.status, 'sid': self.sid}


def test_reconcile_terminal_releases_slot_without_new_live_get(configured, monkeypatch):
    first = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    queries = []

    def fetch(url, **kwargs):
        queries.append(url)
        assert url.endswith('/Calls/' + SID + '.json')
        assert kwargs['auth'] == (ACCOUNT, 'test-only-auth-token')
        return FakeCallLookup('completed')

    assert phone.reconcile_active_calls(transport=fetch)
    assert len(queries) == 1
    assert phone.get_call(first['id'])['status'] == 'completed'
    # Una nueva reserva es segura sin consultar a Twilio de nuevo.
    monkeypatch.setattr(FakeResponse, 'json', lambda self: {'sid': 'CA' + '4' * 32})
    next_call = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    assert next_call['status'] == 'queued'


def test_start_call_auto_reconciles_then_reserves(configured, monkeypatch):
    previous = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    lookups = []

    def fake_lookup(url, **kwargs):
        lookups.append(url)
        return FakeCallLookup('busy')

    monkeypatch.setattr(FakeResponse, 'json', lambda self: {'sid': 'CA' + '5' * 32})
    replacement = phone.start_test_call(
        ALLOW, confirmed=True, transport=fake_post, status_transport=fake_lookup
    )
    assert len(lookups) == 1
    assert phone.get_call(previous['id'])['status'] == 'busy'
    assert replacement['status'] == 'queued'
    assert replacement['id'] != previous['id']


@pytest.mark.parametrize('remote_status', ['queued', 'initiated', 'ringing', 'in-progress'])
def test_reconcile_never_releases_remote_active(configured, remote_status):
    active = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    with pytest.raises(phone.ActiveCallError, match='no verificable'):
        phone.start_test_call(
            ALLOW, confirmed=True, transport=fake_post,
            status_transport=lambda *a, **k: FakeCallLookup(remote_status),
        )
    assert phone.get_call(active['id'])['status'] not in phone.TERMINAL


@pytest.mark.parametrize('problem', ['timeout', '401', 'unknown', 'sid_mismatch'])
def test_reconcile_fails_closed_when_lookup_is_unreliable(configured, problem):
    import requests
    active = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)

    def broken_lookup(url, **kwargs):
        if problem == 'timeout':
            raise requests.exceptions.ReadTimeout('secret-sensitive')
        if problem == '401':
            return FakeCallLookup('completed', http_status=401)
        if problem == 'unknown':
            return FakeCallLookup('deleting')
        return FakeCallLookup('completed', sid='CA' + 'b' * 32)

    with pytest.raises(phone.ActiveCallError):
        phone.start_test_call(
            ALLOW, confirmed=True, transport=fake_post,
            status_transport=broken_lookup,
        )
    assert phone.get_call(active['id'])['status'] == 'queued'


def test_reserved_without_sid_requires_manual_confirmation(configured):
    call_id, _ = phone._reserve(ALLOW)
    assert phone.get_call(call_id)['status'] == 'reserved'
    assert not phone.reconcile_active_calls(transport=lambda *a, **k: pytest.fail('No GET'))
    with pytest.raises(phone.ActiveCallError):
        phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)


def test_read_only_refresh_verifies_terminal_and_does_not_start_new_call(configured):
    first = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    result = phone.refresh_call_status(
        first['id'], transport=lambda *a, **k: FakeCallLookup('no-answer')
    )
    assert result['status'] == 'no-answer'
    # Una vez terminal, no consulta Twilio nuevamente.
    result = phone.refresh_call_status(
        first['id'], transport=lambda *a, **k: pytest.fail('No further requests')
    )
    assert result['status'] == 'no-answer'


def test_signed_early_webhook_before_call_sid_is_saved(configured):
    from urllib.parse import urlparse

    def respond_after_callback(url, **kwargs):
        callback_url = kwargs['data']['StatusCallback']
        parsed = urlparse(callback_url)
        assert parsed.query.startswith('call_id=')
        fields = {'CallSid': SID, 'CallStatus': 'completed'}
        contents = callback_url + ''.join(k + v for k, v in sorted(fields.items()))
        signature = base64.b64encode(hmac.new(
            b'test-only-auth-token', contents.encode(), hashlib.sha1
        ).digest()).decode()
        with TestClient(server.app) as client:
            response = client.post(
                parsed.path + '?' + parsed.query, data=fields,
                headers={'X-Twilio-Signature': signature},
            )
            assert response.status_code == 200
        return FakeResponse()

    first = phone.start_test_call(ALLOW, confirmed=True, transport=respond_after_callback)
    assert first['status'] == 'completed'
    assert phone.get_call(first['id'])['call_sid'] == SID
    assert phone.get_call(first['id'])['status'] == 'completed'


def test_signature_requires_query_and_mismatched_sid_does_not_replace(configured):
    first = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    path = '/twilio/status?call_id=' + first['id']
    params = {'CallSid': 'CA' + '3' * 32, 'CallStatus': 'completed'}
    url = phone.public_url(path)
    content = url + ''.join(k + v for k, v in sorted(params.items()))
    sig = base64.b64encode(hmac.new(
        b'test-only-auth-token', content.encode(), hashlib.sha1
    ).digest()).decode()
    with TestClient(server.app) as client:
        assert client.post(path, data=params).status_code == 403
        assert client.post('/twilio/status', data=params,
                           headers={'X-Twilio-Signature': sig}).status_code == 403
        assert client.post(path, data=params,
                           headers={'X-Twilio-Signature': sig}).status_code == 409
    assert phone.get_call(first['id'])['status'] == 'queued'
    assert phone.get_call(first['id'])['call_sid'] == SID


def test_ambiguous_connection_error_does_not_unlock_call(configured):
    import requests

    def connection_dropped(url, **kwargs):
        raise requests.exceptions.ConnectionError('simulated network dropped')

    with pytest.raises(phone.CallPolicyError, match='NO repita'):
        phone.start_test_call(ALLOW, confirmed=True, transport=connection_dropped)
    assert phone._active_calls()[0]['call_sid'] is None
    assert phone._active_calls()[0]['status'] == 'initiated'


def test_successful_response_without_sid_keeps_reservation(configured):
    class MissingSid:
        def raise_for_status(self):
            pass

        def json(self):
            return {'status': 'queued'}

    with pytest.raises(phone.CallPolicyError, match='SID verificable'):
        phone.start_test_call(ALLOW, confirmed=True,
                              transport=lambda *args, **kwargs: MissingSid())
    assert phone._active_calls()[0]['status'] == 'initiated'


def test_late_callback_does_not_resurrect_completed_call(configured):
    item = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    phone.update_call(item['id'], 'completed')
    phone.update_call(item['id'], 'ringing', SID)
    assert phone.get_call(item['id'])['status'] == 'completed'


def test_admin_reconcile_cli_only_reads_by_default(configured, monkeypatch, capsys):
    from scripts import reconcile_calls

    item = phone.start_test_call(ALLOW, confirmed=True, transport=fake_post)
    monkeypatch.setattr('sys.argv', ['reconcile_calls'])
    assert reconcile_calls.main() == 0
    result = capsys.readouterr().out
    assert item['id'] in result
    assert 'queued' in result
    assert ALLOW not in result
    assert phone.get_call(item['id'])['status'] == 'queued'
