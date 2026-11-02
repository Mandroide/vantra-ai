"""Fase 3: métricas discriminatorias, MCMC bayesiano y Monte Carlo del impacto, antes y después de las mitigaciones.

    uv run python scripts/run_simulation.py            # lee results/holdout_v2_{antes,despues}_demo_cases.csv

Salidas en results/fase3/:
  resumen.json                 métricas, posteriores, Monte Carlo, probabilidades y sensibilidad
  posterior_<escenario>.csv    muestras MCMC (las usa el dashboard para simular en vivo)
  montecarlo_despues.csv       2,000 escenarios de ejemplo con entradas y salidas
Determinista: semillas fijas.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analytics import intents, mcmc, montecarlo  # noqa: E402
from analytics.assumptions import SUPUESTOS  # noqa: E402

RES = ROOT / "results"
OUT = RES / "fase3"
REGISTROS = ["formal", "coloquial", "errores_stt"]
N_MC = 10_000


def counts(rows, register):
    sub = [r for r in rows if r["register"] == register]
    return sum(r["passes"] == "True" for r in sub), len(sub)


def analyze(tag: str) -> dict:
    rows = intents.load_cases(RES / f"holdout_v2_{tag}_demo_cases.csv")
    k_n = {g: counts(rows, g) for g in REGISTROS}
    t0 = time.time()
    fit = mcmc.hierarchical([k_n[g][0] for g in REGISTROS], [k_n[g][1] for g in REGISTROS], REGISTROS,
                            seed=11 if tag == "despues" else 12)
    crit = intents.critical_breakdown(rows)
    fit_crit = mcmc.beta_binomial(crit["accion_equivocada"], crit["n"], seed=7)
    fit_crit_any = mcmc.beta_binomial(crit["fallos"], crit["n"], seed=8)
    k_all = sum(r["passes"] == "True" for r in rows)
    fit_all = mcmc.beta_binomial(k_all, len(rows), seed=9)
    mcmc_s = time.time() - t0

    # Validación del muestreador: la Beta-Binomial tiene solución conjugada exacta Beta(1+k, 1+n-k).
    a, b = 1 + k_all, 1 + len(rows) - k_all
    analytic_mean = a / (a + b)
    analytic_sd = (a * b / ((a + b) ** 2 * (a + b + 1))) ** 0.5

    perf = {"p_formal": fit.draws["formal"], "p_coloquial": fit.draws["coloquial"], "p_stt": fit.draws["errores_stt"],
            "p_error_critico": fit_crit.draws["p"]}
    t1 = time.time()
    mc = montecarlo.run(perf, n=N_MC, seed=2026)
    mc_s = time.time() - t1

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"posterior_{tag}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(perf))
        for row in zip(*[np.round(v, 5) for v in perf.values()]):
            w.writerow(row)
    if tag == "despues":
        idx = np.random.default_rng(0).choice(N_MC, 2000, replace=False)
        keys_in = [s.key for s in SUPUESTOS] + list(montecarlo.PERF_KEYS)
        keys_out = list(mc.outputs)
        with (OUT / "montecarlo_despues.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(keys_in + keys_out)
            for i in idx:
                w.writerow([round(float(mc.inputs[k][i]), 5) for k in keys_in] +
                           [round(float(mc.outputs[k][i]), 4) for k in keys_out])

    out_keys = ["tasa_resolucion", "contenidas_mes", "horas_liberadas_mes", "fte_liberados", "ahorro_bruto_mes",
                "costo_bot_mes", "riesgo_mes", "neto_mes", "roi_anio1", "payback_meses", "vpn_36m",
                "costo_por_llamada_bot", "costo_por_llamada_humana", "costo_min_asesor_usd"]
    return {
        "conteos_por_registro": {g: {"k": k_n[g][0], "n": k_n[g][1]} for g in REGISTROS},
        "exactitud_global": {"k": k_all, "n": len(rows)},
        "discriminativas": intents.per_class(rows),
        "criticos": crit,
        "latencia_demo": intents.latency(rows),
        "mcmc": {
            "jerarquico": fit.summary(), "aceptacion_jerarquico": fit.acceptance,
            "p_accion_equivocada_critica": fit_crit.summary()["p"], "p_fallo_critico": fit_crit_any.summary()["p"],
            "p_global": fit_all.summary()["p"], "aceptacion_beta": fit_all.acceptance,
            "validacion_conjugada": {"media_analitica": analytic_mean, "sd_analitica": analytic_sd,
                                     "media_mcmc": float(fit_all.draws["p"].mean()),
                                     "sd_mcmc": float(fit_all.draws["p"].std())},
            "prob_coloquial_menor_que_formal": float(np.mean(fit.draws["coloquial"] < fit.draws["formal"])),
            "brecha_formal_menos_coloquial": {
                "media": float(np.mean(fit.draws["formal"] - fit.draws["coloquial"])),
                "p05": float(np.quantile(fit.draws["formal"] - fit.draws["coloquial"], 0.05)),
                "p95": float(np.quantile(fit.draws["formal"] - fit.draws["coloquial"], 0.95))},
            "segundos": round(mcmc_s, 2),
        },
        "montecarlo": {
            "n": N_MC, "segundos": round(mc_s, 2),
            "salidas": {k: mc.stats(k) for k in out_keys},
            "prob_roi_positivo": mc.prob("roi_anio1", ">", 0.0),
            "prob_neto_positivo": mc.prob("neto_mes", ">", 0.0),
            "prob_payback_12m": float(np.mean(mc.outputs["payback_meses"] < 12)),
            "prob_vpn_positivo": mc.prob("vpn_36m", ">", 0.0),
            "spearman_neto": montecarlo.spearman(mc, "neto_mes"),
        },
        "tornado_neto": montecarlo.tornado(perf, "neto_mes") if tag == "despues" else None,
    }


def main() -> None:
    t = time.time()
    resumen = {"generado": time.strftime("%Y-%m-%d %H:%M:%S"), "escenarios": {}}
    for tag in ("antes", "despues"):
        resumen["escenarios"][tag] = analyze(tag)
        e = resumen["escenarios"][tag]
        m, j = e["montecarlo"], e["mcmc"]["jerarquico"]
        print(f"[{tag}] exactitud v2 {e['exactitud_global']['k']}/{e['exactitud_global']['n']} | "
              f"posterior formal {j['formal']['media']:.3f} coloquial {j['coloquial']['media']:.3f} "
              f"stt {j['errores_stt']['media']:.3f} (R-hat max {max(v['rhat'] for v in j.values()):.3f}) | "
              f"neto/mes P50 US${m['salidas']['neto_mes']['p50']:,.0f} | P(ROI>0) {m['prob_roi_positivo']:.1%} | "
              f"horas liberadas P50 {m['salidas']['horas_liberadas_mes']['p50']:,.0f}")
    # Escenarios de decisión y curva de viabilidad por volumen (sobre la posterior «después»).
    rows = list(csv.DictReader((OUT / "posterior_despues.csv").open(encoding="utf-8")))
    perf = {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}
    esc = {}
    for key, e in montecarlo.ESCENARIOS.items():
        r = montecarlo.run_scenario(perf, key)
        esc[key] = {"nombre": e["nombre"], "neto_mes": r.stats("neto_mes"), "roi_anio1": r.stats("roi_anio1"),
                    "vpn_36m": r.stats("vpn_36m"), "payback_meses": r.stats("payback_meses"),
                    "horas_liberadas_mes": r.stats("horas_liberadas_mes"), "fte_liberados": r.stats("fte_liberados"),
                    "prob_neto_positivo": r.prob("neto_mes", ">", 0), "prob_roi_positivo": r.prob("roi_anio1", ">", 0),
                    "prob_vpn_positivo": r.prob("vpn_36m", ">", 0),
                    "prob_payback_12m": float(np.mean(r.outputs["payback_meses"] < 12))}
        print(f"  escenario {e['nombre']:<48} P(VPN>0) {esc[key]['prob_vpn_positivo']:.1%}  "
              f"P(ROI año 1>0) {esc[key]['prob_roi_positivo']:.1%}  neto P50 US${esc[key]['neto_mes']['p50']:,.0f}")
    resumen["escenarios_decision"] = esc
    vols = [30_000, 50_000, 80_000, 120_000, 160_000, 200_000, 250_000, 300_000]
    resumen["curva_volumen"] = {
        "nube_actual": montecarlo.curva_volumen(perf, vols),
        "local_actual": montecarlo.curva_volumen(perf, vols, montecarlo.LOCAL),
        "local_guardrail": montecarlo.curva_volumen(perf, vols, montecarlo.LOCAL, error_critico_factor=0.2),
    }
    resumen["supuestos"] = [{"clave": s.key, "variable": s.label, "unidad": s.unit, "min": s.low, "moda": s.mode,
                             "max": s.high, "fuente": s.source, "grupo": s.group} for s in SUPUESTOS]
    resumen["segundos_total"] = round(time.time() - t, 1)
    (OUT / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, default=float),
                                      encoding="utf-8")
    print(f"Guardado en results/fase3/ ({resumen['segundos_total']} s)")


if __name__ == "__main__":
    main()
