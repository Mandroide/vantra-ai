# Fase 3 — Validación experimental, riesgos y alcance de resultados

## Desempeño del prototipo

El conjunto textual de evaluación congelado (held-out v2) contiene 114 frases. Los resultados de DEMO fueron 17/114
(14.9 %) antes de las mejoras y 83/114 (72.8 %) después. Esta exactitud no equivale a WER ni a resolución exitosa de
llamadas de voz en operación real. El archivo de evaluación conserva su SHA-256.

## Seguridad y derivación

El escenario económico favorable simula una reducción del 80 % de la tasa posterior de error crítico, mediante un factor
multiplicativo de 0.2. No garantiza un techo de error del 1 %. Las solicitudes de derivación se registran o simulan: la
transferencia telefónica real a un asesor no se ha demostrado con este conjunto de evidencias.

## Incertidumbre de costos

`analytics.montecarlo.run_tariff_stress` permite examinar cómo cambia el VPN del escenario favorable al sustituir el
costo por minuto por tarifas públicas de telefonía saliente a República Dominicana. Son pruebas de sensibilidad, no
costos operativos observados ni una cotización completa de voz: no incluyen necesariamente STT, TTS, LLM, impuestos ni
descuentos de contrato.

El tiempo humano potencialmente liberado representa capacidad de reasignación. Solo puede registrarse como ahorro
monetario realizado si se identifica y demuestra el mecanismo económico de recuperación del costo.

## Gobernanza del despliegue

Antes de trabajar con datos personales reales se requiere evaluar consentimiento, residencia y transferencias de
información, retención, seguridad de proveedores y secreto bancario. Un sistema local de STT/TTS no asegura por sí solo
que la telefonía, los metadatos u otros servicios estén alojados dentro del país.

Las medidas de equidad y seguridad deben replicarse sobre datos independientes y conversaciones de voz con autorización.
La muestra actual de 114 frases no sustituye dicha validación.

**Tarifa de referencia:** https://www.twilio.com/en-us/voice/pricing/do (consulta: 1 de noviembre de 2026).

Los datos congelados permanecen sin alteraciones. No se debe modificar la huella esperada para resolver fallos de
integridad.
