"""Pruebas de seguridad offline sobre llamadas y NLU compartido."""
import asyncio
from contextlib import closing
import sqlite3

import pytest

from src.critical_policy import consent_accepted, critical_intent
import src.telephony as tel
import src.telephony_server as voice
import src.observability as metrics
from scripts.evaluate_live_voice import evaluate_rows

PHONE = '+18091234567'


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(tel, 'DB', tmp_path / 'pilot.sqlite3')
    monkeypatch.setattr(metrics, 'DB', tmp_path / 'pilot.sqlite3')
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'legacy-auth-token-for-only-offline-tests')
    monkeypatch.setenv('VANTRA_PHONE_HASH_KEY', 'new-stable-hash-key-for-tests-' + 'Y' * 40)
    monkeypatch.setenv('VANTRA_MODE', 'LIVE')
    monkeypatch.setenv('TWILIO_CALLS_ENABLED', 'true')
    monkeypatch.setenv('TWILIO_TEST_NUMBERS', PHONE)
    monkeypatch.setenv('TWILIO_PUBLIC_BASE_URL', 'https://voice.example.com')
    monkeypatch.setenv('TWILIO_ACCOUNT_SID', 'AC' + '2' * 32)
    monkeypatch.setenv('TWILIO_FROM_NUMBER', '+15551234567')
    for v in ('DEEPGRAM_API_KEY', 'ANTHROPIC_API_KEY', 'AZURE_SPEECH_KEY'):
        monkeypatch.setenv(v, 'dummy')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'eastus')
    monkeypatch.setattr(tel, '_allowed_now', lambda: True)
    return tmp_path


@pytest.mark.parametrize('phrase', [
    'Borre mi número de sus contactos', 'Quítenme de las campañas',
    'Bórrenme de esa lista, no me llamen más', 'No me vuelvan a contactar',
])
def test_phone_and_chat_share_dnc_intent(phrase):
    assert critical_intent(phrase) == 'dnc'


def test_critical_priorities():
    assert critical_intent('No me grabes') == 'consent_denied'
    assert critical_intent('Me salió un cargo raro que yo no hice') == 'fraud'
    assert not consent_accepted('silencio')
    assert not consent_accepted('Sí pero no me llamen más')
    assert consent_accepted('Sí, acepto')


def test_hash_independent_of_twilio_token(isolated, monkeypatch):
    tel.add_do_not_call(PHONE)
    first = tel._phone_hash(PHONE)
    assert first.startswith('v2:')
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'rotated-auth-token')
    assert tel._phone_hash(PHONE) == first
    with pytest.raises(tel.CallPolicyError, match='DNC'):
        tel._reserve(PHONE)


def test_missing_hash_key_blocks_real_calls(isolated, monkeypatch):
    monkeypatch.delenv('VANTRA_PHONE_HASH_KEY')
    with pytest.raises(tel.CallPolicyError, match='VANTRA_PHONE_HASH_KEY'):
        tel._preflight(PHONE, True)


def test_legacy_dnc_blocks_until_migrated(isolated, monkeypatch):
    old_token = 'legacy-auth-token-for-only-offline-tests'
    with closing(tel._conn()) as c:
        c.execute('INSERT INTO phone_dnc VALUES (?,?)', (tel._legacy_phone_hash(PHONE, old_token), 100))
    with pytest.raises(tel.CallPolicyError, match='heredadas'):
        tel._reserve('+18095550123')
    result = tel.migrate_legacy_dnc([PHONE], old_token)
    assert result == {'migrated': 1, 'unresolved_legacy_dnc': 0}
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'new-token')
    with pytest.raises(tel.CallPolicyError, match='DNC'):
        tel._reserve(PHONE)


def test_unknown_legacy_dnc_never_discarded(isolated):
    with closing(tel._conn()) as c:
        c.execute('INSERT INTO phone_dnc VALUES (?,?)', ('deadbeef' * 8, 100))
    assert tel.migrate_legacy_dnc([PHONE], 'legacy-auth-token-for-only-offline-tests')['unresolved_legacy_dnc'] == 1
    with pytest.raises(tel.CallPolicyError, match='heredadas'):
        tel._reserve(PHONE)


def test_telemetry_never_accepts_free_text(isolated):
    call_id = 'a' * 32
    assert not metrics.record_call_event(call_id, 'tts', 'mi clave es secreta')
    assert not metrics.record_call_event(call_id, 'hack', 'ok')
    assert metrics.record_call_event(call_id, 'tts', 'ok', 120)
    assert metrics.record_call_event(call_id, 'agent', 'ok', 420)
    overview = metrics.call_telemetry_summary()
    assert overview['events'] == 2
    assert overview['stages']['tts']['p50_ms'] == 120
    raw = (isolated / 'pilot.sqlite3').read_bytes()
    assert b'mi clave' not in raw and PHONE.encode() not in raw


async def drive(bridge, phrase):
    await bridge.handle_transcription(phrase)


def test_voice_enforces_consent_and_optout(isolated, monkeypatch):
    class FakeSocket:
        pass

    bridge = voice.CallBridge(FakeSocket(), 'a' * 32, 'CA' + '1' * 32, 'MZ' + '9' * 32)
    output = []

    async def fake_send(text, *, goodbye=False):
        output.append((text, goodbye))

    monkeypatch.setattr(bridge, '_send_audio', fake_send)

    def forbidden(*args, **kwargs):
        pytest.fail('No se debe consultar Claude ni herramientas para consentimiento pendiente')

    monkeypatch.setattr(voice, 'respond', forbidden)
    asyncio.run(drive(bridge, 'me puede hablar de préstamos'))
    assert output[-1][1] is True and not bridge.consent_accepted
    assert not bridge.utterances
    output.clear()
    asyncio.run(drive(bridge, 'Borre mi número de sus contactos'))
    assert output[-1][1] is True
    assert tel.legacy_dnc_count() == 0
    with closing(tel._conn()) as c:
        assert c.execute('SELECT count(*) FROM phone_dnc').fetchone()[0] == 0  # id no existe


def test_voice_optout_persisted_for_real_call(isolated, monkeypatch):
    call_id, nonce = tel._reserve(PHONE)
    bridge = voice.CallBridge(object(), call_id, 'CA' + '1' * 32, 'MZ' + '9' * 32)
    output = []

    async def fake_send(text, *, goodbye=False):
        output.append((text, goodbye))

    monkeypatch.setattr(bridge, '_send_audio', fake_send)
    asyncio.run(drive(bridge, 'Quítenme de las campañas'))
    assert output[-1][1] is True
    with pytest.raises(tel.CallPolicyError, match='DNC'):
        tel._reserve(PHONE)


def test_voice_positive_consent_and_sensitive_escalation(isolated, monkeypatch):
    bridge = voice.CallBridge(object(), 'b' * 32, 'CA' + '1' * 32, 'MZ' + '9' * 32)
    messages = []

    async def fake_send(text, *, goodbye=False):
        messages.append((text, goodbye))

    monkeypatch.setattr(bridge, '_send_audio', fake_send)
    asyncio.run(drive(bridge, 'Sí, acepto'))
    assert bridge.consent_accepted
    asyncio.run(drive(bridge, 'Me salió un cargo raro que yo no hice'))
    assert messages[-1][1] is True
    assert bridge.utterances == 0


def test_live_annotation_metrics_are_aggregate_only():
    rows = [dict(scenario_id='S1', register='coloquial', intent_reference='fraud', intent_predicted='fraud',
                 reference_transcript='un cargo raro', stt_transcript='un cargo', turn_latency_ms='1500',
                 task_pass='true', critical_policy_pass='true')]
    data = evaluate_rows(rows)
    assert data['groups']['all']['n'] == 1
    assert data['groups']['all']['mean_utterance_wer'] == 0.3333
    assert 'reference_transcript' not in str(data)
    assert data['groups']['all']['macro_f1'] == 1


def test_partial_provider_usage_never_claims_full_cost(isolated):
    call_id = 'b' * 32
    assert metrics.record_provider_usage(call_id, 'anthropic_input_tokens', 100, None)
    assert metrics.record_provider_usage(call_id, 'azure_tts_characters', 75, .001)
    assert not metrics.record_provider_usage(call_id, 'customer_secret', 22, .1)
    output = metrics.usage_summary()
    assert output['records'] == 2
    assert output['partial_estimated_usd'] == .001
    assert output['unpriced_records'] == 1
    assert output['complete_bill'] is False


def test_invalid_tariffs_are_unknown_not_zero(isolated, monkeypatch):
    monkeypatch.setenv('LLM_INPUT_USD_PER_MILLION', 'not-a-number')
    assert metrics.configured_tariff('LLM_INPUT_USD_PER_MILLION') is None
    monkeypatch.setenv('LLM_INPUT_USD_PER_MILLION', '0.2')
    assert metrics.configured_tariff('LLM_INPUT_USD_PER_MILLION') == .2
