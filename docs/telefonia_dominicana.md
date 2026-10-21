# Vantra AI · Llamadas salientes reales a República Dominicana (piloto)

> **Secuencia de configuración para usuarios
nuevos:** [Inicio](getting-started.md) → [Docker](docker-deployment.md) → [Twilio](twilio-setup.md) → [ngrok](ngrok-setup.md) → [Primera llamada](first-call.md).
> Este archivo conserva la **referencia técnica** del módulo telefónico.


**Estado:** implementación y pruebas unitarias con simulaciones disponibles; **ninguna llamada telefónica ni prueba en
vivo de los proveedores fue realizada durante la preparación de este paquete**.

## Alcance y controles

El botón «Llamada REAL · piloto restringido» inicia **una** llamada mediante la API REST de Twilio. Se permite solo a
teléfonos E.164 dominicanos `+1809XXXXXXX`, `+1829XXXXXXX` y `+1849XXXXXXX`, previamente agregados a
`TWILIO_TEST_NUMBERS` tras obtener permiso verificable del titular. Se requiere doble confirmación manual. Está apagado
por defecto (`TWILIO_CALLS_ENABLED=false`).

El servidor comprueba de nuevo permisos, horario de Santo Domingo (lunes a viernes, 9:00–17:59), lista de exclusión
persistente, un máximo de **1 llamada simultánea** y **3 solicitudes diarias**. Máximo de 180 segundos por llamada. **No
existe carga CSV, marcación masiva, auto-reintentos ni números arbitrarios.**

Un destinatario puede decir «no me llame» para registrar automáticamente su exclusión en SQLite (HMAC, sin guardar su
teléfono). El operador puede agregar una exclusión manual desde la misma pestaña de Gradio. Las conversaciones y audios
no se persisten en el servidor Vantra; se envían a los proveedores Deepgram (audio), Azure Speech (texto para TTS) y,
cuando corresponde, Anthropic (texto). Revise por separado las políticas de procesamiento y retención de cada proveedor
y los registros que pueda conservar Twilio. No afirmar que esta arquitectura es suficiente para cumplimiento normativo
bancario ni para campañas comerciales públicas.

## Credenciales necesarias

Ya están contempladas las de Deepgram, Anthropic y Azure. Ahora son necesarias, además, las de **Twilio Programmable
Voice**:

- `TWILIO_ACCOUNT_SID`: Account SID (comienza por `AC`).
- `TWILIO_AUTH_TOKEN`: Auth Token; **nunca** publicarlo.
- `TWILIO_FROM_NUMBER`: número Twilio con capacidad de voz o caller ID autorizado (E.164).
- `TWILIO_TEST_NUMBERS`: destinatarios con consentimiento comprobable, separados por comas, todos dominicanos.
- `TWILIO_PUBLIC_BASE_URL`: HTTPS público de un túnel TLS o dominio con proxy hacia el servicio **8000**; sin ruta al
  final.
- `TWILIO_CALLS_ENABLED=true`: habilitación explícita; **mantener false hasta estar listos**.

En la consola de Twilio, active **Voice Geographic Permissions para República Dominicana**. En cuentas trial los
destinatarios deben estar verificados y **puede no admitirse el TwiML `<Connect><Stream>` necesario para este código**;
la documentación de los trials cambia y algunas funciones requieren pasar a una cuenta de pago. Valide que el número de
origen tenga permiso para llamar a los destinos elegidos. Puede haber cargos de telefonía además de STT, LLM y TTS.

## Ejecución directa con uv

```bash
cd vantra-ai
cp .env.example .env
# Edite .env con sus datos. Mantenga TWILIO_CALLS_ENABLED=false al principio.
uv lock              # si todavía no se ha generado uv.lock
uv sync --group dev
uv run python -m pytest -q
uv run python scripts/check_twilio_setup.py  # configura y verifica, NO llama
```

Terminal 1 — interfaz privada:

```bash
uv run python app.py
# http://127.0.0.1:7860
```

Terminal 2 — servidor de audio y webhooks:

```bash
uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000
# http://127.0.0.1:8000/healthz
```

Exponga **solo el puerto 8000** mediante un túnel HTTPS/WSS seguro, por ejemplo un túnel de desarrollo hacia
`localhost:8000`. Configure `TWILIO_PUBLIC_BASE_URL=https://<host-publico>` y reinicie ambos procesos. Los caminos
públicos son `POST /twilio/status` y `WSS /twilio/media`; NO necesitan configurarse manualmente en Twilio porque la
llamada TwiML y el callback se suministran con cada solicitud. El servidor verifica la firma `X-Twilio-Signature` y un
nonce por llamada.

**No exponga Gradio 7860** a Internet sin autenticación y defensa CSRF, límites y controles de acceso. La interfaz
realiza llamadas reales y su acceso debe restringirse a personal autorizado.

Cuando haya verificado el número de origen, destinatario, consentimiento, túnel seguro y costos, cambie
`TWILIO_CALLS_ENABLED=true` en `.env` y **reinicie ambos procesos**. En Gradio abra «Llamada REAL · piloto restringido»,
escriba el número (E.164), marque ambas casillas y pulse «Iniciar UNA llamada real». El estado inicial `queued` no
significa que el destinatario haya contestado. Consulte el estado mediante el botón o la consola Twilio. Pulse
«Finalizar llamada» si lo desea.

## Con Docker Compose

```bash
docker compose up --build
```

`vantra` queda en `127.0.0.1:7860` y `twilio-webhook` en `127.0.0.1:8000` del host. Comparten un volumen de estado
`/state/vantra.sqlite3` para evitar inconsistencias entre la aplicación Gradio y el servidor FastAPI. El túnel HTTPS
hacia `localhost:8000` debe seguir disponible desde Internet. **No abra ninguno de estos puertos sin protección**.

## Audio y conversación

```text
Gradio (operador local) → Twilio REST → número +1809/+1829/+1849
               │
               ▼
  Twilio <Connect><Stream> → WSS firmado → FastAPI
               │
         audio μ-law 8kHz (cliente)
               ▼
      Deepgram streaming STT (es)
               ▼
        agente Python / Claude
               ▼
     Azure Speech TTS RAW μ-law 8kHz
               ▼
     WSS media+mark → Twilio → teléfono
```

La conversación funciona **por turnos** y silencia la entrada mientras habla el agente. No implementa *barge-in*
(interrumpir mientras habla), transferencias a una centralita real, grabación, colas o panel de supervisión en tiempo
real. Claude se consulta en preguntas que no pueden resolverse por reglas; muchas consultas del catálogo pasan por
herramientas Python. Los valores bancarios son ficticios.

## Diagnóstico

| Síntoma                         | Revisión                                                                                                                        |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Bloqueado antes de llamar       | Confirmación, lista positiva, horario RD, flag `TWILIO_CALLS_ENABLED`, lista DNC y 3 llamadas/día.                              |
| Twilio rechaza `Calls.json`     | País permitido en Voice Geo Permissions, plan trial, destinatario verificado, saldo/cuenta y caller ID.                         |
| Suena y finaliza                | Acceso WSS público, firma, nonce, conexión FastAPI; salida del túnel `https` y `wss`.                                           |
| Contesta sin oír voz            | Azure Speech: región, clave y disponibilidad de `es-DO-RamonaNeural`; comprobar bytes RAW μ-law.                                |
| Escucha voz pero no responde    | Deepgram streaming STT, suscripción, permisos y `language=es`, `encoding=mulaw`, 8000 Hz.                                       |
| Llama pero Claude nunca aparece | Muchas consultas se resuelven determinísticamente; pruebe pregunta fuera del catálogo y revise acceso a API sin revelar claves. |
| Solicitud HTTP expiró           | **NO vuelva a pulsar Llamar**: confirme primero en Twilio Console si se inició. Estado queda reservado como `initiated`.        |

**Notas operativas:** la clave del HMAC de exclusión es `TWILIO_AUTH_TOKEN`: si la rota, migre cuidadosamente la tabla
DNC (o regenere las exclusiones desde una fuente de consentimiento autorizada). La validación está diseñada para una
única instancia del piloto con SQLite compartido; no ha pasado auditoría de producción. Un proveedor de telefonía no
garantiza entrega a todos los operadores del país.

## Fuentes de documentación oficial

- Twilio, [Media Streams y requisitos](https://www.twilio.com/docs/voice/media-streams).
- Twilio, [mensajes WebSocket (μ-law 8000)](https://www.twilio.com/docs/voice/media-streams/websocket-messages).
- Twilio, [crear llamadas salientes](https://www.twilio.com/docs/voice/api/call-resource).
-

Twilio, [guía de llamadas para República Dominicana](https://www.twilio.com/en-us/guidelines/do/dominican-republic--voice-guidelines---twilio).

- Twilio, [restricciones de cuenta trial](https://www.twilio.com/docs/usage/trials/try-out-voice).
- Twilio, [validación de firma](https://www.twilio.com/docs/usage/security).
- Deepgram, [streaming STT](https://developers.deepgram.com/reference/speech-to-text/listen-streaming).
-

Microsoft, [Azure TTS formatos de audio](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/rest-text-to-speech).
