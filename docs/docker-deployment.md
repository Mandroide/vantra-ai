# Ejecución con Docker Compose

Esta guía corresponde a [`../compose.yaml`](../compose.yaml), con **dos servicios** en una sola computadora. La
aplicación no necesita un contenedor LocalStack para llamar a Twilio o a las APIs de voz.

## 1. Verificar el entorno

Desde la carpeta del repositorio (en PyCharm → Terminal):

```powershell
docker --version
docker compose version
docker info
```

Requiere Docker Desktop iniciado con motor Linux. Confirme que hay Internet durante el primer build y que los puertos
`7860` y `8000` del equipo no están ocupados.

## 2. Configuración y arranque

```powershell
Copy-Item .env.example .env
# Abra .env en PyCharm; mantenga DEMO y llamadas desactivadas.
docker compose config --services
docker compose up -d --build
docker compose ps
```

Si ya existe `.env`, **no sobrescriba sus claves** con `Copy-Item`. La instrucción de copia corresponde a una
instalación inicial.

| Servicio Compose | Contenido                    | URL local                       |
|------------------|------------------------------|---------------------------------|
| `vantra`         | Gradio + agente              | <http://127.0.0.1:7860>         |
| `twilio-webhook` | FastAPI / WebSocket / Twilio | <http://127.0.0.1:8000/healthz> |

`/healthz` devuelve `ok` y un booleano `telephony_enabled`; **no** hace llamadas ni acredita funcionamiento de las APIs.
Los puertos están enlazados en `127.0.0.1` para no exponerlos en la red local por defecto.

## 3. Logs y comprobaciones

```powershell
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
docker compose ps
```

Para seguir logs del servidor de voz: `docker compose logs -f twilio-webhook` (Ctrl+C detiene la vista, **no los
contenedores**). No publique logs que contengan información de usuarios ni identificadores de llamada.

Prueba de salud desde PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Para aislar fallos, compruebe primero DEMO en Gradio y después LIVE por texto/audio.
Consulte [diagnóstico](troubleshooting.md).

## 4. Actualizar configuración o código

Si cambió **solo `.env`**, fuerce recreación para inyectar valores nuevos:

```powershell
docker compose up -d --force-recreate
```

Si cambió **código, dependencias o Dockerfile**:

```powershell
docker compose up -d --build
```

Nota: `uv.lock` todavía no estaba incorporado al paquete fuente original. Genérelo en un entorno conectado a PyPI
(`uv lock`) y agréguelo al repositorio; tras ello Docker lo respeta al construir. Antes de disponer del lock, el build
resuelve dependencias en línea y **no es completamente reproducible**.

## 5. Estado SQLite persistente

Ambos servicios montan `vantra_state` en `/state` y establecen `VANTRA_DB_PATH=/state/vantra.sqlite3`. Así comparten los
estados de llamada, bloqueos DNC y límites del piloto. Si cambia el nombre de proyecto Compose o elimina el volumen,
podrá perder las exclusiones guardadas.

- Detener **conservando** el volumen: `docker compose down`.
- Eliminar también el volumen: `docker compose down -v` (**destructivo**, no lo ejecute durante un piloto).
- Ver estado: `docker compose ps`.
- El código no conserva audios deliberadamente en SQLite; revise el tratamiento de cachés y proveedores antes de usar
  personas reales.

## 6. Conectar ngrok desde Windows, fuera de Docker

Abra **otra terminal del host** y ejecute `ngrok http 8000`. No es necesario agregar ngrok a Compose: el túnel expone la
conexión a `127.0.0.1:8000` que Docker publica en el host.

Copie solo la base HTTPS pública a `.env` (`TWILIO_PUBLIC_BASE_URL=https://...`) y recree los dos servicios. **Nunca**
exponga el puerto 7860 con ngrok; ese panel controla llamadas reales y no dispone de autenticación apta para Internet.

Procedimiento completo: [ngrok](ngrok-setup.md) → [primera llamada](first-call.md).

## 7. Límites del despliegue

Este Compose corresponde a **desarrollo/piloto local**, no a un entorno productivo ni multiinstancia. No hay
balanceador, centralita, autenticación de operadores ni base de datos distribuida. Las credenciales se suministran por
variables de entorno a los contenedores y un operador con privilegios sobre Docker podría inspeccionarlas. Para
producción se necesitarían controles adicionales, secretos administrados, autenticación, monitoreo, privacidad y
revisión legal.

Referencia: [Docker Compose `up`](https://docs.docker.com/reference/cli/docker/compose/up/).
