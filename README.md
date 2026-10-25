# Vantra AI

**Agente conversacional de voz para un banco ficticio · MVP académico**  
Universidad Autónoma de Santo Domingo (UASD) · Maestría en Ciencia de Datos e Inteligencia Artificial · Capstone
Projects, Fase 2.

Vantra AI permite consultar productos bancarios ficticios, calcular cuotas con funciones deterministas, registrar
prospectos de prueba y simular derivaciones. Ofrece una interfaz web con Gradio y adaptadores para reconocimiento de
voz, modelo de lenguaje y síntesis de audio. Incluye un **piloto restringido de llamadas salientes a números dominicanos
previamente autorizados** con Twilio.

> **Estado de validación:** las pruebas de lógica y escenarios sintéticos se pueden ejecutar sin credenciales. El equipo
> ha aportado evidencia de una conversación telefónica piloto; esa evidencia no equivale a una validación sistemática de
> seguridad, latencia, costos ni desempeño de proveedores LIVE. No hay conexiones con bancos reales, transferencias
> humanas operativas ni autorización para utilizarlo comercialmente.

## Funciones

| Componente          | Comportamiento                                                                                                                       |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| DEMO                | Chat por texto y operaciones con datos sintéticos sin APIs externas.                                                                 |
| LIVE                | Conectores de Deepgram (STT), Anthropic Claude (LLM, cuando la consulta lo requiere) y Azure Speech (TTS). Requiere cuentas válidas. |
| Telefonía           | Llamada saliente **manual** mediante Twilio REST y procesamiento de audio en WebSocket. Deshabilitada de forma predeterminada.       |
| Seguridad de piloto | Lista de destinatarios permitidos, consentimiento declarado, lista DNC, horario configurable y límites de volumen.                   |
| Evaluación          | Pytest y 12 escenarios × 3 variantes de texto = 36 verificaciones offline.                                                           |
| Ingeniería          | uv, Docker Compose, Ruff, pre-commit y GitHub Actions.                                                                               |

## Inicio rápido con Docker

**Requisitos:** Docker Desktop/Engine con Compose v2, acceso a Internet para construir la imagen y terminal abierta en
la raíz del repositorio (`compose.yaml`). PyCharm es opcional.

```powershell
# Windows PowerShell
Copy-Item .env.example .env
# Dejar VANTRA_MODE=DEMO y TWILIO_CALLS_ENABLED=false
docker compose up -d --build
docker compose ps
```

En Linux/macOS use `cp .env.example .env`. **Si `.env` ya existe, no lo sobrescriba.**

- Interfaz: <http://127.0.0.1:7860>
- Salud del servidor de telefonía: <http://127.0.0.1:8000/healthz>

Pruebe en Gradio: **«Cotiza 300000 pesos a 36 meses»**. Compruebe los registros:

```bash
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook
```

`/healthz` comprueba la accesibilidad de FastAPI; **no certifica una llamada ni los servicios externos**. Para detener
sin borrar el volumen SQLite: `docker compose down` (evitar `down -v` si necesita mantener la lista DNC).

## Desarrollo local con uv

Compatible con Python **3.11 y 3.12**, según `pyproject.toml`:

```bash
uv lock                     # si aún falta uv.lock
uv sync --group dev
uv run python -m pytest -q
uv run python scripts/run_evaluation.py
uv run python app.py
```

Para levantar además el receptor Twilio, en otra terminal:

```bash
uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000
```

**Reproducibilidad:** `uv.lock` aún no está incluido. Generarlo con acceso a PyPI, versionarlo y luego ejecutar
`uv sync --locked --group dev`. La imagen admite un primer build sin lock, pero no puede garantizar exactamente las
mismas versiones hasta que se versione.

## Configuración de APIs y llamadas

1. Copie `.env.example` como `.env`, complete claves y región real del servicio Azure. No publique el archivo.
2. Cambie a `VANTRA_MODE=LIVE`, recree los servicios y pruebe primero Deepgram, Claude y Azure **desde Gradio**.
3. Para telefonía, configure Twilio Voice, origen autorizado, permisos geográficos para República Dominicana y lista de
   teléfonos de prueba con consentimiento documentado.
4. Configure un método de conectividad **ngrok en Docker**, **Cloudflare Tunnel** o **Caddy con HTTPS directo**; escriba
   la URL base HTTPS en `TWILIO_PUBLIC_BASE_URL`. No publique el puerto de Gradio.
5. Ejecute `python scripts/connectivity.py check`, `python scripts/connectivity.py up` y, cuando el dominio esté
   disponible, `python scripts/connectivity.py probe` para comprobar HTTPS y el rechazo del WebSocket sin firma.
6. Mantenga **`TWILIO_CALLS_ENABLED=false`** hasta confirmar el consentimiento, la accesibilidad pública y los permisos
   del proveedor. Solo entonces habilite una llamada manual a un número autorizado.

```bash
docker compose up -d --force-recreate
```

Las llamadas aceptan `+1809`, `+1829` o `+1849` seguidos de siete dígitos; no existe marcación masiva.
`TWILIO_DAILY_CALL_LIMIT` admite entre 1 y 10 intentos diarios (predeterminado 3). **Antes de bloquear por
simultaneidad**, el programa consulta en Twilio cualquier llamada local activa con SID y libera el cupo únicamente ante
un estado terminal confirmado. Si Twilio no responde o aún no existe SID, mantiene el bloqueo. El botón **Consultar
estado** también sincroniza con Twilio. Para revisar registros de cualquier sesión sin iniciar llamadas:
`docker compose exec vantra python -m scripts.reconcile_calls --check`. Consulte [telefonía](docs/telephony.md)
y [diagnóstico](docs/troubleshooting.md). Si necesita realizar una prueba **manual previamente consentida** fuera del
horario técnico predeterminado, consulte `TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS` en la guía de telefonía.

## Git y finales de línea

El archivo [`.gitattributes`](.gitattributes) normaliza el texto a **LF** para Python, Docker, YAML, documentación y los
datos de prueba, independientemente de usar Windows/PyCharm, macOS o Linux. Los scripts nativos de Windows (`.bat`,
`.cmd`, `.ps1`) se entregan con **CRLF** y los audios, imágenes, documentos y bases SQLite se tratan como **binarios**.
Git no cambia la codificación de los archivos: guarde el texto en UTF-8.

Si ya había archivos versionados antes de incorporar `.gitattributes`, realice una sola normalización después de revisar
los cambios: `git add --renormalize .` y `git diff --cached --check`. No agregamos Git LFS por defecto: exigiría
instalarlo y configurarlo en cada equipo; si se incorporan grabaciones grandes, evalúen LFS antes de subirlas.

## Validación y calidad

```bash
uv run python -m pytest -q --cov=src --cov=app --cov-report=term-missing
uv run ruff check .
uv run pre-commit install
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
```

Los archivos de `results/` contienen **resultados de DEMO sintético**, no mediciones de precisión acústica, naturalidad,
latencia o facturación LIVE. Las pruebas LIVE requieren voluntarios, consentimiento, evaluación humana y registro de
consumo del proveedor.

## Estructura

```text
app.py                   Interfaz Gradio (texto, voz y telefonía restringida)
src/agent.py             Agente y reglas de negocio
src/speech.py            STT Deepgram por archivo y TTS Azure
src/telephony.py         Políticas, llamadas y reconciliación de estados REST Twilio
src/telephony_server.py  Webhooks, WebSocket y audio telefónico
src/tools.py             Herramientas y cálculos financieros sintéticos
src/storage.py           Persistencia SQLite
compose.yaml             Servicios base: vantra y twilio-webhook
compose.*.yaml           Modos de conectividad: ngrok, cloudflare, direct
infra/Caddyfile           Proxy público con TLS automático (direct)
scripts/connectivity.py  Comprobar, arrancar, detener y probar acceso público
data/                    Catálogo y casos ficticios
tests/, scripts/          Pruebas y evaluación automatizada
results/                 Evidencias deterministas de DEMO
docs/                    Documentación técnica y académica del MVP
```

## Documentación

| Guía                                               | Contenido                                                                               |
|----------------------------------------------------|-----------------------------------------------------------------------------------------|
| [Instalación](docs/installation.md)                | PyCharm, Docker, uv, pruebas y CI.                                                      |
| [Configuración](docs/configuration.md)             | Variables `.env`, proveedores y credenciales.                                           |
| [Arquitectura](docs/architecture.md)               | Componentes, flujos y límites técnicos.                                                 |
| [Telefonía](docs/telephony.md)                     | Twilio, ngrok/Cloudflare/Caddy, HTTPS/WSS, cambio de proveedor y controles dominicanos. |
| [Evaluación](docs/evaluation.md)                   | Escenarios, métricas, subgrupos y evidencias.                                           |
| [Ética](docs/ethics.md)                            | Riesgos, medidas y limitaciones.                                                        |
| [Resolución de problemas](docs/troubleshooting.md) | Diagnóstico Docker, proveedores y errores Twilio.                                       |

## Seguridad y alcance

Utilice **solo datos y números de prueba autorizados**. El panel Gradio no cuenta con autenticación robusta para
publicarlo como servicio público. Evite grabaciones, datos financieros reales y secretos en el repositorio, capturas o
registros. La voz telefónica se procesa con terceros; confirme sus términos y requisitos legales antes de cualquier uso
más allá de pruebas consentidas.

**Entregables académicos:** el informe PDF, Canvas, reflexión extensa y evidencias finales se mantienen **fuera del
repositorio de software**, en la carpeta de entrega de la asignatura. Las funciones codificadas no se consideran pruebas
de aceptación de APIs reales.
