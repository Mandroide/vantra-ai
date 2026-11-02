"""Supuestos del modelo de impacto, cada uno con su distribución y su origen.

Todas las variables inciertas usan distribuciones triangulares (mínimo, más probable, máximo), salvo las tasas de
desempeño del agente, que salen de la posterior bayesiana estimada con MCMC sobre el held-out v2 (analytics/mcmc.py).

Fuentes consultadas en octubre de 2026 (ver informe, anexo de fuentes):
[S1] Salario mínimo empresas grandes no sectorizadas: RD$29,988 desde el 1 de febrero de 2026 (Resolución
     CNS-01-2025). EY Tax Alert, «República Dominicana: salario mínimo 2026».
[S2] Aportes patronales: AFP 7.10%, SFS 7.09%, SRL ~1.15%, INFOTEP 1% (~16.34%); salario de Navidad = 1/12 del
     salario anual. RemotePass, «Dominican Republic Payroll».
[S3] Rango salarial de agentes de contact center y costo patronal (~24.7% sobre la base, sin vacaciones ni
     bonificación). HiveDesk, «Average Salary in the Dominican Republic (2026)».
[S4] AHT en instituciones financieras: aproximadamente 6 minutos (Nextiva, citado por Sobot, «AHT benchmarks
     2025»); encuesta de Call Centre Helper: 77% de los centros entre 3 y 9 minutos.
[S5] Tasa de cambio Banco Central, 19 de octubre de 2026: compra RD$61.3649, venta RD$61.8322 (Revista Mercado).
[S6] Twilio Voice, República Dominicana: SIP/app US$0.004 por minuto; Media Streams US$0.0044 por minuto;
     saliente a móvil US$0.1925 por minuto (twilio.com/voice/pricing/do).
[S7] Deepgram Nova-3 streaming ~US$0.0092/min y Azure Neural TTS ~US$16 por millón de caracteres (páginas de
     precios, octubre de 2026; ver core de voz del MVP).
[E]  Supuesto del equipo, sin fuente pública directa: se expone con un rango amplio y se somete a sensibilidad.
"""
from __future__ import annotations

from dataclasses import dataclass

DOP_PER_USD = 61.60  # [S5] punto medio aproximado entre compra y venta del 19-oct-2026
HORAS_PAGADAS_MES = 44 * 52 / 12  # jornada legal de 44 horas semanales (Código de Trabajo de RD), ~190.7 h/mes


@dataclass(frozen=True)
class Tri:
    """Variable incierta con distribución triangular."""
    key: str
    label: str
    unit: str
    low: float
    mode: float
    high: float
    source: str
    group: str = "operación"

    @property
    def mean(self) -> float:
        return (self.low + self.mode + self.high) / 3


SUPUESTOS: list[Tri] = [
    # --------------------------------------------------------------- volumen y alcance
    Tri("llamadas_mes", "Llamadas mensuales del contact center", "llamadas", 30_000, 50_000, 80_000,
        "[E] Banco mediano; se ajusta en el dashboard", "volumen"),
    Tri("alcance", "Proporción de llamadas en el alcance del agente", "proporción", 0.20, 0.30, 0.40,
        "[E] Consultas de producto, tasas, cotizaciones, devoluciones y escalamientos", "volumen"),
    Tri("coloquial", "Proporción de clientes que hablan en registro coloquial", "proporción", 0.30, 0.45, 0.60,
        "[E] Supuesto conservador para la población dominicana", "población"),
    Tri("errores_stt", "Proporción de llamadas formales con errores de transcripción", "proporción", 0.10, 0.20, 0.35,
        "[E] A validar con audio real (WER por acento pendiente)", "población"),
    Tri("aceptacion", "Clientes que aceptan ser atendidos por el agente", "proporción", 0.55, 0.70, 0.85,
        "[E] Quienes no piden un humano de entrada ni cuelgan", "población"),
    Tri("criticas", "Proporción de llamadas del alcance con intención crítica", "proporción", 0.05, 0.10, 0.15,
        "[E] Fraude, privacidad, exclusión de llamadas y pedidos de aprobación", "riesgo"),
    # --------------------------------------------------------------- costo del agente humano
    Tri("salario", "Salario base mensual del agente", "RD$", 29_988, 35_000, 45_000,
        "[S1][S3] Piso legal de empresa grande; agentes con experiencia hasta ~RD$45,000", "costo humano"),
    Tri("carga", "Factor de costo patronal sobre el salario", "factor", 1.25, 1.30, 1.40,
        "[S2][S3] TSS+INFOTEP ~16.3% + regalía 8.33%; el máximo incluye vacaciones y bonificación", "costo humano"),
    Tri("utilizacion", "Proporción de horas pagadas en atención productiva", "proporción", 0.55, 0.65, 0.75,
        "[E] Descuenta pausas, capacitación, ausentismo y tiempo ocioso", "costo humano"),
    Tri("aht", "Tiempo medio de atención humana (AHT)", "minutos", 4.0, 6.0, 9.0,
        "[S4] ~6 min en instituciones financieras; 77% de centros entre 3 y 9 min", "costo humano"),
    Tri("aht_extra", "Minutos extra del asesor cuando el bot no resuelve", "minutos", 0.0, 0.5, 1.0,
        "[E] El cliente repite su caso al ser transferido", "costo humano"),
    # --------------------------------------------------------------- costo del agente de IA
    Tri("min_bot", "Duración de una llamada atendida por el bot", "minutos", 2.0, 3.0, 5.0,
        "[E] Medir con llamadas reales del piloto", "costo IA"),
    Tri("min_bot_fallo", "Minutos de bot antes de transferir una llamada no resuelta", "minutos", 0.5, 1.0, 1.5,
        "[E] Intento fallido antes de la derivación", "costo IA"),
    Tri("costo_min_bot", "Costo variable por minuto de bot (voz + telefonía + cómputo)", "US$/min", 0.02, 0.04, 0.08,
        "[S6][S7] STT ~0.009 + TTS ~0.007 + SIP/Media Streams ~0.008 + cómputo; el máximo cubre uso de LLM",
        "costo IA"),
    Tri("inversion", "Inversión inicial (integración, seguridad, piloto)", "US$", 15_000, 25_000, 40_000,
        "[E] Integración con la central telefónica, revisión de seguridad y piloto controlado", "costo IA"),
    Tri("operacion_mes", "Costo fijo mensual (infraestructura, mantenimiento, evaluación)", "US$", 1_500, 3_000, 5_000,
        "[E] Servidores, monitoreo y mantenimiento de reglas con evaluación continua", "costo IA"),
    Tri("costo_error_critico", "Costo esperado por cada intención crítica mal atendida", "US$", 5, 25, 100,
        "[E] Fraude no escalado a tiempo, reclamación o sanción; rango deliberadamente amplio", "riesgo"),
]
BY_KEY = {s.key: s for s in SUPUESTOS}

# Horizonte y tasa de descuento para el valor presente neto.
HORIZONTE_MESES = 36
TASA_DESCUENTO_ANUAL = 0.12  # [E] costo de oportunidad de una inversión tecnológica en banca
