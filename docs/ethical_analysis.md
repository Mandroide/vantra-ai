# Reflexión ética — Vantra AI (Fase 2)

## 1. Riesgos específicos del agente bancario ficticio

**Datos de entrenamiento y dialecto.** Un sistema STT y un modelo de lenguaje pueden representar con menor precisión el
español dominicano coloquial, la mezcla de inglés y español, la pronunciación regional o voces de personas con
discapacidad del habla. El efecto sería una experiencia desigual: tasas mal transcritas, abandono de solicitudes o falsa
atribución de intención. Mitigación: recopilar audio sintético voluntario, diversidad de estilos sin inferir identidad,
medir WER y éxito por registros, confirmar cantidades críticas. Las tres variantes de texto actuales NO prueban equidad
acústica.

**Tasas, montos y alucinación.** Un LLM puede producir cifras plausibles pero falsas, con daño potencial si un usuario
las interpreta como oferta. Mitigación implementada: catálogo ficticio versionable, funciones deterministas, respuestas
numéricas generadas desde resultados de herramientas, avisos de simulación y prohibición de aprobar créditos. Pendiente:
validar respuestas LIVE a ataques de inyección indirecta y evitar nuevas rutas que permitan al modelo introducir tasas
de su imaginación.

**Acceso a datos privados.** Una consulta podría intentar obtener saldos, documentos o datos de terceros, incluso con
ingeniería social. Mitigación: no conectar a sistemas bancarios reales, no pedir credenciales, bloquear patrones
sensibles y utilizar datos sintéticos. Estos filtros heurísticos NO equivalen a verificación de identidad ni a controles
de autorización de producción.

**Grabación y consentimiento.** Audio, voz y transcripción pueden constituir datos personales; existe riesgo en
remitirlos a proveedores extranjeros, conservarlos en caches o reutilizarlos sin permiso. Mitigación: consentimiento
explícito antes de enviar audio, advertencia sobre proveedores, solo voces ficticias, base sin transcripciones y sin
copias locales deliberadas. Límites: Gradio/hosting puede conservar temporalmente audio, y los proveedores pueden tener
sus propias políticas de retención. No desplegar públicamente sin revisión contractual, legal y controles de retención.

**Automatización de decisiones y discriminación.** Automatizar una aprobación crediticia por características
socioeconómicas o proxies (barrio, forma de hablar, voz) puede perjudicar grupos protegidos. La función
`check_prequalification` nunca aprueba ni rechaza. Para un uso real sería necesario evaluar requisitos bancarios,
explicabilidad, revisión humana, derechos de reclamación, protección de datos y políticas antifraude.

**Llamadas comerciales y exclusión DNC.** Contactar personas sin autorización, en horas indebidas o después de oponerse
genera perjuicios y riesgos legales. En el MVP se simula una regla de consentimiento, exclusión Do-Not-Call y horario de
ejemplo; no existe telefonía. Las horas 09:00–18:00 son un parámetro técnico de DEMO y NO una conclusión jurídica sobre
la República Dominicana o LATAM. Antes de una campaña real se requiere revisión legal específica, gestión de
consentimientos y supresión auditable.

**Falsa expectativa de atención humana.** Un agente que dice «le transfiero» cuando no hay persona real puede crear
riesgo especial al reportar fraude. Mitigación: respuesta explícita «transferencia simulada»; en producción, integración
autenticada, disponibilidad real, canal alternativo y pruebas de continuidad.

## 2. Orígenes de sesgo y mitigaciones

- **Datos/servicios:** cobertura STT desigual -> muestra lingüística documentada y comparación WER.
- **Proxies:** registro coloquial asociado erróneamente con nivel económico -> no inferir ingresos, género, etnia o
  elegibilidad por voz.
- **Interfaz:** micrófono inaccesible o ambiente ruidoso -> canal alternativo de texto y confirmación.
- **Retroalimentación:** optimizar conversiones sobre quejas puede invisibilizar fallos -> medir escalamientos, rechazos
  y tasas de error junto con el costo.
- **Contexto institucional:** usuarios pueden confundir simulación con banca real -> aviso permanente de «Banco Demo
  ficticio», sin reclamos de certificación.

## 3. Comprobaciones y compromisos pendientes

Hay verificaciones automatizadas de denegación de datos sensibles, aprobación no vinculante, consentimiento de audio en
interfaz y reglas DNC simuladas. Falta auditoría adversarial del modelo con credenciales, prueba de dialecto en STT,
evaluación por participantes, revisión legal local, política formal de retención, controles de acceso y supervisión
humana efectiva. Las métricas obtenidas **no permiten afirmar ausencia de sesgo**.

## 4. Responsabilidad

El equipo mantiene responsabilidad sobre la configuración, calidad de datos, evaluación y operación. Una respuesta del
modelo no sustituye decisiones de profesionales financieros ni el consentimiento de los usuarios. Las decisiones de
crédito, reclamaciones y fraude deben quedar bajo una persona y sistemas formalmente autorizados.
