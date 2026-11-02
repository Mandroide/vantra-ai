# Evaluación, subgrupos y evidencias académicas

## Alcance comprobable

El repositorio ofrece **12 escenarios sintéticos con tres variantes textuales cada uno (36 casos)** y pruebas unitarias,
ejecutables sin claves mediante:

```bash
uv run python -m pytest -q
uv run python scripts/run_evaluation.py
```

Los resultados se guardan en `results/demo_evaluation_36.csv`, `results/subgroups_demo.csv` y
`results/summary_demo.json`. Esos archivos documentan el motor determinista **DEMO**: no constituyen evidencia de una
llamada real, de la calidad de Claude, de la precisión de Deepgram ni de la voz de Azure. No equipare casos superados
con satisfacción humana o ausencia de sesgo.

## Escenarios

| Grupo        | Casos   | Qué se verifica                                            |
|--------------|---------|------------------------------------------------------------|
| Información  | E01–E03 | Tarjetas, préstamos y certificados del banco ficticio.     |
| Operaciones  | E04–E06 | Cálculo, precalificación no vinculante y seguimiento.      |
| Seguridad    | E07–E09 | Privacidad, exclusión de contacto y consentimiento.        |
| Escalamiento | E10–E12 | Solicitud humana, fraude y quejas; transferencia simulada. |

E08 comprueba la política de contactos mediante herramienta. E06 incluye la confirmación en un turno adicional. Las
variantes escritas por el equipo no representan una muestra demográfica ni acústica de la República Dominicana.

## Fase 3: held-out congelado, MCMC y Monte Carlo

- **Desarrollo y prueba separados.** Las mitigaciones de `src/nlu.py` se diseñaron con el held-out v1
  (`data/holdout_scenarios.json`). El held-out v2 (`data/holdout_v2_scenarios.json`, 114 frases, huella SHA-256 en
  `data/holdout_v2.sha256`) se escribió y congeló antes de modificar el agente y solo se usa para medir.
- **Resultados en v2 (DEMO):** exactitud de 14.9% (17/114) a 72.8% (83/114); F1 macro por intención de 0.23 a 0.79;
  casos críticos con acción equivocada de 3 a 1 de 36 (los demás críticos fallidos quedan sin resolver y, con
  `VANTRA_FALLBACK=humano`, pasan a un asesor). Por registro: formal 82.5%, errores de STT 77.8%, coloquial 57.9%.
- **Sesgo de autoría:** v2 lo escribió el mismo equipo que conocía el tipo de corrección; su resultado puede ser
  optimista. El ruido de STT de v1 y v2 sale del mismo generador; falta medir WER con audio real.
- **MCMC:** modelo jerárquico logit por registro con Metropolis dentro de Gibbs y Beta-Binomial para la tasa de acción
  equivocada en intenciones críticas (validada contra la solución conjugada). Probabilidad posterior de que el registro
  coloquial esté peor atendido que el formal: 95%.
- **Monte Carlo:** 10,000 escenarios con supuestos citados en `analytics/assumptions.py`. Los resultados por escenario
  de decisión están en `results/fase3/resumen.json` y en el cuadro de mando.

## Trazabilidad técnica de telefonía

Los logs del servicio `twilio-webhook` emiten eventos `twilio_status`, `voice_stream_started`, `voice_agent`,
`voice_tts` y `voice_stream_ended`, con `call_ref` seudonimizado y tiempos de procesamiento de algunas etapas. Los
estados antiguos se pueden conciliar mediante `python -m scripts.reconcile_calls --check` sin iniciar llamadas. Estos
datos no contienen audio ni transcripciones y son útiles para diagnóstico; **no bastan** para calcular WER, latencia de
extremo a extremo o coste de proveedores. No se deben reportar como evaluación estadística de llamadas LIVE.

## Evaluación LIVE propuesta

Ejecute sesiones con usuarios voluntarios y consentimiento documentado; registre en cada intento `scenario_id`,
modalidad, registro lingüístico, complejidad, resultado, transcripción STT verificada, herramientas invocadas, versión
de proveedores, tiempos parciales, costos de facturación y cualquier fallo/derivación. No incorpore teléfonos, audios ni
identificadores personales en archivos públicos. Revise manualmente las respuestas y la exactitud financiera,
preferiblemente con doble revisión de discrepancias.

| Métrica              | Definición                                                                                               |
|----------------------|----------------------------------------------------------------------------------------------------------|
| Éxito de tarea       | Casos correctos según rúbrica humana / casos intentados.                                                 |
| Exactitud financiera | Respuestas acordes al catálogo y a sus supuestos / respuestas financieras evaluadas.                     |
| Escalamiento         | Eventos sensibles manejados correctamente / eventos sensibles evaluados.                                 |
| WER                  | `(sustituciones + eliminaciones + inserciones) / palabras de referencia`; requiere transcripción humana. |
| Latencia por turno   | Tiempo de captura a respuesta, separado en STT, agente y TTS.                                            |
| Costo                | Consumo efectivamente facturado dividido entre llamadas o interacciones.                                 |

Compare subgrupos por **tipo de consulta, español formal/coloquial, complejidad y modalidad texto/audio** con los
tamaños muestrales visibles. Los objetivos iniciales (p. ej., éxito ≥ 85 %) son criterios propuestos, **no resultados
observados**.

## Demostración en clase

Secuencia sugerida: consulta de tarjeta → cotización RD$300,000/36 meses → registro de prospecto → denegación de dato
privado → escalamiento simulado → demostración de DNC/consentimiento → presentación de resultados DEMO, límites y
Canvas. El equipo ha reportado una grabación de conversación telefónica piloto; para usarla en clase, confirme el
consentimiento del participante y distinga la evidencia de interacción de una medición estadística de calidad. Una
llamada adicional en vivo es opcional y requiere consentimiento. Si falla el proveedor, exponga el error real, sin
sustituirlo por evidencias simuladas presentadas como auténticas.

## Material de entrega separado del repositorio

El paquete académico de la Fase 2 debe contener el informe PDF, resultados y metodología de evaluación, reflexión ética,
Business Model Canvas revisado y enlaces al repositorio/demo, junto con evidencias en Drive. Las conclusiones de negocio
(ahorro, conversiones, preferencia por acento, costo de llamada) siguen siendo **hipótesis hasta medirse**. El Canvas
original estimaba USD 0.02–0.03/min y USD 5–10 para APIs: no deben reportarse como gastos observados.

**Pendientes de verificación:** `uv.lock` versionado, despliegue accesible validado mediante
`scripts/connectivity.py probe`, medición de llamadas LIVE de WER/latencias/costos, revisión humana, documentos finales
aprobados y permisos de acceso a las evidencias. Para riesgos específicos, consulte [ethics.md](ethics.md).

## Utilidades adicionales de medición

`src/kpis.py` ofrece cálculos de WER, F1 de etiquetas y percentiles P50/P95 para **datasets etiquetados**. No asigna
automáticamente WER a las llamadas reales: esto requiere audio transcrito por personas autorizadas y de referencia.

`src/storage.py` registra conteos y latencia de las interacciones con Gradio. Su unidad de análisis es la solicitud a la
interfaz, no una llamada telefónica completada. Estos conteos se muestran exclusivamente en el dashboard de Streamlit,
junto con los conteos de operaciones sintéticas. El modelo probabilístico de negocio sigue siendo
`analytics/montecarlo.py`, con `analytics/mcmc.py` para incertidumbre de desempeño. Los resultados del held-out v2
congelado no se reescriben para reflejar otra metodología.

## Evaluación LIVE a partir de anotaciones autorizadas (v0.4)

Copie `data/live_evaluation_template.csv` a `data/live_inputs/pruebas.csv` (ruta excluida de Git). Introduzca únicamente
referencias de pruebas consentidas y sin información personal: `scenario_id`, `register`, intenciones de
referencia/predicha, transcripciones STT/revisada, latencia integral en ms y marcas `true`/`false` de tarea y política
crítica. Para casos no críticos deje `critical_policy_pass` vacío.

```powershell
python -m scripts.evaluate_live_voice data/live_inputs/pruebas.csv
```

Escribe agregados locales en `results/live_metrics_private.json`: n, WER promedio por intervención, macro-F1, éxito,
latencia P50/P95 y política crítica por registro. **No inicia llamadas ni produce métricas LIVE por sí solo**. El WER
calculado es promedio de frases, no WER de corpus ponderado por palabras. El módulo `src/observability.py` contiene solo
tiempos parciales/estados operativos, no etiquetas de referencia. El conjunto congelado de 114 frases permanece sin
modificaciones.

### Consumos LIVE y estimaciones parciales

La pestaña *Telefonía observada* contabiliza tokens de entrada/salida de Claude, caracteres TTS y segundos de audio
enviados a Deepgram. Si en `.env` existen tarifas unitarias **positivas verificadas** (`LLM_INPUT_USD_PER_MILLION`,
`LLM_OUTPUT_USD_PER_MILLION`, `AZURE_USD_PER_MILLION_CHARACTERS`, `DEEPGRAM_USD_PER_MINUTE`), estima únicamente el
subtotal de esos componentes. No incorpora costo de Twilio, impuestos, mínimos, otros proveedores ni conciliación de
facturación. Si una tarifa falta, su costo se muestra como desconocido, nunca como cero.
