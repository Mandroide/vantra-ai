"""STT Deepgram y TTS Azure, cargados solo cuando se requieren."""
import mimetypes
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import requests

from src.config import env, key


def audio_seconds(path):
    try:
        with wave.open(str(path),'rb') as wav: return wav.getnframes()/float(wav.getframerate())
    except Exception: return None

def transcribe_deepgram(path):
    """Archivo grabado por el usuario; nunca se almacena la transcripción en disco."""
    if not path or not Path(path).is_file(): raise ValueError('No se recibió un audio válido')
    media=mimetypes.guess_type(str(path))[0] or 'audio/wav'
    with open(path,'rb') as fh:
        response=requests.post('https://api.deepgram.com/v1/listen',params={'model':env('DEEPGRAM_MODEL','nova-3'),'language':'es','smart_format':'true'},
                               headers={'Authorization':'Token '+key('DEEPGRAM_API_KEY'),'Content-Type':media},data=fh,timeout=50)
    response.raise_for_status()
    data=response.json()
    alt=data['results']['channels'][0]['alternatives'][0]
    return alt.get('transcript',''),float(data.get('metadata',{}).get('duration',audio_seconds(path) or 0))

def speak_azure(text):
    import azure.cognitiveservices.speech as speechsdk
    cfg=speechsdk.SpeechConfig(subscription=key('AZURE_SPEECH_KEY'),region=key('AZURE_SPEECH_REGION'))
    cfg.speech_synthesis_voice_name=env('AZURE_SPEECH_VOICE','es-DO-RamonaNeural')
    cfg.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
    temp=tempfile.NamedTemporaryFile(suffix='.wav',delete=False);temp.close()
    synth=speechsdk.SpeechSynthesizer(speech_config=cfg,audio_config=speechsdk.audio.AudioOutputConfig(filename=temp.name))
    res=synth.speak_text_async(text[:1400]).get()
    if res.reason!=speechsdk.ResultReason.SynthesizingAudioCompleted:
        os.unlink(temp.name)
        raise RuntimeError('Azure Speech no logró generar audio; revise región, clave y voz')
    return temp.name

def speak_local(text):
    """TTS opcional de sistema Linux; voz aproximada, NO es acento dominicano."""
    binary=shutil.which('espeak-ng') or shutil.which('espeak')
    if not binary: raise RuntimeError('Instale espeak-ng para TTS local o configure Azure')
    f=tempfile.NamedTemporaryFile(suffix='.wav',delete=False);f.close()
    subprocess.run([binary,'-v','es','-s','155','-w',f.name,text[:1400]],check=True,timeout=25,capture_output=True)
    return f.name
