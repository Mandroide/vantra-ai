# Instalación inicial — PyCharm + Docker Desktop

## 0. Objetivo y requisitos

Para comenzar **no necesita Twilio ni APIs**: primero validaremos que el proyecto levanta en modo `DEMO`. En la segunda
etapa usaremos proveedores externos y, solo cuando esté preparado, telefonía real.

- Equipo Windows 11 con PyCharm (también sirve Linux/macOS, adaptando comandos).
- Docker Desktop iniciado con motor Linux y Docker Compose v2. En Windows, revise WSL 2 si Docker lo solicita.
- Internet para descargar imágenes y dependencias en el primer build.
- Archivo `compose.yaml` y `.env.example` en la **raíz del repositorio**.
- Una cuenta de ngrok y Twilio **solo** para llamadas reales.

**PyCharm es el editor; Docker es el ejecutor.** No necesita configurar el intérprete local de PyCharm para ejecutar la
aplicación mediante Compose, aunque puede hacerlo para depuración con uv.

## 1. Abrir el proyecto en PyCharm

1. Extraiga el ZIP del repositorio; abra la carpeta `vantra-ai` (la que contiene `app.py` y `compose.yaml`), no su
   carpeta padre.
2. En PyCharm, abra la pestaña **Terminal** y compruebe que está en esa carpeta (`pwd` en PowerShell o `Get-Location`;
   `ls` o `dir` para ver `compose.yaml`).
3. Compruebe Docker:

```powershell
docker --version
docker compose version
docker info
```

Si `docker info` no logra conectarse, abra Docker Desktop y espere a que el motor arranque. No continúe hasta obtener
una respuesta normal.

## 2. Crear `.env` sin secretos para DEMO

En **PowerShell** (terminal de PyCharm):

```powershell
Copy-Item .env.example .env
```

En Bash: `cp .env.example .env`. Abra `.env` y deje al menos:

```dotenv
VANTRA_MODE=DEMO
TWILIO_CALLS_ENABLED=false
TWILIO_PUBLIC_BASE_URL=
```

No agregue claves durante la prueba DEMO. El archivo `.env` está ignorado por Git.
Consulte [configuración](configuration.md) para completar las claves cuando corresponda.

## 3. Construir y ejecutar los dos servicios

```powershell
docker compose config --services
docker compose up -d --build
docker compose ps
```

`docker compose config --services` debe enumerar `vantra` y `twilio-webhook`. El build inicial requiere descarga de
imágenes, por lo que puede tardar varios minutos.

Abra en **su propia computadora**:

- Interfaz Gradio: <http://127.0.0.1:7860>
- Estado del servidor telefónico: <http://127.0.0.1:8000/healthz>

Una respuesta típica de `/healthz` es `{"ok":true,"telephony_enabled":false}`. Es un indicador de que FastAPI contesta,
**no prueba WebSocket ni llamadas**.

En la pestaña «Atención entrante», escriba «¿Qué tasa tiene el préstamo personal?» y compruebe que obtiene una respuesta
basada en el catálogo ficticio. La pestaña «Campaña saliente: simulación» **no llama** a nadie; es la prueba segura
inicial.

## 4. Si falla el arranque

```powershell
docker compose ps
docker compose logs --tail=80 vantra
docker compose logs --tail=80 twilio-webhook
```

Revise las causas más comunes en [solución de problemas](troubleshooting.md). Para detener sin borrar el volumen SQLite:

```powershell
docker compose down
```

**No utilice `docker compose down -v` en un entorno donde necesite conservar los registros**, porque elimina el volumen
del proyecto, incluidos estados de llamadas y exclusiones locales.

## 5. Siguiente etapa: habilitar LIVE sin llamar

1. Complete Anthropic, Deepgram y Azure en `.env` según [configuración](configuration.md).
2. Cambie `VANTRA_MODE=LIVE` y **mantenga** `TWILIO_CALLS_ENABLED=false`.
3. Aplique los cambios:

```powershell
docker compose up -d --force-recreate
docker compose logs --tail=40 vantra
```

4. Compruebe las funciones de texto, audio de entrada (Deepgram) y voz de salida (Azure) **una a una**, con datos y
   audio de prueba autorizados. El componente de texto puede responder mediante reglas sin llamar a Claude.
5. Solo después continúe con [Twilio](twilio-setup.md), [ngrok](ngrok-setup.md) y [primera llamada](first-call.md).

## Alternativa: desarrollo directo con uv (sin Docker)

Para desarrollo local desde PyCharm:

```powershell
uv lock
uv sync --group dev
uv run python -m pytest -q
uv run python app.py
```

En otra terminal:

```powershell
uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000
```

Si falta `uv.lock`, `uv lock` lo genera resolviendo dependencias online; añádalo a Git y después use
`uv sync --locked --group dev`. Docker no ejecuta Pytest durante el arranque normal: las pruebas se ejecutan con uv o
desde GitHub Actions. Consulte [DevOps](devops.md).
