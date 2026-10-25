from src.kpis import word_error_rate, intent_metrics, latency_percentiles


def test_wer():
    assert word_error_rate('solicito una tarjeta', 'solicito tarjeta') == 1 / 3
    assert word_error_rate('', 'hola') is None
    assert word_error_rate('hola banco', 'hola banco') == 0


def test_f1():
    m = intent_metrics(['fraude', 'info', 'fraude'], ['fraude', 'fraude', 'fraude'])
    assert m['n'] == 3
    assert m['by_label']['fraude']['recall'] == 1
    assert intent_metrics([], [])['macro_f1'] is None


def test_latency():
    assert latency_percentiles([100, 200])['p50_ms'] == 150
    assert latency_percentiles([])['p95_ms'] is None
