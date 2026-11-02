"""Cuadro de mando de Vantra AI (Fase 3): desempeño del agente, MCMC bayesiano y Monte Carlo del impacto.

    uv sync --locked --group dashboard
    uv run streamlit run dashboard.py            # http://localhost:8501

Todo se calcula en vivo y sin llaves de API:
- las métricas del agente se recalculan ejecutando el held-out v2 contra el código actual (src/agent.py);
- la posterior bayesiana se estima con MCMC (analytics/mcmc.py) a partir de esos resultados;
- el Monte Carlo (analytics/montecarlo.py) se vuelve a correr cada vez que se mueve un supuesto.
La línea base «antes» es el archivo congelado results/holdout_v2_antes_demo_cases.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("VANTRA_DB_PATH", str(Path(tempfile.gettempdir()) / "vantra_dashboard.sqlite3"))

from analytics import intents, mcmc, montecarlo  # noqa: E402
from analytics.assumptions import BY_KEY, DOP_PER_USD, SUPUESTOS  # noqa: E402

st.set_page_config(page_title="Vantra AI · Cuadro de mando", page_icon="📊", layout="wide")

# Paleta categórica validada (orden fijo; el color sigue a la entidad, no al rango).
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
REG_LABEL = {"formal": "Formal", "coloquial": "Coloquial dominicano", "errores_stt": "Con errores de STT"}
PERF_LABEL = {"p_formal": "Resolución en registro formal", "p_coloquial": "Resolución en registro coloquial",
              "p_stt": "Resolución con errores de STT", "p_error_critico": "Acción equivocada en intención crítica"}
LABEL = {**{s.key: s.label for s in SUPUESTOS}, **PERF_LABEL}

INTENT_LABEL = {"requisitos": "Requisitos", "tasa": "Tasa de interés", "cotizacion": "Cotización",
                "aprobacion": "Pedir aprobación *", "devolucion_llamada": "Devolución de llamada",
                "privacidad": "Privacidad *", "exclusion_dnc": "Exclusión de llamadas *",
                "consentimiento_audio": "No grabar audio", "humano": "Pedir un humano", "fraude": "Fraude *",
                "queja": "Queja", "sin_resolver": "Sin resolver"}


def usd(x, d=0):
    if x is None or not np.isfinite(x):
        return "N/D"
    return f"{'−' if x < 0 else ''}US${abs(x):,.{d}f}"


def pct(x, d=1):
    return "N/D" if x is None else f"{100 * x:.{d}f}%"


def theme(chart: alt.Chart) -> alt.Chart:
    return (chart.configure_view(strokeWidth=0)
            .configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=INK2, titleColor=INK2,
                            labelFontSize=12, titleFontSize=12, titleFontWeight="normal", labelLimit=340)
            .configure_axisX(tickCount=7)
            .configure_legend(labelColor=INK2, titleColor=INK2, orient="top", labelFontSize=12, titleFontSize=12))


# ----------------------------------------------------------------------------- evaluación en vivo
def _load_grader():
    spec = importlib.util.spec_from_file_location("rhe", ROOT / "scripts" / "run_holdout_evaluation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@st.cache_data(show_spinner="Ejecutando el held-out v2 contra el agente actual…")
def evaluate_current(agent_hash: str) -> list[dict]:
    """Corre los 114 casos congelados contra src/agent.py tal como está ahora. agent_hash invalida la caché."""
    from src.agent import Session, respond

    grader = _load_grader()
    cases = json.loads((ROOT / "data" / "holdout_v2_scenarios.json").read_text(encoding="utf-8"))
    rows = []
    for c in cases:
        ans, _ = respond(c["text"], Session(), mode="DEMO")
        ok, reasons, tool_ok = grader.grade(c, ans.text, ans.tools)
        rows.append({"id": c["id"], "intent": c["intent"], "register": c["register"], "critical": c["critical"],
                     "passes": str(ok), "tools": ";".join(e["name"] for e in ans.tools), "status": ans.status,
                     "response": ans.text, "latency_ms": ans.elapsed_ms, "text": c["text"]})
    return rows


def agent_hash() -> str:
    import hashlib

    h = hashlib.sha256()
    for p in ("src/agent.py", "src/nlu.py", "src/tools.py"):
        h.update((ROOT / p).read_bytes())
    return h.hexdigest()[:12]


@st.cache_data
def baseline_rows() -> list[dict]:
    p = ROOT / "results" / "holdout_v2_antes_demo_cases.csv"
    return intents.load_cases(p) if p.exists() else []


def reg_counts(rows):
    return {g: (sum(r["passes"] == "True" for r in rows if r["register"] == g),
                sum(1 for r in rows if r["register"] == g)) for g in REG_LABEL}


@st.cache_data(show_spinner="Estimando la posterior con MCMC…")
def fit_posterior(counts: tuple, crit: tuple, seed: int = 11):
    """counts: ((k,n) por registro); crit: (acciones equivocadas, n críticos)."""
    names = list(REG_LABEL)
    fit = mcmc.hierarchical([c[0] for c in counts], [c[1] for c in counts], names, seed=seed)
    fit_c = mcmc.beta_binomial(crit[0], crit[1], seed=7)
    perf = {"p_formal": fit.draws["formal"], "p_coloquial": fit.draws["coloquial"], "p_stt": fit.draws["errores_stt"],
            "p_error_critico": fit_c.draws["p"]}
    diag = {"rhat": {**fit.rhat, "p_error_critico": fit_c.rhat["p"]},
            "ess": {**fit.ess, "p_error_critico": fit_c.ess["p"]},
            "aceptacion": fit.acceptance, "aceptacion_beta": fit_c.acceptance,
            "cadenas": {k: fit.chains[k][:, :600].tolist() for k in ("formal", "coloquial")}}
    return perf, diag


# ----------------------------------------------------------------------------- barra lateral: supuestos
with st.sidebar:
    st.markdown("### Vantra AI · Cuadro de mando")
    st.caption("Banco ficticio. Costos en dólares, a RD\\$%.2f por dólar." % DOP_PER_USD)
    esc_key = st.selectbox("Escenario de decisión", list(montecarlo.ESCENARIOS),
                           format_func=lambda k: montecarlo.ESCENARIOS[k]["nombre"], index=0)
    esc = montecarlo.ESCENARIOS[esc_key]
    st.markdown("**Ajustar supuestos (valor más probable)**")
    st.caption("El mínimo y el máximo se mueven en la misma proporción. Cada cambio vuelve a correr la simulación.")
    overrides = dict(esc["overrides"])
    for key, step, fmt in (("llamadas_mes", 5_000, "%d"), ("salario", 1_000, "%d"), ("aht", 0.5, "%.1f"),
                           ("aceptacion", 0.05, "%.2f"), ("costo_min_bot", 0.005, "%.3f"),
                           ("operacion_mes", 250, "%d"), ("inversion", 1_000, "%d")):
        s = BY_KEY[key]
        lo, mo, hi = overrides.get(key, (s.low, s.mode, s.high))
        top = float(max(hi * 2, mo * 2))
        new_mode = st.slider(f"{s.label} ({s.unit})", float(lo * 0.5 if key != "aceptacion" else 0.3),
                             top if key != "aceptacion" else 0.95, float(mo), step=float(step), format=fmt, key=key)
        if new_mode != mo:
            ratio = new_mode / mo
            overrides[key] = (lo * ratio, new_mode, min(hi * ratio, 0.99) if key == "aceptacion" else hi * ratio)
    factor = st.slider("Factor sobre la tasa de acción equivocada en intenciones críticas", 0.05, 1.5,
                       float(esc["error_critico_factor"]), 0.05,
                       help="1.0 = lo medido en el held-out v2; 0.2 = meta de alrededor de 1% (guardrail).")
    cerrar = st.toggle("Cerrar la brecha coloquial (meta de equidad)", value=esc["cerrar_brecha"])
    n_sim = st.select_slider("Escenarios de Monte Carlo", [2_000, 5_000, 10_000, 20_000], value=10_000)
    seed = st.number_input("Semilla", value=2026, step=1)

# ----------------------------------------------------------------------------- datos en vivo
rows_now = evaluate_current(agent_hash())
rows_before = baseline_rows()
crit_now = intents.critical_breakdown(rows_now)
perf, diag = fit_posterior(tuple(reg_counts(rows_now).values()), (crit_now["accion_equivocada"], crit_now["n"]))
perf_s = montecarlo.apply_perf(perf, factor, cerrar)
res = montecarlo.run(perf_s, n=int(n_sim), seed=int(seed), overrides=overrides)
o = res.outputs

tabs = st.tabs(["Resumen", "Desempeño del modelo", "Monte Carlo", "Sensibilidad", "Diagnóstico MCMC",
                "Probar el agente", "Supuestos y fuentes", "Telemetría Gradio"])

# ----------------------------------------------------------------------------- 1. resumen
with tabs[0]:
    st.markdown(f"#### {esc['nombre']}" + (" · supuestos ajustados" if overrides != esc["overrides"] else ""))
    p_vpn, p_roi = res.prob("vpn_36m", ">", 0), res.prob("roi_anio1", ">", 0)
    neto, horas, fte = res.stats("neto_mes"), res.stats("horas_liberadas_mes"), res.stats("fte_liberados")
    pb = res.stats("payback_meses")
    k = st.columns(5)
    k[0].metric("P(VPN > 0) a 36 meses", pct(p_vpn, 0), help="Probabilidad de valor presente neto positivo a 36 "
                                                             "meses, descontado al 12% anual.")
    k[1].metric("Ahorro neto mensual", usd(neto["p50"]), help=f"Mediana. El 90% de los escenarios queda entre "
                                                              f"{usd(neto['p05'])} y {usd(neto['p95'])}.")
    share = pb.get("proporcion_finita", 1.0)
    k[2].metric("Recuperación", "No se recupera" if pb["p50"] is None or share < 0.5 else f"{pb['p50']:.0f} meses",
                help=f"Solo el {pct(share, 0)} de los escenarios recupera la inversión"
                     + ("" if pb["p50"] is None else f"; en ellos, la mediana es {pb['p50']:.0f} meses."))
    k[3].metric("Horas liberadas al mes", f"{horas['p50']:,.0f}", help=f"Mediana. Equivalen a {fte['p50']:.1f} "
                                                                       "puestos de tiempo completo dedicados hoy a consultas repetitivas.")
    k[4].metric("P(ROI > 0) en el año 1", pct(p_roi, 0))
    st.caption(f"{int(n_sim):,} escenarios de Monte Carlo. El desempeño del agente sale de la posterior MCMC sobre "
               f"{len(rows_now)} frases del held-out v2 evaluadas en vivo contra el código actual.")

    df = pd.DataFrame({"neto": o["neto_mes"]})
    hist = alt.Chart(df).mark_bar(color=C1, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("neto:Q", bin=alt.Bin(maxbins=50), title="Ahorro neto mensual (US$)", axis=alt.Axis(format="~s")),
        y=alt.Y("count():Q", title="Escenarios"),
        tooltip=[alt.Tooltip("count():Q", title="Escenarios")])
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
    st.altair_chart(theme(alt.layer(hist, zero).properties(height=280, title="Distribución del ahorro neto mensual")),
                    width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        comp = pd.DataFrame([
            {"Concepto": "Ahorro en tiempo de asesores", "US$/mes (mediana)": np.median(o["ahorro_bruto_mes"])},
            {"Concepto": "Costo del agente de IA", "US$/mes (mediana)": -np.median(o["costo_bot_mes"])},
            {"Concepto": "Riesgo por errores críticos", "US$/mes (mediana)": -np.median(o["riesgo_mes"])},
        ])
        st.markdown("**De dónde sale el resultado**")
        st.dataframe(comp.style.format({"US$/mes (mediana)": "{:,.0f}"}), hide_index=True, width="stretch")
    with c2:
        st.markdown("**Costo por llamada atendida (mediana)**")
        st.dataframe(pd.DataFrame([
            {"Canal": "Asesor humano", "US$ por llamada": np.median(o["costo_por_llamada_humana"])},
            {"Canal": "Agente de IA (incluye costo fijo y transferencias)",
             "US$ por llamada": np.median(o["costo_por_llamada_bot"])},
        ]).style.format({"US$ por llamada": "{:.3f}"}), hide_index=True, width="stretch")

# ----------------------------------------------------------------------------- 2. desempeño
with tabs[1]:
    m_now, m_before = intents.per_class(rows_now), intents.per_class(rows_before) if rows_before else None
    acc_now = sum(r["passes"] == "True" for r in rows_now) / len(rows_now)
    acc_before = (sum(r["passes"] == "True" for r in rows_before) / len(rows_before)) if rows_before else None
    lat = intents.latency(rows_now)
    k = st.columns(5)
    k[0].metric("Exactitud (held-out v2)", pct(acc_now), None if acc_before is None else
    f"{100 * (acc_now - acc_before):+.1f} p.p. vs. antes")
    k[1].metric("F1 macro por intención", f"{m_now['macro']['f1']:.2f}", None if not m_before else
    f"{m_now['macro']['f1'] - m_before['macro']['f1']:+.2f}")
    k[2].metric("F1 en intenciones críticas", f"{m_now['macro_criticas']['f1']:.2f}", None if not m_before else
    f"{m_now['macro_criticas']['f1'] - m_before['macro_criticas']['f1']:+.2f}")
    k[3].metric("Críticos mal atendidos", f"{crit_now['accion_equivocada']} de {crit_now['n']}",
                help=f"Casos críticos en los que el agente tomó una acción equivocada. Además, "
                     f"{crit_now['sin_resolver']} quedan sin resolver y, en despliegue, se derivan a un asesor.")
    k[4].metric("Latencia del motor (p95)", f"{lat.get('p95_ms', 0):.2f} ms", help="Solo el motor de reglas, sin voz.")

    rows_f1 = []
    for name, m in (("Antes", m_before), ("Después", m_now)):
        if not m:
            continue
        for it, v in m["por_intencion"].items():
            rows_f1.append({"Intención": INTENT_LABEL[it], "Momento": name,
                            "F1": v["f1"], "Precisión": v["precision"], "Recall": v["recall"]})
    df = pd.DataFrame(rows_f1)
    if len(df):
        ch = alt.Chart(df).mark_bar(cornerRadiusEnd=4, size=10).encode(
            y=alt.Y("Intención:N", title=None, sort=list(dict.fromkeys(df["Intención"]))),
            yOffset=alt.YOffset("Momento:N", sort=["Antes", "Después"]),
            x=alt.X("F1:Q", scale=alt.Scale(domain=[0, 1]), title="F1 por intención (* = crítica)"),
            color=alt.Color("Momento:N", scale=alt.Scale(domain=["Antes", "Después"], range=[C2, C1]), title=None),
            tooltip=["Intención", "Momento", alt.Tooltip("F1:Q", format=".2f"),
                     alt.Tooltip("Precisión:Q", format=".2f"),
                     alt.Tooltip("Recall:Q", format=".2f")])
        st.altair_chart(theme(ch.properties(height=430)), width="stretch")

    st.markdown("**Brecha por registro lingüístico (posterior bayesiana, intervalo del 90%)**")
    post = []
    for g, lab in REG_LABEL.items():
        d = perf[{"formal": "p_formal", "coloquial": "p_coloquial", "errores_stt": "p_stt"}[g]]
        post.append({"Registro": lab, "media": float(d.mean()), "p05": float(np.quantile(d, .05)),
                     "p95": float(np.quantile(d, .95))})
    dp = pd.DataFrame(post)
    rule = alt.Chart(dp).mark_rule(strokeWidth=2, color=C1).encode(
        y=alt.Y("Registro:N", title=None, sort=list(REG_LABEL.values())),
        x=alt.X("p05:Q", scale=alt.Scale(domain=[0, 1]),
                title="Probabilidad de resolver bien"), x2="p95:Q")
    dot = alt.Chart(dp).mark_circle(size=90, color=C1, stroke="white", strokeWidth=2, opacity=1).encode(
        y=alt.Y("Registro:N", sort=list(REG_LABEL.values())), x="media:Q",
        tooltip=["Registro", alt.Tooltip("media:Q", format=".1%"), alt.Tooltip("p05:Q", format=".1%"),
                 alt.Tooltip("p95:Q", format=".1%")])
    st.altair_chart(theme(alt.layer(rule, dot).properties(height=150)), width="stretch")
    gap = perf["p_formal"] - perf["p_coloquial"]
    st.caption(f"Probabilidad de que el registro coloquial esté peor atendido que el formal: "
               f"**{pct(float(np.mean(gap > 0)), 0)}**; brecha media de {100 * gap.mean():.1f} puntos.")
    with st.expander("Matriz de confusión (filas = intención real, columnas = lo que hizo el agente)"):
        cm = pd.DataFrame(intents.confusion(rows_now)).T.rename(index=INTENT_LABEL, columns=INTENT_LABEL)
        st.dataframe(cm, width="stretch")
    with st.expander("Casos que todavía fallan"):
        st.dataframe(pd.DataFrame([{"id": r["id"], "intención": r["intent"], "registro": r["register"],
                                    "crítica": r["critical"], "frase": r["text"], "respuesta": r["response"][:90]}
                                   for r in rows_now if r["passes"] != "True"]), hide_index=True,
                     width="stretch")

# ----------------------------------------------------------------------------- 3. monte carlo
with tabs[2]:
    st.markdown("**Comparación de escenarios de decisión** (cada uno con 5,000 simulaciones y la misma posterior)")
    comp = []
    for key, e in montecarlo.ESCENARIOS.items():
        r = montecarlo.run_scenario(perf, key, n=5_000, seed=int(seed))
        comp.append({"Escenario": e["nombre"], "P(VPN>0)": r.prob("vpn_36m", ">", 0),
                     "P(ROI año 1>0)": r.prob("roi_anio1", ">", 0), "Ahorro neto P50": r.stats("neto_mes")["p50"],
                     "Horas liberadas P50": r.stats("horas_liberadas_mes")["p50"]})
    st.dataframe(pd.DataFrame(comp).style.format({"P(VPN>0)": "{:.0%}", "P(ROI año 1>0)": "{:.0%}",
                                                  "Ahorro neto P50": "US${:,.0f}", "Horas liberadas P50": "{:,.0f}"}),
                 hide_index=True, width="stretch")

    vols = [30_000, 50_000, 80_000, 120_000, 160_000, 200_000, 250_000, 300_000]
    curve = []
    for name, ov, fac in (("Nube, desempeño actual", {}, 1.0), ("Stack local, desempeño actual", montecarlo.LOCAL, 1.0),
                          ("Stack local, error crítico ≤1%", montecarlo.LOCAL, 0.2)):
        for p in montecarlo.curva_volumen(perf, vols, ov, fac, n=2_000):
            curve.append({"Configuración": name, "Llamadas al mes": p["llamadas_mes"], "P(VPN>0)": p["p_vpn_positivo"]})
    dc = pd.DataFrame(curve)
    dom = ["Nube, desempeño actual", "Stack local, desempeño actual", "Stack local, error crítico ≤1%"]
    base = alt.Chart(dc).encode(
        x=alt.X("Llamadas al mes:Q", axis=alt.Axis(format="~s"), title="Llamadas mensuales del contact center"),
        y=alt.Y("P(VPN>0):Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%"),
                title="Probabilidad de VPN positivo"),
        color=alt.Color("Configuración:N", scale=alt.Scale(domain=dom, range=[C1, C2, C3]), title=None),
        tooltip=["Configuración", alt.Tooltip("Llamadas al mes:Q", format=","),
                 alt.Tooltip("P(VPN>0):Q", format=".0%")])
    line = base.mark_line(strokeWidth=2) + base.mark_circle(size=64, opacity=1, stroke="white", strokeWidth=2)
    meta = alt.Chart(pd.DataFrame({"y": [0.8]})).mark_rule(color=INK2, strokeWidth=1).encode(y="y:Q")
    st.altair_chart(theme(alt.layer(line, meta).properties(height=320, title="¿A partir de qué volumen se paga solo? "
                                                                             "(línea = 80% de confianza)")),
                    width="stretch")

    df = pd.DataFrame({"VPN a 36 meses": o["vpn_36m"]})
    h2 = alt.Chart(df).mark_bar(color=C1, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("VPN a 36 meses:Q", bin=alt.Bin(maxbins=50), title="VPN a 36 meses (US$)", axis=alt.Axis(format="~s")),
        y=alt.Y("count():Q", title="Escenarios"))
    st.altair_chart(theme(alt.layer(h2, zero).properties(height=240, title="Escenario seleccionado: VPN a 36 meses")),
                    width="stretch")

# ----------------------------------------------------------------------------- 4. sensibilidad
with tabs[3]:
    st.markdown("**Tornado: cada variable en su percentil 10 y 90, con las demás en la mediana** (ahorro neto mensual)")
    tor = montecarlo.tornado(perf_s, "neto_mes")[:12]
    dt = pd.DataFrame([{"Variable": LABEL[t["variable"]], "Percentil": "P10", "Ahorro neto": t["salida_bajo"]}
                       for t in tor] + [
                          {"Variable": LABEL[t["variable"]], "Percentil": "P90", "Ahorro neto": t["salida_alto"]}
                          for t in tor])
    order = [LABEL[t["variable"]] for t in tor]
    ch = alt.Chart(dt).mark_circle(size=90, opacity=1, stroke="white", strokeWidth=2).encode(
        y=alt.Y("Variable:N", sort=order, title=None),
        x=alt.X("Ahorro neto:Q", title="Ahorro neto mensual (US$)", axis=alt.Axis(format="~s")),
        color=alt.Color("Percentil:N", scale=alt.Scale(domain=["P10", "P90"], range=[C1, C2]), title=None),
        tooltip=["Variable", "Percentil", alt.Tooltip("Ahorro neto:Q", format=",.0f")])
    bars = alt.Chart(pd.DataFrame([{"Variable": LABEL[t["variable"]], "a": min(t["salida_bajo"], t["salida_alto"]),
                                    "b": max(t["salida_bajo"], t["salida_alto"])} for t in tor])).mark_rule(
        color=GRID, strokeWidth=6).encode(y=alt.Y("Variable:N", sort=order), x="a:Q", x2="b:Q")
    base_rule = alt.Chart(pd.DataFrame({"x": [tor[0]["base"]]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
    st.altair_chart(theme(alt.layer(bars, ch, base_rule).properties(height=420)), width="stretch")
    st.markdown("**Correlación de rangos (Spearman) entre cada entrada y el ahorro neto**")
    sp = montecarlo.spearman(res, "neto_mes")
    st.dataframe(pd.DataFrame([{"Variable": LABEL.get(k, k), "ρ de Spearman": v} for k, v in list(sp.items())[:12]])
                 .style.format({"ρ de Spearman": "{:+.2f}"}), hide_index=True, width="stretch")

# ----------------------------------------------------------------------------- 5. mcmc
with tabs[4]:
    k = st.columns(4)
    k[0].metric("R-hat máximo", f"{max(diag['rhat'].values()):.3f}", help="Menor que 1.01 indica convergencia.")
    k[1].metric("Tamaño efectivo mínimo", f"{min(diag['ess'].values()):,.0f}")
    k[2].metric("Aceptación (modelo jerárquico)", pct(diag["aceptacion"], 0))
    k[3].metric("Aceptación (Beta-Binomial)", pct(diag["aceptacion_beta"], 0))
    st.caption("Modelo jerárquico logit con Metropolis dentro de Gibbs: 4 cadenas, 3,000 de calentamiento y 8,000 "
               "muestras por cadena. La tasa de acción equivocada en intenciones críticas usa una Beta-Binomial "
               "muestreada con Metropolis y validada contra su solución conjugada.")
    tr = []
    for g in ("formal", "coloquial"):
        for c, chain in enumerate(diag["cadenas"][g]):
            tr += [{"Iteración": i, "Valor": v, "Cadena": f"Cadena {c + 1}", "Registro": REG_LABEL[g]}
                   for i, v in enumerate(chain)]
    dtr = pd.DataFrame(tr)
    ch = alt.Chart(dtr).mark_line(strokeWidth=1, opacity=0.8).encode(
        x="Iteración:Q", y=alt.Y("Valor:Q", scale=alt.Scale(zero=False), title="p"),
        color=alt.Color("Cadena:N", scale=alt.Scale(range=[C1, C2, C3, INK2]), title=None),
        row=alt.Row("Registro:N", title=None))
    st.altair_chart(theme(ch.properties(height=140, width=900)), width="content")

# ----------------------------------------------------------------------------- 6. agente en vivo
with tabs[5]:
    from src import nlu
    from src.agent import Session, respond

    st.markdown("Escriba lo que diría un cliente y vea cómo lo entiende el agente: texto normalizado, intención "
                "detectada y acción tomada. Todo corre localmente, sin API.")
    q = st.text_input("Frase del cliente", "Bórrenme de esa lista, no me llamen más")
    if q:
        a, _ = respond(q, Session(), mode="DEMO")
        row = {"tools": ";".join(e["name"] for e in a.tools), "status": a.status, "response": a.text}
        c1, c2 = st.columns(2)
        c1.markdown(f"**Texto normalizado:** `{nlu.canon(q)}`")
        c1.markdown(f"**Intención detectada:** {intents.predicted_intent(row).replace('_', ' ')}")
        c1.markdown(f"**Herramientas:** {row['tools'] or 'ninguna'} · **Estado:** {a.status} · {a.elapsed_ms} ms")
        c2.info(a.text)

# ----------------------------------------------------------------------------- 7. supuestos
with tabs[6]:
    st.dataframe(pd.DataFrame([{"Grupo": s.group, "Variable": s.label, "Unidad": s.unit, "Mínimo": s.low,
                                "Más probable": s.mode, "Máximo": s.high, "Fuente o justificación": s.source}
                               for s in SUPUESTOS]), hide_index=True, width="stretch")
    st.caption("Las fuentes [S1] a [S7] se detallan en analytics/assumptions.py y en el informe. [E] indica un "
               "supuesto del equipo que debe validarse en el piloto.")

# ----------------------------------------------------------------------------- indicadores operativos observados
with tabs[7]:
    st.markdown("#### Métricas locales de Gradio")
    st.caption(
        "Estos indicadores proceden de SQLite. No representan una medición de precisión, WER, satisfacción ni costos LIVE.")
    from src.storage import telemetry_summary

    try:
        telemetry = telemetry_summary()
    except Exception as exc:
        st.warning(f"Telemetría no disponible: {type(exc).__name__}")
    else:
        for mode in ("DEMO", "LIVE"):
            values = telemetry[mode]
            st.markdown(f"**Modo {mode}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Interacciones Gradio registradas", str(values["interacciones_gradio_observadas"]))
            p50 = values["latencia_aplicacion_p50_ms"]
            p95 = values["latencia_aplicacion_p95_ms"]
            c2.metric("Latencia aplicación P50", "Sin datos" if p50 is None else f"{p50:,.1f} ms")
            c3.metric("Latencia aplicación P95", "Sin datos" if p95 is None else f"{p95:,.1f} ms")
    st.info(
        "Las llamadas reales gestionadas por Twilio se registran en sus eventos y logs; no se incluyen en los contadores Gradio.")
