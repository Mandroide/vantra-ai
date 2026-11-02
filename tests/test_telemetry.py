"""Telemetría de aplicación sin contenido conversacional ni datos de usuarios."""
from src import storage


def test_telemetry_only_numeric(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB", tmp_path / "telemetry.sqlite3")
    storage.record_interaction_metric("LIVE", "OK", 250.0)
    storage.record_interaction_metric("LIVE", "OK", 650.0)
    storage.record_interaction_metric("otro", "OK", 700.0)
    storage.record_interaction_metric("LIVE", "OK", float("nan"))
    metrics = storage.telemetry_summary()
    assert metrics["LIVE"]["interacciones_gradio_observadas"] == 2
    assert metrics["LIVE"]["latencia_aplicacion_p95_ms"] > 250
    assert metrics["DEMO"]["interacciones_gradio_observadas"] == 0
    with storage.connection() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(interaction_metrics)")}
    assert columns == {"id", "created_at", "mode", "status", "elapsed_ms"}


def test_telemetry_rejects_unrecognized_status(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB", tmp_path / "telemetry.sqlite3")
    storage.record_interaction_metric("DEMO", "dato privado accidental", 100.0)
    with storage.connection() as conn:
        status = conn.execute("SELECT status FROM interaction_metrics").fetchone()[0]
    assert status == "OTRO"
