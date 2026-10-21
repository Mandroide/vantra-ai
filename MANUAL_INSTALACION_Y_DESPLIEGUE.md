# Vantra AI — Manual completo de instalación y despliegue

**Proyecto:** Capstone UASD · Fase 2 · agente de voz de **Banco Demo**, institución ficticia.  
**Entorno recomendado:** Windows 11 + PyCharm + Docker Desktop + ngrok.  
**Estado:** modo DEMO con pruebas offline; código de integración LIVE (Anthropic, Deepgram, Azure Speech y Twilio)
**todavía pendiente de verificación completa con servicios reales**. El documento no implica que las llamadas hayan sido
probadas.

> Este manual es la **ruta de principio a fin**. Para cada etapa existen instrucciones ampliadas en [
`docs/`](docs/README.md). No proporciona números ni claves reales; no incluye un despliegue público de Gradio. El uso
> telefónico está limitado al piloto manual consentido.

## 0. Lo que debe tener listo

| Elemento             | Requisito                                                                                               |
|----------------------|---------------------------------------------------------------------------------------------------------|
| Equipo               | Windows 11 con PyCharm y Docker Desktop abierto, usando contenedores Linux.                             |
| Archivos             | Carpeta `vantra-ai` con `compose.yaml`, `app.py`, `.env.example`.                                       |
| Azure Speech         | Recurso Speech, clave y **región de ese mismo recurso**.                                                |
| Anthropic y Deepgram | API keys y acceso a servicios, con cuota/facturación disponible.                                        |
| Twilio Voice         | Cuenta que permita llamar a RD, credenciales, origen de voz autorizado, permisos geográficos y balance. |
| Destino              | **Su teléfono** o un número dominicano del equipo **con consentimiento previo documentado**.            |
| ngrok                | Agente instalado y autenticado; permite crear URL HTTPS pública hacia `8000`.                           |

La versión **DEMO no requiere las cuentas ni las claves externas**. El objetivo inicial es verificar una aplicación
funcional con datos bancarios ficticios antes de habilitar cobros o llamadas.

> **Advertencia Twilio Trial:** el trial actual puede permitir únicamente determinados destinos, países y parámetros de
> creación de llamadas; el flujo TwiML personalizado con `<Connect><Stream>` de Vantra AI **no debe suponerse compatible**
> con ese nivel. Antes de una llamada con streaming, confirme en su cuenta y en
> los [límites oficiales de prueba](https://www.twilio.com/docs/usage/trials/try-out-voice) que su plan permite el flujo;
> podría necesitar pasar a una cuenta de pago. Ninguna lista de teléfonos o túnel elimina esa limitación.

## 1. Abrir PyCharm y verificar Docker

1. Descomprima el archivo del repositorio, o clone su URL de GitHub **cuando exista**. Abra en PyCharm la carpeta **
   `vantra-ai`**, no su carpeta superior.
2. Desde la pestaña **Terminal** de PyCharm, situada en la raíz del repositorio, ejecute:

```powershell
docker --version
docker compose version
docker info
```

Si `docker info` no responde, abra Docker Desktop, habilite/espere el motor Linux y compruebe la instalación de WSL2 si
Windows lo exige. No hace falta configurar un intérprete local de PyCharm para **ejecutar con Docker**.

## 2. DEMO: arranque sin claves ni llamadas

Si no existe `.env`, cópielo desde el ejemplo (sin sobrescribir uno existente):

```powershell
Copy-Item .env.example .env
```

En `.env` confirme:

```dotenv
VANTRA_MODE=DEMO
TWILIO_CALLS_ENABLED=false
```

Construya e inicie los dos servicios:

```powershell
docker compose config --services
docker compose up -d --build
docker compose ps
```

Debe ver **`vantra`** (Gradio, puerto local **7860**) y **`twilio-webhook`** (FastAPI, puerto local **8000**). Ambos
puertos están vinculados a `127.0.0.1` en `compose.yaml`.

- Abra **http://127.0.0.1:7860** y pregunte «Cotiza 300000 pesos a 36 meses» o «¿Qué requisitos tiene una tarjeta?». Use
  productos ficticios.
- Abra **http://127.0.0.1:8000/healthz**: debe devolver JSON con `ok: true` y `telephony_enabled: false`.
- En Gradio la campaña **simulada** no realiza una llamada telefónica.

Si hay errores, revise por separado:

```powershell
docker compose logs --tail=80 vantra
docker compose logs --tail=80 twilio-webhook
```

No muestre estos registros en capturas públicas sin revisarlos primero: pueden incluir identificadores de solicitudes o
información de las pruebas.

## 3. LIVE: configurar voz y agente sin habilitar telefonía

Abra **el mismo archivo `.env`** junto a `compose.yaml` y complete (las cadenas `REEMPLAZAR` son ejemplos y **no**
funcionarán):

```dotenv
VANTRA_MODE=LIVE
ANTHROPIC_API_KEY=REEMPLAZAR
ANTHROPIC_MODEL=REVISAR_MODELO_DISPONIBLE
DEEPGRAM_API_KEY=REEMPLAZAR
DEEPGRAM_MODEL=nova-3
AZURE_SPEECH_KEY=REEMPLAZAR
AZURE_SPEECH_REGION=REEMPLAZAR_REGION_REAL
AZURE_SPEECH_VOICE=es-DO-RamonaNeural
TWILIO_CALLS_ENABLED=false
```

`ANTHROPIC_MODEL` debe coincidir con un ID disponible para **su** cuenta; el ejemplo real del proyecto está en
`.env.example`. La región Azure no es «República Dominicana»: debe ser la que figura en **Keys and Endpoint** del
recurso Speech.

Aplique los cambios y compruebe primero los servicios individuales desde Gradio:

```powershell
docker compose up -d --force-recreate
docker compose ps
```

- **Anthropic:** haga una consulta abierta. Las consultas al catálogo pueden procesarse por reglas locales, así que una
  respuesta de texto no prueba por sí sola la invocación de Claude.
- **Deepgram:** envíe un audio de prueba consentido y compruebe su transcripción.
- **Azure Speech:** active «Generar audio de respuesta», compruebe que aparece audio y que puede reproducirlo.

Si falla alguna, **no** habilite Twilio. Revise [`docs/configuration.md`](docs/configuration.md) y [
`docs/troubleshooting.md`](docs/troubleshooting.md).

## 4. Twilio: preparar cuenta y número dominicano

1. Abra [Twilio Console](https://console.twilio.com/); confirme el proyecto/cuenta, las restricciones de plan y su
   capacidad de **Programmable Voice**.
2. Obtenga **Account SID**, **Auth Token** y un origen `From` permitido para llamadas de voz (el número de origen **no
   tiene que ser dominicano**).
3. Revise **Voice Geographic Permissions** para República Dominicana; los nombres de menú pueden variar. Verifique que
   el plan permita llamar al país y usar TwiML/Media Streams. **Trial puede no ser suficiente**, especialmente para
   `<Connect><Stream>`.
4. Si el plan exige verificar el destinatario, complételo. **La verificación de Twilio no es consentimiento**.
5. Use **solo** un número con formato `+1809XXXXXXX`, `+1829XXXXXXX` o `+1849XXXXXXX` cuyo titular haya aceptado la
   prueba.

En `.env`, complete y **todavía no active**:

```dotenv
TWILIO_CALLS_ENABLED=false
TWILIO_ACCOUNT_SID=AC_REEMPLAZAR
TWILIO_AUTH_TOKEN=REEMPLAZAR
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
TWILIO_TEST_NUMBERS=+1809XXXXXXX
TWILIO_PUBLIC_BASE_URL=
```

Para varios destinatarios con permiso, sepárelos por comas. La lista solo indica qué números están permitidos; debe
conservar aparte la evidencia de consentimiento. No añada contactos de clientes reales ni contactos públicos. La
telefonía está limitada por código a **una llamada simultánea, tres solicitudes por día, 180 segundos máximo y
lunes-viernes de 09:00 a 17:59 hora Santo Domingo**.

## 5. ngrok: obtener `TWILIO_PUBLIC_BASE_URL`

Compruebe que Docker está funcionando y que **http://127.0.0.1:8000/healthz** responde.
Instale [ngrok para Windows](https://ngrok.com/download), cree su cuenta y copie su **authtoken**, que nunca debe
publicar.

En una terminal del sistema (no necesita entrar en Docker):

```powershell
ngrok config add-authtoken SU_AUTHTOKEN
ngrok http 8000
```

Deje esta terminal abierta. ngrok mostrará una línea semejante a:

```text
Forwarding  https://ejemplo.ngrok-free.app -> http://localhost:8000
```

La URL mostrada aquí es **ficticia**: copie la suya y guárdela en `.env`:

```dotenv
TWILIO_PUBLIC_BASE_URL=https://DOMINIO_REAL_DE_SU_NGROK
```

**No** use `localhost`, el puerto `7860`, `/healthz`, `/twilio/status` ni `/twilio/media` como parte de la base.
Compruebe en el navegador **`https://DOMINIO_REAL_DE_SU_NGROK/healthz`**. La aplicación genera automáticamente:

```text
POST https://DOMINIO_REAL_DE_SU_NGROK/twilio/status
WSS  wss://DOMINIO_REAL_DE_SU_NGROK/twilio/media
```

No necesita agregar estas rutas manualmente a Twilio Console para llamadas iniciadas por el código actual. Una respuesta
HTTPS correcta de `/healthz` **no demuestra que WSS y Twilio funcionen**.

Cuando cambie la URL del túnel, actualice `.env` y recree ambos contenedores. Mantenga **Gradio 7860 privado**: su
interfaz no está endurecida para publicar el botón de llamadas reales.

## 6. Primera llamada real — solo después de todas las verificaciones

**Antes de habilitar `true`**, asegúrese de que:

- Los tres proveedores LIVE pasaron las pruebas individuales y tienen cuota disponible.
- Twilio autoriza la llamada a República Dominicana y el plan admite **TwiML con `<Connect><Stream>`**.
- El teléfono de destino está en `TWILIO_TEST_NUMBERS` y existe consentimiento verificable.
- Docker muestra los dos contenedores y `/healthz` público funciona con la URL **actual**.
- Hoy es **lunes a viernes y son entre las 09:00 y las 17:59**, hora Santo Domingo. No excede los límites y no existe
  exclusión Do-Not-Call.
- Hay un operador junto al teléfono de prueba para responder y finalizar la llamada; han revisado costos y privacidad.

Si todo se cumple, cambie:

```dotenv
TWILIO_CALLS_ENABLED=true
```

Y aplique variables nuevas:

```powershell
docker compose up -d --force-recreate
```

Abra **http://127.0.0.1:7860** → pestaña **«Llamada REAL · piloto restringido»**. Introduzca el E.164 autorizado, marque
las dos confirmaciones y pulse **una sola vez** «Iniciar UNA llamada real».

- `queued` significa petición recibida por Twilio, **no** una conversación satisfactoria.
- Observe en paralelo `docker compose logs -f twilio-webhook`, ngrok y los registros de llamadas de Twilio Console.
- Si escucha el saludo, haga una consulta simple («¿Qué requisitos tiene la tarjeta?») y, después, otra para evaluar la
  interacción; **no comparta datos bancarios reales**.
- Finalice desde Gradio o el propio teléfono. Si recibe un **timeout**, **NO pulse de nuevo** hasta revisar el estado de
  la llamada en Twilio: podría estar ya activa.

La voz telefónica está implementada **por turnos**; no incluye interrupción simultánea (*barge-in*) ni transferencia
humana real. Si el destinatario pide no recibir llamadas, registre su exclusión DNC y termine. No elimine el volumen
SQLite para «resetear» exclusiones.

## 7. Verificar, ejecutar pruebas y recopilar evidencias

**Pruebas offline** (opcionalmente con uv instalado en la máquina):

```powershell
uv lock                          # Si aún no se versionó uv.lock
uv sync --group dev
uv run python -m pytest -q
uv run ruff check .
uv run python scripts/run_evaluation.py
```

El `Dockerfile` de ejecución no incorpora `scripts/` ni Pytest en la imagen final: ejecute esas órdenes **en el host con
uv o a través de CI**, no mediante `docker compose exec vantra`. Las 36 verificaciones del modo DEMO miden reglas
automáticas, **no rendimiento de STT/LLM/TTS real**. Si se genera un `uv.lock`, agréguelo al repositorio; sin lock
versionado la reproducción de dependencias no está totalmente fijada.

Para evidencia del Capstone, registre identificador de prueba **anónimo**, categoría, éxito, latencia, calidad de
transcripción/síntesis, fecha, duración, costo del proveedor y errores; distinga **DEMO**, **LIVE Gradio** y **LIVE
telefónico**. No guarde números de teléfono ni credenciales en un Drive abierto al público. Consulte [
`docs/evaluation_protocol.md`](docs/evaluation_protocol.md) y [
`docs/evidence_checklist.md`](docs/evidence_checklist.md).

## 8. Operación, actualizaciones y fallos

```powershell
# Estado y logs
docker compose ps
docker compose logs --tail=100 vantra
docker compose logs --tail=100 twilio-webhook

# Cambió solo .env
docker compose up -d --force-recreate

# Cambió código o dependencias
docker compose up -d --build

# Detener preservando el volumen de datos y exclusiones
docker compose down
```

**No use `docker compose down -v` durante las pruebas:** borra el volumen compartido con estados y DNC. Si cambia ngrok,
ajuste la base; si hay error 403 de webhook, revise coincidencia de URL y credenciales, no desactive la comprobación de
firmas. Si el teléfono marca pero se corta, revise streaming WSS, permisos Twilio y logs FastAPI; si no hay voz, examine
TTS Azure; si no reconoce palabras, examine Deepgram streaming. Más casos en [
`docs/troubleshooting.md`](docs/troubleshooting.md).

## 9. Cierre y límites de seguridad

- Twilio, Deepgram, Anthropic y Azure son servicios **externos**: pueden generar cargos y tratar información de
  audio/texto conforme a sus políticas.
- Las llamadas y la verificación del consentimiento no están certificadas para uso bancario real. El piloto solo debe
  dirigirse a voluntarios autorizados.
- **No** hay llamadas automatizadas masivas, autenticación pública robusta en Gradio, CRM bancario, verificación de
  identidad bancaria, telefonía entrante ni transferencias humanas reales.
- El estado de llamada/DNC está en SQLite compartido. La rotación de `TWILIO_AUTH_TOKEN` afecta el cálculo HMAC de la
  lista DNC y requiere gestionar la transición con cuidado.
- No publique `.env`, números, tokens, grabaciones, capturas con datos personales ni logs sin anonimizar.
- Este manual cubre **cómo** instalar y realizar la prueba; **no afirma** que Docker, Twilio o el pipeline de voz se
  hayan validado en este entorno. El equipo debe registrar el resultado real de la primera prueba.

**Guías
detalladas:** [índice de documentación](docs/README.md) · [inicio](docs/getting-started.md) · [variables](docs/configuration.md) · [Docker](docs/docker-deployment.md) · [Twilio](docs/twilio-setup.md) · [ngrok](docs/ngrok-setup.md) · [primera llamada](docs/first-call.md) · [problemas](docs/troubleshooting.md).
