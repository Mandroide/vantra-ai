# Instalación, ejecución y flujo de desarrollo

Esta guía parte de la raíz del repositorio y funciona desde la terminal integrada de **PyCharm** o una terminal normal.
La vía recomendada para la demostración es **Docker Compose**; uv permite desarrollo y depuración directos.

## Requisitos

- Docker Desktop (Windows/macOS) o Docker Engine + Compose v2 (Linux). En Windows, motor de contenedores Linux
  habilitado.
- Acceso a Internet para obtener imágenes y dependencias.
- Opcional: Python 3.11/3.12 y [uv](https://docs.astral.sh/uv/) para desarrollo nativo.
- Claves de APIs y un túnel HTTPS **solo** para LIVE/telefonía, no para DEMO.

Verifique:

```bash
docker --version
docker compose version
docker info
```

## Ejecución inicial: DEMO

1. Abra la carpeta que contiene `compose.yaml` en PyCharm.
2. Cree `.env` a partir de `.env.example` (`Copy-Item .env.example .env` en PowerShell o `cp .env.example .env` en
   bash). Si el archivo existe, consérvelo.
3. Compruebe `VANTRA_MODE=DEMO` y `TWILIO_CALLS_ENABLED=false`.
4. Ejecute:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=80 vantra
docker compose logs --tail=80 twilio-webhook
```

5. Abra <http://127.0.0.1:7860> y consulte: «¿Qué requisitos tiene la tarjeta?» y «Cotiza 300000 pesos a 36 meses».
6. Verifique <http://127.0.0.1:8000/healthz>. Este endpoint no valida proveedores externos.

`compose.yaml` levanta `vantra` (Gradio: 7860) y `twilio-webhook` (FastAPI: 8000); ambos puertos se publican únicamente
en `127.0.0.1`. Comparten el volumen `vantra_state` para SQLite, incluidos estados telefónicos y exclusiones DNC.

## Ciclo cotidiano de desarrollo

```bash
# Ver registros
docker compose logs -f vantra
docker compose logs -f twilio-webhook

# Si cambia .env
docker compose up -d --force-recreate

# Si cambia código o Dockerfile
docker compose up -d --build

# Parar conservando datos
docker compose down
```

Si cambia el puerto local `TWILIO_WEBHOOK_PORT`, actualice también la configuración de ngrok. Evite
`docker compose down -v`: borra el volumen local y puede perder las exclusiones DNC.

## Desarrollo nativo con uv

```bash
uv lock                         # necesario solo mientras falte uv.lock
uv sync --group dev
uv run python -m pytest -q
uv run python app.py
```

Para telefonía, arranque en otra terminal: `uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000`.

**Pendiente de reproducibilidad:** `uv.lock` no está versionado en el paquete actual. Genérelo con acceso a PyPI,
compruebe cambios, agréguelo a Git y cambie a `uv sync --locked --group dev`. Los comandos Docker y CI pueden resolver
dependencias inicialmente, pero esto no equivale a resolución congelada.

## Pruebas y calidad

```bash
uv run python -m pytest -q --cov=src --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run pre-commit install
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
```

Si el formateador identifica diferencias, aplique `uv run ruff format .` y revise los cambios. No confunda cobertura de
código con calidad de voz o precisión del LLM. El workflow `.github/workflows/ci.yml` prueba Python 3.11/3.12,
evaluación DEMO y construcción Docker sin desplegar ni consumir claves de proveedores. `.github/workflows/docker.yml`
permite una ejecución manual adicional; Dependabot gestiona propuestas de actualización. No se usa Jenkins.

## Próximos pasos

Configure los servicios mediante [configuration.md](configuration.md). Para llamadas de prueba autorizadas,
siga [telephony.md](telephony.md) **después** de comprobar DEMO y LIVE por Gradio.
Consulte [troubleshooting.md](troubleshooting.md) si algún servicio falla.
