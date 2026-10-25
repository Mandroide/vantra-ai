"""Pruebas offline de presencia y coherencia de los archivos de DevOps."""

import tomllib
from pathlib import Path

from scripts.check_secrets import main as check_secrets

ROOT = Path(__file__).resolve().parents[1]


def test_uv_project_is_not_production_bank():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "vantra-ai"
    assert data["tool"]["uv"]["package"] is False
    assert data["project"]["requires-python"] == ">=3.11,<3.13"
    assert "dev" in data["dependency-groups"]


def test_ci_does_not_push_image_or_require_live_api_keys():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "VANTRA_MODE: DEMO" in workflow
    assert "python -m pytest" in workflow
    assert "docker/build-push-action" in workflow
    assert "push: false" in workflow
    assert "uv sync --locked" in workflow
    assert "scripts/run_evaluation.py" in workflow
    assert "secrets.ANTHROPIC_API_KEY" not in workflow


def test_dockerfile_excludes_env_and_runs_non_root():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "USER vantra" in dockerfile
    assert "COPY --from=builder /app/.venv" in dockerfile
    assert "COPY --chown=vantra:vantra scripts ./scripts" in dockerfile
    assert "\n.env\n" in dockerignore
    assert ".git" in dockerignore.splitlines()


def test_secret_scan_passes_synthetic_repository():
    assert check_secrets() == 0


def test_gitattributes_normalizes_source_without_touching_binary():
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto" in attrs
    for pattern in ("*.py", "*.yml", "*.yaml", "*.md", "*.json", "*.csv", "Dockerfile"):
        assert any(line.lstrip().startswith(pattern + " ") and "text eol=lf" in line for line in attrs.splitlines())
    for extension in ("*.ogg", "*.mp3", "*.wav", "*.png", "*.pdf", "*.zip", "*.sqlite3"):
        assert any(line.lstrip().startswith(extension + " ") and "binary" in line for line in attrs.splitlines())
    assert "*.ps1" in attrs and "eol=crlf" in attrs
