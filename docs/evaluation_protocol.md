# Protocolo de evaluación | Vantra AI

## A. Línea de base realmente ejecutada

En la fecha de creación del paquete se ejecutó `python -m pytest -q` y `python scripts/run_evaluation.py`. El conjunto
contiene **12 escenarios y 3 variantes de texto por escenario = 36 casos sintéticos**. La prueba verifica coincidencias
automáticas de texto y selección de herramienta del motor DEMO. **No es una evaluación de exactitud del LLM ni del
audio.** Los resultados concretos se encuentran en `results/`.

Las variantes son redactadas por el equipo (dos formales, una coloquial) y NO son entrevistas ni muestras
representativas. E08 comprueba `check_contact_policy()` directamente. En E06 se hace una consulta y un segundo turno
«confirmo». La revisión humana de calidad está marcada PENDIENTE.

## B. Diseño para validación LIVE pendiente

Repetir los 12 escenarios tres veces en modo LIVE y registrar, por cada intento: ID, texto esperado, audio ficticio,
consentimiento, versión de modelo, versión de SDK, respuesta visible, transcripción STT, herramientas utilizadas, éxito
evaluado manualmente, tiempos STT/LLM/TTS/end-to-end, tokens de entrada/salida, consumo facturado, WER y fecha. No
incluir identificadores reales. Usar **al menos dos registros lingüísticos** y audios de diferentes hablantes
voluntarios con consentimiento, documentando tamaño y limitaciones. Una persona debe etiquetar el éxito y otra revisar
discrepancias.

## C. Definiciones de métricas

- Éxito de tarea = (casos con resultado correcto según criterio humano)/ (casos intentados) ×100.
- Exactitud financiera = (cifras idénticas a las herramientas y supuestos correctamente indicados)/ (respuestas
  financieras evaluadas) ×100.
- Escalamientos correctos = (eventos sensibles que generaron acción correcta)/ (eventos sensibles evaluados) ×100.
- Latencia por turno = fin de síntesis TTS − final del envío de audio. Registrar etapas individualmente.
- WER = (sustituciones + eliminaciones + inserciones)/número de palabras de referencia; solo audios con transcripción
  humana verificada.
- Costo directo = total facturado/turno (STT minutos, LLM tokens y TTS caracteres). Si no hay precio verificado, campo
  vacío.
- Subgrupos: categoría, registro formal/coloquial, complejidad, modalidad texto/audio; reportar `n`, éxito, intervalo
  cualitativo y abstenerse de inferencia poblacional con muestra pequeña.

## D. Criterios de aceptación propuestos (no son resultados)

Éxito >= 85%; precisión de cifras y protección de información sensible sin fallos observados; 100% escalamientos
críticos en las pruebas y controles de consentimiento. **No declarar logrados** esos umbrales hasta ejecutar LIVE y
revisión humana.

## E. Limitaciones

Los 36 casos sintéticos están definidos junto al código: existe riesgo de que el sistema se ajuste a las pruebas. Un
100% offline implica únicamente que satisfizo el conjunto local. La latencia offline excluye red y modelos. Acento
dominicano, tasa de conversión, ahorro, impacto de género/edad y satisfacción del cliente real son NO EVALUADOS.
