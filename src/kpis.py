"""Métricas de evaluación auditable; requieren etiquetas y audio de referencia reales."""
from collections import Counter
import numpy as np


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    """WER de Levenshtein por tokens; devuelve None si referencia vacía."""
    reference_words = reference.casefold().split()
    hypothesis_words = hypothesis.casefold().split()
    if not reference_words:
        return None
    previous = list(range(len(hypothesis_words) + 1))
    for i, word in enumerate(reference_words, 1):
        current = [i]
        for j, predicted in enumerate(hypothesis_words, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (word != predicted)))
        previous = current
    return previous[-1] / len(reference_words)


def intent_metrics(references: list[str], predictions: list[str]) -> dict:
    """Precisión, recall y F1 por etiqueta y macro-F1; sin entradas, no computable."""
    if len(references) != len(predictions):
        raise ValueError('Longitudes desiguales')
    if not references:
        return {'n': 0, 'macro_f1': None, 'by_label': {}}
    labels = sorted(set(references) | set(predictions))
    stats = {}
    for label in labels:
        tp = sum(r == label and p == label for r, p in zip(references, predictions))
        fp = sum(r != label and p == label for r, p in zip(references, predictions))
        fn = sum(r == label and p != label for r, p in zip(references, predictions))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        stats[label] = {'precision': round(precision, 4), 'recall': round(recall, 4),
                        'f1': round(f1, 4), 'support': sum(r == label for r in references)}
    return {'n': len(references), 'macro_f1': round(sum(s['f1'] for s in stats.values()) / len(stats), 4),
            'by_label': stats}


def latency_percentiles(milliseconds: list[float]) -> dict:
    if not milliseconds: return {'n': 0, 'p50_ms': None, 'p95_ms': None}
    values = np.asarray(milliseconds, float)
    if np.any(values < 0): raise ValueError('Latencia negativa')
    return {'n': len(values), 'p50_ms': round(float(np.percentile(values, 50)), 2),
            'p95_ms': round(float(np.percentile(values, 95)), 2)}
