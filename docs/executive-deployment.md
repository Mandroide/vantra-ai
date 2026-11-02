# Informe de soporte del despliegue ejecutivo · Fase 3 (25 pts)

**Alcance:** Banco Demo ficticio; evaluación de impacto económico mediante hipótesis, nunca retorno medido de una
institución. Presentación ejecutiva de 10 minutos y demostración reproducible.

## Arquitectura y despliegue

- `app.py` implementa el MVP Gradio; pestaña **Dashboard ejecutivo · KPIs y Monte Carlo**.
- Gradio local en `7860`. FastAPI recibe webhooks de Twilio en `8000`. La conectividad pública se configura con
  `scripts/connectivity.py` y ngrok/Cloudflare/Caddy.
- Deepgram STT + Anthropic Claude + Azure Speech TTS: conectores disponibles bajo claves LIVE. SQLite registra
  solicitudes sintéticas, estados telefónicos y **métricas numéricas locales de interacción** sin contenido de voz.
- `src/impact.py` genera escenarios estocásticos; `src/dashboard/executive.py` presenta supuestos, indicadores y
  gráficos; `scripts/run_simulation.py` exporta JSON/CSV.
- Publicar la URL de Gradio solo detrás de autenticación y controles de acceso; los túneles sirven para **webhooks** de
  FastAPI, no para exponer públicamente el panel de llamadas.

## Métricas técnicas y qué falta medir

| Métrica                                                    | Fuente actual                                                     | Alcance                                                         |
|------------------------------------------------------------|-------------------------------------------------------------------|-----------------------------------------------------------------|
| 36/36 comprobaciones                                       | `results/summary_demo.json`                                       | Regresión textual DEMO sintética, no generalización             |
| Latencia P50/P95                                           | `interaction_metrics` SQLite vía Gradio                           | Solo interacción textual/tiempo aplicación; no llamada completa |
| Éxito en frases nuevas: 17.6%                              | Diapositivas compartidas por el equipo, sin conjunto adjunto      | Cifra declarada, no revalidada; **no tasa LIVE**                |
| WER por registro, F1 por intención, resolución segura LIVE | Sin corpus transcrito ni rúbrica auditada disponible              | Pendientes                                                      |
| Costo real/min y tasa de derivación LIVE                   | Requiere facturación, métricas telefónicas y sesiones consentidas | Pendientes                                                      |

**No confundir la cobertura de pruebas con la precisión del modelo.** El modo DEMO tiene reglas deterministas. F1 solo
puede calcularse con etiquetas de intención y predicciones; WER requiere referencia humana. RMSE no aplica a esta tarea
sin objetivo de regresión.

## Modelo probabilístico (Monte Carlo)

`uv run python -m scripts.run_simulation --runs 10000 --seed 8269`

Variables de entrada (todos son **supuestos ilustrativos en DOP**):

| Variable               | Valor central | Qué representa                                     |
|------------------------|--------------:|----------------------------------------------------|
| Llamadas mensuales     |        12,000 | Demanda posible de un contact center hipotético    |
| Elegibilidad           |           45% | Fracción enviada al agente                         |
| Resolución segura      |           70% | **Meta hipotética** condicionada a validación real |
| Costo humano por caso  |         RD$95 | Costo marginal/oportunidad, no nómina auditada     |
| Costo IA por intento   |         RD$18 | APIs, Twilio y cargo variable **supuestos**        |
| Realización del ahorro |           50% | Valor económico capturable del tiempo liberado     |
| OPEX fijo mensual      |     RD$35,000 | Soporte, observabilidad y supervisión              |
| Implementación inicial |    RD$250,000 | Inversión hipotética                               |
| Tiempo humano          |    5 min/caso | Tiempo que potencialmente se libera                |
| Incertidumbre          |          ±20% | Distribuciones triangulares independientes         |

Se calculan 10,000 corridas para 12 meses. Cada variable se sortea independientemente alrededor del valor central con
distribución triangular simétrica acotada. El **costo IA se paga por todos los intentos** aun cuando fallen. La
capacidad humana liberada no implica reducción equivalente en nómina: solo se monetiza el `labor_realization`.

`neto_anual = (12 × resueltas × costo_humano × realización) - (12 × intentos × costo_IA + 12 × OPEX_fijo + inversión_inicial)`.

`ROI = neto_anual / costo_anual_total_proyecto × 100`.

El modelo produce percentiles P5/P50/P95, P (neto>0), horas potencialmente liberadas y correlación de rangos aproximada
para sensibilidad. La cifra 17.6% del borrador del equipo se utiliza **solo como escenario de estrés hipotético**; no
equivale a tasa real de resolución en voz. No se ha estimado con datos de usuarios o registros contables. La
independencia de variables y la ausencia de pérdidas extremas legales hacen que **no sea un pronóstico**.

## Gobierno y decisión go/no-go

**Recomendación:** financiar, como máximo, un piloto controlado con consentimiento explícito y supervisión humana; no
autorizar despliegue bancario autónomo ni una campaña masiva.

Criterios de avance propuestos: 100% de controles críticos de consentimiento, DNC, privacidad y fraude en un set de
prueba independiente; exactitud financiera 100% en consultas auditadas; medir WER/latencia por registro, costo real por
llamada resuelta y tasa de derivación en un grupo de prueba; validar jurídicamente privacidad y grabación; recalibrar
Monte Carlo con costos reales.

Los controles propuestos siguen como referencia no certificante las prácticas de gobernanza del **NIST AI RMF, perfil IA
generativa**
(`https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence`)
y la **Ley 172-13** (`https://www.sb.gob.do/regulacion/leyes/ley-no-172-13-proteccion-de-los-datos/`). El informe no
constituye dictamen legal.

## Material entregable

- Informe ejecutivo PDF/DOCX en el paquete académico.
- Gradio interactivo + `results/impact/monte_carlo_summary.json` y `monte_carlo_samples.csv`.
- Pitch PPTX de 10 minutos, Canvas para transcribir a Canvanizer.
- Código/pruebas/CI; no incluye tokens, grabaciones personales ni credenciales.

## Validación y límites

Pruebas offline de repositorio deben ejecutarse en el ambiente destino con `uv run pytest`; el arranque de Docker, las
integraciones LIVE, costos reales y despliegue web público requieren credenciales y un entorno externo. `uv.lock` debe
generarse en equipo con Python 3.12 y acceso a resolución de paquetes.
