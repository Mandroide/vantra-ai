# Mejora de diagnóstico de Twilio

La interfaz anterior ocultaba el estado y el código devueltos por Twilio, presentando siempre un error genérico
`HTTPError`.

## Cambios

- `src/telephony.py`: se agregó `summarize_twilio_http_error`; extrae solo `status_code` y `code` (numérico) del JSON de
  error. No expone mensaje del proveedor porque podría contener números de teléfono.
- `app.py`: captura HTTPError explícitamente y muestra diagnóstico seguro.
- `tests/test_telephony.py`: tres pruebas adicionales (código y respuesta con contenido sensible, error Trial, ausencia
  de JSON o respuesta).
- `docs/troubleshooting.md`: pasos de verificación y limitaciones de cuentas Trial.

## Pruebas

49 pruebas automáticas superadas localmente con pytest. No se ejecutó ninguna llamada real a Twilio.

## Uso

1. Sustituya o abra este repositorio, preserve `.env` local y reconstruya con `docker compose up -d --build`.
2. Recargue la interfaz de Gradio e intente únicamente una llamada consentida y permitida durante el horario del piloto.
3. Informe el estado HTTP y código numérico observados. No comparta Auth Token, SID completo, teléfonos ni contenido de
   respuesta.
