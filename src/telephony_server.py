"""FastAPI para Twilio Media Streams bidireccional + Deepgram live + Claude + Azure TTS.

Lanzar separado de Gradio: uvicorn src.telephony_server:app --port 8000
NO es un marcador masivo: permite únicamente las llamadas iniciadas manualmente desde
la interfaz local, a teléfonos autorizados mediante TWILIO_TEST_NUMBERS.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import hashlib
import re
import time
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import websockets

from src.agent import Session, respond, normalize
from src.config import env, key
from src.telephony import (CALL_SID, get_call, get_call_by_sid, public_url, claim_stream, mark_do_not_call,
                           stop_test_call, twilio_valid_signature, update_call)

log = logging.getLogger('vantra.telephony')
app = FastAPI(title='Vantra AI · Twilio Webhook (piloto)', docs_url=None, redoc_url=None,
              openapi_url=None)
GOODBYE = ('adios', 'hasta luego', 'cuelga', 'termina la llamada', 'terminar llamada',
           'no gracias', 'no, gracias')
OPT_OUT = ('no me llame', 'no me llamen', 'no me llames', 'no vuelva a llamar',
           'no me vuelvas a llamar', 'no quiero llamadas',
           'no me contacte', 'deje de llamar', 'quiten mi numero', 'borrar mi numero')


@app.get('/healthz')
async def health():
    return {'ok': True, 'telephony_enabled': env('TWILIO_CALLS_ENABLED', 'false') == 'true'}


@app.get('/readyz')
async def ready():
    # No autentica APIs externas: comprueba configuración esencial, sin exponer claves.
    from urllib.parse import urlparse
    enabled = env('TWILIO_CALLS_ENABLED', 'false').lower() == 'true'
    base = env('TWILIO_PUBLIC_BASE_URL', '')
    parsed = urlparse(base)
    configured = (parsed.scheme == 'https' and bool(parsed.hostname)
                  and all(bool(env(name, '')) for name in (
                      'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER',
                      'DEEPGRAM_API_KEY', 'ANTHROPIC_API_KEY', 'AZURE_SPEECH_KEY',
                      'AZURE_SPEECH_REGION')))
    # No devuelve secretos; Caddy no lo publica, pero un túnel puede enrutarlo.
    return {'server_ready': True, 'twilio_configured': configured if enabled else False,
            'twilio_enabled': enabled}


@app.post('/twilio/status')
async def status_callback(request: Request):
    # Usar URL pública configurada, NO Host manipulable ni X-Forwarded-Host del cliente.
    params = {str(k): str(v) for k, v in (await request.form()).items()}
    signature = request.headers.get('X-Twilio-Signature', '')
    # Twilio firma también la query completa. Reconstruir con base canónica
    # para no depender de cabeceras Host/X-Forwarded manipulables por el cliente.
    query = request.scope.get('query_string', b'').decode('ascii')
    callback_url = public_url('/twilio/status') + ('?' + query if query else '')
    if not twilio_valid_signature(callback_url, signature, params):
        raise HTTPException(status_code=403, detail='Firma de Twilio inválida')
    sid = params.get('CallSid', '')
    if not CALL_SID.fullmatch(sid):
        raise HTTPException(status_code=400, detail='Call SID inválido')
    call_id = request.query_params.get('call_id', '')
    # Este identificador viaja en el callback para cubrir la carrera donde
    # Twilio notifica antes de que POST /Calls devuelva el SID a Gradio.
    info = get_call(call_id) if re.fullmatch(r'[0-9a-f]{32}', call_id) else None
    if info is None and not call_id:  # Compatibilidad con llamadas antiguas.
        info = get_call_by_sid(sid)
    if info:
        if info['call_sid'] and info['call_sid'] != sid:
            raise HTTPException(status_code=409, detail='Call SID no corresponde a llamada')
        state = params.get('CallStatus', '')
        if state in {'queued', 'initiated', 'ringing', 'in-progress', 'completed',
                     'busy', 'failed', 'no-answer', 'canceled'}:
            update_call(info['id'], state, sid)
            log.info('twilio_status event=%s call_ref=%s', state,
                     hashlib.sha256(sid.encode()).hexdigest()[:12])
    else:
        log.warning('twilio_status_unmatched call_ref=%s',
                    hashlib.sha256(sid.encode()).hexdigest()[:12])
    return JSONResponse({'ok': True})


def _signature_websocket(signature: str) -> bool:
    ws_url = public_url('/twilio/media').replace('https://', 'wss://', 1)
    return any(twilio_valid_signature(candidate, signature)
               for candidate in (ws_url, ws_url + '/'))


def azure_mulaw_8k(text: str) -> bytes:
    """Azure RAW mu-law 8kHz/8-bit/mono: SIN encabezado WAV, listo para Twilio."""
    import azure.cognitiveservices.speech as speechsdk
    speech = speechsdk.SpeechConfig(subscription=key('AZURE_SPEECH_KEY'),
                                    region=key('AZURE_SPEECH_REGION'))
    speech.speech_synthesis_voice_name = env('AZURE_SPEECH_VOICE', 'es-DO-RamonaNeural')
    speech.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz8BitMonoMULaw)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech, audio_config=None)
    result = synthesizer.speak_text_async(text[:650]).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted or not result.audio_data:
        raise RuntimeError('Azure no devolvió audio RAW mu-law válido')
    return bytes(result.audio_data)


def deepgram_url() -> str:
    options = {
        'model': env('DEEPGRAM_MODEL', 'nova-3'), 'language': 'es',
        'encoding': 'mulaw', 'sample_rate': '8000', 'channels': '1',
        'endpointing': '500', 'interim_results': 'true', 'punctuate': 'true',
        'smart_format': 'true',
    }
    return 'wss://api.deepgram.com/v1/listen?' + urlencode(options)


class CallBridge:
    def __init__(self, websocket: WebSocket, call_id: str, call_sid: str, stream_sid: str):
        self.websocket, self.call_id = websocket, call_id
        self.call_sid, self.stream_sid = call_sid, stream_sid
        self.session = Session()
        self.speaking = False
        self.processing = False
        self.hang_after_mark = False
        self.stop_requested = False
        self.pending_parts: list[str] = []
        self.worker: asyncio.Task | None = None
        self.dg = None
        self.utterances = 0
        self.call_ref = hashlib.sha256(call_sid.encode()).hexdigest()[:12]

    async def _send_audio(self, text: str, *, goodbye=False):
        self.speaking = True
        started = time.perf_counter()
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(azure_mulaw_8k, text), timeout=25)
            log.info('voice_tts call_ref=%s duration_ms=%.1f bytes=%d',
                     self.call_ref, (time.perf_counter()-started)*1000, len(raw))
            # Twilio acepta cualquier tamaño, enviamos bloques pequeños para facilitar su búfer.
            for i in range(0, len(raw), 1600):
                await self.websocket.send_json({
                    'event': 'media', 'streamSid': self.stream_sid,
                    'media': {'payload': base64.b64encode(raw[i:i+1600]).decode('ascii')}})
            self.hang_after_mark = goodbye
            await self.websocket.send_json({
                'event': 'mark', 'streamSid': self.stream_sid,
                'mark': {'name': 'voice_end'}})
        except Exception:
            self.speaking = False
            raise

    async def _terminate(self):
        if self.stop_requested:
            return
        self.stop_requested = True
        try:
            await asyncio.to_thread(stop_test_call, self.call_id)
        except Exception:
            log.warning('No se pudo actualizar el fin de la llamada', exc_info=False)
        try:
            await self.websocket.close(code=1000)
        except Exception:
            pass

    async def greet(self):
        await self._send_audio(
            'Hola. Soy Vantra, una inteligencia artificial de Banco Demo, un banco ficticio. '
            'Esta es una llamada de prueba que usted autorizó. El audio se procesa en tiempo '
            'real por servicios externos; no lo grabamos en nuestro servidor. '
            'Si desea finalizar o dejar de recibir llamadas, dígalo. ¿Desea continuar?')

    async def handle_transcription(self, phrase: str):
        if self.processing or self.speaking or self.stop_requested:
            return
        text = phrase.strip()[:900]
        if not text:
            return
        self.processing = True
        try:
            utterance = normalize(text)
            if any(x in utterance for x in OPT_OUT):
                await asyncio.to_thread(mark_do_not_call, self.call_id)
                await self._send_audio('Entendido. Su número queda excluido de futuras pruebas. Gracias.', goodbye=True)
                return
            if any(x in utterance for x in GOODBYE):
                await self._send_audio('Gracias por su tiempo. Finalizamos esta llamada de prueba.', goodbye=True)
                return
            self.utterances += 1
            if self.utterances > 12:
                await self._send_audio('Llegamos al límite de intervenciones de la prueba. Gracias.', goodbye=True)
                return
            started = time.perf_counter()
            result, self.session = await asyncio.wait_for(
                asyncio.to_thread(respond, text, self.session, 'LIVE'), timeout=35)
            log.info('voice_agent call_ref=%s duration_ms=%.1f outcome=%s',
                     self.call_ref, (time.perf_counter()-started)*1000,
                     'error' if result.status == 'PROVIDER_ERROR' else 'ok')
            if result.status == 'PROVIDER_ERROR':
                await self._send_audio('El asistente no está disponible ahora. Finalizamos la llamada.', goodbye=True)
            else:
                await self._send_audio(result.text)
        except Exception:
            log.warning('Fallo procesando un turno de voz: %s', self.call_id, exc_info=False)
            try:
                await self._send_audio('Disculpe, ocurrió un error técnico. Finalizamos la prueba.', goodbye=True)
            except Exception:
                await self._terminate()
        finally:
            self.processing = False

    async def deepgram_keepalive(self):
        # Deepgram puede cerrar la conexión si Twilio no envía audio durante TTS.
        while not self.stop_requested:
            await asyncio.sleep(6)
            try:
                await self.dg.send(json.dumps({'type': 'KeepAlive'}))
            except Exception:
                return

    async def recv_deepgram(self):
        async for packet in self.dg:
            if self.stop_requested:
                break
            if not isinstance(packet, str):
                continue
            try:
                data = json.loads(packet)
            except ValueError:
                continue
            if data.get('type') != 'Results':
                continue
            if self.speaking or self.processing:
                self.pending_parts.clear()
                continue
            alternatives = data.get('channel', {}).get('alternatives', [])
            part = (alternatives[0].get('transcript') or '').strip() if alternatives else ''
            if data.get('is_final') and part:
                self.pending_parts.append(part)
            if data.get('speech_final'):
                complete = ' '.join(self.pending_parts)
                self.pending_parts.clear()
                if complete:
                    if self.worker and not self.worker.done():
                        continue
                    self.worker = asyncio.create_task(self.handle_transcription(complete))

    async def run(self):
        # Deepgram WS recibe exactamente bytes raw que envía Twilio (mulaw/8000).
        async with websockets.connect(
            deepgram_url(), additional_headers={'Authorization': f'Token {key("DEEPGRAM_API_KEY")}'},
            open_timeout=12, max_size=1024 * 1024, ping_interval=20) as dg:
            self.dg = dg
            listener = asyncio.create_task(self.recv_deepgram())
            keepalive = asyncio.create_task(self.deepgram_keepalive())
            try:
                await self.greet()
                while not self.stop_requested:
                    try:
                        message = await asyncio.wait_for(self.websocket.receive_json(), timeout=190)
                    except (asyncio.TimeoutError, WebSocketDisconnect):
                        break
                    event = message.get('event')
                    if event == 'stop':
                        break
                    if event == 'mark':
                        self.speaking = False
                        if self.hang_after_mark:
                            await self._terminate()
                            break
                    if event == 'media' and not self.speaking and not self.processing:
                        payload = message.get('media', {}).get('payload', '')
                        if isinstance(payload, str) and len(payload) < 32000:
                            try:
                                chunk = base64.b64decode(payload, validate=True)
                                if chunk:
                                    await dg.send(chunk)
                            except Exception:
                                # Resistente a paquetes malformados; solo remitentes autenticados.
                                pass
                    if listener.done():
                        log.warning('Deepgram perdió conexión durante llamada', exc_info=False)
                        break
            finally:
                listener.cancel()
                keepalive.cancel()
                await asyncio.gather(listener, keepalive, return_exceptions=True)
                if self.worker:
                    self.worker.cancel()
                    await asyncio.gather(self.worker, return_exceptions=True)
                try:
                    await dg.send(json.dumps({'type': 'CloseStream'}))
                except Exception:
                    pass
                if not self.stop_requested:
                    await self._terminate()


@app.websocket('/twilio/media')
async def media_stream(ws: WebSocket):
    if env('TWILIO_CALLS_ENABLED', 'false').lower() != 'true':
        await ws.close(code=1008)
        return
    if not _signature_websocket(ws.headers.get('X-Twilio-Signature', '')):
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        # Twilio envía primero 'connected', luego 'start'. No aceptar sin nonce válido.
        first = await asyncio.wait_for(ws.receive_json(), timeout=12)
        if first.get('event') != 'connected':
            await ws.close(code=1008)
            return
        start = await asyncio.wait_for(ws.receive_json(), timeout=12)
        if start.get('event') != 'start':
            await ws.close(code=1008)
            return
        meta = start.get('start', {})
        par = meta.get('customParameters', {})
        call_id, nonce, sid = par.get('call_id', ''), par.get('nonce', ''), meta.get('callSid', '')
        stream_sid = meta.get('streamSid', '')
        if not stream_sid or not claim_stream(call_id, nonce, sid):
            await ws.close(code=1008)
            return
        bridge = CallBridge(ws, call_id, sid, stream_sid)
        log.info('voice_stream_started call_ref=%s', bridge.call_ref)
        try:
            await bridge.run()
        finally:
            log.info('voice_stream_ended call_ref=%s turns=%d',
                     bridge.call_ref, bridge.utterances)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    except Exception:
        log.warning('La sesión telefónica terminó con error (sin registrar audio)', exc_info=False)
        try:
            await ws.close(code=1011)
        except Exception:
            pass
