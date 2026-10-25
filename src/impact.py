"""Escenarios económicos sintéticos para comité: NO son pronósticos ni métricas reales.

Modelo de 12 meses: ingresos evitados (solo fracción de capacidad humana realizable),
menos todas las llamadas enviadas a IA, gastos fijos y puesta en marcha.
La eficiencia tecnológica se interpreta como resolución segura, NO como mera respuesta.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np


@dataclass(frozen=True)
class Assumptions:
    monthly_calls: int = 12000
    eligible_share: float = 0.45
    safe_resolution: float = 0.70
    human_cost_dop: float = 95.0
    ai_attempt_cost_dop: float = 18.0
    labor_realization: float = 0.50
    fixed_monthly_dop: float = 35000.0
    setup_dop: float = 250000.0
    human_minutes: float = 5.0
    uncertainty: float = 0.20
    months: int = 12
    n_runs: int = 10000
    seed: int = 8269

    def validated(self):
        for name in ('eligible_share', 'safe_resolution', 'labor_realization'):
            value = getattr(self, name)
            if not (0 <= value <= 1):
                raise ValueError(f'{name} debe estar entre 0 y 1')
        for name in ('monthly_calls', 'human_cost_dop', 'ai_attempt_cost_dop',
                     'fixed_monthly_dop', 'setup_dop', 'human_minutes'):
            if getattr(self, name) < 0:
                raise ValueError(f'{name} no admite negativos')
        if not (0 <= self.uncertainty <= 0.8):
            raise ValueError('uncertainty debe estar entre 0 y 0.8')
        if self.months < 1 or not 100 <= self.n_runs <= 100000:
            raise ValueError('months o n_runs fuera de rango')
        return self


def _tri(rng, nominal, uncertainty, n, low=0.0, high=None):
    left = max(low, nominal * (1 - uncertainty))
    right = nominal * (1 + uncertainty)
    if high is not None:
        right = min(high, right)
    return rng.triangular(left, nominal, right, size=n) if left < right else np.full(n, nominal)


def simulate(config: Assumptions = Assumptions()):
    """Monte Carlo con bandas triangulares *supuestas*, y semillas repetibles."""
    p = config.validated()
    rng = np.random.default_rng(p.seed)
    n = p.n_runs
    sampled = {
        'monthly_calls': _tri(rng, p.monthly_calls, p.uncertainty, n),
        'eligible_share': _tri(rng, p.eligible_share, p.uncertainty, n, high=1),
        'safe_resolution': _tri(rng, p.safe_resolution, p.uncertainty, n, high=1),
        'human_cost_dop': _tri(rng, p.human_cost_dop, p.uncertainty, n),
        'ai_attempt_cost_dop': _tri(rng, p.ai_attempt_cost_dop, p.uncertainty, n),
        'labor_realization': _tri(rng, p.labor_realization, p.uncertainty, n, high=1),
        'fixed_monthly_dop': _tri(rng, p.fixed_monthly_dop, p.uncertainty, n),
        'setup_dop': _tri(rng, p.setup_dop, p.uncertainty, n),
    }
    attempts = sampled['monthly_calls'] * sampled['eligible_share']
    resolved = attempts * sampled['safe_resolution']
    monthly_avoided = resolved * sampled['human_cost_dop'] * sampled['labor_realization']
    monthly_api = attempts * sampled['ai_attempt_cost_dop']
    annual_avoided = monthly_avoided * p.months
    annual_cost = (monthly_api + sampled['fixed_monthly_dop']) * p.months + sampled['setup_dop']
    annual_net = annual_avoided - annual_cost
    # ROI sobre costo del proyecto, no sobre ingresos del banco.
    roi = np.divide(annual_net, annual_cost, out=np.zeros_like(annual_net), where=annual_cost > 0) * 100
    released_hours_month = resolved * p.human_minutes / 60
    # Solo parte monetizable estimada; el resto es capacidad liberada, no ahorro de caja.
    realized_hours_month = released_hours_month * sampled['labor_realization']
    quant = lambda v: dict(zip(('p5', 'p50', 'p95'), [round(float(x), 2) for x in np.percentile(v, [5, 50, 95])]))
    # Sensibilidad orientativa: correlación por rangos con beneficio neto.
    outcome_ranks = np.argsort(np.argsort(annual_net)).astype(float)
    sensitivity = {}
    for k, v in sampled.items():
        if np.std(v) < 1e-10:
            corr = 0
        else:
            corr = float(np.corrcoef(np.argsort(np.argsort(v)), outcome_ranks)[0, 1])
        sensitivity[k] = round(corr, 3)
    summary = {
        'scope': 'SIMULACIÓN HIPOTÉTICA, no datos operativos medidos ni ROI garantizado',
        'currency': 'DOP', 'runs': n, 'months': p.months, 'seed': p.seed,
        'assumptions': asdict(p),
        'annual_net_dop': quant(annual_net),
        'annual_roi_pct': quant(roi),
        'monthly_safe_resolutions': quant(resolved),
        'monthly_released_hours': quant(released_hours_month),
        'monthly_realized_hours': quant(realized_hours_month),
        'annual_cost_dop': quant(annual_cost),
        'probability_positive_net': round(float(np.mean(annual_net > 0)), 4),
        'sensitivity_spearman_approx': dict(sorted(sensitivity.items(), key=lambda e: abs(e[1]), reverse=True)),
        'limitations': [
            'Parámetros hipotéticos, no estimados de facturas ni muestras representativas',
            'Distribuciones triangulares independientes alrededor de valores elegidos; no captura shocks conjuntos',
            'Se computa costo evitado únicamente en la fracción labor_realization y no equivalen horas liberadas a caja',
            'No cuantifica pérdidas extremas de incidentes ni costes legales; requerirían datos adicionales',
            'La tasa de éxito técnico del DEMO no puede trasladarse directamente a llamadas LIVE',
        ],
    }
    traces = {'annual_net_dop': annual_net, 'annual_roi_pct': roi,
              'monthly_resolved': resolved, 'monthly_released_hours': released_hours_month,
              'annual_cost_dop': annual_cost}
    return summary, traces


def compare_cases(config: Assumptions):
    """Dos escenarios EXPLÍCITOS: estrés a 17.6% ilustrativo y meta al valor elegido.
    El 17.6% fue reportado por el equipo para frases nuevas DEMO; NO es tasa LIVE.
    """
    stress, _ = simulate(replace(config, safe_resolution=0.176))
    target, traces = simulate(config)
    return {'stress_illustrative': stress, 'target_hypothetical': target}, traces
