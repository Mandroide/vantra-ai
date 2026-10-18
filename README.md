# Vantra AI — MVP académico de agente bancario de voz

**UASD · Maestría en Ciencia de Datos e Inteligencia Artificial · Capstone Projects · Fase 2**  
**Fecha del paquete:** 18 de octubre de 2026. **Banco Demo es ficticio.** No use datos reales.

## 1. Estado exacto de implementación

| Función                                          | DEMO sin claves                       | LIVE con APIs                                                   |
|--------------------------------------------------|---------------------------------------|-----------------------------------------------------------------|
| Consultas bancarias por texto                    | Implementada, determinista            | Implementada, determinista                                      |
| Catálogo, tasas y cuotas                         | Implementada                          | Implementada                                                    |
| Memoria de producto en la sesión                 | Implementada                          | Implementada                                                    |
| Prospectos y devoluciones de llamada simuladas   | Implementada                          | Implementada                                                    |
| Escalamientos simulados                          | Implementada                          | Implementada                                                    |
| Campaña saliente de demostración (sin telefonía) | Implementada                          | Implementada                                                    |
| Texto libre mediante Claude                      | Respuesta de reserva determinista     | Integración de código disponible; **requiere probar con clave** |
| Audio de entrada vía Deepgram                    | No                                    | Integración de código disponible; **requiere probar con clave** |
| Audio de salida vía Azure Speech                 | TTS local opcional, voz no dominicana | Integración de código disponible; **requiere probar con clave** |
| Llamadas telefónicas reales, CRM bancario real   | No                                    | No                                                              |

**No se ha comprobado el circuito LIVE con servicios externos**. La interfaz funciona en modo DEMO por texto sin
contratar servicios. El modo LIVE es una integración propuesta y codificada, no un resultado experimental validado. No
publicar credenciales.

## 2. Requisitos e instalación (uv recomendado)

- **uv** (https://docs.astral.sh/uv/) y conexión a internet para instalar dependencias.
- Python **3.11 o 3.12**; el proyecto recomienda **3.12** mediante `.python-version`.
- El archivo `pyproject.toml` es la fuente de dependencias. `requirements.txt` se conserva por compatibilidad.

```bash
git clone https://github.com/Mandroide/vantra-ai
cd vantra-ai
# Si el paquete sigue sin publicarse, abra esta carpeta directamente.
uv sync --group dev
cp .env.example .env    # Windows: copy .env.example .env
uv run python app.py
```

Abrir `http://127.0.0.1:7860`. Por defecto la aplicación usa `VANTRA_MODE=DEMO`, sin claves de APIs.

**Estado del lock:** el entorno de elaboración del paquete no disponía de acceso de red a PyPI
ni de Python 3.12. Por ello **no se generó ni se simuló un `uv.lock`**. Queda pendiente
que un integrante ejecute `uv lock` en una computadora conectada y lo incorpore al repositorio.
Mientras tanto, CI y Docker pueden resolver las dependencias en línea, pero su reproducción
no está congelada. Una vez versionado, ambos validarán las dependencias bloqueadas.

**Alternativa sin uv:** Python 3.11/3.12 y `python -m pip install -r requirements.txt`,
seguido de `python app.py`. Este método no garantiza versiones idénticas.

### Pruebas y calidad con uv

```bash
uv run python -m pytest -q --cov=src --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format .             # modificar código a formato uniforme
uv run pre-commit install
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
```

Los hooks locales pueden eludirse: el workflow CI ejecuta validación adicional en Pull Requests.

### Docker y Docker Compose

```bash
docker build -t vantra-ai:mvp .
docker run --rm -p 127.0.0.1:7860:7860 vantra-ai:mvp
docker compose up --build
```

El contenedor incluye solamente las dependencias necesarias para ejecutar la aplicación,
usa un usuario sin privilegios y no incorpora claves API. Compose enlaza el puerto en
`127.0.0.1`; no exponga la aplicación públicamente sin autenticación, políticas de retención
y límites de consumo. **No se ejecutó Docker localmente en el entorno de entrega** porque
no estaba instalado; el workflow de GitHub incorpora la validación del build.

Consulte `docs/devops.md` para el diseño de GitHub Actions, Dependabot y revisión de PRs.

### Prueba rápida (texto)

Pruebe «¿Cuáles son los requisitos de una tarjeta?», «¿Qué tasa tiene el préstamo?», «Cotiza 300000 pesos a 36 meses»,
«Mi tarjeta fue robada» y «Quiero que me llamen» (y luego «confirmo»).

### Síntesis local opcional

En Linux, instale `espeak-ng` y configure `ENABLE_LOCAL_TTS=true` en `.env`, activando además «Generar audio». **No
equivale a una voz dominicana** ni reconoce audio entrante. En modo DEMO se puede usar audio saliente opcional
independientemente de esa variable, siempre que `espeak` esté instalado.

## 3. Modo LIVE: configuración antes de evaluar voz

En `.env` cambie `VANTRA_MODE=LIVE` y complete:

```dotenv
ANTHROPIC_API_KEY=su_clave
ANTHROPIC_MODEL=claude-sonnet-5
DEEPGRAM_API_KEY=su_clave
DEEPGRAM_MODEL=nova-3
AZURE_SPEECH_KEY=su_clave
AZURE_SPEECH_REGION=su_region
AZURE_SPEECH_VOICE=es-DO-RamonaNeural
```

Reinicie `uv run python app.py`. El audio requiere aceptar la casilla de consentimiento por cada interacción. Los tres
servicios implican transferencia de audio/texto a proveedores externos; use **solo grabaciones sintéticas**. La clave
Azure y región deben corresponder al mismo recurso; verifique que el modelo Anthropic esté disponible para su cuenta. La
voz Azure es una opción de configuración, **no evidencia de naturalidad** en un piloto. Pueden presentarse cargos.

- Deepgram: https://developers.deepgram.com/docs/pre-recorded-audio
- Anthropic: https://platform.claude.com/docs/en/api/messages/create
- Azure: https://learn.microsoft.com/azure/ai-services/speech-service/how-to-speech-synthesis
- Gradio: https://www.gradio.app/main/docs/gradio/audio

## 4. Pruebas y evaluación reproducible

```bash
uv run python -m pytest -q
uv run python scripts/make_scenarios.py
uv run python scripts/run_evaluation.py
```

Artefactos generados en `results/`:

- `demo_evaluation_36.csv`: 36 verificaciones del **motor offline** (12 escenarios, 3 variaciones).
- `subgroups_demo.csv`: agregados por escenario, categoría, registro y modalidad.
- `summary_demo.json`: resultados, metodología y limitaciones.

**Interpretación estricta:** `passes_auto_rules=True` significa coincidencia de regla/acción definida en código. No
significa que un modelo generativo reconoció voz, que un usuario real completó una tarea, ni que exista ausencia de
sesgo. Un resultado perfecto en pruebas predefinidas **no prueba generalización**. Las latencias offline son tiempos
locales del motor de reglas, no tiempos de STT/LLM/TTS. Los costos reales y WER quedan **sin datos**, no se imputan como
0.

Para completar la evaluación de voz real, véase `docs/evaluation_protocol.md` y el modelo vacío
`../evidencias/plantilla_pruebas_live.csv`.

## 5. Componentes y datos

```text
app.py                   Interfaz Gradio: texto, audio, consentimientos, modo saliente
src/agent.py             Motor de reglas DEMO y orquestación Claude opcional
src/tools.py             Catálogo, tasas, amortización, lead, callback, escalamiento
src/speech.py            STT Deepgram y TTS Azure/espeak
src/storage.py           SQLite: solo IDs y etiquetas sintéticas
src/config.py            Configuración de entorno
scripts/make_scenarios.py Genera 36 casos sintéticos
scripts/run_evaluation.py Evalúa reglas y exporta CSV/JSON
tests/                  Pruebas unitarias ejecutables
data/                   Catálogo ficticio y escenarios
results/                Evidencia resultante de la ejecución, sin secretos
docs/                   Arquitectura, protocolo, ética, Canvas, demo
```

No hay datos personales de clientes reales. Los registros SQLite se crean en el directorio temporal del sistema, por
defecto `vantra_demo.sqlite3`. Para aislarlos, exporte `VANTRA_DB_PATH` a una ruta distinta. Las grabaciones subidas a
Gradio pueden existir temporalmente en su caché; no prometa eliminación inmediata fuera de los controles de su
despliegue. No habilite acceso público antes de aplicar controles de autenticación, retención y privacidad.

## 6. Ejecución reproducible frente a resultados de IA

El modo DEMO es determinista **a nivel de resultados semánticos**; los identificadores autoincrementales y tiempos de
ejecución varían. Las mismas pruebas deberían satisfacer las mismas reglas, pero no tienen tiempos idénticos. El modo
LIVE depende de modelos y versiones remotos, permisos, facturación, red y variabilidad. Documente fecha, proveedor,
modelo y configuraciones al recolectar evidencias.

## 7. Responsables sugeridos

| Integrante            | Área asignada (pendiente de ratificación) |
|-----------------------|-------------------------------------------|
| Manuel García         | Arquitectura/integración                  |
| Kelvin Feliz Camarena | Agente y Claude                           |
| Francisco Mejía       | STT y TTS                                 |
| Rafael Moronta        | Gradio                                    |
| Luis González         | Datos y herramientas financieras          |
| Federico Marte        | Evaluación y subgrupos                    |
| Rafael Pimentel       | Seguridad, ética e informe                |

Se trata de **una distribución propuesta**, no de un registro de tareas ejecutadas individualmente.

## 8. Publicación pendiente (requiere cuentas autorizadas)

1. Para despliegue en Hugging Face Spaces, cree un Space Gradio y configure los secretos allí. Active
   autenticación/consentimiento y revise cache de audios. Verifique permisos y consumo antes de divulgarlo.
2. Copie el paquete de evidencias y el informe en Drive y habilite acceso mediante enlace **solo para materiales
   públicos/sintéticos**, después de verificar que no hay secretos.
3. Ejecute LIVE con credenciales propias, grabe video con consentimiento, mida latencias y costos, complete la tabla
   real y sustituya secciones «PENDIENTE» del informe.

**No se publicaron repositorios, Spaces ni carpetas Drive automáticamente**, porque no hay acceso autorizado a esas
cuentas desde este entorno.

## 9. Limitaciones éticas y funcionales

Sin CRM real, operadores humanos, verificación de identidad, certificación regulatoria, grabación segura ni campañas
telefónicas. Las listas DNC y los horarios son simulaciones de reglas; no implican cumplimiento normativo. La seguridad
de un LLM puede fallar y requiere evaluación adversarial externa antes de cualquier uso comercial. Nunca usar el MVP
para tomar decisiones de elegibilidad o tratar información bancaria real.
