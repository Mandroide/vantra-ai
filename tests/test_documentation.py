"""Verifica navegación básica de la documentación de instalación y telefonía.

No requiere red, APIs ni Docker: protege enlaces relativos y nombres de variables.
"""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GUIDES = (
    ROOT / "README.md",
    ROOT / "MANUAL_INSTALACION_Y_DESPLIEGUE.md",
    DOCS / "README.md",
    DOCS / "getting-started.md",
    DOCS / "configuration.md",
    DOCS / "docker-deployment.md",
    DOCS / "twilio-setup.md",
    DOCS / "ngrok-setup.md",
    DOCS / "first-call.md",
    DOCS / "troubleshooting.md",
)


def test_links_in_operational_guides_exist():
    for guide in GUIDES:
        text = guide.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            destination = (guide.parent / unquote(target)).resolve()
            assert destination.is_file(), f"Enlace roto: {guide.relative_to(ROOT)} -> {target}"


def test_configuration_guide_lists_required_runtime_variables():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    guide = (DOCS / "configuration.md").read_text(encoding="utf-8")
    for field in (
            "VANTRA_MODE", "DEEPGRAM_API_KEY", "ANTHROPIC_API_KEY", "AZURE_SPEECH_KEY",
            "AZURE_SPEECH_REGION", "TWILIO_CALLS_ENABLED", "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_PUBLIC_BASE_URL",
            "TWILIO_TEST_NUMBERS",
    ):
        assert f"{field}=" in example, field
        assert field in guide, field


def test_quickstart_does_not_claim_unverified_live_results():
    guide = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pendientes de validación real" in guide
    assert "Primera llamada" in guide
    assert "TWILIO_CALLS_ENABLED=false" in guide
    assert "ngrok http 8000" in guide
