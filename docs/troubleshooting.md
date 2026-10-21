# Diagnóstico y resolución de problemas

**Regla general:** no publique capturas, trazas ni logs que muestren API keys, teléfonos reales, firmas Twilio o
información identificable de los probadores.

## Comandos de observación (Docker)

Desde PyCharm → Terminal en `vantra-ai`:

```powershell
docker compose ps
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Si cambió solo `.env`, ejecute `docker compose up -d --force-recreate`. Si cambió código/Dockerfile,
`docker compose up -d --build`. Para ver el estado de la llamada, revise también el panel de Twilio y no únicamente
Gradio.

## Errores habituales

| Síntoma                                           | Comprobación                                                                                                                                         | Acción recomendada                                                                                               |
|---------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `docker` no encontrado                            | Docker Desktop y terminal/Path                                                                                                                       | Instalar y reiniciar terminal.                                                                                   |
| `docker info` no conecta                          | Docker Desktop / WSL2                                                                                                                                | Iniciar motor Linux; esperar estado Ready.                                                                       |
| Puerto 7860/8000 ocupado                          | Servicios locales previos                                                                                                                            | Cerrar proceso en conflicto o ajustar `VANTRA_PORT`/`TWILIO_WEBHOOK_PORT` **concordando ngrok**.                 |
| Build Docker falla instalando Python              | Conectividad y versiones PyPI; `uv.lock` ausente                                                                                                     | Reintentar con conexión; generar y versionar `uv.lock`; revisar logs del build.                                  |
| `ModuleNotFoundError` desde PyCharm               | Ejecución en host en lugar del contenedor                                                                                                            | Para Compose use `docker compose up`; si usa uv, `uv sync --group dev`.                                          |
| Gradio muestra `DEMO` después de cambiar a `LIVE` | `compose.yaml` pasa variables al crear contenedores                                                                                                  | Confirmar `.env` y recrear; refrescar página.                                                                    |
| Claude no aparece en una respuesta                | Consultas del catálogo las resuelve Python                                                                                                           | Probar consulta abierta y revisar credenciales/modelo/cuotas; no asumir que todo texto invoca LLM.               |
| Deepgram no transcribe desde Gradio               | Modo LIVE, audio, casilla de autorización, credenciales, formato                                                                                     | Revisar logs y límites; probar grabación simple.                                                                 |
| Azure devuelve `TTS no disponible`                | `AZURE_SPEECH_KEY`, región de recurso, disponibilidad de voz y cuota                                                                                 | Verificar Azure Portal y voz en modo LIVE; la casilla «Generar audio» debe estar activada.                       |
| `/healthz` local falla                            | Servidor `twilio-webhook`, puerto 8000                                                                                                               | `docker compose logs --tail=100 twilio-webhook`.                                                                 |
| `/healthz` público falla                          | ngrok y puerto destino                                                                                                                               | Mantener `ngrok http 8000` activo; comparar URL; comprobar HTTP HTTPS; no usar 7860.                             |
| `TWILIO_PUBLIC_BASE_URL` inválida                 | Esquema y rutas                                                                                                                                      | Debe ser solo `https://host-publico`, sin `/healthz`, `/twilio/media` ni puerto.                                 |
| Llamada bloqueada por aplicación                  | `TWILIO_CALLS_ENABLED`, `VANTRA_MODE`, allowlist, horario, DNC, máximo 3/día                                                                         | Cumplir controles; no omitir ni falsificar consentimiento.                                                       |
| Twilio rechaza llamada                            | Saldo/trial, Geo Permissions de **Voice**, verificación del destino, origen autorizado; Trial puede restringir `Create a Call` y `<Connect><Stream>` | Revisar logs y límites del plan; no eludir controles, considerar plan compatible.                                |
| Twilio crea llamada, pero corta                   | WebSocket no conecta, firma, URL pública diferente, nonce                                                                                            | Revisar logs de `twilio-webhook`, ngrok y Twilio Debugger/Logs.                                                  |
| Twilio 31920                                      | WSS no logra handshake (101)                                                                                                                         | Verificar `wss://.../twilio/media`, ruta sin query y soporte WebSocket del túnel.                                |
| Firma 403 en `/twilio/status`                     | Base HTTPS usada al firmar no coincide, token cambiado, cabecera ausente                                                                             | Actualizar `.env` con host actual y recrear ambos servicios. No deshabilitar validación.                         |
| Hay conversación, pero sin audio en un sentido    | Azure RAW μ-law / Deepgram streaming / redes                                                                                                         | Revisar trazas de integración, cuotas y compatibilidad a 8 kHz.                                                  |
| Timeout al llamar                                 | Petición incierta; Twilio pudo aceptar llamada                                                                                                       | **NO reintentar hasta consultar la consola Twilio**.                                                             |
| Se bloquean nuevas llamadas indefinidamente       | Estado anterior no terminal / callback perdido                                                                                                       | Verificar situación real en Twilio antes de intervenir el registro; no borrar SQLite/DNC como «solución rápida». |
| El destinatario pide no contactar                 | Lista DNC local                                                                                                                                      | Registrar exclusión y terminar comunicación.                                                                     |

## Comprobar si cambió la URL de ngrok

Si reinició ngrok, su dominio público podría haber cambiado. `TWILIO_PUBLIC_BASE_URL` debe coincidir **exactamente** con
el origen activo. El servidor FastAPI usa esa URL para verificar firmas; dejar una URL anterior puede producir errores
incluso si `/healthz` local responde.

## Sobre las diferencias entre Gradio y llamada telefónica

Gradio procesa audio **por archivo** cuando el usuario pulsa un botón. La telefonía usa **streaming WebSocket** continuo
y audio μ-law mono 8 kHz, además de llamadas a Azure y Deepgram. Que Gradio genere audio correctamente **no prueba** el
circuito telefónico, aunque sí ayuda a aislar credenciales y problemas de servicio.

## Cómo recopilar un reporte de fallo útil

Anote **sin secretos**: sistema operativo; versión Docker/Compose; paso donde falló; modo DEMO/LIVE; hora aproximada;
código de error del proveedor; servicio y endpoint involucrado; resultado de `/healthz`; captura anonimizada o resumen
del log. Si se trata de una llamada, confirme si Twilio llegó a crear un `CallSid` (no publique IDs sensibles
innecesariamente).

Referencias: [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams), [error 31920](https://www.twilio.com/docs/api/errors/31920), [Docker Compose](https://docs.docker.com/compose/), [ngrok](https://ngrok.com/docs/).
