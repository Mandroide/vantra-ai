# Telefonía saliente autorizada: Twilio y República Dominicana

La pestaña **«Llamada REAL · piloto restringido»** inicia una llamada telefónica manual mediante Twilio. El sistema **no
realiza campañas masivas** y su integración con Deepgram, Claude y Azure aún exige validación integral con los
proveedores. Para operar con personas reales se necesitan consentimiento documentado, revisión legal y controles de
acceso; este procedimiento se limita a pruebas voluntarias.

## 1. Preparar Twilio

1. Habilite **Programmable Voice** en una cuenta que permita realizar llamadas mediante API y usar Media Streams
   bidireccionales. Las cuentas Trial pueden tener restricciones para `<Connect><Stream>` y la creación de llamadas.
2. Configure un número de origen (`TWILIO_FROM_NUMBER`) que pueda realizar llamadas salientes; compruebe su tipo,
   permisos y requisitos de caller ID.
3. Verifique en Twilio Console los **Voice Geographic Permissions** para República Dominicana y el estado de
   facturación/cuota.
4. Para un plan Trial, compruebe las restricciones de números destinatarios verificados. No intente eludir las
   limitaciones del proveedor.
5. Obtenga `Account SID` y `Auth Token` de la misma cuenta, sin registrarlos en Git ni en capturas públicas.

El destino debe tener formato E.164: **`+1809XXXXXXX`, `+1829XXXXXXX` o `+1849XXXXXXX`** (siete dígitos tras el
prefijo). Por seguridad, el software rechaza otros prefijos.

## 2. Configurar `.env`

```dotenv
VANTRA_MODE=LIVE
TWILIO_CALLS_ENABLED=false
TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS=false
TWILIO_DAILY_CALL_LIMIT=3
TWILIO_ACCOUNT_SID=AC_REEMPLAZAR_CON_SID_REAL
TWILIO_AUTH_TOKEN=REEMPLAZAR
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
TWILIO_PUBLIC_BASE_URL=
TWILIO_TEST_NUMBERS=+1809XXXXXXX
```

`TWILIO_TEST_NUMBERS` admite **varios números separados por comas**, siempre que exista autorización previa verificable
para cada titular. Complete también `DEEPGRAM_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`;
revise [configuration.md](configuration.md). Nunca publique números reales en ejemplos ni en el repositorio.

## 3. Levantar Docker y exponer FastAPI con ngrok

Desde la raíz del proyecto, en PyCharm:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=80 twilio-webhook
```

Compruebe **http://127.0.0.1:8000/healthz**. Después instale ngrok desde <https://ngrok.com/download>, obtenga un
authtoken en su panel y ejecútelo en una terminal separada:

```bash
ngrok config add-authtoken SU_TOKEN_PRIVADO
ngrok http 8000
```

No coloque el token real en el repositorio. ngrok mostrará una URL pública con HTTPS, por ejemplo
`https://ejemplo.ngrok-free.app` (URL ilustrativa). Copie **solo la base HTTPS**:

```dotenv
TWILIO_PUBLIC_BASE_URL=https://ejemplo.ngrok-free.app
```

La aplicación construye `https://.../twilio/status` y `wss://.../twilio/media`; **no agregue rutas, puerto, `/healthz`
ni `wss://` a la variable base**. Verifique en el navegador `https://SU_DOMINIO_REAL/healthz`. Esto comprueba la
conectividad, **no la respuesta de Twilio o la calidad de una llamada**.

Si ngrok cambia el dominio público, actualice la variable y recree ambos servicios:
`docker compose up -d --force-recreate`. El túnel debe apuntar al puerto 8000, **nunca al 7860 de Gradio**. Mantenga
abierto ngrok mientras prueba.

## 4. Verificación antes de marcar

- DEMO y LIVE de voz funcionan previamente por Gradio (modo, STT, LLM en consultas abiertas y TTS).
- La cuenta de Twilio tiene permiso de salida, saldo/cuota y soporte de WebSocket bidireccional.
- El número de origen está autorizado y el destino es del titular que dio consentimiento **antes** de la llamada.
- El destino figura en `TWILIO_TEST_NUMBERS`, no está en DNC y cumple los permisos geográficos.
- FastAPI y ngrok responden desde el dominio público; la máquina y los contenedores están protegidos.
- La conversación se presenta como prueba con Banco Demo **ficticio** y reconoce que el audio pasa por servicios
  externos.

Puede comprobar las variables locales con `uv run python scripts/check_twilio_setup.py` (en el host con uv). Ese script
**no crea llamadas ni verifica facturación o permisos de Twilio**.

## 5. Primera llamada controlada

1. Modifique `.env` a `TWILIO_CALLS_ENABLED=true` **solo después** de completar las verificaciones.
2. Recree los servicios: `docker compose up -d --force-recreate`.
3. Abra <http://127.0.0.1:7860> → **Llamada REAL · piloto restringido**.
4. Introduzca el destino E.164 autorizado, confirme ambas casillas y seleccione **«Iniciar UNA llamada real»**.
5. Observe el estado en Gradio, Twilio Console y `docker compose logs -f twilio-webhook`. La aceptación de Twilio **no
   significa que se haya contestado**.
6. Compruebe, con el participante, el saludo de identificación de IA, el audio de ambos sentidos, la finalización y la
   posibilidad de exclusión DNC.
7. Al terminar, desactive `TWILIO_CALLS_ENABLED`, recree contenedores y documente errores, latencias y costos realmente
   observados.

**Límites técnicos:** una llamada simultánea, límite diario configurable entre 1 y 10 intentos
(`TWILIO_DAILY_CALL_LIMIT`, predeterminado: 3), duración máxima de 180 segundos y horario por defecto de lunes a
viernes, 09:00–17:59 (`America/Santo_Domingo`). Para pruebas **manuales previamente autorizadas** fuera de horario
establezca temporalmente:

```dotenv
TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS=true
```

Luego `docker compose up -d --force-recreate`. Esta opción **solo desactiva la regla horaria local**; conserva
consentimiento, lista positiva, DNC y límites. Restáurela a `false` al terminar. No sustituye las normas de
comunicaciones comerciales aplicables.

**Límite diario:** el contador considera todas las solicitudes reservadas, incluidas las que Twilio rechaza (por
ejemplo, HTTP 401). Se reinicia a medianoche de Santo Domingo. Para ampliar temporalmente las pruebas a cinco intentos,
configure `TWILIO_DAILY_CALL_LIMIT=5` en `.env` y ejecute `docker compose up -d --force-recreate`. No borre el volumen
de SQLite para reiniciar el contador; podría borrar también la lista de exclusiones. Resolver primero el error del
proveedor evita consumir más intentos.

## 6. Diagnóstico y seguridad

- Si Twilio rechaza iniciar llamada, registre únicamente **estado HTTP y código numérico Twilio**;
  consulte [troubleshooting.md](troubleshooting.md) y **Twilio Console → Monitor → Debugger**. No reintente
  automáticamente: una solicitud con timeout podría haberse aceptado.
- Si Twilio crea la llamada pero no se escucha audio, examine `/twilio/media`, logs de WebSocket, credenciales/formatos
  Deepgram y Azure, y restricciones de la cuenta.
- Si un participante rechaza más comunicaciones, finalice y registre la exclusión DNC. No borre el volumen SQLite para
  sortear un bloqueo.
- Para esta demostración no hay transferencia efectiva a un operador humano, autenticación de usuarios ni garantías de
  disponibilidad.

Referencias: [Twilio Calls API](https://www.twilio.com/docs/voice/api/call-resource), [Media Streams](https://www.twilio.com/docs/voice/media-streams), [Twilio Trial](https://www.twilio.com/docs/usage/trials/try-out-voice), [ngrok](https://ngrok.com/docs/).
