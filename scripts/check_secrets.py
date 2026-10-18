"""Detección básica de secretos accidentales y artefactos privados en el repositorio.

Es una defensa adicional; NO garantiza ausencia de secretos. Usar también revisiones
humanas y protección de secretos de la plataforma GitHub.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "results"}
BAD_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
BAD_EXT = {".sqlite", ".sqlite3", ".db", ".pem", ".p12", ".pfx", ".key"}
DETECT = [
    ("clave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Anthropic/OpenAI", re.compile(r"\b(?:sk-ant-|sk-proj-|sk-)[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp_|gho_|ghs_|ghu_|github_pat_)[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
]


def checked_paths() -> list[Path]:
    """En Git inspecciona solo archivos versionados; en ZIP usa filtros conservadores."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=False
    )
    if result.returncode == 0 and result.stdout:
        return [ROOT / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    return [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not set(p.relative_to(ROOT).parts).intersection(SKIP)
    ]


def main() -> int:
    failures: list[str] = []
    for path in checked_paths():
        rel = path.relative_to(ROOT)
        if path.name in BAD_NAMES or path.suffix.lower() in BAD_EXT:
            failures.append(f"{rel}: archivo sensible incluido")
            continue
        if path.stat().st_size > 1_000_000 or path.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".wav", ".mp3", ".zip", ".pdf", ".docx",
        }:
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if path.name == ".env.example":
            # Archivo de ejemplo: conserva las claves vacías, pero detecta tokens reales.
            pass
        for category, pattern in DETECT:
            if pattern.search(contents):
                failures.append(f"{rel}: patrón de {category}")
    if failures:
        print("Archivos sensibles potenciales detectados:\n" + "\n".join(failures))
        return 1
    print("Revisión heurística local de secretos: sin coincidencias.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
