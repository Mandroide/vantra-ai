"""Evita que la integración Streamlit-Docker se quede sin código o dependencias."""
from pathlib import Path
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_overlay_and_dependencies():
    overlay = yaml.safe_load((ROOT / "compose.dashboard.yaml").read_text(encoding="utf-8"))
    service = overlay["services"]["dashboard"]
    assert service["build"]["args"]["WITH_DASHBOARD"] == "true"
    assert "streamlit" in service["command"]
    assert service["ports"][0].startswith("127.0.0.1:")
    assert (ROOT / "uv.lock").exists()
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert any(dep.startswith("streamlit") for dep in cfg["dependency-groups"]["dashboard"])


def test_dockerfile_includes_dashboard_code_and_lock():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "--group dashboard" in dockerfile
    assert "COPY --chown=vantra:vantra dashboard.py" in dockerfile
    assert "COPY --chown=vantra:vantra analytics" in dockerfile
    assert "COPY --chown=vantra:vantra results" in dockerfile
    assert "results/" not in ignore


def test_fallback_propagated_to_both_services():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    for service in ("vantra", "twilio-webhook"):
        assert "VANTRA_FALLBACK" in compose["services"][service]["environment"]
