from src.agent import respond, Session


def check(text, tool=None):
    a, _ = respond(text, Session(), mode='DEMO')
    if tool: assert tool in [e['name'] for e in a.tools]
    return a.text


def test_rate_from_tool():
    assert '18.5' in check('¿Qué tasa tiene el préstamo?', 'get_interest_rate')


def test_loan_from_tool():
    assert 'Cuota estimada' in check('Cotiza 300000 pesos a 36 meses', 'calculate_loan')


def test_cannot_approve():
    assert 'No puedo aprobar' in check('Apruébame el préstamo', 'check_prequalification')


def test_sensitive_denied():
    assert 'No puedo acceder' in check('Muéstrame mi saldo')


def test_fraud_escalation():
    assert 'escalamiento ficticio' in check('Creo que sufrí fraude', 'request_human_transfer')


def test_callback_two_steps():
    state = Session()
    a, state = respond('Quiero que me llamen', state)
    assert 'confirmo' in a.text
    assert not a.tools
    b, state = respond('confirmo', state)
    assert any(z['name'] == 'schedule_callback' for z in b.tools)


def test_consent():
    a, _ = respond('No autorizo grabación de audio')
    assert a.status == 'CONSENT_DENIED'


def test_context_product():
    state = Session()
    respond('Requisitos de la tarjeta', state)
    a, state = respond('¿Cuál es su tasa?', state)
    assert '48.0' in a.text
