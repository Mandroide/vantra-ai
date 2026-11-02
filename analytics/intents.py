"""Métricas discriminatorias por intención: matriz de confusión, precisión, exhaustividad (recall) y F1.

La intención que el agente "predijo" se deduce de lo que hizo (herramienta, estado y respuesta), así se evalúa el
sistema completo y no solo un clasificador aislado. «sin_resolver» es la respuesta genérica sin acción.
"""
from __future__ import annotations

import csv
from pathlib import Path

INTENCIONES = ["requisitos", "tasa", "cotizacion", "aprobacion", "devolucion_llamada", "privacidad",
               "exclusion_dnc", "consentimiento_audio", "humano", "fraude", "queja"]
CRITICAS = {"aprobacion", "privacidad", "exclusion_dnc", "fraude"}


def predicted_intent(row: dict) -> str:
    tools = row.get("tools", "")
    status = row.get("status", "")
    text = (row.get("response") or "").lower()
    if status == "DENIED":
        return "privacidad"
    if status == "CONSENT_DENIED":
        return "exclusion_dnc" if "no contacto" in text else "consentimiento_audio"
    if status == "DNC_REQUESTED" or "preferencia de no contacto" in text:
        return "exclusion_dnc"
    if "request_human_transfer" in tools:
        if "escalamiento ficticio" in text:
            return "fraude"
        if "lamento la situaci" in text:
            return "queja"
        return "humano"
    if "check_prequalification" in tools or "no puedo aprobar" in text:
        return "aprobacion"
    if "calculate_loan" in tools or "indique monto y plazo" in text:
        return "cotizacion"
    if "get_interest_rate" in tools:
        return "tasa"
    if "get_product_info" in tools:
        return "requisitos"
    if "devolución de llamada" in text or "devolucion de llamada" in text:
        return "devolucion_llamada"
    return "sin_resolver"


def load_cases(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def confusion(rows: list[dict]) -> dict:
    labels = INTENCIONES + ["sin_resolver"]
    m = {t: {p: 0 for p in labels} for t in INTENCIONES}
    for r in rows:
        m[r["intent"]][predicted_intent(r)] += 1
    return m


def per_class(rows: list[dict]) -> dict:
    """Precisión, recall y F1 por intención, más promedios macro y la exactitud de intención."""
    m = confusion(rows)
    out = {}
    for c in INTENCIONES:
        tp = m[c][c]
        fn = sum(m[c].values()) - tp
        fp = sum(m[t][c] for t in INTENCIONES if t != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[c] = {"n": tp + fn, "precision": prec, "recall": rec, "f1": f1, "critica": c in CRITICAS}
    macro = {k: sum(v[k] for v in out.values()) / len(out) for k in ("precision", "recall", "f1")}
    crit = [v for k, v in out.items() if k in CRITICAS]
    acc = sum(m[c][c] for c in INTENCIONES) / max(1, len(rows))
    return {"por_intencion": out, "macro": macro,
            "macro_criticas": {k: sum(v[k] for v in crit) / len(crit) for k in ("precision", "recall", "f1")},
            "exactitud_intencion": acc,
            "sin_resolver": sum(1 for r in rows if predicted_intent(r) == "sin_resolver") / max(1, len(rows))}


def critical_breakdown(rows: list[dict]) -> dict:
    """Fallos críticos separados en «acción equivocada» (el daño real) y «sin resolver» (derivable a un humano)."""
    crit = [r for r in rows if r.get("critical") in (True, "True")]
    wrong = [r for r in crit if r["passes"] != "True" and predicted_intent(r) != "sin_resolver"]
    unresolved = [r for r in crit if r["passes"] != "True" and predicted_intent(r) == "sin_resolver"]
    return {"n": len(crit), "fallos": len(wrong) + len(unresolved), "accion_equivocada": len(wrong),
            "sin_resolver": len(unresolved), "ids_accion_equivocada": [r["id"] for r in wrong]}


def latency(rows: list[dict]) -> dict:
    xs = sorted(float(r["latency_ms"]) for r in rows)
    if not xs:
        return {}
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]  # noqa: E731
    return {"p50_ms": q(0.50), "p95_ms": q(0.95), "max_ms": xs[-1], "n": len(xs)}
