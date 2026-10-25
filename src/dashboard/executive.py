"""Dashboard interactivo: indicadores observados *offline* separados de simulaciones."""
from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from src.impact import Assumptions, compare_cases
from src.storage import telemetry_summary

ROOT = Path(__file__).resolve().parents[2]


def technical_kpis():
    p = ROOT / 'results/summary_demo.json'
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
        return {
            'scope': d.get('evaluation_scope', 'DEMO, no LIVE'),
            'case_count': d.get('total'), 'passed_offline': d.get('passed'),
            'success_rate_offline': round(d.get('passed', 0) / max(d.get('total', 1), 1) * 100, 1),
            'live_wer': 'No medido', 'live_p95_latency': 'No medido',
            'live_cost': 'No medido',
            'telemetria_gradio': telemetry_summary(),
        }
    except (OSError, ValueError, TypeError):
        return {'scope': 'Datos de evaluación DEMO no disponibles'}


def make_plots(traces, sensitivity):
    fig1, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.hist(traces['annual_net_dop'] / 1000, bins=42, edgecolor='white', linewidth=0.4)
    ax.axvline(0, ls='--', lw=1.5, color='#B91C1C')
    ax.set(xlabel='Beneficio neto anual hipotético (miles RD$)', ylabel='Corridas',
           title='Monte Carlo: distribución de escenarios')
    fig1.tight_layout()
    top = list(sensitivity.items())[:7]
    fig2, ax2 = plt.subplots(figsize=(7.2, 3.2))
    ax2.barh([k for k, v in top][::-1], [v for k, v in top][::-1])
    ax2.set_xlim(-1, 1)
    ax2.set(xlabel='Correlación por rangos (aprox.)', title='Sensibilidad del beneficio neto')
    ax2.axvline(0, lw=0.7, color='gray')
    fig2.tight_layout()
    return fig1, fig2


def refresh_dashboard(volume, eligible, safe, cost_human, cost_ai, realization,
                      fixed_cost, setup, uncertainty, seed):
    cfg = Assumptions(
        monthly_calls=int(volume), eligible_share=eligible / 100,
        safe_resolution=safe / 100, human_cost_dop=cost_human,
        ai_attempt_cost_dop=cost_ai, labor_realization=realization / 100,
        fixed_monthly_dop=fixed_cost, setup_dop=setup,
        uncertainty=uncertainty / 100, seed=int(seed), n_runs=10000)
    cases, traces = compare_cases(cfg)
    target = cases['target_hypothetical'];
    stress = cases['stress_illustrative']

    def money(v): return f"RD$ {v:,.0f}"

    text = (f"### Escenario de inversión (SUPUESTOS, no resultados reales)\n"
            f"**Beneficio neto anual P50:** {money(target['annual_net_dop']['p50'])}  ·  "
            f"**ROI P50:** {target['annual_roi_pct']['p50']:.1f}%  ·  "
            f"**P(neto > 0):** {target['probability_positive_net'] * 100:.1f}%\n\n"
            f"**P5 / P95:** {money(target['annual_net_dop']['p5'])} / {money(target['annual_net_dop']['p95'])}  ·  "
            f"**Horas liberadas/mes P50:** {target['monthly_released_hours']['p50']:,.0f} "
            f"(monetizables: {target['monthly_realized_hours']['p50']:,.0f})\n\n"
            f"**Estrés ilustrativo con resolución 17.6%:** ROI P50 {stress['annual_roi_pct']['p50']:.1f}%; "
            f"no representa desempeño LIVE.\n\n"
            f"*Se supone incertidumbre triangular ±{uncertainty:.0f}% independiente. "
            f"Solo se monetiza una fracción de las horas liberadas.*")
    f1, f2 = make_plots(traces, target['sensitivity_spearman_approx'])
    return text, f1, f2, cases


def build_dashboard_tab():
    with gr.Tab('Dashboard ejecutivo · KPIs y Monte Carlo'):
        gr.Markdown(
            '## Impacto y riesgo de Vantra AI\n**La simulación es hipotética.** No equivale a ahorro, precisión LIVE ni facturación observados.')
        tech = gr.JSON(value=technical_kpis(), label='Evidencia DEMO + telemetría de aplicación (sin audio)')
        gr.Button('Actualizar telemetría registrada').click(technical_kpis, outputs=tech)
        with gr.Accordion('Hipótesis para escenarios y sensibilidad (RD$)', open=True):
            with gr.Row():
                volume = gr.Slider(1000, 40000, value=12000, step=1000, label='Llamadas mensuales')
                eligible = gr.Slider(0, 100, value=45, step=1, label='% elegibles para IA')
                safe = gr.Slider(0, 100, value=70, step=1, label='% resolución segura HIPOTÉTICA')
            with gr.Row():
                cost_human = gr.Slider(20, 250, value=95, step=5, label='Costo humano por llamada (RD$)')
                cost_ai = gr.Slider(2, 90, value=18, step=2, label='Costo IA por intento (RD$)')
                realization = gr.Slider(0, 100, value=50, step=5, label='% valor laboral realizable')
            with gr.Row():
                fixed_cost = gr.Slider(0, 150000, value=35000, step=5000, label='Operación fija mensual (RD$)')
                setup = gr.Slider(0, 1000000, value=250000, step=25000, label='Inversión inicial (RD$)')
                uncertainty = gr.Slider(0, 60, value=20, step=5, label='Variación triangular ±%')
                seed = gr.Number(value=8269, precision=0, label='Semilla reproducible')
            go = gr.Button('Ejecutar 10,000 corridas de Monte Carlo', variant='primary')
        headline = gr.Markdown()
        with gr.Row():
            histogram = gr.Plot(label='Beneficio neto anual')
            impact = gr.Plot(label='Sensibilidad')
        detail = gr.JSON(label='Resultados exportables y supuestos (simulación)')
        inputs = [volume, eligible, safe, cost_human, cost_ai, realization, fixed_cost, setup, uncertainty, seed]
        outputs = [headline, histogram, impact, detail]
        go.click(refresh_dashboard, inputs=inputs, outputs=outputs)
        gr.Markdown(
            '**Gobernanza:** no autorizar despliegue autónomo si falla fraude, DNC, privacidad o escalamiento. Consulte `docs/ethics.md`.')
