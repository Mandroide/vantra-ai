"""Evaluación reproducible de anotaciones LIVE *locales y sintéticas/autorizadas*.

Entrada CSV (no versionar archivos reales): scenario_id,register,intent_reference,
intent_predicted,reference_transcript,stt_transcript,turn_latency_ms,
task_pass,critical_policy_pass.

No exporta transcripciones: emite solo métricas agregadas con tamaños de muestra.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from src.kpis import intent_metrics, latency_percentiles, word_error_rate

FIELDS = ('scenario_id', 'register', 'intent_reference', 'intent_predicted',
          'reference_transcript', 'stt_transcript', 'turn_latency_ms',
          'task_pass', 'critical_policy_pass')


def evaluate_rows(rows: list[dict]) -> dict:
    if not rows:
        return {'n': 0, 'message': 'Sin mediciones LIVE', 'groups': {}}
    groups = {}
    for label in sorted(set(row['register'] for row in rows) | {'all'}):
        selected = rows if label == 'all' else [r for r in rows if r['register'] == label]
        if not selected:
            continue
        wers = [word_error_rate(r['reference_transcript'], r['stt_transcript']) for r in selected]
        latencies = [float(r['turn_latency_ms']) for r in selected]
        if any(not math.isfinite(v) or v < 0 for v in latencies):
            raise ValueError('Latencia no válida; revise la anotación')
        w = [v for v in wers if v is not None]
        task_pass = sum(r['task_pass'].strip().lower() == 'true' for r in selected)
        critical = [r for r in selected if r['critical_policy_pass'].strip().lower() in {'true', 'false'}]
        groups[label] = {
            'n': len(selected),
            'task_success_rate': round(task_pass / len(selected), 4),
            'macro_f1': intent_metrics([r['intent_reference'] for r in selected],
                                       [r['intent_predicted'] for r in selected])['macro_f1'],
            'mean_utterance_wer': round(sum(w) / len(w), 4) if w else None,
            'n_wer': len(w),
            'latency': latency_percentiles(latencies),
            'critical_policy_n': len(critical),
            'critical_policy_success_rate': (round(sum(r['critical_policy_pass'].strip().lower() == 'true'
                                                       for r in critical) / len(critical), 4)
                                             if critical else None),
        }
    return {'n': len(rows), 'source': 'anotaciones LIVE locales, no inferidas del modo DEMO',
            'groups': groups}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Agregados de métricas LIVE (sin transcripciones en salida)')
    parser.add_argument('input_csv', type=Path)
    parser.add_argument('--output', type=Path, default=Path('results/live_metrics_private.json'))
    args = parser.parse_args(argv)
    with args.input_csv.open(newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            parser.error(f'Columnas faltantes: {sorted(missing)}')
        data = list(reader)
    result = evaluate_rows(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Evaluadas {result['n']} anotaciones; resultados agregados en {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
