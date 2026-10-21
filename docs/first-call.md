# Primera llamada real — lista de verificación y procedimiento

**Alcance:** una llamada manual a **su teléfono dominicano o al de un integrante autorizado**, desde la pestaña «Llamada
REAL · piloto restringido» de Gradio. La conexión STT → agente → TTS todavía **debe validarse en vivo**. No utilice el
sistema para campañas a terceros ni números no autorizados.

## A. Lista obligatoria antes de pulsar «Llamar»

- [ ] El titular del número dio autorización **previa y verificable** para recibir esta llamada concreta.
- [ ] El destino es E.164 RD: `+1809XXXXXXX`, `+1829XXXXXXX` o `+1849XXXXXXX`, y está exactamente en
  `TWILIO_TEST_NUMBERS`.
- [ ] La cuenta Twilio está activa, con crédito/cuota y **Voice Geo Permissions** habilitados para República Dominicana;
  si es Trial, confirme además que **el plan permite el TwiML personalizado `<Connect><Stream>`** utilizado por el
  repositorio (no asumir que basta con verificar el destinatario).
- [ ] `TWILIO_FROM_NUMBER` es un número/caller ID de voz autorizado.
- [ ] Claude/Deepgram/Azure tienen credenciales vigentes; Azure usa la **región real del recurso**, y las pruebas
  previas de voz por Gradio no arrojaron errores.
- [ ] Docker muestra ambos servicios en `docker compose ps`; funciona `http://127.0.0.1:8000/healthz`.
- [ ] ngrok está abierto y `https://SU_DOMINIO/healthz` devuelve el JSON esperado; la URL `TWILIO_PUBLIC_BASE_URL` es
  esa base, sin ruta ni puerto.
- [ ] Es **lunes a viernes, 09:00–17:59 (America/Santo_Domingo)**.
- [ ] No hay otra llamada en curso; no se excedieron 3 solicitudes del día; el contacto no solicitó DNC.
- [ ] Existe un operador presente para supervisar y colgar si es necesario; se acordó una prueba máxima de 180 s.
- [ ] El operador entiende el posible costo real de telefonía, STT, LLM y TTS y tiene medios para suspender la llamada.

**Si falta cualquiera de estas condiciones, mantenga `TWILIO_CALLS_ENABLED=false` y no llame.**

## B. Secuencia de ejecución (PyCharm + Docker)

**Terminal de PyCharm (raíz del repositorio):**

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

**Terminal Windows separada:**

```powershell
ngrok http 8000
```

Copie la URL que imprima ngrok. En `.env` deje `VANTRA_MODE=LIVE` y todas las claves correctamente configuradas; agregue
el origen real HTTPS. **Solo después de comprobar todos los puntos A** cambie:

```dotenv
TWILIO_CALLS_ENABLED=true
```

Aplique variables nuevas:

```powershell
docker compose up -d --force-recreate
```

Vuelva a probar `/healthz`: ahora debería reflejar `"telephony_enabled": true`. Esto solo verifica el flag, **no** que
Twilio acepte llamadas.

Abra **http://127.0.0.1:7860**. Entre a la pestaña «Llamada REAL · piloto restringido». Escriba el número E.164
autorizado, marque las dos confirmaciones y pulse **una sola vez** «Iniciar UNA llamada real».

Si el resultado muestra `queued`, significa **solicitud aceptada por Twilio**, no que el teléfono haya sonado o
contestado. Observe Twilio Console → logs de llamadas y utilice «Consultar estado» en Gradio; las etiquetas del panel de
Twilio varían por versión.

Cuando el destinatario conteste, el agente debería identificarse como asistente de IA del **Banco Demo ficticio**. Haga
una consulta sencilla del catálogo, por ejemplo «¿Qué requisitos tiene la tarjeta?» y otra fuera de reglas para examinar
el modelo. Evalúe si el audio se escucha, si transcribe español y si la respuesta llega dentro de un tiempo razonable.
**No suponga que ya funciona hasta escuchar una conversación completa.**

Para finalizar, use «Finalizar llamada» desde Gradio o cuelgue desde el teléfono. Confirme que el estado final aparezca
en la consola Twilio. Si el usuario pide «no vuelva a llamar», registre además su exclusión (DNC) y compruebe que la
próxima solicitud sea bloqueada **sin iniciar llamada**.

## C. Si algo sale mal

- Si aparece un error **antes** de `queued`, lea el texto de Gradio, [diagnóstico](troubleshooting.md) y logs de ambos
  servicios. No desactive controles para forzar la llamada.
- Si el botón da **timeout**, **no vuelva a pulsar**: la petición pudo haber sido recibida por Twilio. Revise Twilio
  Console para evitar duplicados.
- Si contesta pero no se oye voz, revise el servidor `twilio-webhook`, la región/voz Azure y los mensajes WSS de Twilio;
  `/healthz` no garantiza audio.
- Si el teléfono sigue conectado tras un error de Gradio, cuelgue desde el propio teléfono o desde Twilio Console.
  Cambiar `.env` no finaliza necesariamente una llamada ya activa.
- Si se detecta una llamada inesperada o uso indebido, deshabilite `TWILIO_CALLS_ENABLED`, recree contenedores y revise
  el estado de llamadas en Twilio.

## D. Evidencia que sí puede adjuntar a la Fase 2

Documente para cada llamada **consentida**: fecha y franja horaria (sin número visible), rol del probador, categoría,
duración, latencia percibida/medida, calidad STT, calidad TTS, resultado, error (si hubo) y costo reportado por el
proveedor. Use identificadores anónimos. No incorpore teléfonos reales, secretos, audios identificables ni
transcripciones con datos personales al Drive de acceso abierto.

Las **36 verificaciones DEMO** no son resultados de llamadas. Si no se puede completar la prueba real, informe
**pendiente**, no «validado». Las transferencias a agentes humanos continúan simuladas.

Siga el [protocolo de evaluación](evaluation_protocol.md) y la [lista de evidencias](evidence_checklist.md).
