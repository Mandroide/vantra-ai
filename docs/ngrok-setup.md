# ngrok — cómo obtener `TWILIO_PUBLIC_BASE_URL`

`TWILIO_PUBLIC_BASE_URL` **no aparece en el panel de Twilio**. Debe ser el origen HTTPS público que apunta a **FastAPI,
puerto 8000**, en su computadora. En este piloto utilizaremos ngrok en Windows, **fuera de Docker**.

## 1. Antes de comenzar

1. Tenga `docker compose up -d --build` ejecutándose en PyCharm.
2. Verifique localmente <http://127.0.0.1:8000/healthz>.
3. Mantenga Gradio en <http://127.0.0.1:7860> **sin túnel público**.

Si la URL local `/healthz` no responde, **no abra ngrok todavía**: revise [Docker](docker-deployment.md)
y [diagnóstico](troubleshooting.md).

## 2. Instalar y conectar ngrok

Descargue el agente para Windows desde [ngrok](https://ngrok.com/download) y regístrese
en [ngrok Dashboard](https://dashboard.ngrok.com/). En una terminal PowerShell compruebe `ngrok version`. Si no reconoce
el comando, verifique el PATH o ejecute `ngrok.exe` desde la carpeta donde se instaló.

En el dashboard, copie su **authtoken** sin publicarlo y ejecute una vez:

```powershell
ngrok config add-authtoken SU_AUTHTOKEN_PERSONAL
```

La ubicación y cuotas de dominios gratuitos pueden variar según el plan. No es necesario contratar un servidor ni
registrar un dominio para realizar la prueba local si su cuenta dispone de endpoint público.

## 3. Exponer exclusivamente FastAPI

En **una tercera terminal** (deje Docker activo):

```powershell
ngrok http 8000
```

Podría aparecer, por ejemplo:

```text
Forwarding  https://ejemplo-vantra.ngrok-free.app -> http://localhost:8000
```

La **dirección de ejemplo no es una URL real de su proyecto**. Copie el origen que ngrok muestre en su máquina,
**incluyendo `https://`**, sin rutas ni puerto:

```dotenv
TWILIO_PUBLIC_BASE_URL=https://SU_DOMINIO_REAL.ngrok-free.app
```

No ponga `http://localhost:8000` ni `https://.../healthz`; Twilio debe llegar desde Internet. El código transforma
`https://` en `wss://` para Media Streams.

## 4. Comprobar desde el navegador

Abra con el navegador **su URL real** terminada en `/healthz`:

```text
https://SU_DOMINIO_REAL.ngrok-free.app/healthz
```

Respuesta esperada cuando todavía está deshabilitada la telefonía:

```json
{"ok": true, "telephony_enabled": false}
```

Puede que el túnel gratuito muestre una página informativa/intersticial en navegación humana según el plan; compruebe si
la ruta devuelve realmente el JSON esperado. En este punto **todavía no** se ha comprobado el WebSocket de Twilio ni la
validación de firmas.

## 5. Guardar la base pública y reiniciar

En `.env`, establezca `TWILIO_PUBLIC_BASE_URL` con su origen HTTPS recién obtenido, manteniendo
`TWILIO_CALLS_ENABLED=false`:

```powershell
docker compose up -d --force-recreate
```

Ambos contenedores deben tener la misma URL actual porque `vantra` la utiliza al construir el TwiML de la llamada y
`twilio-webhook` al validar firmas y los parámetros de sesión.

## 6. Relación entre HTTP y WebSocket

El código construye internamente estas rutas:

| Uso                           | Dirección que construye Vantra AI  |
|-------------------------------|------------------------------------|
| Verificar accesibilidad HTTPS | `https://SU_DOMINIO/healthz`       |
| Notificación de estado Twilio | `https://SU_DOMINIO/twilio/status` |
| Audio bidireccional (TLS)     | `wss://SU_DOMINIO/twilio/media`    |

**No configure manualmente estas rutas** en Twilio Console para el caso saliente implementado: el código las envía por
llamada. Twilio Media Streams utiliza WebSocket seguro (`wss://`), no `ws://`.

## 7. Persistencia de URL y seguridad

- Mantenga ngrok ejecutándose **todo el tiempo** que dure la llamada; si cierra la terminal, el túnel podría terminar.
- Si ngrok asigna **otro dominio** al reiniciarse, cambie `.env`, recree los contenedores y repita `/healthz`. Nunca
  suponga que su URL anterior sigue activa.
- El túnel habilita acceso público a `/healthz` y a los endpoints de FastAPI; éstos requieren controles de firma donde
  corresponde. No significa que el prototipo esté auditado para producción.
- El inspector local de ngrok podría mostrar metadatos y contenido de solicitudes. No comparta capturas con secretos,
  destinatarios ni payloads telefónicos.
- **No ejecute `ngrok http 7860`** para este piloto: Gradio no dispone de autenticación apropiada para habilitar
  llamadas públicamente.

Después de confirmar el túnel: [Twilio](twilio-setup.md) → [Primera llamada](first-call.md).

Fuentes: [ngrok HTTP endpoints](https://ngrok.com/docs/universal-gateway/http/), [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams), [errores de handshake WSS](https://www.twilio.com/docs/api/errors/31920).
