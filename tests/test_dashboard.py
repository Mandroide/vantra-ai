"""El cuadro de mando arranca sin errores y muestra las métricas clave (requiere el grupo «dashboard»)."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402
from pathlib import Path  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "dashboard.py")


def test_dashboard_arranca_y_calcula(tmp_path, monkeypatch):
    monkeypatch.setenv("VANTRA_DB_PATH", str(tmp_path / "d.sqlite3"))
    at = AppTest.from_file(APP, default_timeout=240).run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "P(VPN > 0) a 36 meses" in labels
    assert "Exactitud (held-out v2)" in labels and "R-hat máximo" in labels
