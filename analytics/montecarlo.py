"""Simulación Monte Carlo del impacto operativo y financiero de desplegar Vantra AI en un contact center bancario.

Cada escenario combina una muestra de los supuestos operativos (analytics/assumptions.py) con una muestra de la
posterior bayesiana del desempeño del agente (analytics/mcmc.py). Así la incertidumbre de la evaluación se propaga
hasta el ROI, en lugar de usar un solo número de exactitud.

Lógica por escenario (mensual):
  resolución r   = coloquial*p_col + (1-coloquial)*[(1-err)*p_formal + err*p_stt]
  contenidas     = llamadas * alcance * r * aceptación          -> no requieren asesor
  transferidas   = llamadas * alcance - contenidas              -> pasan a un asesor (política de derivación)
  costo/min asesor = salario * carga / (horas pagadas * 60 * utilización)            [RD$ -> US$]
  ahorro bruto   = contenidas * AHT * costo/min  -  transferidas * minutos extra * costo/min
  costo bot      = (contenidas*min_bot + transferidas*min_bot_fallo) * costo/min_bot + operación fija
  riesgo         = llamadas * alcance * críticas * p_accion_equivocada * costo por error crítico
  neto           = ahorro bruto - costo bot - riesgo
  ROI año 1      = (12 * neto - inversión) / inversión;  payback = inversión / neto;  VPN a 36 meses al 12%
  horas liberadas = contenidas * AHT / 60;  FTE equivalentes = horas / (horas pagadas * utilización)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from analytics.assumptions import (BY_KEY, DOP_PER_USD, HORAS_PAGADAS_MES, HORIZONTE_MESES, SUPUESTOS,
                                   TASA_DESCUENTO_ANUAL)

PERF_KEYS = ("p_formal", "p_coloquial", "p_stt", "p_error_critico")


def sample_triangular(rng, n: int, overrides: dict | None = None) -> dict[str, np.ndarray]:
    """Muestra todos los supuestos. overrides: {clave: valor fijo} o {clave: (low, mode, high)}."""
    overrides = overrides or {}
    out = {}
    for s in SUPUESTOS:
        o = overrides.get(s.key)
        if o is None:
            out[s.key] = rng.triangular(s.low, s.mode, s.high, n)
        elif isinstance(o, (tuple, list)):
            lo, mo, hi = o
            out[s.key] = rng.triangular(lo, mo, hi, n) if hi > lo else np.full(n, float(mo))
        else:
            out[s.key] = np.full(n, float(o))
    return out


def evaluate(x: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Calcula las salidas a partir de entradas vectorizadas (supuestos + desempeño)."""
    en_alcance = x["llamadas_mes"] * x["alcance"]
    r = x["coloquial"] * x["p_coloquial"] + (1 - x["coloquial"]) * (
        (1 - x["errores_stt"]) * x["p_formal"] + x["errores_stt"] * x["p_stt"])
    contenidas = en_alcance * r * x["aceptacion"]
    transferidas = en_alcance - contenidas
    costo_min_asesor = x["salario"] * x["carga"] / (HORAS_PAGADAS_MES * 60 * x["utilizacion"]) / DOP_PER_USD
    ahorro_bruto = contenidas * x["aht"] * costo_min_asesor - transferidas * x["aht_extra"] * costo_min_asesor
    costo_bot = (contenidas * x["min_bot"] + transferidas * x["min_bot_fallo"]) * x["costo_min_bot"] + x[
        "operacion_mes"]
    riesgo = en_alcance * x["criticas"] * x["p_error_critico"] * x["costo_error_critico"]
    neto = ahorro_bruto - costo_bot - riesgo
    roi = (12 * neto - x["inversion"]) / x["inversion"]
    payback = np.where(neto > 0, x["inversion"] / np.maximum(neto, 1e-9), np.inf)
    i = (1 + TASA_DESCUENTO_ANUAL) ** (1 / 12) - 1
    annuity = (1 - (1 + i) ** -HORIZONTE_MESES) / i
    vpn = neto * annuity - x["inversion"]
    horas = contenidas * x["aht"] / 60
    fte = horas / (HORAS_PAGADAS_MES * x["utilizacion"])
    return {"tasa_resolucion": r * x["aceptacion"], "contenidas_mes": contenidas, "transferidas_mes": transferidas,
            "costo_min_asesor_usd": costo_min_asesor, "ahorro_bruto_mes": ahorro_bruto, "costo_bot_mes": costo_bot,
            "riesgo_mes": riesgo, "neto_mes": neto, "roi_anio1": roi, "payback_meses": payback, "vpn_36m": vpn,
            "horas_liberadas_mes": horas, "fte_liberados": fte,
            "costo_por_llamada_bot": costo_bot / np.maximum(contenidas + transferidas, 1),
            "costo_por_llamada_humana": x["aht"] * costo_min_asesor}


@dataclass
class Result:
    inputs: dict[str, np.ndarray]
    outputs: dict[str, np.ndarray]

    def stats(self, key: str) -> dict:
        v = self.outputs[key]
        finite = v[np.isfinite(v)]
        if finite.size == 0:  # p. ej. payback cuando ningún escenario recupera la inversión
            return {"media": None, "p05": None, "p50": None, "p95": None, "proporcion_finita": 0.0}
        out = {"media": float(np.mean(finite)), "p05": float(np.quantile(finite, 0.05)),
               "p50": float(np.quantile(finite, 0.5)), "p95": float(np.quantile(finite, 0.95))}
        if finite.size < v.size:
            out["proporcion_finita"] = float(finite.size / v.size)
        return out

    def prob(self, key: str, op: str, thr: float) -> float:
        v = self.outputs[key]
        return float(np.mean(v > thr) if op == ">" else np.mean(v < thr))


def run(perf_draws: dict[str, np.ndarray], n: int = 10_000, seed: int = 2026, overrides: dict | None = None) -> Result:
    """perf_draws: muestras de la posterior para p_formal, p_coloquial, p_stt y p_error_critico."""
    rng = np.random.default_rng(seed)
    x = sample_triangular(rng, n, overrides)
    for k in PERF_KEYS:
        d = np.asarray(perf_draws[k])
        x[k] = d[rng.integers(0, len(d), n)]  # remuestreo de la posterior
    return Result(inputs=x, outputs=evaluate(x))


def _rank(a):
    r = np.empty(len(a))
    r[np.argsort(a, kind="mergesort")] = np.arange(len(a))
    return r


def spearman(res: Result, target: str = "neto_mes") -> dict[str, float]:
    """Correlación de rangos entre cada entrada y la salida: qué incertidumbre pesa más en el resultado."""
    y = _rank(res.outputs[target])
    out = {}
    for k, v in res.inputs.items():
        if np.ptp(v) == 0:
            continue
        out[k] = float(np.corrcoef(_rank(v), y)[0, 1])
    return dict(sorted(out.items(), key=lambda kv: -abs(kv[1])))


def tornado(perf_draws: dict[str, np.ndarray], target: str = "neto_mes", lo_q: float = 0.10,
            hi_q: float = 0.90) -> list[dict]:
    """Sensibilidad de una variable a la vez: cada entrada en su P10 y P90 con las demás en su mediana."""
    base = {s.key: np.array([np.median(np.random.default_rng(0).triangular(s.low, s.mode, s.high, 20000))])
            for s in SUPUESTOS}
    for k in PERF_KEYS:
        base[k] = np.array([float(np.median(perf_draws[k]))])
    base_val = float(evaluate(base)[target][0])
    rows = []
    rng = np.random.default_rng(1)
    for key in [s.key for s in SUPUESTOS] + list(PERF_KEYS):
        if key in PERF_KEYS:
            lo, hi = np.quantile(perf_draws[key], [lo_q, hi_q])
        else:
            s = BY_KEY[key]
            sample = rng.triangular(s.low, s.mode, s.high, 20000)
            lo, hi = np.quantile(sample, [lo_q, hi_q])
        vals = []
        for v in (lo, hi):
            x = {k: a.copy() for k, a in base.items()}
            x[key] = np.array([v])
            vals.append(float(evaluate(x)[target][0]))
        rows.append({"variable": key, "bajo": float(lo), "alto": float(hi), "salida_bajo": vals[0],
                     "salida_alto": vals[1], "rango": abs(vals[1] - vals[0]), "base": base_val})
    return sorted(rows, key=lambda r: -r["rango"])


# ----------------------------------------------------------------------------- escenarios de decisión
GRANDE = {"llamadas_mes": (120_000, 150_000, 200_000)}
LOCAL = {"costo_min_bot": (0.005, 0.01, 0.02), "operacion_mes": (2_500, 4_000, 6_000),
         "inversion": (25_000, 35_000, 50_000)}
ESCENARIOS = {
    "base": {"nombre": "Banco mediano, nube", "overrides": {}, "error_critico_factor": 1.0, "cerrar_brecha": False},
    "sin_brecha": {"nombre": "Banco mediano sin brecha coloquial", "overrides": {}, "error_critico_factor": 1.0,
                   "cerrar_brecha": True},
    "grande": {"nombre": "Banco grande, nube", "overrides": GRANDE, "error_critico_factor": 1.0,
               "cerrar_brecha": False},
    "grande_local": {"nombre": "Banco grande, stack local", "overrides": {**GRANDE, **LOCAL},
                     "error_critico_factor": 1.0, "cerrar_brecha": False},
    "grande_guardrail": {"nombre": "Banco grande, nube, error crítico ≤1%", "overrides": GRANDE,
                         "error_critico_factor": 0.2, "cerrar_brecha": False},
    "grande_local_guardrail": {"nombre": "Banco grande, stack local, error crítico ≤1%",
                               "overrides": {**GRANDE, **LOCAL}, "error_critico_factor": 0.2, "cerrar_brecha": False},
}


def apply_perf(perf: dict, error_critico_factor: float = 1.0, cerrar_brecha: bool = False) -> dict:
    """Modifica la posterior para escenarios hipotéticos (no son mediciones):
    error_critico_factor escala la tasa de acción equivocada en intenciones críticas (0.2 = meta de ~1%);
    cerrar_brecha iguala el desempeño coloquial al formal (meta de equidad)."""
    p = dict(perf)
    p["p_error_critico"] = np.asarray(perf["p_error_critico"]) * error_critico_factor
    if cerrar_brecha:
        p["p_coloquial"] = np.asarray(perf["p_formal"])
    return p


def run_scenario(perf: dict, key: str, n: int = 10_000, seed: int = 2026) -> Result:
    e = ESCENARIOS[key]
    return run(apply_perf(perf, e["error_critico_factor"], e["cerrar_brecha"]), n=n, seed=seed,
               overrides=e["overrides"])


def curva_volumen(perf: dict, volumenes, overrides: dict | None = None, error_critico_factor: float = 1.0,
                  n: int = 4_000, seed: int = 7) -> list[dict]:
    """P(VPN a 36 meses > 0) para cada volumen mensual fijo, con el resto de la incertidumbre intacta."""
    out = []
    p = apply_perf(perf, error_critico_factor)
    for v in volumenes:
        r = run(p, n=n, seed=seed, overrides={**(overrides or {}), "llamadas_mes": float(v)})
        out.append({"llamadas_mes": int(v), "p_vpn_positivo": r.prob("vpn_36m", ">", 0.0),
                    "neto_p50": r.stats("neto_mes")["p50"]})
    return out
