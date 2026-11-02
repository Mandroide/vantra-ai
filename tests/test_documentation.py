"""Coherencia de las ocho guías consolidadas, offline y sin credenciales."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GUIDES = (
    ROOT / "README.md",
    DOCS / "architecture.md",
    DOCS / "installation.md",
    DOCS / "configuration.md",
    DOCS / "telephony.md",
    DOCS / "evaluation.md",
    DOCS / "ethics.md",
    DOCS / "troubleshooting.md",
)


def test_eight_canonical_markdown_files():
    assert set(ROOT.glob("*.md")) | set(DOCS.glob("*.md")) == set(GUIDES)


def test_relative_documentation_links_exist():
    for guide in GUIDES:
        text = guide.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            destination = (guide.parent / unquote(target)).resolve()
            assert destination.is_file(), f"Enlace roto: {guide.relative_to(ROOT)} -> {target}"


def test_configuration_guide_lists_runtime_variables():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    guide = (DOCS / "configuration.md").read_text(encoding="utf-8")
    telephony = (DOCS / "telephony.md").read_text(encoding="utf-8")
    for field in (
            "VANTRA_MODE", "DEEPGRAM_API_KEY", "ANTHROPIC_API_KEY", "AZURE_SPEECH_KEY",
            "AZURE_SPEECH_REGION", "TWILIO_CALLS_ENABLED", "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_PUBLIC_BASE_URL",
            "TWILIO_TEST_NUMBERS", "TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS",
            "TWILIO_DAILY_CALL_LIMIT", "CONNECTIVITY_PROVIDER", "NGROK_AUTHTOKEN",
            "CLOUDFLARE_TUNNEL_TOKEN", "VANTRA_PUBLIC_HOST", "CADDY_EMAIL",
    ):
        assert f"{field}=" in example, field
        assert field in guide or field in telephony, field


def test_readme_does_not_claim_verified_live_calls():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "evidencia de una conversación telefónica piloto" in text
    assert "TWILIO_CALLS_ENABLED=false" in text
    assert "scripts/connectivity.py" in text
    assert "36 verificaciones offline" in text
