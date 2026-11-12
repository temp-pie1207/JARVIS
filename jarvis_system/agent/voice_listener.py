#!/usr/bin/env python3
"""
JARVIS Voice Commander — Hands-Free Voice Control for Linux
Continuously listens to your microphone, transcribes speech using faster-whisper,
executes system commands with full host access, and speaks responses aloud.
"""

import sys
import time
import queue
import logging
import numpy as np
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import sounddevice as sd
from faster_whisper import WhisperModel
from jarvis_system.agent.jarvis_agent import JarvisAgent
from jarvis_system.config import JarvisConfig

logger = logging.getLogger("JARVIS.VoiceCommand")

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024  # ~64ms per block
ENERGY_THRESHOLD = 0.015  # Voice activity threshold (RMS)
SILENCE_DURATION = 1.2  # Seconds of silence to trigger end of utterance
MIN_SPEECH_DURATION = 0.6  # Minimum speech duration to discard noise clicks

def run_voice_commander(model_size: str = "tiny.en", wake_word: str = ""):
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print("\033[1;36m  🎙️  JARVIS Hands-Free Voice Control Active\033[0m")
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print("Loading local whisper speech recognition model...")

    stt_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    agent = JarvisAgent(voice_enabled=True)

    print("\033[1;32m✓ System ready! Speak naturally into your microphone.\033[0m")
    print("Examples:")
    print("  • 'Jarvis, open WhatsApp'")
    print("  • 'Jarvis, check my system status and battery'")
    print("  • 'Jarvis, set volume to 80 percent'")
    print("  • 'Jarvis, send a desktop notification saying hello'")
    print("  • 'Jarvis, check my unread emails'")
    print("\nPress Ctrl+C anytime to stop listening.\n")

    audio_q = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            pass
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK_SIZE, callback=audio_callback):
        state = "LISTENING"  # "LISTENING" or "RECORDING"
        recorded_chunks = []
        silence_start = None
        speech_start = None

        print("\033[1;32m🟢 [Listening for speech...]\033[0m", end="\r", flush=True)

        while True:
            try:
                block = audio_q.get()
                rms = np.sqrt(np.mean(block**2))

                now = time.time()

                if state == "LISTENING":
                    if rms > ENERGY_THRESHOLD:
                        state = "RECORDING"
                        speech_start = now
                        silence_start = None
                        recorded_chunks = [block]
                        print("\n\033[1;33m🎙️  [Recording your voice...]\033[0m", end="\r", flush=True)

                elif state == "RECORDING":
                    recorded_chunks.append(block)

                    if rms < ENERGY_THRESHOLD:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= SILENCE_DURATION:
                            # Finished speaking
                            total_duration = now - speech_start
                            if total_duration >= MIN_SPEECH_DURATION:
                                audio_data = np.concatenate(recorded_chunks, axis=0).flatten()
                                
                                print("\n\033[1;34m⚡ [Transcribing...]\033[0m", end="\r", flush=True)
                                segments, _ = stt_model.transcribe(audio_data, beam_size=1, language="en")
                                text = " ".join([seg.text for seg in segments]).strip()

                                # Cleanup text
                                text_clean = text.lower().strip()
                                for char in [".", ",", "!", "?"]:
                                    text_clean = text_clean.replace(char, "")

                                # Ignore common Whisper hallucination on noise
                                if text_clean and text_clean not in ("you", "thank you", "thanks for watching", "subtitles by", "bye"):
                                    print(f"\n\033[1;32m🎤 You said:\033[0m \"{text}\"")
                                    
                                    # Strip optional wake word
                                    cmd = text
                                    if cmd.lower().startswith("jarvis"):
                                        cmd = cmd[6:].lstrip(",: ").strip()

                                    if not cmd:
                                        cmd = text

                                    print("\033[1;35m⚙️  [JARVIS Executing Action...]\033[0m")
                                    response = agent.execute_instruction(cmd)
                                    print(f"\n\033[1;34m🤖 JARVIS:\033[0m {response}\n")

                            # Reset back to listening
                            state = "LISTENING"
                            recorded_chunks = []
                            silence_start = None
                            print("\033[1;32m🟢 [Listening for speech...]\033[0m", end="\r", flush=True)
                    else:
                        silence_start = None

            except KeyboardInterrupt:
                print("\n\nVoice commander stopped.")
                break
            except Exception as e:
                logger.error(f"Error in voice loop: {e}")
                time.sleep(0.5)


if __name__ == "__main__":
    run_voice_commander()
