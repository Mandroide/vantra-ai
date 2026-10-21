# Implementación de telefonía real — Vantra AI (RD)

**Actualización de código — 19 de octubre de 2026**

## Qué se implementó

- `src/telephony.py`: iniciación individual de llamadas salientes reales mediante Twilio REST (sin SDK), validación de
  teléfonos `+1809/+1829/+1849`, allowlist con consentimiento externo, horario America/Santo_Domingo, DNC permanente, 1
  llamada simultánea, máximo 3 solicitudes diarias y duración máxima de 180 segundos. Número destino representado por
  HMAC en SQLite, no texto claro.
- `src/telephony_server.py`: FastAPI con `POST /twilio/status` y WebSocket `/twilio/media`; verificación de
  `X-Twilio-Signature`, nonce por llamada, audio bidireccional Twilio μ-law 8kHz, Deepgram streaming STT, agente Vantra
  AI y Azure Speech TTS RAW μ-law. Indicaciones de fin de llamada y registro de exclusión vocal.
- `app.py`: nueva pestaña **Llamada REAL · piloto restringido** para iniciar una llamada, consultar estado, colgar y
  registrar exclusiones. La simulación existente permanece disponible.
- `compose.yaml`: servicio adicional `twilio-webhook`, puerto 8000 local y volumen SQLite compartido.
- `pyproject.toml`, `requirements.txt`, `.env.example`, `Dockerfile`: dependencias, variables nuevas y estado
  compartido.
- `tests/test_telephony.py`: casos de seguridad, normalización, HMAC, webhooks, restricciones, formato de audio, inicio
  y corte simulados.
- `docs/telefonia_dominicana.md`: guía de configuración paso a paso con requisitos Twilio, túnel HTTPS/WSS y solución de
  problemas.

## Comprobación de elaboración

**43 pruebas offline superadas** en el entorno de elaboración. La verificación heurística de secretos no detectó
coincidencias. Compilación sintáctica de los módulos correcta. **No hubo ningún intento real de llamada**, ni
verificación de conectividad hacia Twilio, Deepgram, Anthropic o Azure. No se construyó imagen Docker por ausencia del
motor Docker y `uv.lock` todavía se debe generar en una computadora con acceso a PyPI.

## Fuera de alcance

No se implementó marcador automático masivo, cola de campañas, CRM bancario real, contacto a números no autorizados,
interrupción por voz (*barge-in*) ni transferencia real a contact center. La funcionalidad no equivale a estar
autorizado a realizar campañas comerciales. Primero debe demostrarse con llamadas consentidas de integrantes del equipo.

**El informe académico de Fase 2 incluido en el paquete es anterior a esta extensión** y no contiene resultados
telefónicos de producción. Adjuntar nuevas mediciones reales después de pruebas consentidas.
