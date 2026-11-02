"""Política compartida de intenciones sensibles (texto y telefonía)."""
from __future__ import annotations

from src import nlu


def critical_intent(text: str) -> str | None:
    """Detecta primero exclusión/revocación; nunca depende de un LLM."""
    canonical = nlu.canon(text)
    checks = (
        ("dnc", nlu.is_do_not_call),
        ("consent_denied", nlu.is_consent_denied),
        ("private", nlu.is_private),
        ("fraud", nlu.is_fraud),
        ("human", nlu.is_human),
        ("complaint", nlu.is_complaint),
    )
    for name, predicate in checks:
        if predicate(canonical):
            return name
    return None


def consent_accepted(text: str) -> bool:
    """Solo expresiones afirmativas inequívocas; el silencio NO es consentimiento."""
    canonical = nlu.canon(text).strip()
    return canonical in {
        "si", "si acepto", "si autorizo", "acepto", "autorizo",
        "claro", "de acuerdo", "adelante", "confirmo", "esta bien",
        "si deseo continuar", "quiero continuar", "ok", "okay",
    }
