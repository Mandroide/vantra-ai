"""Interfaz Gradio; ejecutar: python app.py"""
import os
import time

import gradio as gr

from src.agent import respond, Session
from src.config import env
from src.speech import transcribe_deepgram, speak_azure, speak_local
from src.storage import counts
from src.tools import check_contact_policy

LIVE=env('VANTRA_MODE','DEMO').upper()=='LIVE'

def render(text, state, history, synth_voice=False):
    state=state or Session();history=history or []
    start=time.perf_counter()
    ans,state=respond(text,state,mode='LIVE' if LIVE else 'DEMO')
    history=history+[{'role':'user','content':text},{'role':'assistant','content':ans.text}]
    audio=None;voice_error=''
    tts_ms=None
    if synth_voice:
        try:
            ts=time.perf_counter()
            audio=speak_azure(ans.text) if LIVE else speak_local(ans.text)
            tts_ms=round((time.perf_counter()-ts)*1000,2)
        except Exception as ex: voice_error='\nTTS no disponible: '+type(ex).__name__
    meta={'modo':ans.mode,'estado':ans.status,'herramientas':[e['name'] for e in ans.tools],
          'latencia_agente_ms':ans.elapsed_ms,'latencia_total_ms':round((time.perf_counter()-start)*1000,2),
          'tokens_entrada_LLM':ans.llm_input_tokens,'tokens_salida_LLM':ans.llm_output_tokens,
          'tts_ms':tts_ms,'costo_api_real_usd':None,
          'advertencia':'Costo API desconocido hasta revisar facturación; no representa desempeño de un banco real'}
    return history,state,audio,meta,voice_error

def send_text(text,state,history,voice):
    if not (text or '').strip(): return history,state,None,{},'',text
    h,s,a,m,e=render(text,state,history,voice)
    return h,s,a,m,e,''

def send_audio(audio,authorized,state,history,voice):
    if not authorized:
        return history,state,None,{'error':'No se otorgó consentimiento para procesar audio'},'Marque el consentimiento y utilice solo voz ficticia.', ''
    if not LIVE:
        return history,state,None,{'modo':'DEMO','STT':'no disponible sin proveedor'},'El modo DEMO admite texto. Configure LIVE y DEEPGRAM_API_KEY para grabar voz.', ''
    if not audio:
        return history,state,None,{'error':'Sin audio'},'Grabe audio antes de enviarlo.', ''
    try:
        t=time.perf_counter();transcript,duration=transcribe_deepgram(audio)
        stt_ms=round((time.perf_counter()-t)*1000,2)
        if not transcript: raise ValueError('No se reconocieron palabras')
        h,s,a,m,e=render(transcript,state,history,voice)
        m['stt_ms']=stt_ms
        m['audio_entrada_seg']=duration
        return h,s,a,m,e,transcript
    except Exception as ex:
        return history,state,None,{'error':'Problema de STT','tipo':type(ex).__name__},'No fue posible procesar el audio. Revise la configuración.', ''

def outbound(consent,dnc,hour):
    rule=check_contact_policy(bool(consent),bool(dnc),int(hour))
    if not rule['allowed']:
        return f"⛔ Simulación bloqueada: {rule['reason']}. No se inició ninguna llamada."
    return 'SIMULACIÓN HABILITADA: Buenos días, soy Vantra AI de Banco Demo ficticio. ¿Desea conocer nuestros productos? (No se hizo ninguna llamada.)'

with gr.Blocks(title='Vantra AI | MVP académico') as app:
    gr.Markdown('# Vantra AI · Agente bancario de voz (MVP)\n**Banco Demo ficticio** | Datos sintéticos | Sin servicio bancario ni telefonía real')
    gr.Markdown('**Modo:** '+('LIVE (requiere claves API)' if LIVE else 'DEMO reproducible (texto)')+' · **Advertencia:** nunca introduzca datos personales, financieros o grabaciones reales.')
    state=gr.State(Session())
    with gr.Tab('Atención entrante'):
        chat=gr.Chatbot(label='Conversación',height=370)
        with gr.Row():
            txt=gr.Textbox(label='Consulta de texto',placeholder='Ej.: Cotiza 300000 pesos a 36 meses',scale=5)
            submit=gr.Button('Enviar',variant='primary',scale=1)
        generate_audio=gr.Checkbox(value=False,label='Generar audio de respuesta (Azure en LIVE; espeak opcional en DEMO)')
        with gr.Row():
            audio_in=gr.Audio(sources=['microphone','upload'],type='filepath',label='Consulta por voz (solo LIVE)')
            allow_audio=gr.Checkbox(value=False,label='Autorizo procesar ESTE audio ficticio mediante un proveedor externo')
            audio_send=gr.Button('Procesar audio')
        audio_out=gr.Audio(label='Respuesta de voz',autoplay=False)
        transcript=gr.Textbox(label='Última transcripción (no se persiste)',interactive=False)
        metrics=gr.JSON(label='Trazabilidad de la interacción')
        errors=gr.Textbox(label='Estado del audio / advertencias',interactive=False)
        reset=gr.Button('Nueva conversación')
        submit.click(send_text,inputs=[txt,state,chat,generate_audio],outputs=[chat,state,audio_out,metrics,errors,txt])
        txt.submit(send_text,inputs=[txt,state,chat,generate_audio],outputs=[chat,state,audio_out,metrics,errors,txt])
        audio_send.click(send_audio,inputs=[audio_in,allow_audio,state,chat,generate_audio],outputs=[chat,state,audio_out,metrics,errors,transcript])
        reset.click(lambda:([],Session(),None,{},'', ''),outputs=[chat,state,audio_out,metrics,errors,transcript])
        gr.Examples(examples=[['¿Cuáles son los requisitos de una tarjeta?'],['¿Qué tasa tiene el préstamo personal?'],['Cotiza 300000 pesos a 36 meses'],['Mi tarjeta fue robada'],['Quiero que me llamen']],inputs=txt)
    with gr.Tab('Campaña saliente: simulación'):
        gr.Markdown('La herramienta solo valida consentimiento, DNC y horario ficticio. **No efectúa llamadas.**')
        out_consent=gr.Checkbox(label='El contacto sintético aceptó comunicaciones comerciales')
        out_dnc=gr.Checkbox(label='Está registrado en Do-Not-Call (DNC)')
        hour=gr.Slider(minimum=0,maximum=23,value=14,step=1,label='Hora local simulada')
        status=gr.Textbox(label='Resultado de la validación')
        gr.Button('Validar e iniciar simulación').click(outbound,[out_consent,out_dnc,hour],status)
    with gr.Tab('Datos de prueba'):
        gr.Markdown('Los registros solo contienen IDs y etiquetas sintéticas en SQLite. No guardamos conversaciones ni audio en SQLite.')
        output=gr.JSON(label='Conteo de operaciones de prueba')
        gr.Button('Actualizar conteos').click(counts,outputs=output)

if __name__=='__main__':
    app.launch(server_name=os.getenv('GRADIO_SERVER_NAME','127.0.0.1'),server_port=int(os.getenv('PORT','7860')),show_error=False)
