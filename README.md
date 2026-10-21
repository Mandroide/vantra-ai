# Vantra AI — Agente de voz bancario (MVP académico)

**UASD · Maestría en Ciencia de Datos e Inteligencia Artificial · Capstone Projects, Fase 2**  
**Caso de uso:** Banco Demo **ficticio**, tarjetas, préstamos y certificados.  
**Estado:** DEMO por texto ejecutable; conectores LIVE y telefonía Twilio codificados, **pendientes de validación real
extremo a extremo**. No es una aplicación bancaria de producción.

> **Manual
completo:** [Instalación y despliegue con PyCharm, Docker, ngrok y Twilio](MANUAL_INSTALACION_Y_DESPLIEGUE.md).  
> **Empiece por
aquí:** [Guía de instalación PyCharm + Docker](docs/getting-started.md) → [Configuración de claves](docs/configuration.md) → [Twilio](docs/twilio-setup.md) → [ngrok](docs/ngrok-setup.md) → [Primera llamada](docs/first-call.md).  
> Todas las guías: **[Índice de documentación](docs/README.md)**.

## 1. Qué hace el proyecto

- **DEMO sin credenciales:** consultas bancarias por texto, catálogo ficticio, cálculo de cuotas, prospectos,
  solicitudes de devolución de llamada, derivación simulada y campaña saliente **simulada**.
- **LIVE (integraciones por validar en vivo):** Deepgram reconoce audio, Anthropic Claude interviene en consultas
  abiertas y Azure Speech genera respuestas de voz. Muchas consultas del catálogo continúan resolviéndose con
  herramientas deterministas.
- **Telefonía real de piloto:** pestaña « **Llamada REAL · piloto restringido**». Código para una llamada saliente
  manual mediante Twilio REST, FastAPI y WebSocket con audio bidireccional. **Desactivada por defecto**, limitada a
  números de RD `+1809`, `+1829` y `+1849` explícitamente permitidos y con consentimiento documentado; no hay campañas
  masivas ni transferencias reales.
- **Evaluación:** pruebas unitarias offline y 36 verificaciones deterministas de escenarios. Los resultados DEMO **no**
  acreditan reconocimiento de voz, naturalidad, costos o latencia de los proveedores.

## 2. Requisitos

- **Opción recomendada en PyCharm:** Docker Desktop con motor Linux + Docker Compose v2.
- **Opción de desarrollo directo:** Python 3.11/3.12 + [uv](https://docs.astral.sh/uv/).
- Acceso a Internet para instalar dependencias. Para LIVE también necesita cuentas y credenciales de proveedores,
  facturación/cuotas y políticas de uso acordes al piloto.

## 3. Inicio rápido en Docker (sin llamadas ni claves)

Desde la **carpeta que contiene `compose.yaml`**, en la terminal de PyCharm/PowerShell:

```powershell
Copy-Item .env.example .env
# Mantenga VANTRA_MODE=DEMO y TWILIO_CALLS_ENABLED=false
docker compose up -d --build
docker compose ps
```

Si ya tiene `.env`, no lo sobrescriba. Abra:

- **Gradio:** <http://127.0.0.1:7860>
- **FastAPI (salud):** <http://127.0.0.1:8000/healthz>

Pruebe «Cotiza 300000 pesos a 36 meses» en Gradio. `healthz` debe responder JSON, pero **no** significa que una llamada
esté funcionando. Para revisar errores:

```powershell
docker compose logs --tail=80 vantra
docker compose logs --tail=80 twilio-webhook
```

Detener conservando el volumen y la lista DNC: `docker compose down`. **No** utilice `docker compose down -v` si
necesita conservar exclusiones o estados.

## 4. Alternativa sin Docker (uv)

```powershell
uv lock                         # una vez, si aún no existe uv.lock
uv sync --group dev
uv run python -m pytest -q
uv run python app.py
```

Para telefonía también debe levantar **otro proceso**:

```powershell
uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000
```

**Reproducibilidad:** en la versión base no se incluyó `uv.lock`. Genérelo con acceso a PyPI, agréguelo a Git y luego
utilice `uv sync --locked --group dev`. Docker/CI no pueden garantizar dependencias idénticas hasta que se versione.
Consulte [DevOps](docs/devops.md).

## 5. Activar LIVE (todavía sin telefonía real)

Cree el recurso Azure Speech; confirme que Deepgram y Anthropic disponen de claves, permisos y saldo/cuota. Complete su
`.env` (no lo publique):

```dotenv
VANTRA_MODE=LIVE
ANTHROPIC_API_KEY=REEMPLAZAR
ANTHROPIC_MODEL=claude-sonnet-5
DEEPGRAM_API_KEY=REEMPLAZAR
DEEPGRAM_MODEL=nova-3
AZURE_SPEECH_KEY=REEMPLAZAR
AZURE_SPEECH_REGION=CODIGO_REAL_DE_REGION
AZURE_SPEECH_VOICE=es-DO-RamonaNeural
TWILIO_CALLS_ENABLED=false
```

Si utiliza Docker, aplique el cambio: `docker compose up -d --force-recreate`. En Gradio pruebe voz entrante aceptando
el consentimiento y seleccione «Generar audio de respuesta» para probar Azure. **La región debe coincidir con la de su
recurso**, y el identificador del modelo debe estar habilitado en su cuenta. Algunos servicios pueden generar cargos.

Guía completa: [variables de entorno y proveedores](docs/configuration.md).

## 6. Telefonía saliente a RD — únicamente piloto consentido

Solo después de verificar el flujo por Gradio, configure Twilio Voice, su caller ID, permisos geográficos de **Voice**
para República Dominicana, destinatario de prueba permitido y un túnel HTTPS/WSS hacia **FastAPI 8000**. **En una cuenta
Twilio Trial actual, el inicio por API y el TwiML con `<Connect><Stream>` pueden no estar permitidos; verifique las
restricciones concretas y considere un plan de pago si la modalidad es incompatible.** El origen HTTPS público mostrado
por ngrok se coloca en `TWILIO_PUBLIC_BASE_URL`; **no se obtiene de Twilio**.

```dotenv
TWILIO_CALLS_ENABLED=false
TWILIO_ACCOUNT_SID=AC_REEMPLAZAR
TWILIO_AUTH_TOKEN=REEMPLAZAR
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
TWILIO_PUBLIC_BASE_URL=https://SU_DOMINIO_REAL.ngrok-free.app
TWILIO_TEST_NUMBERS=+1809XXXXXXX
```

En otra terminal Windows: `ngrok http 8000`. Compruebe `https://SU_DOMINIO_REAL.ngrok-free.app/healthz`, sin exponer
Gradio `7860`. **Solo después de completar todas las comprobaciones** active `TWILIO_CALLS_ENABLED=true`, recree los
contenedores y pulse manualmente «Iniciar UNA llamada real».

**Restricciones del código:** 1 llamada simultánea; máximo de 3 solicitudes por día; duración máxima 180 s; lunes a
viernes 09:00–17:59 hora Santo Domingo; allowlist estricta, consentimiento confirmado y DNC local. No es un sistema de
call center productivo ni garantía de cumplimiento normativo.

Guías
ordenadas: [Twilio](docs/twilio-setup.md) → [ngrok](docs/ngrok-setup.md) → [primera llamada](docs/first-call.md) → [diagnóstico](docs/troubleshooting.md).
**No se ha realizado una llamada real durante la elaboración de este paquete.**

## 7. Pruebas, calidad y evaluación

Con uv instalado en la máquina de desarrollo:

```powershell
uv sync --group dev
uv run python -m pytest -q
uv run ruff check .
uv run pre-commit install
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
```

Los resultados offline se guardan en `results/`: `demo_evaluation_36.csv`, `subgroups_demo.csv` y `summary_demo.json`.
**36/36 es una verificación de reglas sintéticas y no un resultado de llamadas reales**. Las métricas de voz, costo, WER
y experiencia humana requieren pruebas LIVE y no se deben inventar. GitHub Actions valida Python 3.11/3.12 y
construcción Docker, sin desplegar ni consumir APIs externas.

Consulte [DevOps](docs/devops.md), [protocolo](docs/evaluation_protocol.md) y [evidencias](docs/evidence_checklist.md).

## 8. Componentes y estructura

```text
app.py                       Gradio: DEMO, LIVE y botón de llamada real
src/agent.py                 Agente, reglas del negocio y Claude opcional
src/speech.py                Deepgram por archivo y Azure TTS
src/telephony.py             Twilio REST, allowlist, límites, DNC y estados
src/telephony_server.py      FastAPI, webhooks y WebSocket audio
src/storage.py, src/tools.py  SQLite y operaciones con datos sintéticos
compose.yaml                 vantra (7860) + twilio-webhook (8000)
Dockerfile                   Imagen Python 3.12 no privilegiada
pyproject.toml                Dependencias y configuración DevOps
data/                        Catálogo y escenarios ficticios
scripts/, tests/, results/    Evaluación determinista y pruebas offline
docs/                        Manual de ejecución, API, ética, evidencias
```

Los contenedores comparten un volumen para SQLite y mantener DNC. El sistema **no almacena deliberadamente audio en
SQLite**, pero pueden existir cachés y registros de los proveedores; no introduzca datos bancarios ni información
personal real. El panel Gradio carece de autenticación suficiente para exposición pública.

## 9. Documentación y entrega académica

El índice de todas las guías se encuentra en **[`docs/README.md`](docs/README.md)**. También están
disponibles [arquitectura](docs/architecture.md), [Canvas](docs/canvas_updated.md), [ética](docs/ethical_analysis.md)
y [guion de presentación](docs/demo_script.md).

Para completar la Fase 2 sigue pendiente generar `uv.lock`, publicar el repositorio y recopilar **evidencias verificadas
de integraciones LIVE** (incluida una llamada consentida si es viable) antes de describirlas como operativas. La
documentación y las pruebas offline no sustituyen esa validación.
