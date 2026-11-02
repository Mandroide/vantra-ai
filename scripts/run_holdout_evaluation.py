"""Evaluación con frases NUEVAS (data/holdout_scenarios.json), desglosada por subgrupo.

    uv run python scripts/run_holdout_evaluation.py                 # DEMO: reglas locales, gratis y determinista
    uv run python scripts/run_holdout_evaluation.py --mode LIVE     # LIVE: lo que las reglas no resuelven va a Claude
    uv run python scripts/run_holdout_evaluation.py --set v2        # conjunto de prueba congelado (Fase 3)
    uv run python scripts/run_holdout_evaluation.py --set v2 --tag antes   # guarda con otro nombre (antes/después)

LIVE necesita ANTHROPIC_API_KEY y ANTHROPIC_MODEL en .env (p. ej. claude-sonnet-5-5 o claude-haiku-5-5).
Salidas en results/: holdout[_v2][_<tag>]_<modo>_cases.csv, _subgroups.csv y _summary.json.

Métricas técnicas: exactitud por rúbrica (con IC95 de Wilson), acierto de herramienta y argumentos, fallos críticos.
Métricas de negocio: % resuelto por reglas (costo de API 0), % derivado al LLM (genera costo), % sin resolver,
latencia y costo estimado por consulta (tokens reales x precio de lista).
"""
import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent import Session, respond  # noqa: E402
from src.config import env  # noqa: E402

FALLBACK = "No tengo información verificada"
# Precios de lista USD por millón de tokens (entrada, salida), verificados en oct-2026.
PRICES = {"claude-sonnet-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (5.00, 25.00)}


def price_for(model: str):
    for k in sorted(PRICES, key=len, reverse=True):
        if model.startswith(k):
            return PRICES[k]
    return None


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * max(0.0, c - h), 1), round(100 * min(1.0, c + h), 1))


def norm(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def grade(case: dict, text: str, tools: list[dict]) -> tuple[bool, list[str], bool | None]:
    """Devuelve (pasa, motivos_de_falla, herramienta_correcta|None)."""
    r = case["rubric"]
    t = norm(text)
    names = [e["name"] for e in tools]
    reasons = []
    tool_ok = None
    if r.get("tools_any"):
        hit = [e for e in tools if e["name"] in r["tools_any"]]
        tool_ok = bool(hit)
        if hit and r.get("tool_args"):
            want = r["tool_args"]
            tool_ok = any(all(_eq(e["arguments"].get(k), v) for k, v in want.items()) for e in hit)
        if not tool_ok:
            reasons.append(
                f"herramienta esperada {r['tools_any']} {r.get('tool_args', '')} no se invocó bien (vio {names})")
    text_ok = True
    if r.get("text_any"):
        text_ok = any(re.search(norm(p), t) for p in r["text_any"])
        if not text_ok:
            reasons.append("la respuesta no cumple el contenido esperado")
    if r.get("mode") == "any":  # basta herramienta O texto (p. ej. pedir confirmación antes de registrar)
        ok = bool(tool_ok) or text_ok
        reasons = [] if ok else reasons
    else:
        ok = (tool_ok is not False) and text_ok
    for p in r.get("forbid", []):
        if re.search(norm(p), t):
            ok = False
            reasons.append(f"dijo algo prohibido /{p}/")
    if r.get("forbid_tools") and names:
        ok = False
        reasons.append(f"invocó herramientas en una consulta privada: {names}")
    return ok, reasons, tool_ok


def _eq(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return a == b


def route_of(ans) -> str:
    if ans.llm_input_tokens > 0:
        return "llm"
    if ans.text.startswith(FALLBACK):
        return "sin_resolver"
    return "reglas"


def summarize(rows: list[dict], price) -> dict:
    n = len(rows)
    k = sum(r["passes"] for r in rows)
    tool_rows = [r for r in rows if r["tool_ok"] != ""]
    crit = [r for r in rows if r["critical"]]
    lat = [r["latency_ms"] for r in rows]
    cost = None
    if price:
        cost = statistics.mean((r["tokens_in"] * price[0] + r["tokens_out"] * price[1]) / 1e6 for r in rows)
    lo, hi = wilson(k, n)
    return {
        "n": n,
        "exactitud_pct": round(100 * k / n, 1) if n else None, "ic95_bajo": lo, "ic95_alto": hi,
        "acierto_herramienta_pct": round(100 * sum(r["tool_ok"] is True for r in tool_rows) / len(tool_rows), 1)
        if tool_rows else None,
        "fallos_criticos": sum(not r["passes"] for r in crit), "n_criticos": len(crit),
        "resuelto_por_reglas_pct": round(100 * sum(r["route"] == "reglas" for r in rows) / n, 1) if n else None,
        "derivado_llm_pct": round(100 * sum(r["route"] == "llm" for r in rows) / n, 1) if n else None,
        "sin_resolver_pct": round(100 * sum(r["route"] == "sin_resolver" for r in rows) / n, 1) if n else None,
        "latencia_media_ms": round(statistics.mean(lat), 2) if lat else None,
        "latencia_p95_ms": round(sorted(lat)[min(len(lat) - 1, int(0.95 * len(lat)))], 2) if lat else None,
        "tokens_media": round(statistics.mean(r["tokens_in"] + r["tokens_out"] for r in rows), 1) if n else 0,
        "costo_medio_usd": round(cost, 6) if cost is not None else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["DEMO", "LIVE"], default="DEMO")
    ap.add_argument("--set", choices=["v1", "v2"], default="v1",
                    help="v1 = desarrollo (Fase 2); v2 = prueba congelada antes de corregir el agente (Fase 3)")
    ap.add_argument("--tag", default="", help="sufijo para distinguir corridas, p. ej. antes / despues")
    args = ap.parse_args()
    model = env("ANTHROPIC_MODEL", "claude-sonnet-5")
    price = price_for(model) if args.mode == "LIVE" else None
    if args.mode == "LIVE" and not env("ANTHROPIC_API_KEY"):
        sys.exit("Falta ANTHROPIC_API_KEY en .env")

    data_file = "holdout_scenarios.json" if args.set == "v1" else "holdout_v2_scenarios.json"
    cases = json.loads((ROOT / "data" / data_file).read_text(encoding="utf-8"))
    rows = []
    t0 = time.time()
    for i, c in enumerate(cases, 1):
        ans, _ = respond(c["text"], Session(), mode=args.mode)
        if args.mode == "LIVE" and ans.status == "PROVIDER_ERROR" and i <= 3:
            sys.exit(
                f"Error del proveedor en el caso {c['id']}: {ans.text}  (revise ANTHROPIC_API_KEY y ANTHROPIC_MODEL)")
        ok, reasons, tool_ok = grade(c, ans.text, ans.tools)
        rows.append({
            "id": c["id"], "intent": c["intent"], "group": c["group"], "register": c["register"],
            "number_format": c.get("number_format") or "", "product": c["product"], "critical": c["critical"],
            "passes": ok, "tool_ok": "" if tool_ok is None else tool_ok, "route": route_of(ans), "status": ans.status,
            "tools": ";".join(e["name"] for e in ans.tools),
            "latency_ms": round(ans.llm_ms if ans.llm_ms else ans.elapsed_ms, 2),
            "tokens_in": ans.llm_input_tokens, "tokens_out": ans.llm_output_tokens,
            "failure_reasons": " | ".join(reasons), "text": c["text"], "response": ans.text[:400],
        })
        if args.mode == "LIVE":
            print(f"[{i}/{len(cases)}] {'OK ' if ok else 'FAL'} {c['id']:<22} {rows[-1]['route']}", flush=True)

    tag = "_".join(x for x in (("v2" if args.set == "v2" else ""), args.tag, args.mode.lower()) if x)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with (out / f"holdout_{tag}_cases.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    subgroups = []
    for dim in ("register", "group", "intent", "product", "critical", "number_format"):
        for val in sorted({str(r[dim]) for r in rows if str(r[dim]) != ""}):
            one = [r for r in rows if str(r[dim]) == val]
            subgroups.append({"dimension": dim, "value": val, **summarize(one, price)})
    with (out / f"holdout_{tag}_subgroups.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=subgroups[0].keys())
        w.writeheader()
        w.writerows(subgroups)
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode, "set": args.set,
               "tag": args.tag,
               "model": model if args.mode == "LIVE" else None, "price_usd_per_mtok": price,
               "duration_s": round(time.time() - t0, 1), "global": summarize(rows, price),
               "failed_ids": [r["id"] for r in rows if not r["passes"]],
               "scope": "Frases nuevas escritas después de las reglas; rúbrica automática. No mide audio ni satisfacción."}
    (out / f"holdout_{tag}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                                     encoding="utf-8")
    g = summary["global"]
    print(
        f"{args.mode} [{args.set}{'/' + args.tag if args.tag else ''}]: exactitud {g['exactitud_pct']}% (IC95 {g['ic95_bajo']}-{g['ic95_alto']}) | "
        f"fallos críticos {g['fallos_criticos']}/{g['n_criticos']} | reglas {g['resuelto_por_reglas_pct']}% | "
        f"LLM {g['derivado_llm_pct']}% | sin resolver {g['sin_resolver_pct']}% | costo medio {g['costo_medio_usd']}")


if __name__ == "__main__":
    main()
