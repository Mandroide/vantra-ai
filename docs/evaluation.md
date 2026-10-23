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
Canvas. Una llamada real es **opcional y solo si se ha probado previamente y el destinatario ha consentido**. Si falla
el proveedor, exponga el error real, sin sustituirlo por evidencias simuladas presentadas como auténticas.

## Material de entrega separado del repositorio

El paquete académico de la Fase 2 debe contener el informe PDF, resultados y metodología de evaluación, reflexión ética,
Business Model Canvas revisado y enlaces al repositorio/demo, junto con evidencias en Drive. Las conclusiones de negocio
(ahorro, conversiones, preferencia por acento, costo de llamada) siguen siendo **hipótesis hasta medirse**. El Canvas
original estimaba USD 0.02–0.03/min y USD 5–10 para APIs: no deben reportarse como gastos observados.

**Pendientes de verificación:** `uv.lock` versionado, despliegue accesible, llamadas reales, medición LIVE de
WER/latencias/costos, revisión humana, documentos finales aprobados y permisos de acceso a las evidencias. Para riesgos
específicos, consulte [ethics.md](ethics.md).
