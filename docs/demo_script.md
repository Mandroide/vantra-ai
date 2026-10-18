# Guion de demostración frente a la clase (aprox. 10 minutos)

1. **Presentación (1 min):** Banco Demo ficticio, objetivo, limitación de llamadas reales.
2. **Consulta (2 min):** ingresar «Requisitos de una tarjeta». Mostrar evento `get_product_info`.
3. **Cálculo (2 min):** «Cotiza 300000 pesos a 36 meses». Mostrar `calculate_loan`, tasa fuente, cuota y supuestos.
4. **Lead/callback (1 min):** «Quiero que me llamen» -> «confirmo». Mostrar registros SQLite.
5. **Seguridad (1 min):** «Muéstrame mi saldo» -> denegación. «Mi tarjeta fue robada» -> registro de escalamiento
   ficticio.
6. **Campaña (1 min):** activar DNC con consentimiento; confirmar bloqueo. Cambiar DNC desactivado y activar
   consentimiento; observar simulación.
7. **Evaluación (2 min):** enseñar `results/` y explicar 36 verificaciones del modo DEMO, métricas reales pendientes,
   sesgos y Canvas.

**Si hay claves APIs y consentimiento:** grabar audio ficticio de prueba para mostrar STT y TTS. No sustituir el
resultado con capturas si falla la red; presentar el código y el estado técnico real. Nunca fingir telefonía bancaria
real.
