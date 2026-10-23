# Resolución de problemas

No comparta claves, teléfonos completos, firmas de Twilio, grabaciones, datos bancarios ni trazas con identificadores de
participantes. Anote solo servicio, hora aproximada, tipo de error, estado HTTP y **código numérico** del proveedor.

## Diagnóstico inicial

```bash
docker compose ps
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
```

Compruebe localmente <http://127.0.0.1:8000/healthz> y, si usa ngrok, `https://SU_DOMINIO_REAL/healthz`.

| Problema                           | Causa o comprobación                                                                                                              |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| Docker no inicia                   | Verificar Docker Desktop, motor Linux y `docker info`.                                                                            |
| Puerto ocupado                     | Cerrar proceso previo o modificar `VANTRA_PORT`/`TWILIO_WEBHOOK_PORT`; actualizar túnel si cambia 8000.                           |
| Cambios de `.env` no aplicados     | Ejecutar `docker compose up -d --force-recreate`.                                                                                 |
| Cambios de código no aplicados     | Ejecutar `docker compose up -d --build`.                                                                                          |
| Gradio sigue en DEMO               | Comprobar `VANTRA_MODE=LIVE`, `.env` correcto y recreación de contenedor.                                                         |
| Claude aparentemente no se usa     | Algunas consultas se resuelven con Python; probar consulta abierta y verificar credencial/modelo/cuota.                           |
| Deepgram no transcribe             | Autorizar audio, comprobar LIVE, clave, modelo, formato y logs.                                                                   |
| Azure no produce sonido            | Activar casilla de TTS, confirmar clave, región exacta, voz y cuota.                                                              |
| No responde `/healthz`             | Verificar servicio `twilio-webhook` y puerto 8000.                                                                                |
| `/healthz` público no responde     | ngrok cerrado, dominio cambiado o túnel dirigido a un puerto incorrecto.                                                          |
| `TWILIO_PUBLIC_BASE_URL` inválida  | Debe ser solo `https://host`, sin rutas ni consulta.                                                                              |
| Llamada bloqueada por aplicación   | Revisar modo, activación, consentimientos, lista permitida, horario, DNC y límites. No suprimir controles para resolver un fallo. |
| Llamada creada sin audio o cortada | Revisar WebSocket `/twilio/media`, conectividad WSS, Twilio Debugger, Deepgram streaming y TTS μ-law/8 kHz.                       |
| Más llamadas bloqueadas tras error | Una petición incierta puede estar activa; confirmar en Twilio Console **antes** de reintentar. No borrar SQLite/DNC.              |

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
host realmente utilizado por ngrok y credenciales; **no desactive la validación de firmas** para hacer pasar la prueba.

## Qué registrar para soporte

Sistema operativo; versión de Compose; modo DEMO/LIVE; paso exacto; servicio implicado; hora; estado HTTP y código de
error; resultado de salud local y pública; descripción anonimizada. Mantenga las credenciales y números reales fuera de
capturas y chats.

Véanse [instalación](installation.md), [configuración](configuration.md) y [telefonía](telephony.md).
