"""Verifica que solo se guardan métricas numéricas, sin contenido conversacional."""


def test_telemetry(tmp_path, monkeypatch):
    from src import storage
    monkeypatch.setattr(storage, 'DB', tmp_path / 'metrics.sqlite3')
    storage.record_interaction_metric('LIVE', 'OK', 250.0)
    storage.record_interaction_metric('LIVE', 'OK', 650.0)
    storage.record_interaction_metric('unknown', 'OK', 700.0)
    d = storage.telemetry_summary()
    assert d['LIVE']['interacciones_texto_observadas'] == 2
    assert d['LIVE']['latencia_aplicacion_p95_ms'] > 250
    assert d['DEMO']['interacciones_texto_observadas'] == 0
