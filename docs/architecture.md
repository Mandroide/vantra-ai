# Arquitectura y decisiones técnicas

El diseño es un MVP de **atención bancaria ficticia**; separa la lógica del agente, las herramientas deterministas, el
procesamiento de voz y el transporte telefónico. La interfaz Gradio opera por turnos; el piloto de Twilio usa audio por
WebSocket. Ambas modalidades requieren pruebas LIVE independientes.

```mermaid
flowchart TD
  U[Participante] --> G[Gradio: texto o audio]
  G -->|Audio autorizado| DG[Deepgram STT por archivo]
  DG --> A[Orquestador Python]
  G -->|Texto| A
  A --> S[Guardrails y políticas]
  S --> F[Catálogo y cálculos deterministas]
  S --> DB[(SQLite sintético)]
  S -->|Preguntas abiertas en LIVE| L[Claude API]
  F --> A
  L --> A
  A --> G
  A -->|TTS opcional LIVE| AZ[Azure Speech]
  AZ --> G

  GR[Botón manual en Gradio] --> T[Twilio REST]
  T --> PSTN[Teléfono autorizado]
  PSTN <-->|Media Streams WSS| PROXY[ngrok / Cloudflare / Caddy]
  PROXY <-->|HTTPS y WSS| WS[FastAPI / WebSocket]
  WS <-->|Audio 8 kHz μ-law| DGS[Deepgram streaming]
  WS --> S
  WS <-->|Audio sintetizado| AZ
```

## Módulos

| Archivo                                                                | Responsabilidad                                                                                        |
|------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `app.py`                                                               | Interfaz, chat, consentimiento de audio, simulación y llamada manual restringida.                      |
| `src/agent.py`                                                         | Reglas, decisiones y uso de Claude cuando corresponda.                                                 |
| `src/tools.py`                                                         | Consulta del catálogo, cuotas y políticas deterministas.                                               |
| `src/speech.py`                                                        | Audio grabado hacia Deepgram y síntesis Azure por archivo.                                             |
| `src/telephony.py`                                                     | Validación RD E.164, DNC, allowlist, límites, solicitudes y reconciliación de estados con Twilio REST. |
| `src/telephony_server.py`                                              | Webhook firmado de estado asociado al ID local, WebSocket, streaming y síntesis telefónica.            |
| `scripts/reconcile_calls.py`                                           | Inspección local y consulta de estados remotos sin originar nuevas llamadas.                           |
| `src/storage.py`                                                       | Registros SQLite del prototipo.                                                                        |
| `scripts/connectivity.py`                                              | Selector ngrok/Cloudflare/direct y prueba pública HTTPS/WSS sin llamadas.                              |
| `compose.ngrok.yaml`, `compose.cloudflare.yaml`, `compose.direct.yaml` | Servicios de acceso público opcionales.                                                                |
| `infra/Caddyfile`                                                      | Proxy directo TLS que publica únicamente rutas de telefonía y healthz.                                 |
| `data/`                                                                | Información de prueba y escenarios sintéticos.                                                         |

## Flujos de llamada

- **Gradio:** se recibe audio de prueba, se solicita consentimiento, Deepgram devuelve texto; el motor responde mediante
  reglas/herramientas y, cuando aplica, Claude; Azure puede sintetizar una respuesta en WAV.
- **Twilio:** una persona operadora inicia explícitamente una única llamada de prueba a un número previamente
  autorizado. Twilio crea la llamada y solicita el TwiML/stream indicado. FastAPI recibe el audio μ-law 8 kHz, lo remite
  a Deepgram streaming, invoca el motor y devuelve audio de Azure adaptado al formato telefónico. Existe un mensaje
  inicial de identificación de IA. La conversación es **por turnos** y no admite interrupciones simultáneas
  garantizadas.

## Diseño financiero y seguridad

Las tasas salen del catálogo ficticio; la cuota sigue la fórmula de amortización `PMT = P·r/(1−(1+r)^(-n))`, con `r`
mensual y `n` meses. No supone seguros, impuestos ni comisiones y no constituye una oferta de crédito. El agente no
aprueba ni rechaza préstamos ni consulta cuentas bancarias reales.

Las restricciones telefónicas incorporan confirmación de consentimiento, lista permitida de `+1809/+1829/+1849`,
exclusión DNC, horario, límite diario configurable de 1 a 10 intentos y máximo de una llamada simultánea. Son
salvaguardas parciales, **no equivalen a cumplimiento normativo ni a autenticación de un servicio productivo**.

La simultaneidad se controla mediante reserva transaccional SQLite. Si existe una llamada registrada como activa, la
aplicación realiza una consulta **GET** al Call SID de Twilio antes de rechazar una nueva reserva; únicamente estados
terminales confirmados liberan ese cupo. El webhook firmado incluye un `call_id` aleatorio en la URL de callback para
asociar notificaciones aunque lleguen antes de recibirse la respuesta de creación. Estados sin SID, redes inaccesibles o
datos inconsistentes mantienen el bloqueo. La actualización de estados es monotónica y no revive llamadas finalizadas.

## Operación y limitaciones

La aplicación se ejecuta con uv o en Docker Compose (`vantra` en 7860 y `twilio-webhook` en 8000) y un volumen SQLite
compartido. El túnel ngrok, el túnel Cloudflare o el proxy Caddy deben dirigirse **solo a FastAPI**, no al panel Gradio.
Todos utilizan `TWILIO_PUBLIC_BASE_URL` y conservan firmas obligatorias y nonce. Los servicios base tienen healthchecks;
`scripts/connectivity.py probe` comprueba HTTPS y un rechazo WSS sin firma, no la interoperabilidad LIVE. Las
credenciales se configuran por entorno. No se debe exponer Gradio públicamente sin autenticación y control de costos.

No existen integraciones con CRM bancario real, autorizaciones de identidad real, transferencia humana efectiva ni
marcación por lotes. El código de los conectores **no demuestra por sí solo** llamadas ni latencias observadas; esas
métricas deben registrarse por separado.

Véanse [instalación](installation.md), [telefonía](telephony.md) y [evaluación](evaluation.md).
