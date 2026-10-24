# Vantra AI

**Agente conversacional de voz para un banco ficticio · MVP académico**  
Universidad Autónoma de Santo Domingo (UASD) · Maestría en Ciencia de Datos e Inteligencia Artificial · Capstone
Projects, Fase 2.

Vantra AI permite consultar productos bancarios ficticios, calcular cuotas con funciones deterministas, registrar
prospectos de prueba y simular derivaciones. Ofrece una interfaz web con Gradio y adaptadores para reconocimiento de
voz, modelo de lenguaje y síntesis de audio. Incluye un **piloto restringido de llamadas salientes a números dominicanos
previamente autorizados** con Twilio.

> **Estado de validación:** las pruebas de lógica y escenarios sintéticos se pueden ejecutar sin credenciales. La
> integración completa con Deepgram, Claude, Azure Speech y Twilio **requiere una validación de extremo a extremo con
cuentas reales**. No hay conexiones con bancos reales, transferencias humanas operativas ni autorización para utilizarlo
> comercialmente.

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
4. Inicie ngrok hacia **FastAPI, puerto 8000** (`ngrok http 8000`) y copie la base `https://…` en
   `TWILIO_PUBLIC_BASE_URL`. Mantenga **`TWILIO_CALLS_ENABLED=false`** hasta completar las verificaciones.
5. Una vez validado el acceso público y los permisos del proveedor, active las llamadas únicamente a contactos
   autorizados y en un entorno local protegido.

```bash
docker compose up -d --force-recreate
```

Las llamadas aceptan `+1809`, `+1829` o `+1849` seguidos de siete dígitos; no existe marcación masiva. Si necesita
realizar una prueba **manual previamente consentida** fuera del horario técnico predeterminado, consulte
`TWILIO_ALLOW_AFTER_HOURS_TEST_CALLS` en la guía de telefonía.

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
src/telephony.py         Políticas y llamadas REST Twilio
src/telephony_server.py  Webhooks, WebSocket y audio telefónico
src/tools.py             Herramientas y cálculos financieros sintéticos
src/storage.py           Persistencia SQLite
compose.yaml             Dos servicios: vantra y twilio-webhook
data/                    Catálogo y casos ficticios
tests/, scripts/          Pruebas y evaluación automatizada
results/                 Evidencias deterministas de DEMO
docs/                    Documentación técnica y académica del MVP
```

## Documentación

| Guía                                               | Contenido                                               |
|----------------------------------------------------|---------------------------------------------------------|
| [Instalación](docs/installation.md)                | PyCharm, Docker, uv, pruebas y CI.                      |
| [Configuración](docs/configuration.md)             | Variables `.env`, proveedores y credenciales.           |
| [Arquitectura](docs/architecture.md)               | Componentes, flujos y límites técnicos.                 |
| [Telefonía](docs/telephony.md)                     | Twilio, ngrok, primera llamada y controles dominicanos. |
| [Evaluación](docs/evaluation.md)                   | Escenarios, métricas, subgrupos y evidencias.           |
| [Ética](docs/ethics.md)                            | Riesgos, medidas y limitaciones.                        |
| [Resolución de problemas](docs/troubleshooting.md) | Diagnóstico Docker, proveedores y errores Twilio.       |

## Seguridad y alcance

Utilice **solo datos y números de prueba autorizados**. El panel Gradio no cuenta con autenticación robusta para
publicarlo como servicio público. Evite grabaciones, datos financieros reales y secretos en el repositorio, capturas o
registros. La voz telefónica se procesa con terceros; confirme sus términos y requisitos legales antes de cualquier uso
más allá de pruebas consentidas.

**Entregables académicos:** el informe PDF, Canvas, reflexión extensa y evidencias finales se mantienen **fuera del
repositorio de software**, en la carpeta de entrega de la asignatura. Las funciones codificadas no se consideran pruebas
de aceptación de APIs reales.
