# Resolución de problemas

No comparta claves, teléfonos completos, firmas de Twilio, grabaciones, datos bancarios ni trazas con identificadores de
participantes. Anote solo servicio, hora aproximada, tipo de error, estado HTTP y **código numérico** del proveedor.

## Diagnóstico inicial

```bash
docker compose ps
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
```

Compruebe localmente <http://127.0.0.1:8000/healthz> y, si usa un proveedor público, `https://SU_DOMINIO_REAL/healthz`.
Ejecute `python scripts/connectivity.py check` y `python scripts/connectivity.py probe` (este último necesita Internet).

| Problema                                     | Causa o comprobación                                                                                                                                                     |
|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Docker no inicia                             | Verificar Docker Desktop, motor Linux y `docker info`.                                                                                                                   |
| Puerto ocupado                               | Cerrar proceso previo o modificar `VANTRA_PORT`/`TWILIO_WEBHOOK_PORT`; actualizar túnel si cambia 8000.                                                                  |
| Cambios de `.env` no aplicados               | Ejecutar `docker compose up -d --force-recreate`.                                                                                                                        |
| Cambios de código no aplicados               | Ejecutar `docker compose up -d --build`.                                                                                                                                 |
| Gradio sigue en DEMO                         | Comprobar `VANTRA_MODE=LIVE`, `.env` correcto y recreación de contenedor.                                                                                                |
| Claude aparentemente no se usa               | Algunas consultas se resuelven con Python; probar consulta abierta y verificar credencial/modelo/cuota.                                                                  |
| Deepgram no transcribe                       | Autorizar audio, comprobar LIVE, clave, modelo, formato y logs.                                                                                                          |
| Azure no produce sonido                      | Activar casilla de TTS, confirmar clave, región exacta, voz y cuota.                                                                                                     |
| No responde `/healthz`                       | Verificar servicio `twilio-webhook` y puerto 8000.                                                                                                                       |
| `/healthz` público no responde               | URL pública no coincide, ngrok/cloudflared apagado, Caddy sin DNS o TLS, proxy encaminado a host incorrecto.                                                             |
| Cloudflare devuelve 403, 1015 o desafío web  | Revisar Cloudflare Access y reglas WAF/Bot/Rate Limiting de las rutas Twilio; no desactivar validación de firmas FastAPI.                                                |
| ngrok muestra 404 o servicio no alcanzable   | Comprobar dominio reservado y `twilio-webhook:8000` (no `localhost` interno).                                                                                            |
| Caddy no obtiene certificado                 | Comprobar DNS, puertos TCP 80/443, firewall, IP pública y `CADDY_EMAIL`.                                                                                                 |
| Cambio de proveedor no surtió efecto         | Detener overlay anterior con `python scripts/connectivity.py down --provider ANTIGUO`, modificar `.env`, `check` y `up`.                                                 |
| WebSocket externo rechaza sin firma HTTP 403 | Es lo **esperado** para una prueba de seguridad; no significa que una llamada válida falle.                                                                              |
| `TWILIO_PUBLIC_BASE_URL` inválida            | Debe ser solo `https://host`, sin rutas ni consulta.                                                                                                                     |
| Llamada bloqueada por aplicación             | Revisar modo, activación, consentimientos, lista permitida, horario, DNC y límites. No suprimir controles para resolver un fallo.                                        |
| Llamada creada sin audio o cortada           | Revisar WebSocket `/twilio/media`, conectividad WSS, Twilio Debugger, Deepgram streaming y TTS μ-law/8 kHz.                                                              |
| Más llamadas bloqueadas tras error           | El sistema intenta conciliar automáticamente con Twilio los SID que figuran activos. Si Twilio aún está activo o no responde, mantiene el bloqueo. No borrar SQLite/DNC. |

## Llamada terminada en Twilio pero `queued` en SQLite

Una notificación de cierre puede perderse o adelantarse a la respuesta de creación. En esta versión, el webhook firmado
asocia los estados con `call_id` y, antes de reservar una nueva llamada, se consulta el estado real de los SID activos.
También puede sincronizar desde Gradio con **Consultar estado**.

Sin realizar llamadas, en PyCharm/Docker:

```powershell
docker compose exec vantra python -m scripts.reconcile_calls
# GET a Twilio: puede cambiar estados locales únicamente con confirmación remota
docker compose exec vantra python -m scripts.reconcile_calls --check
```

- `completed`, `busy`, `failed`, `no-answer` o `canceled`: se actualiza SQLite y deja de ocupar el cupo de
  simultaneidad.
- `queued`, `initiated`, `ringing`, `in-progress`: se mantiene el bloqueo.
- `reserved`/`initiated` sin SID, HTTP 401, timeout o respuesta no verificable: se mantiene el bloqueo. Revise Twilio
  Console antes de cualquier intervención manual.

El límite diario de intentos es **independiente**: aunque se libere la simultaneidad, los intentos previos continúan
sumando. Nunca ejecute `docker compose down -v` para resolverlo; borraría también la lista de exclusión.

## Twilio: error HTTP al iniciar llamada

El mensaje `HTTPError` no permite concluir que faltan fondos; una respuesta de la API puede deberse a credenciales,
origen, permisos geográficos, restricciones Trial u otro motivo. La aplicación muestra estado HTTP y, cuando existe,
código numérico Twilio sin imprimir la respuesta íntegra.

1. Consulte **Twilio Console → Monitor → Debugger** y, si se creó la llamada, sus Voice Logs.
2. Compare el código con la [documentación oficial de errores](https://www.twilio.com/docs/api/errors). Ejemplos
   posibles:

| Código            | Pista de diagnóstico                                        |
|-------------------|-------------------------------------------------------------|
| `20003`           | Autenticación de API incorrecta.                            |
| `21210` / `21212` | Autorización o validez del origen.                          |
| `21215`           | Voice Geographic Permissions del país de destino.           |
| `21219`           | Verificación del número destinatario exigida por la cuenta. |
| `10002`           | Función restringida para cuenta Trial.                      |

3. Revise si la cuenta admite **`<Connect><Stream>` y Media Streams bidireccionales**; algunas modalidades Trial no lo
   permiten. Un cambio de túnel o de `VANTRA_MODE` no elimina esa restricción.
4. Evite reintentos repetidos, especialmente si hubo timeout. Verifique primero el estado real en Twilio.

## WebSocket y firmas

La ruta Twilio debe ser `wss://SU_DOMINIO_REAL/twilio/media`. Un error de handshake (por ejemplo, 31920) requiere
revisar el túnel y la respuesta WebSocket. Si el webhook de estados responde 403, compruebe `TWILIO_PUBLIC_BASE_URL`,
host público utilizado por el proxy y credenciales; **no desactive la validación de firmas** para hacer pasar la prueba.

## Prueba de conectividad sin gastos telefónicos

`python scripts/connectivity.py probe` verifica `GET /healthz` por HTTPS y que `/twilio/media` rechace un WebSocket
**sin** `X-Twilio-Signature`. Si responde HTTP 403, el bloqueo de conexiones no autenticadas funciona. **No confirma**
el streaming legítimo ni las APIs de voz. No publique la salida de `docker compose config`, que puede revelar variables
sensibles.

## Qué registrar para soporte

Sistema operativo; versión de Compose; modo DEMO/LIVE; paso exacto; servicio implicado; hora; estado HTTP y código de
error; resultado de salud local y pública; descripción anonimizada. Mantenga las credenciales y números reales fuera de
capturas y chats.

Véanse [instalación](installation.md), [configuración](configuration.md) y [telefonía](telephony.md).
