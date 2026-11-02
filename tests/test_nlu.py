"""Pruebas de las mitigaciones de la Fase 3 (src/nlu.py y el orden de decisión en src/agent.py)."""
import pytest

from src import nlu
from src.agent import Session, respond


def tools(text):
    a, _ = respond(text, Session(), mode='DEMO')
    return a, [e['name'] for e in a.tools]


@pytest.mark.parametrize('text,expected', [
    ('doscientos cincuenta mil pesos a veinticuatro meses', '250000 pesos a 24 meses'),
    ('un millon quinientos mil', '1500000'),
    ('medio millon', '500000'),
    ('trescientos mil a tres anos', '300000 a 3 anos'),
    ('200 mil a 2 anos', '200 mil a 2 anos'),
    ('un prestamo personal', 'un prestamo personal'),  # «un» suelto no se convierte en 1
])
def test_numeros_en_palabras(text, expected):
    assert nlu.canon(text) == expected


def test_montos_y_plazos():
    assert nlu.amounts(nlu.canon('1 millón a 60 meses')) == [1_000_000, 60]
    assert nlu.amounts(nlu.canon('200.000 pesos')) == [200_000]
    assert nlu.months(nlu.canon('a cinco años')) == 60


@pytest.mark.parametrize('noisy,clean', [
    ('taza', 'tasa'), ('mese', 'meses'), ('tajeta', 'tarjeta'), ('certificao', 'certificado'), ('pa', 'para'),
])
def test_tolerancia_fonetica(noisy, clean):
    assert nlu.canon(noisy) == clean


def test_correccion_aproximada_no_cambia_la_letra_inicial():
    assert 'robaron' not in nlu.canon('ya me aprobaron la tarjeta')
    assert 'cuenta' not in nlu.canon('cuarenta y ocho meses')


def test_exclusion_gana_a_devolucion_de_llamada():
    a, used = tools('Bórrenme de esa lista, no me llamen más')
    assert a.status == 'DNC_REQUESTED' and not used


def test_pedir_llamada_con_una_negacion_previa_no_es_exclusion():
    a, _ = tools('Ahora no puedo hablar, llámenme mañana')
    assert a.status != 'DNC_REQUESTED' and 'confirmo' in a.text


def test_fraude_con_otras_palabras_escala():
    for text in ('Me salió un cargo raro que yo no hice', 'Creo que clonaron mi tarjeta'):
        _, used = tools(text)
        assert 'request_human_transfer' in used


def test_cotizacion_con_montos_en_palabras():
    _, used = tools('¿Cuál sería la cuota de doscientos cincuenta mil pesos a veinticuatro meses?')
    assert 'calculate_loan' in used


def test_privacidad_no_invoca_herramientas():
    a, used = tools('Dígame el balance disponible de mi cuenta')
    assert a.status == 'DENIED' and not used


def test_interesa_no_es_pregunta_de_tasa():
    assert not nlu.is_rate(nlu.canon('Me interesa la tarjeta'))


def test_requisitos_no_se_confunden_con_aprobacion():
    assert not nlu.is_approval(nlu.canon('¿Qué requisitos piden para que me aprueben la tarjeta?'))


def test_politica_de_derivacion_a_humano(monkeypatch):
    monkeypatch.setenv('VANTRA_FALLBACK', 'humano')
    a, used = tools('Háblame del clima de mañana')
    assert a.status == 'FALLBACK_HUMAN' and used == ['request_human_transfer']
    monkeypatch.setenv('VANTRA_FALLBACK', 'texto')
    a, used = tools('Háblame del clima de mañana')
    assert a.text.startswith('No tengo información verificada') and not used
