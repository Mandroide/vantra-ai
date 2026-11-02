# Vantra AI

**Agente conversacional de voz para un banco ficticio · MVP académico**  
Universidad Autónoma de Santo Domingo (UASD) · Maestría en Ciencia de Datos e Inteligencia Artificial · Capstone
Projects, Fase 3 (integración consolidada).

Vantra AI permite consultar productos bancarios ficticios, calcular cuotas con funciones deterministas, registrar
prospectos de prueba y simular derivaciones. Ofrece una interfaz web con Gradio y adaptadores para reconocimiento de
voz, modelo de lenguaje y síntesis de audio. Incluye un **piloto restringido de llamadas salientes a números dominicanos
previamente autorizados** con Twilio.

> **Estado de validación:** las pruebas de lógica y escenarios sintéticos se pueden ejecutar sin credenciales. El equipo
> ha aportado evidencia de una conversación telefónica piloto; esa evidencia no equivale a una validación sistemática de
> seguridad, latencia, costos ni desempeño de proveedores LIVE. No hay conexiones con bancos reales, transferencias
> humanas operativas ni autorización para utilizarlo comercialmente.

## Funciones

| Componente           | Comportamiento                                                                                                                       |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| DEMO                 | Chat por texto y operaciones con datos sintéticos sin APIs externas.                                                                 |
| LIVE                 | Conectores de Deepgram (STT), Anthropic Claude (LLM, cuando la consulta lo requiere) y Azure Speech (TTS). Requiere cuentas válidas. |
| Telefonía            | Llamada saliente **manual** mediante Twilio REST y procesamiento de audio en WebSocket. Deshabilitada de forma predeterminada.       |
| Seguridad de piloto  | Lista de destinatarios permitidos, consentimiento declarado, lista DNC, horario configurable y límites de volumen.                   |
| Evaluación           | Pytest y 12 escenarios × 3 variantes de texto = 36 verificaciones offline.                                                           |
| Ingeniería           | uv, Docker Compose, Ruff, pre-commit y GitHub Actions.                                                                               |
| Comprensión (Fase 3) | `src/nlu.py`: tolerancia a errores de transcripción, montos en palabras y prioridad de fraude, privacidad y exclusión.               |
| Analítica (Fase 3)   | `analytics/`: F1 por intención, MCMC bayesiano jerárquico, Monte Carlo del ROI y sensibilidad.                                       |
| Cuadro de mando      | `dashboard.py` (Streamlit): KPIs técnicos y de negocio, simulación en vivo y prueba del agente.                                      |

## Arquitectura consolidada y fuentes de evidencia

Esta versión toma como **base el repositorio de la Fase 3 presentado por el equipo**. Conserva `src/nlu.py`, el held-out
v2 congelado, la inferencia MCMC, el análisis Monte Carlo y el dashboard Streamlit.
Del borrador anterior se incorporan únicamente utilidades **compatibles y complementarias**: telemetría local sin
texto/audio y funciones de WER/F1/latencias, visualizadas exclusivamente en Streamlit. **No se incorpora el modelo
alternativo de ROI de 12 meses**, ya que los supuestos, monedas y horizontes difieren; la fuente de referencia económica
es `analytics/montecarlo.py`, con supuestos en `analytics/assumptions.py`.

Resultados del held-out v2: 17/114 (14.9 %) antes, 83/114 (72.8 %) después, en modo DEMO. Son **evaluaciones textuales
sintéticas**, no precisión medida en llamadas LIVE. Se mantienen los archivos de evidencia de la presentación sin
alterar su huella.

## Dos interfaces, un solo modelo de negocio

- **Gradio (puerto local 7860):** conversación, voz, telefonía autorizada y gestión de exclusiones DNC. **No incluye
  dashboard analítico.**
- **Streamlit (puerto local 8501): único dashboard para evaluación held-out v2, MCMC, Monte Carlo, sensibilidad,
  supuestos, diagnóstico, telemetría de Gradio y operaciones sintéticas. Los escenarios económicos del informe proceden
  de esta implementación.

Para ejecutar ambas interfaces con Docker (sin túnel):

```powershell
docker compose -f compose.yaml -f compose.dashboard.yaml up -d --build
```

Abra <http://127.0.0.1:7860> y <http://127.0.0.1:8501>. En una sesión con ngrok también puede combinar los archivos
`-f compose.ngrok.yaml -f compose.dashboard.yaml`; solo el webhook de Twilio se expone mediante el túnel. **No publique
los dashboards sin autenticación.**

Para ejecución local sin Docker:

```powershell
uv sync --locked --group dev --group dashboard
uv run --locked --group dashboard streamlit run dashboard.py
```

Si usas un `.env` de la Fase 3, puedes elegir `VANTRA_FALLBACK=humano` para derivar consultas no comprendidas; el valor
`texto` se mantiene para reproducir la evaluación congelada. El overlay Docker propaga el modo configurado en
`compose.yaml`.

## Si actualiza una carpeta que contenía el dashboard Gradio antiguo

**No copie el ZIP sobre archivos heredados sin revisar las diferencias**: la extracción de un ZIP no elimina archivos
obsoletos. Si Pytest intenta importar `tests/test_impact.py` o `src/dashboard/executive.py`, está utilizando módulos del
borrador anterior, **no** del repositorio unificado. El dashboard oficial es `dashboard.py` (Streamlit), y los cálculos
económicos oficiales son `analytics/mcmc.py` y `analytics/montecarlo.py`.

En PyCharm, conserve primero sus cambios en Git. Compruebe los archivos antiguos con `git status --short` y
`git ls-files tests/test_impact.py src/dashboard/executive.py src/impact.py`. Mueva esos módulos y las pruebas
dependientes a una copia de seguridad **fuera de la carpeta del proyecto** antes de ejecutar Pytest. No borre `.env`,
SQLite, ni el volumen Docker de Vantra. No instale Matplotlib únicamente para mantener el dashboard antiguo.

Para validar el dashboard Streamlit localmente instale su grupo opcional de dependencias:

```powershell
uv sync --locked --group dev --group dashboard
uv run --locked --group dashboard python -m pytest -q
uv run --locked --group dashboard streamlit run dashboard.py
```

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
uv sync --locked --group dev
uv run python -m pytest -q
uv run python scripts/run_evaluation.py
uv run python app.py
```

Para levantar además el receptor Twilio, en otra terminal:

```bash
uv run uvicorn src.telephony_server:app --host 127.0.0.1 --port 8000
```

**Reproducibilidad:** `uv.lock` está versionado; `uv sync --locked` instala exactamente las mismas versiones.

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

## Fase 3: cuadro de mando, MCMC y Monte Carlo

```bash
uv sync --locked --group dev --group dashboard
uv run python scripts/run_holdout_evaluation.py --set v2 --tag despues   # held-out v2 congelado, agente actual
uv run python scripts/run_simulation.py                                  # MCMC + Monte Carlo -> results/fase3/
uv run streamlit run dashboard.py                                        # http://localhost:8501
```

- `data/holdout_v2_scenarios.json` (114 frases) se escribió y congeló **antes** de corregir el agente; su huella está en
  `data/holdout_v2.sha256` y la verifica `tests/test_holdout.py`. El held-out v1 (Fase 2) se usó para diseñar las
  mitigaciones; v2 solo para medir. Línea base congelada: `results/holdout_v2_antes_demo_*`.
- Resultado en v2 (DEMO): exactitud de 14.9% a 72.8%, F1 macro de 0.23 a 0.79 y casos críticos con acción
  equivocada de 3 a 1 de 36. El registro coloquial sigue por debajo del formal (brecha documentada en
  [Evaluación](docs/evaluation.md)).
- `scripts/run_simulation.py` estima la posterior con MCMC (Metropolis, 4 cadenas, R-hat ≤ 1.01) y la propaga a
  10,000 escenarios de Monte Carlo con supuestos citados en `analytics/assumptions.py`. Es determinista (semillas
  fijas).
- El dashboard vuelve a ejecutar el held-out v2 contra el código actual, recalcula la posterior y simula en vivo al
  mover los supuestos.

Los archivos de `results/` contienen **resultados de DEMO sintético**, no mediciones de precisión acústica, naturalidad,
latencia o facturación LIVE. Las pruebas LIVE requieren voluntarios, consentimiento, evaluación humana y registro de
consumo del proveedor.

## Estructura

```text
app.py                   Interfaz Gradio (texto, voz y telefonía restringida)
src/agent.py             Agente y reglas de negocio
src/nlu.py               Normalización tolerante, números en palabras e intenciones (Fase 3)
analytics/               Métricas por intención, MCMC, Monte Carlo y supuestos con fuentes (Fase 3)
dashboard.py             Cuadro de mando Streamlit (Fase 3)
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
results/                 Evidencias deterministas de DEMO; results/fase3/ para MCMC y Monte Carlo
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

## Cambios de seguridad y medición v0.4.0

La política crítica se comparte entre el chat y el servidor telefónico (`src/critical_policy.py`). En las llamadas se
solicita confirmación verbal inequívoca **además del consentimiento previo documentado** antes de procesar consultas
generales. Los pedidos de exclusión DNC, privacidad, fraude y atención humana se reconocen sin depender de Claude; no
existe transferencia humana real.

**Antes de habilitar llamadas LIVE** cree un secreto estable distinto del token de Twilio:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Guárdelo exclusivamente en `.env` bajo `VANTRA_PHONE_HASH_KEY`. El nuevo formato HMAC `v2:` preserva exclusiones frente
a la rotación de `TWILIO_AUTH_TOKEN`. Si hay hashes DNC heredados, **se bloquean las llamadas**
hasta [migrarlos](docs/telephony.md); no se eliminan automáticamente. No comparta ni versione secretos.

Las métricas telefónicas se visualizan en una pestaña separada del dashboard Streamlit (`src/observability.py`), sin
audios, transcripciones ni números. Para evaluar WER/F1/latencia con anotaciones autorizadas se proporciona
`data/live_evaluation_template.csv` y `python -m scripts.evaluate_live_voice data/live_inputs/pruebas.csv`. El archivo
de entrada es privado; por defecto no existen resultados LIVE. CI ejecuta la batería de seguridad y exige cobertura
inicial del 70 %.

**Costos:** las unidades LIVE registradas en SQLite permiten estimar un subtotal con tarifas configuradas; la factura
completa de Twilio/servicios sigue sin verificarse. El ROI continúa siendo una proyección Monte Carlo independiente de
estos registros.

## Diagnóstico de cuatro fallos frecuentes al actualizar en Windows / PyCharm

Si se extrae una versión ZIP **sobre** un checkout anterior, los archivos antiguos
permanecen en el árbol y Git puede conservar rutas eliminadas en su índice.
El parche de compatibilidad corrige tres causas de falsos fallos:

- `test_secret_scan_passes_synthetic_repository`: ignora rutas versionadas que ya no existen
  y sigue detectando archivos sensibles reales.
- `test_eight_canonical_markdown_files`: exige la presencia de las ocho guías, pero permite
  documentos adicionales sin eliminarlos.
- `test_dominican_local_schedule_blocks`: establece el permiso de pruebas fuera de horario
  en `false` durante la prueba, sin depender de las opciones de su `.env`.

**Integridad del held-out v2:** la prueba admite una conversión de finales de línea
LF/CRLF causada por Windows, pero **no** acepta alteraciones de datos ni huellas recalculadas.
Para conocer su estado real:

```powershell
uv run python -m scripts.verify_frozen_holdout
uv run --locked --group dashboard python -m pytest -q
```

Si indica `modified`, respalde la copia actual y restaure exclusivamente
`data/holdout_v2_scenarios.json` desde la distribución original confiable. No ejecute
`scripts/make_holdout_v2.py` ni cambie `data/holdout_v2.sha256` para hacer pasar la prueba.

**Actualización segura:** descomprima el nuevo ZIP en una carpeta *nueva*. Lleve a ella
solo los cambios propios revisados y su `.env` privado, sin publicar este último.
Conserve y respalde la base de datos y volúmenes Docker; nunca use `docker compose down -v`
para una actualización rutinaria. Gradio sigue siendo el agente operativo; **Streamlit
es el único dashboard**.
