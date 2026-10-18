"""Mocks de conectores: comprueban contrato de código, NO servicios externos reales."""
import sys
import types
import wave
from types import SimpleNamespace


def test_deepgram_payload_mock(tmp_path,monkeypatch):
    from src.speech import transcribe_deepgram
    dest=tmp_path/'voz.wav'
    with wave.open(str(dest),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x00\x00'*160)
    calls=[]
    class Resp:
        def raise_for_status(self): pass
        def json(self):return {'results':{'channels':[{'alternatives':[{'transcript':'hola banco demo'}]}]},'metadata':{'duration':0.01}}
    def fake_post(*args,**kwargs):
        calls.append((args,kwargs));return Resp()
    monkeypatch.setenv('DEEPGRAM_API_KEY','CLAVE_DE_PRUEBA_NO_REAL')
    monkeypatch.setattr('src.speech.requests.post',fake_post)
    transcript,duration=transcribe_deepgram(dest)
    assert transcript=='hola banco demo' and duration==0.01
    assert calls[0][0][0].endswith('/v1/listen')
    assert calls[0][1]['headers']['Content-Type']=='audio/x-wav' or calls[0][1]['headers']['Content-Type']=='audio/wav'

def test_claude_tool_use_mock(monkeypatch):
    """No se hace red ni se prueba la disponibilidad del modelo remoto."""
    class Client:
        def __init__(self,**kwargs):self.calls=0
        @property
        def messages(self):return self
        def create(self,**kwargs):
            self.calls+=1
            if self.calls==1:
                blocks=[SimpleNamespace(type='tool_use',name='get_product_info',input={'product':'tarjeta'},id='t1')]
            else: blocks=[SimpleNamespace(type='text',text='El catálogo es ficticio.')]
            return SimpleNamespace(content=blocks,usage=SimpleNamespace(input_tokens=3,output_tokens=4))
    mod=types.ModuleType('anthropic');mod.Anthropic=Client
    monkeypatch.setitem(sys.modules,'anthropic',mod)
    monkeypatch.setenv('ANTHROPIC_API_KEY','CLAVE_DE_PRUEBA_NO_REAL')
    from src.agent import respond,Session
    answer,_=respond('Háblame del servicio en general',Session(),mode='LIVE')
    assert answer.text=='El catálogo es ficticio.'
    assert answer.tools[0]['name']=='get_product_info'
    assert answer.llm_input_tokens==6 and answer.llm_output_tokens==8

def test_gradio_blocks_smoke_without_browser():
    from app import app,send_text,send_audio
    from src.agent import Session
    assert app is not None
    history,state,audio,metrics,err,cleared=send_text('Cotiza 300000 pesos a 36 meses',Session(),[],False)
    assert 'Cuota estimada' in history[-1]['content']
    assert 'calculate_loan' in metrics['herramientas']
    assert cleared==''
    before,state,audio,metrics,err,transcript=send_audio(None,False,Session(),[],False)
    assert 'No se otorgó consentimiento' in metrics['error']
