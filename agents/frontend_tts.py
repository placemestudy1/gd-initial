import json
from livekit.agents import tts, utils
from livekit.agents.tts import TTSCapabilities

class FrontendTTS(tts.TTS):
    """
    A 'Dummy' TTS plugin that doesn't actually synthesize audio.
    Instead, it publishes the text transcript over the LiveKit data channel
    so the frontend can synthesize it using the browser's Web Speech API.
    It emits a tiny silent audio frame so the AgentSession pipeline continues.
    """
    def __init__(self, room, speaker_name: str, role: str):
        super().__init__(
            capabilities=TTSCapabilities(streaming=False),
            sample_rate=48000,
            num_channels=1
        )
        self.room = room
        self.speaker_name = speaker_name
        self.role = role

    def synthesize(
        self,
        text: str,
        *,
        conn_options=None,
    ) -> tts.ChunkedStream:
        return FrontendChunkedStream(self, text, conn_options=conn_options)


class FrontendChunkedStream(tts.ChunkedStream):
    def __init__(self, tts_instance: FrontendTTS, input_text: str, conn_options=None):
        super().__init__(tts=tts_instance, input_text=input_text, conn_options=conn_options)
        self._tts: FrontendTTS = tts_instance

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        if self._input_text and self._input_text.strip():
            # Send the text to the frontend over the data channel
            payload = json.dumps({
                "event": "transcript",
                "speaker": self._tts.speaker_name,
                "text": self._input_text,
                "role": self._tts.role,
                "speak": True
            })
            try:
                if self._tts.room and self._tts.room.local_participant:
                    await self._tts.room.local_participant.publish_data(payload.encode(), reliable=True)
            except Exception as e:
                import logging
                logging.warning(f"Could not publish frontend TTS data: {e}")

        # Emit a single tiny silent PCM frame so LiveKit is happy
        # 48000 Hz, 1 channel, 16-bit PCM => 2 bytes per sample.
        # We'll emit 10ms of silence = 480 samples = 960 bytes.
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=48000,
            num_channels=1,
            mime_type="audio/pcm"
        )
        
        # 10ms of silence
        output_emitter.push(b'\x00' * 960)
        output_emitter.flush()

        if self._input_text and self._input_text.strip():
            # Estimate how long the text will take to speak and sleep for that duration.
            # Average reading speed is ~150 words per minute (2.5 words per sec).
            # We also add a small buffer (e.g. 1.0s) to allow for TTS initialization and pauses.
            word_count = len(self._input_text.split())
            estimated_duration = (word_count / 2.5) + 1.0
            import asyncio
            await asyncio.sleep(estimated_duration)
