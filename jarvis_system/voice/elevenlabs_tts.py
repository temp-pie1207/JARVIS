import os
import uuid
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from jarvis_system.config import JarvisConfig

logger = logging.getLogger("JARVIS.Voice")

class ElevenLabsVoiceService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        play_locally: Optional[bool] = None
    ):
        self.api_key = api_key or JarvisConfig.ELEVENLABS_API_KEY
        self.voice_id = voice_id or JarvisConfig.ELEVENLABS_VOICE_ID
        self.model_id = model_id or JarvisConfig.ELEVENLABS_MODEL_ID
        self.play_locally = play_locally if play_locally is not None else JarvisConfig.PLAY_AUDIO_LOCALLY
        self.client = None

        if self.api_key and self.api_key != "your_elevenlabs_api_key_here":
            try:
                from elevenlabs.client import ElevenLabs
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs client: {e}")

    def is_configured(self) -> bool:
        return self.client is not None

    def list_voices(self) -> List[Dict[str, Any]]:
        """Fetch available voices for the connected ElevenLabs account."""
        if not self.is_configured():
            return []
        try:
            voices_response = self.client.voices.get_all()
            result = []
            for v in voices_response.voices:
                result.append({
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "category": getattr(v, "category", "premade"),
                    "description": getattr(v, "description", "")
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching ElevenLabs voices: {e}")
            return []

    def _play_audio_on_host(self, audio_path: str):
        """Play audio file out loud on host machine speakers using mpv, paplay, or ffplay."""
        def _worker():
            try:
                # Prefer mpv if available
                if subprocess.run(["which", "mpv"], capture_output=True).returncode == 0:
                    subprocess.run(["mpv", "--no-video", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif subprocess.run(["which", "paplay"], capture_output=True).returncode == 0:
                    subprocess.run(["paplay", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif subprocess.run(["which", "ffplay"], capture_output=True).returncode == 0:
                    subprocess.run(["ffplay", "-nodisp", "-autoexit", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.warning(f"Could not play audio locally on host speakers: {e}")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        play_locally: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes text into high-quality speech using ElevenLabs.
        Saves output as mp3 to public audio directory and optionally plays on host speakers.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "ElevenLabs API key is not configured.",
                "audio_url": None,
                "file_path": None
            }

        target_voice_id = voice_id or self.voice_id
        should_play = play_locally if play_locally is not None else self.play_locally

        try:
            # Ensure target directory exists
            output_dir = JarvisConfig.PUBLIC_AUDIOS_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            file_id = f"jarvis_{uuid.uuid4().hex[:10]}.mp3"
            target_path = output_dir / file_id

            # Call ElevenLabs text-to-speech convert
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=target_voice_id,
                model_id=self.model_id
            )

            with open(target_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)

            public_url = f"/audios/{file_id}"

            # If local playback enabled, play on computer speakers immediately
            if should_play:
                self._play_audio_on_host(str(target_path))

            return {
                "success": True,
                "audio_url": public_url,
                "file_path": str(target_path),
                "voice_id": target_voice_id,
                "played_locally": should_play
            }

        except Exception as e:
            if "missing_permissions" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.info("Speaking with local TTS engine (spd-say)...")
            else:
                logger.error(f"Speech synthesis error: {e}")
            if should_play and subprocess.run(["which", "spd-say"], capture_output=True).returncode == 0:
                try:
                    clean = text.replace('"', '').replace("'", "")[:250]
                    subprocess.Popen(["spd-say", "-r", "10", clean], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            return {
                "success": False,
                "error": str(e),
                "audio_url": None,
                "file_path": None
            }
