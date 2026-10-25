# Telefonía de Vantra AI: Twilio, túneles y acceso HTTPS directo

Esta guía configura **llamadas salientes manuales** a números dominicanos preautorizados, conectadas a Twilio Media
Streams. No es un marcador masivo ni un servicio bancario de producción. El chat de Gradio se mantiene accesible **solo
en localhost**; la única aplicación que se publica es el receptor FastAPI. La llamada conversacional a un compañero
reportada por el equipo es evidencia de un piloto, pero **no certifica** seguridad, rendimiento ni disponibilidad de una
solución comercial.

## Flujo de telefonía

```text
Operador en Gradio (localhost:7860)
    -> consentimiento + lista autorizada + DNC + límites
    -> API REST Twilio: llamada saliente al teléfono de prueba (+1809/+1829/+1849)
    -> webhook de estado HTTPS /twilio/status
    -> Media Streams WSS /twilio/media
    -> FastAPI -> Deepgram streaming -> Claude y herramientas -> Azure TTS μ-law 8 kHz
```

Twilio necesita una **URL pública HTTPS persistente** para el webhook y un endpoint **WSS** para el audio; Docker por sí
solo no los proporciona. La aplicación genera los dos endpoints a partir de `TWILIO_PUBLIC_BASE_URL`. El proveedor de
acceso público **no altera el agente**. Ver [architecture.md](architecture.md).

## 1. Credenciales y política del piloto

Configure en `.env`:

```dotenv
VANTRA_MODE=LIVE
TWILIO_CALLS_ENABLED=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_TEST_NUMBERS=
TWILIO_PUBLIC_BASE_URL=
TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS=false
TWILIO_DAILY_CALL_LIMIT=3
```

También necesita `DEEPGRAM_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`. Utilice el mismo
Account SID y Auth Token de Twilio para iniciar llamadas y verificar firmas. El número origen debe tener capacidad
Voice. Compruebe **Voice Geographic Permissions** para República Dominicana, las condiciones de la cuenta y las cuotas.
Las cuentas Trial pueden limitar números verificados y Media Streams. **No publique `.env`, registros con números ni
capturas con secretos.**

Destinatarios: exclusivamente E.164 `+1809XXXXXXX`, `+1829XXXXXXX`, `+1849XXXXXXX`. `TWILIO_TEST_NUMBERS` enumera
contactos con consentimiento previo comprobable. Una casilla de confirmación no reemplaza la evidencia del
consentimiento. Existe exclusión DNC, máximo de una llamada simultánea, un límite de **1 a 10 intentos diarios**
(predeterminado 3, incluyendo fallos del proveedor) y horario local de lunes a viernes 09:00–17:59. Para una prueba
excepcional y consentida fuera de horario puede configurarse `TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS=true`; no elimina la
normativa aplicable.

## 2. Elegir una sola conectividad

Hay tres archivos que se **combinan** con `compose.yaml`; ninguno se utiliza solo. Seleccione el proveedor en `.env` con
`CONNECTIVITY_PROVIDER=ngrok|cloudflare|direct`. Se puede ejecutar con `python scripts/connectivity.py` (o
`uv run python ...`). El script valida coherencia y ejecuta Compose sin almacenar tokens adicionales.

### A. ngrok en Docker (recomendado para desarrollo)

Reserve un dominio de desarrollo persistente en su cuenta ngrok; ejemplo ilustrativo: `https://ejemplo.ngrok-free.dev`.
Copie su token en `.env`:

```dotenv
CONNECTIVITY_PROVIDER=ngrok
NGROK_AUTHTOKEN=SU_TOKEN
TWILIO_PUBLIC_BASE_URL=https://ejemplo.ngrok-free.dev
```

Comandos desde PyCharm, en la raíz del repositorio:

```powershell
python scripts/connectivity.py check
python scripts/connectivity.py up
python scripts/connectivity.py status
```

Equivalente explícito: `docker compose -f compose.yaml -f compose.ngrok.yaml up -d --build`. ngrok se conecta **dentro
de la red Docker** a `http://twilio-webhook:8000`. No hace falta ngrok instalado en Windows ni `ngrok http 8000` en otra
terminal.

### B. Cloudflare Tunnel en Docker (hostname propio)

Cree un túnel **administrado** en el panel de Cloudflare con un dominio que controle. Configure **Public Hostname**, por
ejemplo `voice.tudominio.com`, apuntando a `http://twilio-webhook:8000` (no a `localhost:8000` ni a `vantra:7860`).
Copie el token del conector:

```dotenv
CONNECTIVITY_PROVIDER=cloudflare
CLOUDFLARE_TUNNEL_TOKEN=SU_TOKEN
TWILIO_PUBLIC_BASE_URL=https://voice.tudominio.com
```

Ejecute `python scripts/connectivity.py check` y después `python scripts/connectivity.py up`. Equivale a
`docker compose -f compose.yaml -f compose.cloudflare.yaml up -d --build`. Verifique que **WebSockets** estén permitidos
y que Cloudflare Access, WAF, bots, CAPTCHA y otras reglas **no impidan a Twilio** conectar a `/twilio/status` y
`/twilio/media`. La validación criptográfica de Twilio se realiza en FastAPI; no deshabilite firmas para sortear reglas
del proxy.

Un *Quick Tunnel* `trycloudflare.com` sirve para pruebas HTTP efímeras, **no** para un callback estable con Twilio:
puede cambiar de URL entre arranques y el script lo rechaza.

### C. Acceso directo con Caddy (servidor público)

Requiere un host con IP pública accesible, DNS `A`/`AAAA` a ese servidor y puertos **80 y 443** libres y habilitados
(incluido el router/cortafuegos cuando corresponda). Configure:

```dotenv
CONNECTIVITY_PROVIDER=direct
VANTRA_PUBLIC_HOST=voice.tudominio.com
CADDY_EMAIL=operaciones@tudominio.com
TWILIO_PUBLIC_BASE_URL=https://voice.tudominio.com
```

`python scripts/connectivity.py up` combina `compose.yaml` + `compose.direct.yaml`, añade el contenedor Caddy y utiliza
`infra/Caddyfile`. Caddy gestiona TLS y el proxy WebSocket; solamente publica `/healthz` y `/twilio/*`, nunca la
interfaz Gradio. `TWILIO_PUBLIC_BASE_URL` debe coincidir exactamente con el hostname de Caddy. **No intente usar este
modo desde un equipo tras CGNAT sin puertos accesibles.**

## 3. Cambio de proveedor y diagnóstico

**Nunca mantenga dos túneles activos a la vez para el mismo entorno.** Antes de cambiar, detenga las llamadas, guarde el
estado de la llamada y ejecute:

```powershell
python scripts/connectivity.py down --provider ngrok
# Edite .env: cambie proveedor, URL y sus credenciales.
python scripts/connectivity.py check
python scripts/connectivity.py up
```

Comprobación local (sin llamadas): `http://127.0.0.1:8000/healthz` y `docker compose ps`. La prueba externa automática,
con conectividad de Internet, es:

```powershell
python scripts/connectivity.py probe
```

Comprueba `https://DOMINIO/healthz` y que `wss://DOMINIO/twilio/media` **rechaza un WebSocket sin firma** (`HTTP 403`
esperado). Esto **no confirma** que un WebSocket legítimo o los proveedores de voz estén funcionando: para eso hay que
hacer una llamada real autorizada y revisar estados y logs.

Para logs del túnel:

```powershell
docker compose -f compose.yaml -f compose.ngrok.yaml logs --tail=100 ngrok
docker compose -f compose.yaml -f compose.cloudflare.yaml logs --tail=100 cloudflared
docker compose -f compose.yaml -f compose.direct.yaml logs --tail=100 caddy
```

`docker compose logs --tail=100 twilio-webhook` sirve para el webhook; `POST /twilio/status 200` únicamente confirma la
recepción del callback, **no una conversación de voz**. En Twilio Console revise `queued` → `ringing` → `in-progress` →
`completed`, y los fallos `busy`, `failed`, `no-answer`, junto con respuestas SIP y códigos Q.850. Si el teléfono nunca
sonó, investigue el operador y la ruta internacional antes de modificar Deepgram/Claude/Azure.

## 4. Recuperación automática del estado y bloqueo por simultaneidad

Las notificaciones de Twilio pueden llegar antes de que la llamada tenga un Call SID guardado o pueden perderse si el
túnel estuvo caído. Para reducir bloqueos falsos:

- Cada llamada saliente incluye `?call_id=<identificador aleatorio>` en **su propio** `StatusCallback`, firmado por
  Twilio. El servidor verifica la firma utilizando la URL completa y enlaza el Call SID con la reserva SQLite sin
  confiar en cabeceras Host.
- Al intentar reservar otra llamada cuando SQLite muestra una activa, `src/telephony.py` ejecuta **GET a Twilio** para
  cualquier Call SID activo. Si confirma `completed`, `busy`, `no-answer`, `failed` o `canceled`, actualiza la base de
  datos y vuelve a evaluar el límite dentro de una transacción SQLite.
- Si Twilio responde `queued`, `initiated`, `ringing` o `in-progress`, si la solicitud falla o si el registro no tiene
  SID, **no libera el cupo**. Se prohíben reintentos automáticos de marcación.
- **Consultar estado** en Gradio sincroniza una llamada con SID. Las consultas GET no generan nuevas llamadas; el límite
  diario sigue contando todas las reservas originales, incluidas las fallidas.

Para revisar llamadas activas desde PyCharm, usando la versión Docker actual:

```powershell
docker compose exec vantra python -m scripts.reconcile_calls
# Consulta Twilio para cada SID activo y actualiza únicamente estados verificados:
docker compose exec vantra python -m scripts.reconcile_calls --check
```

El comando no muestra números de teléfono ni Auth Tokens. Si aparece un registro sin SID (`reserved` o un timeout de
creación), se necesita verificar **manualmente** en Twilio Console el historial antes de corregirlo; no borre SQLite ni
la lista DNC. Una operación de cambio de estado manual solo es aceptable después de confirmar con evidencia que no
existe una llamada activa. Los registros históricos no se eliminan.

### Validación tras actualizar el repositorio

Ejecute `docker compose up -d --build --force-recreate` desde PyCharm. Compruebe
`docker compose logs --tail=100 twilio-webhook` y revise el estado con el comando anterior **antes** de lanzar otra
llamada autorizada. El código corregido cubre carreras de callback y bloqueos por estados terminales, pero la ruta real
a Twilio debe validarse desde su propia cuenta.

## 4. Seguridad de webhooks y WebSocket

- Se valida `X-Twilio-Signature` con HMAC, token de Twilio y **URL pública completa (incluida la query firmada)**; nunca
  se confía en un `Host` enviado por el cliente. WebSocket admite la variante con barra final recomendada por Twilio.
- El WebSocket exige firma válida y un `call_id` con `nonce` de un solo flujo asociado a la llamada iniciada en el
  sistema. No se admite abrir arbitrariamente conversaciones entrantes.
- Caddy aplica una lista explícita de rutas; los túneles exponen el servidor FastAPI, **no Gradio**. `/readyz` solo está
  disponible localmente en FastAPI y no revela claves.
- Solo se admiten llamadas manuales a la lista positiva. No habilite campaña masiva ni desplegue la UI en Internet sin
  autenticación, control de acceso y revisión legal.
- FastAPI no registra audio ni transcripciones: registra estado Twilio, inicio/fin de stream y tiempos parciales de
  agente y síntesis usando un identificador seudonimizado `call_ref`. Son **tiempos internos**, no latencia total ni
  costo facturado. Los logs pueden contener metadatos de operación y requieren control de acceso. La retención y los
  registros de los proveedores externos requieren revisión independiente.

**Documentación
oficial:** [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams), [Twilio: validación de solicitudes](https://www.twilio.com/docs/usage/security), [ngrok Docker](https://ngrok.com/download/docker), [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/), [Caddy HTTPS](https://caddyserver.com/docs/automatic-https).
