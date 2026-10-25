"""Invariantes de impacto: resultados sintéticos reproducibles, sin costos omitidos."""
import pytest
from dataclasses import replace
from src.impact import Assumptions, simulate, compare_cases
from src.dashboard.executive import technical_kpis


def test_repeatable():
    s1, _ = simulate(Assumptions(n_runs=1010))
    s2, _ = simulate(Assumptions(n_runs=1010))
    assert s1 == s2


def test_simulation_size_and_bounds():
    summary, traces = simulate(Assumptions(n_runs=1000))
    assert len(traces['annual_net_dop']) == 1000
    assert 0 <= summary['probability_positive_net'] <= 1
    assert summary['annual_net_dop']['p5'] <= summary['annual_net_dop']['p50'] <= summary['annual_net_dop']['p95']


def test_no_resolution_never_profitable():
    summary, _ = simulate(Assumptions(n_runs=1000, safe_resolution=0))
    assert summary['probability_positive_net'] == 0


def test_increasing_success_improves_outcome():
    p = Assumptions(n_runs=2000)
    lo, _ = simulate(replace(p, safe_resolution=0.1))
    hi, _ = simulate(replace(p, safe_resolution=0.8))
    assert hi['annual_net_dop']['p50'] > lo['annual_net_dop']['p50']


def test_zero_uncertainty_is_deterministic():
    p = Assumptions(n_runs=300, uncertainty=0)
    s, t = simulate(p)
    assert s['annual_net_dop']['p5'] == s['annual_net_dop']['p95']


def test_invalid_values():
    with pytest.raises(ValueError): simulate(Assumptions(safe_resolution=1.1))
    with pytest.raises(ValueError): simulate(Assumptions(n_runs=10))


def test_compare_labels_not_observed():
    cases, _ = compare_cases(Assumptions(n_runs=500))
    assert 'stress_illustrative' in cases
    assert 'HIPOTÉTICA' in cases['target_hypothetical']['scope']


def test_offline_scope():
    assert 'DEMO' in technical_kpis()['scope']
