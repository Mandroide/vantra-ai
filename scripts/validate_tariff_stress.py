"""Reproduce la sensibilidad económica de Fase 3 sobre la posterior archivada.

    uv run --locked --group dashboard python -m scripts.validate_tariff_stress

No altera ni regenera el conjunto congelado. Muestra escenarios CONDICIONALES.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from analytics import montecarlo as mc

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "results/fase3/posterior_despues.csv"
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    perf = {key: np.array([float(r[key]) for r in rows]) for key in mc.PERF_KEYS}
    scenarios = [
        ("Original local + reducción de error 80%",
         mc.run_scenario(perf, "grande_local_guardrail", n=10000, seed=2026)),
        ("Todos minutos Twilio saliente local",
         mc.run_tariff_stress(perf, mc.TWILIO_RD_SALIENTE_LOCAL_USD_MIN, n=10000, seed=2026)),
        ("Todos minutos Twilio saliente móvil",
         mc.run_tariff_stress(perf, mc.TWILIO_RD_SALIENTE_MOVIL_USD_MIN, n=10000, seed=2026)),
    ]
    print("Hipótesis, no mediciones del banco. Todos los minutos de estrés se suponen salientes.")
    for name, result in scenarios:
        print(f"{name}: P(VPN>0)={result.prob('vpn_36m', '>', 0) * 100:.2f}%; "
              f"Neto P50={result.stats('neto_mes')['p50']:,.0f} USD/mes")
    print(f"Muestras posteriores con tasa crítica escalada >1%: "
          f"{100 * np.mean(perf['p_error_critico'] * 0.2 > 0.01):.2f}%")


if __name__ == "__main__":
    main()
