"""Interfaz Gradio; ejecutar: python app.py"""
import os, time
import requests
import gradio as gr
from src.agent import respond, Session
from src.config import env
from src.speech import transcribe_deepgram, speak_azure, speak_local
from src.storage import counts
from src.tools import check_contact_policy
from src.telephony import start_test_call, stop_test_call, get_call, add_do_not_call, CallPolicyError, \
    summarize_twilio_http_error

LIVE = env('VANTRA_MODE', 'DEMO').upper() == 'LIVE'


def render(text, state, history, synth_voice=False):
    state = state or Session();
    history = history or []
    start = time.perf_counter()
    ans, state = respond(text, state, mode='LIVE' if LIVE else 'DEMO')
    history = history + [{'role': 'user', 'content': text}, {'role': 'assistant', 'content': ans.text}]
    audio = None;
    voice_error = ''
    tts_ms = None
    if synth_voice:
        try:
            ts = time.perf_counter()
            audio = speak_azure(ans.text) if LIVE else speak_local(ans.text)
            tts_ms = round((time.perf_counter() - ts) * 1000, 2)
        except Exception as ex:
            voice_error = '\nTTS no disponible: ' + type(ex).__name__
    meta = {'modo': ans.mode, 'estado': ans.status, 'herramientas': [e['name'] for e in ans.tools],
            'latencia_agente_ms': ans.elapsed_ms, 'latencia_total_ms': round((time.perf_counter() - start) * 1000, 2),
            'tokens_entrada_LLM': ans.llm_input_tokens, 'tokens_salida_LLM': ans.llm_output_tokens,
            'tts_ms': tts_ms, 'costo_api_real_usd': None,
            'advertencia': 'Costo API desconocido hasta revisar facturación; no representa desempeño de un banco real'}
    return history, state, audio, meta, voice_error


def send_text(text, state, history, voice):
    if not (text or '').strip(): return history, state, None, {}, '', text
    h, s, a, m, e = render(text, state, history, voice)
    return h, s, a, m, e, ''


def send_audio(audio, authorized, state, history, voice):
    if not authorized:
        return history, state, None, {
            'error': 'No se otorgó consentimiento para procesar audio'}, 'Marque el consentimiento y utilice solo voz ficticia.', ''
    if not LIVE:
        return history, state, None, {'modo': 'DEMO',
                                      'STT': 'no disponible sin proveedor'}, 'El modo DEMO admite texto. Configure LIVE y DEEPGRAM_API_KEY para grabar voz.', ''
    if not audio:
        return history, state, None, {'error': 'Sin audio'}, 'Grabe audio antes de enviarlo.', ''
    try:
        t = time.perf_counter();
        transcript, duration = transcribe_deepgram(audio)
        stt_ms = round((time.perf_counter() - t) * 1000, 2)
        if not transcript: raise ValueError('No se reconocieron palabras')
        h, s, a, m, e = render(transcript, state, history, voice)
        m['stt_ms'] = stt_ms
        m['audio_entrada_seg'] = duration
        return h, s, a, m, e, transcript
    except Exception as ex:
        return history, state, None, {'error': 'Problema de STT', 'tipo': type(
            ex).__name__}, 'No fue posible procesar el audio. Revise la configuración.', ''


def outbound(consent, dnc, hour):
    rule = check_contact_policy(bool(consent), bool(dnc), int(hour))
    if not rule['allowed']:
        return f"⛔ Simulación bloqueada: {rule['reason']}. No se inició ninguna llamada."
    return 'SIMULACIÓN HABILITADA: Buenos días, soy Vantra AI de Banco Demo ficticio. ¿Desea conocer nuestros productos? (No se hizo ninguna llamada.)'


def call_real(number, prior_consent, authorized_recipient):
    """Acción deliberada desde interfaz LOCAL; sin llamadas masivas ni automatización."""
    if not authorized_recipient or not prior_consent:
        return 'Bloqueado: debe confirmar autorización del destinatario y consentimiento documentado.', ''
    try:
        result = start_test_call(number, confirmed=True)
        return f"Twilio recibió solicitud: {result['status']}. SID: {result['call_sid']}. Estado pendiente de confirmación.", \
            result['id']
    except (CallPolicyError, RuntimeError) as exc:
        return f'Bloqueado: {exc}', ''
    except requests.exceptions.HTTPError as exc:
        return summarize_twilio_http_error(exc), ''
    except Exception as exc:
        return f'Twilio no pudo iniciar llamada ({type(exc).__name__}). Revise facturación, número origen y permisos geográficos.', ''


def phone_block(number, authorization):
    if not authorization:
        return 'Confirme que es una solicitud de exclusión del titular antes de registrar DNC.'
    try:
        add_do_not_call(number)
        return 'Número excluido de futuras llamadas (no se almacena en texto claro).'
    except Exception as exc:
        return f'No se pudo registrar exclusión: {type(exc).__name__}.'


def call_refresh(call_id):
    if not call_id:
        return 'No hay ninguna llamada iniciada desde esta sesión.'
    item = get_call(call_id)
    return (f"Estado registrado: {item['status']} · SID: {item['call_sid'] or 'pendiente'}" if item
            else 'No se encontró la llamada.')


def call_stop(call_id):
    if not call_id:
        return 'No hay llamada activa en esta sesión.'
    try:
        result = stop_test_call(call_id)
        return f"Solicitud de finalización enviada: {result['status']}."
    except Exception as exc:
        return f'Error al finalizar llamada: {type(exc).__name__}.'


with gr.Blocks(title='Vantra AI | MVP académico') as app:
    gr.Markdown(
        '# Vantra AI · Agente bancario de voz (MVP)\n**Banco Demo ficticio** | Datos sintéticos | Telefonía real solo en piloto restringido con consentimiento')
    gr.Markdown('**Modo:** ' + (
        'LIVE (requiere claves API)' if LIVE else 'DEMO reproducible (texto)') + ' · **Advertencia:** nunca introduzca datos personales, financieros o grabaciones reales.')
    state = gr.State(Session())
    with gr.Tab('Atención entrante'):
        chat = gr.Chatbot(label='Conversación', height=370)
        with gr.Row():
            txt = gr.Textbox(label='Consulta de texto', placeholder='Ej.: Cotiza 300000 pesos a 36 meses', scale=5)
            submit = gr.Button('Enviar', variant='primary', scale=1)
        generate_audio = gr.Checkbox(value=False,
                                     label='Generar audio de respuesta (Azure en LIVE; espeak opcional en DEMO)')
        with gr.Row():
            audio_in = gr.Audio(sources=['microphone', 'upload'], type='filepath', label='Consulta por voz (solo LIVE)')
            allow_audio = gr.Checkbox(value=False,
                                      label='Autorizo procesar ESTE audio ficticio mediante un proveedor externo')
            audio_send = gr.Button('Procesar audio')
        audio_out = gr.Audio(label='Respuesta de voz', autoplay=False)
        transcript = gr.Textbox(label='Última transcripción (no se persiste)', interactive=False)
        metrics = gr.JSON(label='Trazabilidad de la interacción')
        errors = gr.Textbox(label='Estado del audio / advertencias', interactive=False)
        reset = gr.Button('Nueva conversación')
        submit.click(send_text, inputs=[txt, state, chat, generate_audio],
                     outputs=[chat, state, audio_out, metrics, errors, txt])
        txt.submit(send_text, inputs=[txt, state, chat, generate_audio],
                   outputs=[chat, state, audio_out, metrics, errors, txt])
        audio_send.click(send_audio, inputs=[audio_in, allow_audio, state, chat, generate_audio],
                         outputs=[chat, state, audio_out, metrics, errors, transcript])
        reset.click(lambda: ([], Session(), None, {}, '', ''),
                    outputs=[chat, state, audio_out, metrics, errors, transcript])
        gr.Examples(examples=[['¿Cuáles son los requisitos de una tarjeta?'], ['¿Qué tasa tiene el préstamo personal?'],
                              ['Cotiza 300000 pesos a 36 meses'], ['Mi tarjeta fue robada'], ['Quiero que me llamen']],
                    inputs=txt)
    with gr.Tab('Campaña saliente: simulación'):
        gr.Markdown('La herramienta solo valida consentimiento, DNC y horario ficticio. **No efectúa llamadas.**')
        out_consent = gr.Checkbox(label='El contacto sintético aceptó comunicaciones comerciales')
        out_dnc = gr.Checkbox(label='Está registrado en Do-Not-Call (DNC)')
        hour = gr.Slider(minimum=0, maximum=23, value=14, step=1, label='Hora local simulada')
        status = gr.Textbox(label='Resultado de la validación')
        gr.Button('Validar e iniciar simulación').click(outbound, [out_consent, out_dnc, hour], status)
    with gr.Tab('Llamada REAL · piloto restringido'):
        gr.Markdown(
            '**Telefonía real con Twilio.** Solo teléfonos dominicanos (+1809/+1829/+1849)\n        **incluidos previamente** en `TWILIO_TEST_NUMBERS` y con consentimiento verificable.\n        No graba audio en este servidor. Se transfiere audio a Deepgram y Azure y texto a Claude.\n        **La conversación es por turnos** (sin interrupciones simultáneas); no es un contact center real.\n        **No exponga esta interfaz sin autenticación.**')
        call_id = gr.State('')
        target = gr.Textbox(label='Número dominicano E.164', placeholder='+1809XXXXXXX', type='text')
        confirm_optin = gr.Checkbox(value=False,
                                    label='Confirmo que tengo consentimiento previo verificable del titular para esta llamada de prueba')
        confirm_allowed = gr.Checkbox(value=False,
                                      label='Confirmo que es un destinatario incluido en mi lista permitida y que no pidió exclusión')
        with gr.Row():
            dial = gr.Button('Iniciar UNA llamada real', variant='stop')
            refresh_call = gr.Button('Consultar estado')
            hangup = gr.Button('Finalizar llamada')
        call_state = gr.Textbox(label='Estado de Twilio', interactive=False)
        dial.click(call_real, inputs=[target, confirm_optin, confirm_allowed], outputs=[call_state, call_id])
        refresh_call.click(call_refresh, inputs=call_id, outputs=call_state)
        hangup.click(call_stop, inputs=call_id, outputs=call_state)
        gr.Markdown('**Lista de exclusión (DNC):** registre aquí una petición de no contacto, incluso antes de llamar.')
        do_not_call_auth = gr.Checkbox(value=False, label='Confirmo que el titular solicitó no recibir más llamadas')
        do_not_call_btn = gr.Button('Registrar exclusión permanente para este número')
        do_not_call_btn.click(phone_block, inputs=[target, do_not_call_auth], outputs=call_state)
    with gr.Tab('Datos de prueba'):
        gr.Markdown(
            'Los registros solo contienen IDs y etiquetas sintéticas en SQLite. No guardamos conversaciones ni audio en SQLite.')
        output = gr.JSON(label='Conteo de operaciones de prueba')
        gr.Button('Actualizar conteos').click(counts, outputs=output)

if __name__ == '__main__':
    app.launch(server_name=os.getenv('GRADIO_SERVER_NAME', '127.0.0.1'), server_port=int(os.getenv('PORT', '7860')),
               show_error=False)
