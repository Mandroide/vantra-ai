import numpy as np
import pytest

from analytics import montecarlo as mc


def posterior_sintetica():
    return {"p_formal": np.full(80, .8), "p_coloquial": np.full(80, .6),
            "p_stt": np.full(80, .7), "p_error_critico": np.full(80, .06)}


def test_escenarios_son_reduccion_hipotetica_no_limite():
    assert "reducción hipotética 80%" in mc.ESCENARIOS["grande_local_guardrail"]["nombre"]
    p = mc.apply_perf(posterior_sintetica(), error_critico_factor=.2)
    assert np.allclose(p["p_error_critico"], .012)
    assert np.any(p["p_error_critico"] > .01)  # no impone ≤1%


def test_estres_tarifa_subida_empeora_vpn_misma_semilla():
    perf = posterior_sintetica()
    a = mc.run_tariff_stress(perf, .1155, n=1000, seed=2026)
    b = mc.run_tariff_stress(perf, .1925, n=1000, seed=2026)
    assert np.all(b.outputs["vpn_36m"] < a.outputs["vpn_36m"])
    assert a.stats("neto_mes")["p50"] > b.stats("neto_mes")["p50"]
    assert (a.outputs["neto_mes"] < 0).any()


def test_tarifa_invalida():
    with pytest.raises(ValueError):
        mc.run_tariff_stress(posterior_sintetica(), float("nan"))
