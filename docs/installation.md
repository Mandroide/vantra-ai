# Instalación y ejecución reproducible

Este proyecto utiliza **Python 3.11 o 3.12**, uv y Docker Compose. Puede desarrollarse con PyCharm en Windows, Linux o
macOS. **Gradio no requiere acceso público** y solo se expone en `127.0.0.1:7860`.

## Preparación de PyCharm y Docker

1. Instale Docker Desktop/Engine con Compose v2 y compruebe `docker compose version`.
2. Abra la carpeta que contiene `compose.yaml` en PyCharm y configure `.env`: copie `.env.example` únicamente si no
   existe ya `.env`.
3. Mantenga inicialmente `VANTRA_MODE=DEMO` y `TWILIO_CALLS_ENABLED=false`.
4. Ejecute `docker compose up -d --build`; compruebe `docker compose ps` y abra `http://127.0.0.1:7860`.
5. Consulte `http://127.0.0.1:8000/healthz` y `http://127.0.0.1:8000/readyz`. El primero indica disponibilidad HTTP; el
   segundo solo confirma presencia básica de variables y nunca certifica las APIs externas.

Los servicios base son `vantra` (Gradio) y `twilio-webhook` (FastAPI). Ambos tienen healthchecks y una base SQLite
persistente en volumen Docker. `docker compose down` **no** borra ese volumen; **no use** `down -v` si necesita
conservar solicitudes y exclusiones DNC.

## Desarrollo local con uv

```bash
uv lock                 # generar y versionar uv.lock si todavía falta
uv sync --group dev
uv run python -m pytest -q
uv run python scripts/run_evaluation.py
uv run python app.py
```

Si ejecuta el receptor telefónico fuera de Docker, use una segunda terminal con
`uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000`. El archivo `uv.lock` **no se incluye en esta
entrega**; generarlo y versionarlo sigue siendo necesario para dependencias totalmente reproducibles.
Consulte [configuration.md](configuration.md).

## Exposición pública para telefonía

**No publique Gradio.** La telefonía real necesita HTTPS y WSS hacia FastAPI, y solo debe habilitarse para pruebas
consentidas. Hay tres modos de acceso público independientes del agente:

| Modo       | Archivos Docker                            | Requisitos                                 |
|------------|--------------------------------------------|--------------------------------------------|
| ngrok      | `compose.yaml` + `compose.ngrok.yaml`      | Authtoken, dominio de desarrollo reservado |
| Cloudflare | `compose.yaml` + `compose.cloudflare.yaml` | Túnel administrado, dominio propio, token  |
| Directo    | `compose.yaml` + `compose.direct.yaml`     | DNS público, puertos 80/443, Caddy         |

Configure `.env`, ejecute `python scripts/connectivity.py check`, luego `python scripts/connectivity.py up`. Las
comprobaciones son **offline**, salvo `probe` que verifica el acceso externo. Para cambiar proveedor, detenga primero el
modo anterior; instrucciones completas en [telephony.md](telephony.md).

## Git en Windows, macOS y Linux

El repositorio incorpora [`.gitattributes`](../.gitattributes) para que los archivos de código, configuración y
documentación se almacenen con finales de línea LF, adecuados para Docker y los hooks de pre-commit. Los scripts nativos
de Windows usan CRLF; los audios y demás archivos binarios no se normalizan. Este archivo no contiene claves ni modifica
`.env`.

En un clon existente, tras introducir estos atributos, el equipo puede ejecutar `git add --renormalize .` y revisar
`git diff --cached --check` antes de confirmar la normalización. No suba secretos ni grabaciones privadas; Git LFS queda
fuera del MVP hasta que haya una necesidad justificada.

## Pruebas y calidad

```bash
uv run python -m pytest -q
uv run ruff check .
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
python scripts/connectivity.py check --provider ngrok
```

La última orden exige valores de ejemplo o credenciales locales configuradas y solo comprueba la estructura, **no**
solicita una llamada. GitHub Actions ejecuta pruebas con mocks y evaluación DEMO sin secretos de proveedores. Ningún
pipeline inicia llamadas reales.

## Actualización del repositorio y conciliación telefónica

Después de actualizar el código desde el ZIP, **conserve su `.env` y el volumen de SQLite**. Desde PyCharm:

```powershell
# Si usa ngrok/cloudflare/direct, continúe utilizando el perfil de su despliegue:
python scripts/connectivity.py up
# Revisa reservas locales sin consultar la API:
docker compose exec vantra python -m scripts.reconcile_calls
# Consulta Twilio y sincroniza solamente estados terminales comprobados:
docker compose exec vantra python -m scripts.reconcile_calls --check
```

Si ya estaban iniciados los contenedores con una versión anterior, reconstruya antes con
`docker compose up -d --build --force-recreate` usando los archivos Compose correspondientes a su proveedor. El modo
LIVE necesita credenciales Twilio válidas para `--check`, **pero no crea llamadas**. Si el registro no tiene Call SID o
Twilio no responde, conserva el bloqueo. Consulte [telephony.md](telephony.md) para el procedimiento seguro.

## Parada y diagnóstico

```bash
docker compose ps
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
docker compose down
```

Si levantó el sistema con overlay, deténgalo con `python scripts/connectivity.py down`, seleccionando el proveedor
configurado. Conservar `.env` fuera del repositorio y no copiar salidas de `docker compose config` (puede incluir
variables sensibles).
