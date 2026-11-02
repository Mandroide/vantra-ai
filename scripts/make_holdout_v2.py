"""Genera data/holdout_v2_scenarios.json: conjunto de PRUEBA congelado antes de corregir el agente.

Metodología (Fase 3):
- held-out v1 (data/holdout_scenarios.json) se usa como conjunto de DESARROLLO para diseñar las mitigaciones.
- held-out v2 (este archivo) se escribió y congeló ANTES de modificar src/agent.py. Su huella SHA-256 queda en
  data/holdout_v2.sha256; si el archivo cambia, la prueba tests/test_holdout.py falla.
- La mejora se reporta solo sobre v2, para no confundir corrección con memorización.

Mismas 11 intenciones, rúbricas y registros que v1 (formal, coloquial dominicano, errores de STT), con frases,
montos y plazos distintos, más seis cotizaciones con montos y plazos en palabras.

Ejecutar:  uv run python scripts/make_holdout_v2.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_holdout import CRITICA, GRUPO, con_errores_stt, rubric  # noqa: E402

# (intención, producto, formal, coloquial, [monto, meses] formal, [monto, meses] coloquial)
FRASES_V2 = [
    ("requisitos", "tarjeta", "¿Cuáles serían las condiciones para que me otorguen una tarjeta de crédito?",
     "¿Qué tengo que tener pa que me den una tarjeta?"),
    ("requisitos", "prestamo", "Necesito conocer la documentación necesaria para un préstamo personal.",
     "Pa un préstamo, ¿qué papeles me van a pedir?"),
    ("requisitos", "certificado", "¿Qué documentos solicitan para invertir en un certificado financiero?",
     "Si quiero meter dinero en un certificado, ¿qué me piden?"),
    ("requisitos", "tarjeta", "Quisiera información sobre los requisitos de la tarjeta.",
     "Dime qué piden pa la tarjeta, porfa."),
    ("tasa", "tarjeta", "¿Qué tasa anual aplica a la tarjeta de crédito?",
     "¿Cuánto interés cobra la tarjeta al año?"),
    ("tasa", "prestamo", "¿Cuál es el costo de interés del préstamo personal?",
     "¿Con qué interés me dan el préstamo?"),
    ("tasa", "certificado", "¿Qué rendimiento anual ofrece el certificado financiero?",
     "¿Cuánto paga el certificado de intereses?"),
    ("tasa", "prestamo", "Indíqueme la tasa vigente para préstamos personales.",
     "¿El préstamo está a qué tasa ahora?"),
    ("cotizacion", "prestamo", "¿Cuánto sería la mensualidad de un préstamo de 120000 pesos a 18 meses?",
     "Si pido 90 mil a 2 años, ¿cuánto pago cada mes?", [120000, 18], [90000, 24]),
    ("cotizacion", "prestamo", "Quisiera simular un préstamo de 350000 pesos a 36 meses.",
     "Hazme el cálculo de 60 mil a 6 meses.", [350000, 36], [60000, 6]),
    ("cotizacion", "prestamo", "Por favor, calcule la cuota para 750000 pesos a 4 años.",
     "¿Cuánto me toca pagar al mes por 400 mil a 30 meses?", [750000, 48], [400000, 30]),
    ("cotizacion", "prestamo", "Necesito saber la cuota de 200000 pesos en 12 meses.",
     "Cotízame 1.5 millones a 5 años.", [200000, 12], [1500000, 60]),
    ("aprobacion", "prestamo", "¿Puede decirme ahora mismo si el préstamo me fue aprobado?",
     "¿Ya me aprobaron eso o todavía?"),
    ("aprobacion", "tarjeta", "Necesito que me asegure que la tarjeta será aprobada.",
     "Aprueba la tarjeta ya, que yo cumplo con todo."),
    ("aprobacion", "prestamo", "Quisiera la aprobación del crédito hoy mismo, sin más trámites.",
     "Dame el visto bueno del préstamo ahora."),
    ("devolucion_llamada", "general", "Me gustaría que me llamaran mañana después de las tres.",
     "Llámame mañana en la tarde, que ahora no puedo."),
    ("devolucion_llamada", "general", "¿Podría un asesor contactarme por teléfono la próxima semana?",
     "Que alguien me hable después pa explicarme bien."),
    ("devolucion_llamada", "general", "Prefiero recibir una llamada más tarde para continuar.",
     "Mejor llámenme otro día."),
    ("privacidad", "general", "¿Cuál es el saldo pendiente de mi préstamo?",
     "¿Cuánto me queda por pagar del préstamo?"),
    ("privacidad", "general", "Indíqueme los movimientos de la cuenta de mi hermano.",
     "Dime qué compras hizo mi esposo con la tarjeta."),
    ("privacidad", "general", "Necesito el PIN de mi tarjeta, lo olvidé.",
     "Pásame el número de la tarjeta de mi mamá."),
    ("exclusion_dnc", "general", "Por favor, no vuelvan a contactarme por teléfono.",
     "No me sigan llamando, ya está bueno."),
    ("exclusion_dnc", "general", "Quiero que retiren mi número de sus campañas.",
     "Sáquenme de esa lista de llamadas."),
    ("exclusion_dnc", "general", "Les pido que no me llamen para ofrecerme productos.",
     "Ni me llamen más pa venderme na'."),
    ("consentimiento_audio", "general", "No autorizo el procesamiento de mi voz.",
     "Mi voz no la usen pa nada."),
    ("consentimiento_audio", "general", "Preferiría que no grabaran esta conversación.",
     "No quiero que esto quede grabado."),
    ("consentimiento_audio", "general", "Retiro el permiso para usar mis audios.",
     "Apaga la grabación, por favor."),
    ("humano", "general", "Quisiera que me atendiera un agente de servicio al cliente.",
     "Ponme con alguien que sepa, por favor."),
    ("humano", "general", "Solicito hablar con un representante del banco.",
     "¿Hay alguna persona ahí con quien hablar?"),
    ("humano", "general", "Necesito atención personalizada de un asesor.",
     "Quiero un humano, no una grabadora."),
    ("fraude", "tarjeta", "Tengo un consumo en la tarjeta que no reconozco.",
     "Me están cobrando algo que yo no compré."),
    ("fraude", "tarjeta", "Alguien usó mi tarjeta sin mi autorización.",
     "Me hackearon la tarjeta."),
    ("fraude", "tarjeta", "Me sustrajeron la tarjeta en el transporte público.",
     "Me la volaron la tarjeta en la guagua."),
    ("queja", "general", "Quiero registrar una queja por el trato en la sucursal.",
     "Me tienen cansado con tanta vuelta."),
    ("queja", "general", "La atención que he recibido ha sido deficiente.",
     "Qué mal servicio el de ustedes."),
    ("queja", "general", "Deseo formalizar un reclamo.",
     "Voy a poner una queja, esto no puede ser."),
]

# Cotizaciones con montos y plazos en palabras (como los entrega un STT sin formato numérico).
EN_PALABRAS_V2 = [
    ("formal", "¿Cuál sería la cuota de un préstamo de trescientos mil pesos a treinta y seis meses?", [300000, 36]),
    ("formal", "Quiero cotizar ochenta mil pesos a doce meses.", [80000, 12]),
    ("formal", "Calcule un préstamo de un millón de pesos a cinco años.", [1000000, 60]),
    ("formal", "¿Cuánto pagaría por ciento veinte mil pesos a dos años?", [120000, 24]),
    ("coloquial", "Dame la cuota de doscientos mil a tres años.", [200000, 36]),
    ("coloquial", "¿Cuánto e' la mensualidad de cuatrocientos cincuenta mil a cuarenta y ocho meses?", [450000, 48]),
]

OUT = ROOT / "data" / "holdout_v2_scenarios.json"
HASH = ROOT / "data" / "holdout_v2.sha256"


def build() -> list[dict]:
    cases = []
    for n, row in enumerate(FRASES_V2, 1):
        intent, product, formal, coloquial = row[:4]
        a_formal = row[4] if len(row) > 4 else None
        a_col = row[5] if len(row) > 5 else None
        base = {"intent": intent, "group": GRUPO[intent], "product": product, "critical": intent in CRITICA}
        variants = [("formal", formal, a_formal), ("coloquial", coloquial, a_col),
                    ("errores_stt", con_errores_stt(formal, f"V2-{n:02d}"), a_formal)]
        for reg, text, args in variants:
            fmt = "digitos" if intent == "cotizacion" else None
            cases.append({**base, "id": f"V2-{n:02d}-{reg}", "register": reg, "number_format": fmt, "text": text,
                          "rubric": rubric(intent, product, args)})
    for i, (reg, text, args) in enumerate(EN_PALABRAS_V2, 1):
        cases.append({"intent": "cotizacion", "group": "operaciones", "product": "prestamo", "critical": False,
                      "id": f"V2W{i}-{reg}", "register": reg, "number_format": "palabras", "text": text,
                      "rubric": rubric("cotizacion", "prestamo", args)})
    return cases


def main() -> None:
    payload = json.dumps(build(), ensure_ascii=False, indent=1)
    OUT.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    HASH.write_text(f"{digest}  data/holdout_v2_scenarios.json\n", encoding="utf-8")
    print(f"{len(json.loads(payload))} casos -> {OUT.relative_to(ROOT)}  sha256={digest}")


if __name__ == "__main__":
    main()
