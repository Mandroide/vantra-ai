# Configuración y secretos de Vantra AI

`.env.example` es el inventario de variables. Cree un `.env` local **fuera de Git** y no adjunte tokens, números
completos ni audios privados a los informes. Docker Compose usa `.env` para interpolación y transmite cada variable
declarada en `compose.yaml` a los contenedores.

## Servicios de IA

| Variable                                                      | Uso                                                        |
|---------------------------------------------------------------|------------------------------------------------------------|
| `VANTRA_MODE`                                                 | `DEMO` (sin proveedores externos) o `LIVE`                 |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`                       | Claude en consultas que requieren LLM                      |
| `DEEPGRAM_API_KEY` / `DEEPGRAM_MODEL`                         | Reconocimiento de voz                                      |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION`                    | Síntesis de voz; región del mismo recurso                  |
| `AZURE_SPEECH_VOICE`                                          | Voz configurada de Azure, p. ej. `es-DO-RamonaNeural`      |
| `LLM_INPUT_USD_PER_MILLION`, `LLM_OUTPUT_USD_PER_MILLION`     | Tarifas de referencia por tokens, actualizar con proveedor |
| `DEEPGRAM_USD_PER_MINUTE`, `AZURE_USD_PER_MILLION_CHARACTERS` | Tarifas de referencia, 0 **no significa gratuito**         |

**Nota:** la disponibilidad de modelos, voces y tarifas puede cambiar y debe comprobarse en las cuentas contratadas.
Azure genera audio μ-law de 8 kHz para Twilio. El modo DEMO no mide precisión acústica ni calidad de Claude.

## Twilio, permisos y seguridad

| Variable                                   | Uso                                                             |
|--------------------------------------------|-----------------------------------------------------------------|
| `TWILIO_CALLS_ENABLED`                     | Desactivado (`false`) de forma predeterminada                   |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | API REST y firmas de webhooks de la misma cuenta                |
| `TWILIO_FROM_NUMBER`                       | Número habilitado para voz saliente                             |
| `TWILIO_TEST_NUMBERS`                      | Lista E.164 dominicana, consentida, separada por comas          |
| `TWILIO_PUBLIC_BASE_URL`                   | Base HTTPS pública estable; sin ruta, puerto ni `/twilio/media` |
| `TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS`      | Excepción solo para pruebas manuales consentidas                |
| `TWILIO_DAILY_CALL_LIMIT`                  | Máximo de **1 a 10** intentos/día; predeterminado 3             |

La URL pública del webhook se obtiene añadiendo `/twilio/status` (la aplicación agrega internamente `?call_id=...` por
solicitud) y la del audio sustituyendo `https` por `wss` y añadiendo `/twilio/media`. Ese parámetro forma parte de la
validación de firma, y **no debe incorporarse manualmente** a `TWILIO_PUBLIC_BASE_URL`. Conserve los límites y la lista
DNC incluso si cambia el proveedor de túnel.

## Opciones de conectividad (solo una)

| Variable                  | Cuándo se utiliza                                                         |
|---------------------------|---------------------------------------------------------------------------|
| `CONNECTIVITY_PROVIDER`   | `ngrok`, `cloudflare` o `direct`; utilizado por `scripts/connectivity.py` |
| `NGROK_AUTHTOKEN`         | Modo ngrok, contenedor `ngrok/ngrok`                                      |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Tunnel administrado                                            |
| `VANTRA_PUBLIC_HOST`      | Host DNS (sin protocolo) de Caddy en modo directo                         |
| `CADDY_EMAIL`             | Correo de ACME/TLS automático para Caddy                                  |

Para ngrok se necesita URL de dominio reservado; para Cloudflare, el hostname público del túnel debe dirigirse a **
`http://twilio-webhook:8000`**; para directo, `VANTRA_PUBLIC_HOST` tiene que coincidir con el hostname de
`TWILIO_PUBLIC_BASE_URL`. **No cambie solamente `CONNECTIVITY_PROVIDER`: también debe actualizar la URL y detener el
overlay anterior.**

Valide sin iniciar llamadas:

```bash
python scripts/connectivity.py check
python scripts/connectivity.py up
python scripts/connectivity.py probe
```

`probe` sí necesita Internet, pero no usa credenciales ni crea llamadas. La guía de [telefonía](telephony.md) explica
cada proveedor y el proceso de migración.

**Referencias:** [Anthropic](https://docs.anthropic.com/), [Deepgram](https://developers.deepgram.com/), [Azure Speech](https://learn.microsoft.com/azure/ai-services/speech-service/), [Twilio Voice](https://www.twilio.com/docs/voice/).
