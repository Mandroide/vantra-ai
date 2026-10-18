# Business Model Canvas actualizado — versión de laboratorio, 18/10/2026

**Estado:** revisión provisional a partir del MVP de demostración y pruebas offline. **No representa validación con
bancos, BPO, clientes reales, tasas de conversión ni costos medidos de APIs.**

| Bloque                | Actualización y nivel de evidencia                                                                                                                                                                                                                |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1. Segmentos          | **HIPÓTESIS original:** bancos y financieras medianas de LATAM; BPO como segundo segmento. Sin entrevistas ni pilotos reales. Prioridad de comprador no validada.                                                                                 |
| 2. Propuesta de valor | **IMPLEMENTADO offline:** consultas de tarjetas, préstamos y certificados; cuota desde función; registro de lead y callback ficticios; escalamiento simulado. **PENDIENTE:** validación de voz natural es-DO, reducción de costos y conversiones. |
| 3. Canales            | **IMPLEMENTADO:** demo local Gradio. **PENDIENTE:** demo web pública, venta directa, integradores, campañas reales.                                                                                                                               |
| 4. Relaciones         | **DISEÑADO:** piloto co-creado de 4-6 semanas, soporte y reportes. **NO VALIDADO** con institución.                                                                                                                                               |
| 5. Ingresos           | **HIPÓTESIS:** setup por vertical, tarifa por minuto/llamada, integración y packs. Precios de venta sin datos de disposición a pagar.                                                                                                             |
| 6. Recursos           | **IMPLEMENTADO:** código Python, catálogo sintético, conjunto de 36 pruebas, esquema de evaluaciones y UI. **PENDIENTE:** claves e infraestructura segura para LIVE.                                                                              |
| 7. Actividades        | **HECHO:** prototipo textual, cálculo, guardrails, pruebas automáticas. **SIGUIENTE:** validar STT/LLM/TTS externos, acento, costos y resultados de usuarios.                                                                                     |
| 8. Socios             | **INTEGRACIONES CODIFICADAS, NO VALIDACIONES CONTRACTUALES:** Anthropic, Deepgram y Microsoft Azure; telefonía Twilio sigue fuera del MVP.                                                                                                        |
| 9. Costos             | **OBSERVADO:** ejecuciones locales con costo API no medido. **HIPÓTESIS Fase 1:** USD 0.02–0.03/min, MVP USD 5–10; no usar como resultado de la Fase 2.                                                                                           |

## Decisiones de revisión respecto al Canvas original

1. «Atiende y hace llamadas»: cambiar por «demostración web por turnos; llamadas PSTN para fase posterior» hasta
   disponer de evidencia real.
2. «Vende y da seguimiento»: cambiar por «registra prospectos y seguimientos sintéticos», sin afirmar conversiones.
3. «Cifras exactas»: mantener como diseño de herramienta **comprobado en pruebas unitarias locales**, condicionado a
   validar sistema LIVE.
4. «Acento dominicano»: describir como objetivo de evaluación, no como capacidad comprobada.
5. «Costo por minuto»: reemplazar valores como supuesto y exigir registro de facturas/minutos reales.
6. «Compliance integrado»: reemplazar por controles parciales/prototípicos y revisión jurídica pendiente.

**Evidencia disponible:** `results/demo_evaluation_36.csv`, `results/subgroups_demo.csv` y registros Pytest. Estas
fuentes prueban alcance de lógica simulada, no ajuste producto-mercado.
