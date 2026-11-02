"""Comprueba la integridad del held-out v2 sin reescribirlo ni recalcular su huella.

Admite únicamente el cambio de fin de línea LF -> CRLF que puede introducir
un editor en Windows. Cambios en contenido, orden o espacios siguen fallando.

Ejecute: uv run python -m scripts.verify_frozen_holdout
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "holdout_v2_scenarios.json"
CHECKSUM = ROOT / "data" / "holdout_v2.sha256"
# Huella publicada del conjunto v2 original; no actualizar tras entrenar o depurar.
FROZEN_SHA256 = "c9d6b0e627d5f2fffed6fda68f8ce20234f8b67d64414f17afbf189fb60e6081"


def integrity_status(content: bytes, expected: str) -> str:
    """'original', 'crlf' o 'modified'; nunca actualiza el checksum confiable."""
    if hashlib.sha256(content).hexdigest() == expected:
        return "original"
    if b"\r\n" in content and hashlib.sha256(
        content.replace(b"\r\n", b"\n")
    ).hexdigest() == expected:
        return "crlf"
    return "modified"


def verify_frozen_holdout() -> tuple[str, str, str]:
    """Devuelve estado, SHA-256 calculado y SHA-256 esperado."""
    manifest_sha = CHECKSUM.read_text(encoding="utf-8").split()[0]
    content = DATA.read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    # El manifiesto tampoco se puede cambiar junto con los datos para eludir la prueba.
    if manifest_sha != FROZEN_SHA256:
        return "checksum-modified", actual, FROZEN_SHA256
    return integrity_status(content, FROZEN_SHA256), actual, FROZEN_SHA256


def main() -> int:
    status, actual, expected = verify_frozen_holdout()
    print(f"Held-out v2: {status}; SHA256 actual={actual}; esperado={expected}")
    if status in {"modified", "checksum-modified"}:
        print(
            "ERROR: el conjunto congelado o su manifiesto difieren de la evidencia original. "
            "Restaurar data/holdout_v2_scenarios.json desde el ZIP confiable "
            "y NO regenerar data/holdout_v2.sha256 para ocultar el cambio."
        )
        return 1
    if status == "crlf":
        print("AVISO: solo difieren los finales de línea CRLF de Windows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
