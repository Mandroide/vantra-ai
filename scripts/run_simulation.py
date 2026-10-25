"""Genera escenario Monte Carlo reproducible y exporta datos para informe/pitch."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.impact import Assumptions, compare_cases


def main(argv=None):
    parser = argparse.ArgumentParser(description='Simulación hipotética de impacto Vantra AI')
    parser.add_argument('--runs', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=8269)
    parser.add_argument('--safe-resolution', type=float, default=0.70)
    parser.add_argument('--output', default='results/impact')
    args = parser.parse_args(argv)
    cfg = Assumptions(n_runs=args.runs, seed=args.seed, safe_resolution=args.safe_resolution)
    summary, traces = compare_cases(cfg)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'monte_carlo_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                                     encoding='utf-8')
    with (output / 'monte_carlo_samples.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(
            ['run', 'annual_net_dop', 'annual_roi_pct', 'monthly_safe_resolutions', 'monthly_released_hours',
             'annual_cost_dop'])
        for i in range(len(traces['annual_net_dop'])):
            writer.writerow([i + 1, *[round(float(traces[key][i]), 4) for key in
                                      ['annual_net_dop', 'annual_roi_pct', 'monthly_resolved', 'monthly_released_hours',
                                       'annual_cost_dop']]])
    print(json.dumps(
        {k: {'p50_roi': v['annual_roi_pct']['p50'], 'p_positive': v['probability_positive_net']} for k, v in
         summary.items()}, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    main()
