# Configuración del entorno y proveedores

Las variables están definidas en `.env.example` y se cargan desde `.env`. No copie claves dentro del código, de la
imagen Docker, de GitHub ni de capturas de pantalla. Las claves de los proveedores deben disponer de permisos y límites
de gasto adecuados.

## Variables de ejecución

| Variable                           | Uso                                                                                               |
|------------------------------------|---------------------------------------------------------------------------------------------------|
| `VANTRA_MODE`                      | `DEMO` (sin APIs) o `LIVE` (integraciones externas).                                              |
| `ANTHROPIC_API_KEY`                | Credencial API de Claude.                                                                         |
| `ANTHROPIC_MODEL`                  | Identificador de modelo habilitado en su cuenta; el ejemplo inicial puede requerir actualización. |
| `DEEPGRAM_API_KEY`                 | Clave para transcripción por archivo y por streaming.                                             |
| `DEEPGRAM_MODEL`                   | Modelo configurado de transcripción.                                                              |
| `AZURE_SPEECH_KEY`                 | Clave del recurso Azure AI Speech.                                                                |
| `AZURE_SPEECH_REGION`              | Región **exacta** de dicho recurso, p. ej., `eastus` si corresponde.                              |
| `AZURE_SPEECH_VOICE`               | Voz TTS: valor inicial `es-DO-RamonaNeural`; confirmar disponibilidad.                            |
| `ENABLE_LOCAL_TTS`                 | Opción local de espeak para DEMO si está instalado; en Compose está deshabilitada.                |
| `LLM_INPUT_USD_PER_MILLION`        | Tarifa estimada configurada manualmente; cero no implica gratuidad.                               |
| `LLM_OUTPUT_USD_PER_MILLION`       | Tarifa estimada de tokens de salida.                                                              |
| `DEEPGRAM_USD_PER_MINUTE`          | Tarifa estimada por minuto procesado.                                                             |
| `AZURE_USD_PER_MILLION_CHARACTERS` | Tarifa estimada de TTS.                                                                           |

Las variables telefónicas son `TWILIO_CALLS_ENABLED`, `TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS`, `TWILIO_ACCOUNT_SID`,
`TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_PUBLIC_BASE_URL` y `TWILIO_TEST_NUMBERS`. Su significado y controles
se documentan en [telephony.md](telephony.md).

## Preparación de cuentas

- **Anthropic:** confirme API Key, acceso al identificador de modelo y límites/facturación habilitados. Algunas
  consultas bancarias se resuelven con Python y no implican una llamada al LLM.
- **Deepgram:** cree clave con acceso al servicio STT y verifique cuota. Audio recibido desde Gradio se envía al
  servicio con permiso explícito del usuario.
- **Azure Speech:** cree recurso Speech, copie clave y región desde Azure Portal y configure una voz admitida. La región
  incorrecta provoca errores aunque la clave sea correcta.
- **Twilio:** requiere configurar telefonía Voice por separado; no se activa solo por establecer `VANTRA_MODE=LIVE`.

## Ejemplo de `.env` sin secretos

```dotenv
VANTRA_MODE=DEMO
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-5
DEEPGRAM_API_KEY=
DEEPGRAM_MODEL=nova-3
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_SPEECH_VOICE=es-DO-RamonaNeural
TWILIO_CALLS_ENABLED=false
TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_PUBLIC_BASE_URL=
TWILIO_TEST_NUMBERS=
```

**No dé por confirmado** que un modelo de ejemplo esté disponible: la cuenta, el nombre y el SDK deben comprobarse
contra el proveedor. Las tarifas en cero significan «sin tarifa registrada», **no costo nulo**.

## Orden recomendado de verificación

1. DEMO: chat por texto y herramientas bancarias.
2. LIVE por texto: comprobar credencial de Anthropic mediante una pregunta abierta.
3. LIVE por audio: autorizar una grabación ficticia de prueba para Deepgram.
4. LIVE con la opción «Generar audio de respuesta»: comprobar Azure Speech.
5. Solo entonces, verificar Twilio y el túnel público mediante [telephony.md](telephony.md).

Reinicie los contenedores después de editar `.env`: `docker compose up -d --force-recreate`. Para aislar errores,
consulte [troubleshooting.md](troubleshooting.md).

Referencias de los
fabricantes: [Anthropic API](https://docs.anthropic.com/), [Deepgram](https://developers.deepgram.com/), [Azure Speech](https://learn.microsoft.com/azure/ai-services/speech-service/), [Twilio Voice](https://www.twilio.com/docs/voice).

### Límite de intentos de telefonía

`TWILIO_DAILY_CALL_LIMIT=3` controla el número máximo de intentos diarios (rango admitido: 1–10) en la zona horaria de
Santo Domingo. Incluye solicitudes fallidas, sin eliminar los controles de consentimiento, autorización de destinatario
y DNC.
