# Variables de entorno y proveedores

El archivo de referencia es [`../.env.example`](../.env.example) y la configuración se lee mediante [
`../src/config.py`](../src/config.py). **No comparta `.env`, capturas con claves ni token de ngrok.** Cree su `.env`
local y asegúrese de que esté excluido de Git (`.gitignore`). Docker Compose lo lee automáticamente cuando se ejecuta
desde la raíz del proyecto.

## Variables relevantes

| Variable                 | Valor inicial/ejemplo                             | Quién la necesita                                                           |
|--------------------------|---------------------------------------------------|-----------------------------------------------------------------------------|
| `VANTRA_MODE`            | `DEMO` o `LIVE`                                   | Gradio y servidor; `LIVE` permite invocar APIs.                             |
| `ANTHROPIC_API_KEY`      | (secreto)                                         | Claude en consultas abiertas.                                               |
| `ANTHROPIC_MODEL`        | `claude-sonnet-5` (configuración del repositorio) | Identificador que su cuenta debe tener habilitado; verifique con Anthropic. |
| `DEEPGRAM_API_KEY`       | (secreto)                                         | Transcripción grabada y streaming telefónico.                               |
| `DEEPGRAM_MODEL`         | `nova-3`                                          | Debe estar disponible en la cuenta/modelo/región.                           |
| `AZURE_SPEECH_KEY`       | (secreto)                                         | Síntesis de voz en modo LIVE.                                               |
| `AZURE_SPEECH_REGION`    | Ej.: `eastus`                                     | **Región exacta del recurso** de Azure, no ubicación del usuario.           |
| `AZURE_SPEECH_VOICE`     | `es-DO-RamonaNeural`                              | Voz deseada; verificar disponibilidad de la voz.                            |
| `TWILIO_CALLS_ENABLED`   | `false`                                           | Interruptor adicional obligatorio para llamadas reales.                     |
| `TWILIO_ACCOUNT_SID`     | `AC...`                                           | Identificador de cuenta Twilio.                                             |
| `TWILIO_AUTH_TOKEN`      | (secreto)                                         | Autenticación, validación de firma y HMAC de DNC.                           |
| `TWILIO_FROM_NUMBER`     | `+1...`                                           | Número/caller ID permitido por Twilio para llamadas de voz.                 |
| `TWILIO_PUBLIC_BASE_URL` | `https://...ngrok-free.app`                       | **URL que genera el túnel**, no procede de Twilio. Sin puerto ni ruta.      |
| `TWILIO_TEST_NUMBERS`    | `+1809XXXXXXX,+1829XXXXXXX`                       | Lista de destinatarios **autorizados**, separados por comas.                |
| `VANTRA_DB_PATH`         | `/state/vantra.sqlite3` dentro de Compose         | Estado compartido y DNC; ya fijado por `compose.yaml`.                      |

No necesita cambiar los campos de tarifas para que funcione; los importes inicialmente `0` indican **tarifas no
verificadas**, no gratuidad. Los servicios pueden cobrar por uso. Compruebe facturación y cuotas antes de hacer pruebas.

## Crear recursos y obtener credenciales (sin pegarlas aquí)

**Deepgram:** desde su consola, genere una API Key con permisos apropiados y compruebe el acceso al modelo. El flujo de
archivos de Gradio y el streaming telefónico emplean modos de reconocimiento distintos.

**Anthropic:** cree su API Key en Anthropic Console, confirme crédito/cuotas, permisos de API y el identificador del
modelo realmente habilitado en su cuenta. En Vantra AI, consultas conocidas pueden resolverse localmente; que la
aplicación responda no implica que se haya invocado Claude.

**Azure:** en Azure Portal, abra el recurso de **Speech / Azure AI Speech**, copie la clave de **Keys and Endpoint** y
anote la región del mismo recurso. No confunda «nombre legible de la región» con el código que acepta el SDK (`eastus`,
etc.). La voz `es-DO-RamonaNeural` es la preferencia propuesta; la disponibilidad y síntesis deben verificarse con una
solicitud real.

**Twilio:** véase [configuración de Twilio](twilio-setup.md) y [ngrok](ngrok-setup.md).

## Ejemplo SIN credenciales reales

```dotenv
VANTRA_MODE=LIVE
ANTHROPIC_API_KEY=REEMPLAZAR_CON_CLAVE_REAL
ANTHROPIC_MODEL=REEMPLAZAR_SI_NO_ESTA_HABILITADO
DEEPGRAM_API_KEY=REEMPLAZAR_CON_CLAVE_REAL
DEEPGRAM_MODEL=nova-3
AZURE_SPEECH_KEY=REEMPLAZAR_CON_CLAVE_REAL
AZURE_SPEECH_REGION=REEMPLAZAR_CON_REGION_REAL
AZURE_SPEECH_VOICE=es-DO-RamonaNeural
TWILIO_CALLS_ENABLED=false
TWILIO_ACCOUNT_SID=AC_REEMPLAZAR
TWILIO_AUTH_TOKEN=REEMPLAZAR
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
TWILIO_PUBLIC_BASE_URL=
TWILIO_TEST_NUMBERS=
```

No copie este bloque como configuración definitiva: son marcadores de posición. `VANTRA_MODE=LIVE` **no realiza llamadas
por sí solo**. Solo el operador, desde la pestaña de telefonía real, puede solicitar una llamada tras habilitar el
segundo interruptor y superar las validaciones.

## Aplicar cambios con Docker

```powershell
docker compose up -d --force-recreate
docker compose ps
```

El contenedor **no** se actualiza simplemente al guardar `.env`: debe recrearse. Para modificar Python o dependencias,
además reconstruya: `docker compose up -d --build`. Evite comandos que vuelquen toda la configuración efectiva del
contenedor en terminales grabadas, porque pueden exponer secretos.

## Seguridad y privacidad

- Nunca incorpore las API Keys al código, README, tickets, logs compartidos o imágenes Docker.
- La aplicación maneja **datos bancarios ficticios**. No use números de cuenta ni identidades de clientes reales.
- Aunque el servidor no conserve deliberadamente el audio en SQLite, Twilio y los proveedores de STT/TTS/LLM pueden
  tener sus propias políticas de registros/retención.
- `TWILIO_AUTH_TOKEN` se usa también para calcular hashes HMAC de las exclusiones. **Rotarlo cambia el hash de nuevos
  números** y puede invalidar la consulta de entradas DNC anteriores. Planifique una migración o revalidación de
  exclusiones antes de cualquier rotación en un piloto activo.
- Si sospecha que una clave fue expuesta, revóquela en el proveedor y genere otra; borrar el archivo no la revoca.

## Referencias oficiales

- [Anthropic API](https://docs.anthropic.com/en/api/getting-started)
- [Deepgram STT](https://developers.deepgram.com/docs/pre-recorded-audio)
- [Azure Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [Twilio Console](https://console.twilio.com/)
