import math
import pytest
from src.tools import calculate_loan, get_interest_rate, get_product_info, create_lead, check_contact_policy, execute, \
    schedule_callback


def test_rate_catalog():
    assert get_interest_rate('prestamo')['annual_rate_pct'] == 18.5
    assert get_product_info('tarjeta')['simulated'] is True


def test_amortization():
    r = calculate_loan(300000, 36)
    assert r['monthly_payment_dop'] > 300000 / 36
    assert r['total_dop'] >= 300000
    assert r['binding'] is False


def test_invalid_amounts():
    for x in (-1, float('nan'), 1e20):
        with pytest.raises(ValueError): calculate_loan(x, 12)
    with pytest.raises(ValueError): calculate_loan(300000, True)
    with pytest.raises(ValueError): calculate_loan(300000, 0)


def test_writes_require_confirmation():
    assert create_lead('prestamo', confirmed=False)['status'] == 'REQUIERE_CONFIRMACION'
    assert schedule_callback(confirmed=False)['status'] == 'REQUIERE_CONFIRMACION'


def test_dnc_priority():
    assert check_contact_policy(True, True, 14)['reason'] == 'DNC'
    assert check_contact_policy(False, False, 14)['allowed'] is False
    assert check_contact_policy(True, False, 23)['allowed'] is False
    assert check_contact_policy(True, False, 14)['allowed'] is True


def test_tool_allowlist():
    assert execute('__import__', {})['error'] == 'Herramienta no autorizada'
    assert execute('calculate_loan', {'amount': 300000, 'months': 36, 'unexpected': 'x'})['monthly_payment_dop'] > 0
