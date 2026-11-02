# Consideraciones éticas y controles del MVP

Vantra AI es un prototipo académico para un **banco ficticio**. El sistema usa datos sintéticos, pero procesar voz de
voluntarios a través de proveedores externos y marcar teléfonos reales introduce riesgos que requieren controles
adicionales.

## Riesgos y mitigaciones

| Riesgo                        | Medida prevista o implementada                                                                                                                                 | Límite actual                                                                                                 |
|-------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| Sesgo de idioma y acento      | Evaluar STT en español dominicano formal y coloquial; comparar WER y éxito por subgrupo.                                                                       | No existen mediciones acústicas representativas; una batería de texto no demuestra equidad.                   |
| Tasas o cuotas inventadas     | Catálogo ficticio y cálculos deterministas para cifras; no aprobación crediticia.                                                                              | La revisión de respuestas LIVE y ataques de prompt injection está pendiente.                                  |
| Datos sensibles o de terceros | Sin sistema bancario real; rechazar consultas privadas y evitar almacenamiento de conversaciones en SQLite.                                                    | Reglas heurísticas; no equivalen a autenticación ni autorización bancaria.                                    |
| Grabación y retención         | Consentimiento explícito de audio de prueba; procesamiento temporal, sin almacenamiento deliberado en SQLite.                                                  | La interfaz, cachés y proveedores pueden retener archivos temporalmente según sus políticas.                  |
| Contactos no solicitados      | Telefonía deshabilitada por defecto, allowlist, consentimiento, DNC, horario, límites y reconciliación verificada de estados con Twilio.                       | No sustituye análisis legal, gestión auditada de consentimientos ni gobernanza de comunicaciones comerciales. |
| Reclamaciones y fraude        | Mensajes de escalamiento o derivación simulada.                                                                                                                | No existe transferencia humana efectiva, línea antifraude ni SLA real.                                        |
| Sesgo crediticio              | No inferir elegibilidad de voz, acento, barrio o proxies; precalificación no vinculante.                                                                       | No existe un modelo crediticio auditado para conceder préstamos.                                              |
| Costo y exposición pública    | Gradio ligado a loopback, acceso público solo al webhook FastAPI mediante ngrok/Cloudflare/Caddy, claves en entorno, firmas verificadas y límites de llamadas. | Gradio carece de autenticación suficiente para despliegue abierto.                                            |

## Principios operativos

- Avisar explícitamente que se habla con IA y con **Banco Demo**, institución inexistente, y explicar el procesamiento
  del audio.
- Usar solo números cuyo titular dio consentimiento verificable para la prueba; honrar la exclusión DNC y terminar
  cuando la persona lo solicite. Si falla la consulta a Twilio, no liberar una reserva de llamada sin evidencia
  verificable del estado final.
- Nunca solicitar ni publicar cédulas, contraseñas, cuentas, audios identificables o transcripciones con información
  privada.
- Registrar errores, latencia y consumo sin identificadores personales. Consultar las reglas de retención y
  transferencia internacional de datos de cada proveedor.
- No utilizar comparaciones por registro lingüístico como inferencias sobre género, origen étnico, ingresos o capacidad
  crediticia.
- Mantener las decisiones financieras sensibles y las reclamaciones bajo supervisión humana autorizada antes de
  cualquier piloto institucional.

## Gobernanza de la Fase 3

- **Paridad por registro como criterio de salida:** la brecha formal–coloquial medida en v2 (82.5% frente a 57.9%) es
  un riesgo de trato desigual; el piloto no avanza mientras la brecha supere 5 puntos con al menos 100 frases reales
  por registro.
- **Intenciones críticas:** fraude, privacidad, exclusión de llamadas y pedidos de aprobación se evalúan antes que
  cualquier otra regla. Meta de avance: tasa de acción equivocada ≤ 1%, demostrada con 300 casos críticos sin error
  (regla del tres, 95% de confianza).
- **Derivación por defecto:** en un piloto se configura `VANTRA_FALLBACK=humano`; ninguna consulta no entendida queda
  sin atención.
- **Marco aplicable en RD:** Ley 172-13 de protección de datos (con reforma en discusión), régimen de secreto bancario
  de la Ley 183-02, Reglamento de Seguridad Cibernética y de la Información (Junta Monetaria, 2018) y Reglamento de
  Protección al Usuario de los Productos y Servicios Financieros (en vigor desde octubre de 2026). Requiere validación
  de asesoría legal.

## Estado de validación

Las pruebas automáticas comprueban algunas restricciones de lógica; **no prueban cumplimiento jurídico, ausencia de
sesgo ni seguridad empresarial**. Antes de utilizar Vantra AI fuera de un entorno académico se requieren evaluación de
impacto, revisión legal local, controles de identidad/acceso, política de retención, supervisión humana y evaluación del
proveedor.

Consulte [evaluation.md](evaluation.md) para las mediciones pendientes y [telephony.md](telephony.md) para el
procedimiento consentido de telefonía.

El cambio de túnel **no altera** el consentimiento, la lista DNC ni las reglas de privacidad. Se deben evitar
intermediarios que registren audios o datos sensibles sin un acuerdo y controles adecuados. El túnel no sustituye
autenticación de la interfaz ni autorización de acciones.

## Gobernanza de la telemetría y separación de evidencia

La nueva telemetría conserva solo modo (DEMO/LIVE), categoría de estado, milisegundos de ejecución y momento. No
registra texto, voz, números de teléfono ni identificadores de clientes. Su retención y borrado siguen siendo
responsabilidad del operador del piloto. Gradio y Streamlit se publican únicamente en loopback local; exponerlos
públicamente requeriría autenticación, control de acceso y pruebas adicionales.

No se deben combinar los porcentajes de exactitud textual del held-out v2 con los conteos de interacciones Gradio para
declarar un éxito operativo medido. Los modelos económicos alternativos del borrador se excluyeron para no presentar ROI
incompatibles bajo una misma marca.
