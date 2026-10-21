# Ingeniería de software y DevOps — Vantra AI

> **Instalación guiada desde
PyCharm:** [Inicio](getting-started.md) → [Docker](docker-deployment.md) → [Variables](configuration.md).

## Decisiones

Se incorpora **uv, Ruff, pre-commit, Pytest + cobertura, Docker/Compose, GitHub Actions y Dependabot**. Jenkins se
omite: duplicaría la infraestructura del pipeline sin cubrir una necesidad académica. La aplicación sigue siendo una
simulación bancaria; estos controles NO demuestran funcionamiento de APIs externas.

### Entorno local

```bash
uv sync --group dev
uv run python -m pytest -q --cov=src --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format .
uv run pre-commit install
uv run pre-commit run --all-files
uv run python scripts/run_evaluation.py
uv run python app.py
```

**Primera configuración del lock:** si el repositorio no contiene `uv.lock`, ejecutar `uv lock` con conexión a PyPI y
añadir el archivo resultante al control de versiones. En CI el paso de arranque puede generarlo para permitir las
primeras pruebas (y adjuntarlo como artefacto), pero **hasta incorporarlo al repositorio no hay resolución de
dependencias completamente congelada**. En cuanto se suba el lock, CI y Docker validan `--locked`. No insertar un lock
inventado o parcial.

### Contenedores

```bash
docker build -t vantra-ai:mvp .
docker run --rm -p 127.0.0.1:7860:7860 vantra-ai:mvp
docker compose up --build
```

Abrir `http://127.0.0.1:7860`. La imagen usa Python 3.12, instala solo dependencias de ejecución, no copia `.env`, corre
como usuario sin privilegios y expone el servicio solo por localhost en las instrucciones de ejecución. Compose lee las
variables de `.env` automáticamente cuando el archivo existe, pero **no lo copia dentro de la imagen**. No ejecutar LIVE
en una máquina accesible al público: falta autenticación y control de costos.

Para detener Compose: `docker compose down`. No se ha validado la construcción de imagen desde el entorno que preparó el
paquete porque Docker no estaba instalado allí.

### Flujo de Pull Request

1. Crear rama y cambiar el componente correspondiente.
2. Ejecutar `uv run ruff format .` y `uv run ruff check .`; revisar cambios de formato.
3. Ejecutar Pytest, evaluación offline y `uv run pre-commit run --all-files`.
4. Subir un Pull Request: GitHub Actions valida **Python 3.11 y 3.12**, comprueba secretos heurísticamente, recopila
   cobertura, verifica 36 reglas offline y construye una imagen Docker (sin publicarla ni ejecutar LIVE).
5. Revisar resultados, proteger `main` exigiendo que los jobs terminen correctamente y aprobar el PR.

El workflow `docker.yml` se ejecuta bajo demanda y no publica imágenes. **No hay CD automático ni Jenkins**. Una
eventual publicación debería disponer de autenticación, límites de uso, consentimiento informado y manejo de secretos.

### Alcance inicial de Ruff

El conjunto activo en `pyproject.toml` se limita a errores de sintaxis, importaciones gravemente problemáticas y
referencias indefinidas. Los archivos anteriores fueron escritos con un formato muy compacto. La primera persona que
configure el entorno debe ejecutar `uv run ruff format .` y confirmar los cambios de formato; posteriormente conviene
ampliar gradualmente `tool.ruff.lint.select`. El formateador queda disponible también como hook local, pero **no se
afirma que el repositorio original ya cumple todo el conjunto de reglas recomendadas**.

### Seguridad y evidencia

El chequeo `scripts/check_secrets.py` busca archivos y tokens comunes, sin sustituir herramientas dedicadas ni revisión
del historial de Git. Evite subir `.env`, datos personales, transcripciones o WAV reales. Las pruebas CI funcionan en
modo DEMO sin credenciales y no deben confundirse con las validaciones LIVE. Los resultados de cobertura serán evidencia
de código ejecutado, no un indicador de calidad de respuestas del LLM.
