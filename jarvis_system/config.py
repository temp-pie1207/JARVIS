import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    load_dotenv(override=False)

class JarvisConfig:
    # OpenAI / LLM Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

    # ElevenLabs Voice & Conversational AI Settings
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_3101m6rqhcqsf7h9mcg1rkf25g0q")
    # Default Voice ID: Bunty or Adam ("7b9mYhmnp0y2qSH1FnBL" or "JBFqnCBsd6RMkjVDRZzb")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "7b9mYhmnp0y2qSH1FnBL")
    ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

    # Local audio playback via host speakers (using mpv / paplay)
    PLAY_AUDIO_LOCALLY = os.getenv("PLAY_AUDIO_LOCALLY", "true").lower() in ("true", "1", "yes")

    # System Access Settings
    SYSTEM_ACCESS_ENABLED = os.getenv("SYSTEM_ACCESS_ENABLED", "true").lower() in ("true", "1", "yes")
    DEFAULT_WORKING_DIR = os.getenv("DEFAULT_WORKING_DIR", str(Path.home()))

    # Public static directory for generated audio/files
    PUBLIC_AUDIOS_DIR = BASE_DIR / "hugginggpt" / "server" / "public" / "audios"

    @classmethod
    def reload(cls):
        if ENV_PATH.exists():
            load_dotenv(ENV_PATH, override=True)
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        cls.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        cls.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)
        cls.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        cls.ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_3101m6rqhcqsf7h9mcg1rkf25g0q")
        cls.ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "7b9mYhmnp0y2qSH1FnBL")
        cls.ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
        cls.PLAY_AUDIO_LOCALLY = os.getenv("PLAY_AUDIO_LOCALLY", "true").lower() in ("true", "1", "yes")
        cls.SYSTEM_ACCESS_ENABLED = os.getenv("SYSTEM_ACCESS_ENABLED", "true").lower() in ("true", "1", "yes")
