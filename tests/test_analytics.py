"""Pruebas de la analítica de la Fase 3: MCMC, Monte Carlo y métricas discriminatorias."""
import numpy as np

from analytics import intents, mcmc, montecarlo
from analytics.assumptions import SUPUESTOS


def test_mcmc_beta_binomial_coincide_con_la_solucion_conjugada():
    k, n = 83, 114
    fit = mcmc.beta_binomial(k, n, draws=4000, seed=3)
    a, b = 1 + k, 1 + n - k
    assert abs(fit.draws["p"].mean() - a / (a + b)) < 0.005
    assert abs(fit.draws["p"].std() - (a * b / ((a + b) ** 2 * (a + b + 1))) ** 0.5) < 0.004
    assert fit.rhat["p"] < 1.02 and fit.ess["p"] > 1000
    assert 0.2 < fit.acceptance < 0.7


def test_mcmc_jerarquico_converge_y_respeta_el_orden():
    fit = mcmc.hierarchical([30, 22, 27], [40, 38, 36], ["a", "b", "c"], draws=2000, burn=1000, seed=5)
    assert max(fit.rhat.values()) < 1.05
    assert fit.draws["a"].mean() > fit.draws["b"].mean()
    # encogimiento parcial: la estimación de b se acerca a la media común respecto a su proporción cruda
    assert fit.draws["b"].mean() > 22 / 38


def _perf(n=4000, p=0.75):
    rng = np.random.default_rng(0)
    return {"p_formal": rng.beta(80, 20, n), "p_coloquial": rng.beta(60, 40, n), "p_stt": rng.beta(75, 25, n),
            "p_error_critico": rng.beta(2, 36, n)}


def test_montecarlo_es_reproducible():
    a = montecarlo.run(_perf(), n=2000, seed=9).outputs["neto_mes"]
    b = montecarlo.run(_perf(), n=2000, seed=9).outputs["neto_mes"]
    assert np.array_equal(a, b)


def _base(**changes):
    x = {s.key: np.array([s.mode]) for s in SUPUESTOS}
    x.update({"p_formal": np.array([0.8]), "p_coloquial": np.array([0.6]), "p_stt": np.array([0.75]),
              "p_error_critico": np.array([0.05])})
    x.update({k: np.array([v]) for k, v in changes.items()})
    return montecarlo.evaluate(x)


def test_modelo_monotono_en_las_palancas_principales():
    base = _base()
    assert _base(p_coloquial=0.8)["contenidas_mes"][0] > base["contenidas_mes"][0]
    assert _base(salario=45_000)["ahorro_bruto_mes"][0] > base["ahorro_bruto_mes"][0]
    assert _base(p_error_critico=0.01)["neto_mes"][0] > base["neto_mes"][0]
    assert _base(operacion_mes=1_500)["neto_mes"][0] > base["neto_mes"][0]
    assert _base(llamadas_mes=150_000)["horas_liberadas_mes"][0] > base["horas_liberadas_mes"][0]


def test_contabilidad_cuadra():
    o = _base()
    assert np.isclose(o["neto_mes"], o["ahorro_bruto_mes"] - o["costo_bot_mes"] - o["riesgo_mes"])
    modo = {s.key: s.mode for s in SUPUESTOS}
    assert np.isclose(o["contenidas_mes"] + o["transferidas_mes"], modo["llamadas_mes"] * modo["alcance"])


def test_escenarios_de_decision_ordenados():
    perf = _perf()
    p = {k: montecarlo.run_scenario(perf, k, n=3000).prob("vpn_36m", ">", 0) for k in montecarlo.ESCENARIOS}
    assert p["grande_local_guardrail"] >= p["grande_local"] >= p["base"]


def test_sensibilidad_devuelve_todas_las_variables():
    t = montecarlo.tornado(_perf())
    assert len(t) == len(SUPUESTOS) + len(montecarlo.PERF_KEYS)
    assert t[0]["rango"] >= t[-1]["rango"]


def test_intencion_predicha_desde_la_accion_del_agente():
    row = lambda **kw: {"tools": "", "status": "OK", "response": "", **kw}  # noqa: E731
    assert intents.predicted_intent(row(status="DENIED")) == "privacidad"
    assert intents.predicted_intent(row(status="DNC_REQUESTED")) == "exclusion_dnc"
    assert intents.predicted_intent(row(tools="request_human_transfer",
                                        response="Por seguridad... escalamiento ficticio #3")) == "fraude"
    assert intents.predicted_intent(row(tools="calculate_loan")) == "cotizacion"
    assert intents.predicted_intent(row(response="No tengo información verificada")) == "sin_resolver"


def test_metricas_por_clase():
    rows = [{"intent": "tasa", "tools": "get_interest_rate", "status": "OK", "response": ""},
            {"intent": "tasa", "tools": "", "status": "OK", "response": "No tengo"},
            {"intent": "fraude", "tools": "get_interest_rate", "status": "OK", "response": ""}]
    m = intents.per_class(rows)["por_intencion"]
    assert m["tasa"]["recall"] == 0.5 and m["tasa"]["precision"] == 0.5
    assert m["fraude"]["recall"] == 0.0
