# Centro de documentación — Vantra AI

Manual unificado: **[Manual completo de instalación y despliegue](../MANUAL_INSTALACION_Y_DESPLIEGUE.md)**.

Guías operativas para el **MVP académico**, no un servicio bancario listo para producción. Siga el orden de la columna
«Cuándo leer»; los archivos se mantienen dentro del mismo repositorio, de forma que funcionan sin Internet después de
descargarlo (salvo descargas de herramientas y enlaces a los proveedores).

| Orden | Documento                                                                                                                                              | Cuándo leerlo                                            |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| 1     | [Inicio rápido y PyCharm](getting-started.md)                                                                                                          | Antes de instalar o ejecutar por primera vez.            |
| 2     | [Variables y proveedores](configuration.md)                                                                                                            | Para preparar `.env` sin publicar secretos.              |
| 3     | [Docker Compose](docker-deployment.md)                                                                                                                 | Para ejecutar interfaz y servidor telefónico.            |
| 4     | [Twilio y teléfonos dominicanos](twilio-setup.md)                                                                                                      | Para activar permisos, origen y destinatario autorizado. |
| 5     | [Ngrok y URL pública](ngrok-setup.md)                                                                                                                  | Para obtener `TWILIO_PUBLIC_BASE_URL`.                   |
| 6     | [Primera llamada REAL](first-call.md)                                                                                                                  | Solo después de superar las comprobaciones previas.      |
| 7     | [Solución de problemas](troubleshooting.md)                                                                                                            | Ante fallos de arranque, APIs o telefonía.               |
| 8     | [Arquitectura](architecture.md) y [referencia técnica de telefonía](telefonia_dominicana.md)                                                           | Para entender el código, sus límites y mensajes.         |
| 9     | [DevOps](devops.md)                                                                                                                                    | Para uv, pre-commit, GitHub Actions y cambios de código. |
| 10    | [Protocolo de evaluación](evaluation_protocol.md), [evidencias](evidence_checklist.md), [ética](ethical_analysis.md) y [guion de demo](demo_script.md) | Para la entrega de la Fase 2.                            |

**Estado verificado:** las pruebas locales del repositorio son offline/mocks; no equivalen a una llamada real ni
certifican funcionamiento con servicios externos. Para ejecutar LIVE se requieren acceso de red, credenciales,
facturación, permisos y consentimiento. No se ha auditado este prototipo para atender clientes reales.

**Reglas de seguridad:** la interfaz Gradio (puerto 7860) debe permanecer privada; solo se publica **el servidor
FastAPI (puerto 8000) a través del túnel HTTPS/WSS**. Nunca publicar `.env`, grabaciones de usuarios, números reales ni
historiales de llamadas. El piloto admite solo números `+1809`, `+1829` y `+1849` con permiso previo, una llamada
simultánea y tres solicitudes por día, de lunes a viernes entre las 09:00 y las 17:59 (hora de Santo Domingo).
