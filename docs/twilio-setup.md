# Twilio Programmable Voice — piloto saliente a República Dominicana

**Esta guía no inicia llamadas.** Prepara la cuenta y el repositorio. Solo continúe si los titulares de los números de
prueba han dado consentimiento previo verificable. Vantra AI acepta exclusivamente números en formato E.164 con prefijos
`+1809`, `+1829` y `+1849` seguidos por 7 dígitos.

## 1. Preparar la cuenta Twilio

1. Acceda a [Twilio Console](https://console.twilio.com/), seleccione el **proyecto correcto** y compruebe si la cuenta
   es Trial o de pago.
2. Identifique **Account SID** (`AC...`) y **Auth Token** en las secciones de credenciales de la consola. No comparta el
   token ni lo suba a Git.
3. Compruebe que la cuenta dispone de capacidad de **Programmable Voice** y saldo/cuotas para una llamada de prueba.
   Verifique restricciones del país donde se registró la cuenta; la modalidad de prueba puede limitar llamadas al país
   de registro, requerir destinos verificados y restringir TwiML/Media Streams. **La guía oficial actual de Twilio Trial
   restringe parámetros de `Create a Call` y no garantiza compatibilidad con la instrucción `<Connect><Stream>` que usa
   Vantra AI; si su plan no permite esa combinación, necesitará una cuenta habilitada para utilizarla.**
4. Obtenga un **número Twilio con capacidad de llamadas salientes** o un identificador de llamada verificado y admitido
   por el plan. Anótelo en E.164 como `TWILIO_FROM_NUMBER`. El prefijo del número **de origen no tiene por qué ser
   dominicano**: depende de disponibilidad, reglas del servicio y permisos. El destino del prototipo sí debe ser
   dominicano.
5. Abra **Voice → Settings → Geo Permissions** (las etiquetas de Console pueden cambiar) y verifique la habilitación de
   **Dominican Republic** para llamadas salientes según las opciones de riesgo disponibles. No confunda permisos de
   **Voice** con los de **Verify** ni Messaging. Algunas rutas requieren aprobación de soporte.
6. Si está en Trial, agregue/verifique el número de destino en la sección de números verificados de su cuenta, de
   acuerdo con la guía que muestre Twilio. La verificación de Twilio **no sustituye consentimiento**.
7. Revise tarifas por destino, identificación de llamadas, eventuales mensajes de prueba y límites para ese plan.

## 2. Datos que debe tener preparados

| Elemento            | Ejemplo de formato                    | Verificación                                                  |
|---------------------|---------------------------------------|---------------------------------------------------------------|
| Account SID         | `AC` seguido de 32 caracteres         | Pertenece al mismo proyecto que el token.                     |
| Auth Token          | Cadena secreta                        | No publicarlo ni pegarlo en el chat.                          |
| Caller ID           | `+1XXXXXXXXXX`                        | Habilitado para voz y autorizado.                             |
| Destino de prueba   | `+1809XXXXXXX`                        | Está en RD, permitido por Twilio y aceptó recibir la llamada. |
| Ventana de contacto | Lunes a viernes, 09:00–17:59, hora RD | Restricción efectiva del código.                              |
| Base pública        | `https://<host>.ngrok-free.app`       | Debe responder `/healthz`, y aceptar WebSocket WSS.           |

**No pruebe con números encontrados públicamente ni con bases de datos de clientes.** Para la clase utilice su propio
teléfono o el de un integrante que haya autorizado expresamente recibir la prueba. Documente el consentimiento de forma
segura fuera de Git y Google Drive público.

## 3. Configurar `.env` sin activar llamadas todavía

```dotenv
VANTRA_MODE=LIVE
TWILIO_CALLS_ENABLED=false
TWILIO_ACCOUNT_SID=AC_REEMPLAZAR
TWILIO_AUTH_TOKEN=REEMPLAZAR
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
TWILIO_PUBLIC_BASE_URL=
TWILIO_TEST_NUMBERS=+1809XXXXXXX
```

También requiere claves reales de **Anthropic, Deepgram y Azure Speech** y la región Azure correcta;
véase [configuración](configuration.md). Para múltiples destinatarios de prueba:
`TWILIO_TEST_NUMBERS=+1809XXXXXXX,+1829XXXXXXX` sin comillas. No agregue números sin consentimiento.

Obtenga la URL de [ngrok](ngrok-setup.md) y agréguela **sin** `/twilio/media`, `/twilio/status`, rutas, puerto ni barra
final.

## 4. Verificar la configuración local antes de activar

Con Docker ejecutando ambos servicios:

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

El archivo `scripts/check_twilio_setup.py` comprueba **presencia y formato de variables locales**, no autenticación ni
créditos. Se puede ejecutar con `uv run python scripts/check_twilio_setup.py` en la raíz del proyecto si dispone de uv.
**Devolverá `FALTA` y código 1 mientras `TWILIO_CALLS_ENABLED=false`, lo cual es intencional antes de la activación.**
**Importante:** el `Dockerfile` actual no incorpora `scripts/` a la imagen de ejecución. Por eso, ejecute este
verificador desde el host con `uv`, **no** con `docker compose exec`. No cambie `TWILIO_CALLS_ENABLED` a `true` solo
para que el verificador diga «OK»; hágalo únicamente después de completar los pasos de seguridad.

## 5. ¿Hay que configurar webhooks en Twilio Console?

**Para llamadas salientes iniciadas mediante esta implementación, no.** `src/telephony.py` envía TwiML inline con
`<Connect><Stream>` y suministra un `StatusCallback` por cada llamada mediante la API de Twilio. Las rutas generadas por
el código son:

```text
https://<su-host>/twilio/status  → POST: eventos de estado
wss://<su-host>/twilio/media    → WebSocket: audio bidireccional
```

Ambas las gestiona `src/telephony_server.py`. `/healthz` se usa solo como prueba HTTPS. Una prueba correcta de
`/healthz` **no demuestra que Twilio conecte el WebSocket** ni que valide la firma del webhook; eso requiere una llamada
autorizada.

## 6. Cuándo habilitar la funcionalidad

Una vez que Twilio permita llamar al destino, el túnel esté activo, las APIs funcionen, los costos estén controlados y
el horario sea válido, cambie **en su máquina local**:

```dotenv
TWILIO_CALLS_ENABLED=true
```

Recree los contenedores: `docker compose up -d --force-recreate`. La llamada **no empieza automáticamente**: requiere
que el operador pulse manualmente «Iniciar UNA llamada real» en Gradio y confirme ambas casillas.

Siga el [procedimiento de primera llamada](first-call.md). Para volver a deshabilitar, cambie a `false` y recree
contenedores. Si sospecha que una llamada sigue activa, verifique/cuelgue también en Twilio Console; cambiar el flag no
garantiza finalizar llamadas que ya comenzaron.

## 7. Límites del código que NO sustituyen las obligaciones legales

- Una llamada simultánea; hasta **3 solicitudes por día**; duración máxima de **180 s**.
- DNC y lista permitida locales; no equivalen a consulta de un registro normativo nacional.
- Validación de horario de **lunes a viernes 09:00–17:59 (America/Santo_Domingo)**.
- No existe marcador masivo, campañas CSV, reintentos automáticos ni transferencias a operadores reales.
- No hay mecanismos para probar consentimiento más allá de la confirmación manual del operador y la lista de teléfonos
  de prueba. Se debe conservar un comprobante de consentimiento **fuera del repositorio público**.
- Para cualquier campaña comercial, busque asesoría sobre normas de telecomunicaciones y privacidad aplicables en RD y
  las políticas de Twilio.

## Fuentes de Twilio

- [Crear llamadas con la API de Twilio](https://www.twilio.com/docs/voice/api/call-resource)
- [Permisos geográficos de llamadas de voz](https://help.twilio.com/articles/223180228-International-Voice-Dialing-Geographic-Permissions-and-How-They-Work)
- [Restricciones Trial de Voice](https://www.twilio.com/docs/usage/trials/try-out-voice)
- [Media Streams bidireccionales](https://www.twilio.com/docs/voice/media-streams)
- [Seguridad de webhooks](https://www.twilio.com/docs/usage/webhooks/webhooks-security)
