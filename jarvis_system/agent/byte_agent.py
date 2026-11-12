#!/usr/bin/env python3
"""
Byte - ElevenLabs Conversational AI Agent Client
Connects to Byte (agent_3101m6rqhcqsf7h9mcg1rkf25g0q) via ElevenLabs Conversational AI WebSockets.
Supports interactive text chat, real-time response transcription, and live voice playback via mpv.
"""

import sys
import json
import base64
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Callable

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from jarvis_system.config import JarvisConfig


class ByteAgentClient:
    def __init__(
        self,
        agent_id: Optional[str] = None,
        play_audio: Optional[bool] = None,
        on_text: Optional[Callable[[str], None]] = None
    ):
        self.agent_id = agent_id or JarvisConfig.ELEVENLABS_AGENT_ID
        self.play_audio = play_audio if play_audio is not None else JarvisConfig.PLAY_AUDIO_LOCALLY
        self.on_text = on_text
        self.ws = None
        self.player_proc = None
        self.running = False
        self._listen_task = None

    def _start_audio_player(self):
        """Starts an mpv process to stream raw PCM 16kHz audio directly to speakers."""
        if not self.play_audio:
            return None
        try:
            return subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--demuxer=rawaudio",
                    "--demuxer-rawaudio-rate=16000",
                    "--demuxer-rawaudio-channels=1",
                    "--demuxer-rawaudio-format=s16le",
                    "--volume=100",
                    "-"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None

    def _write_audio(self, pcm_data: bytes):
        if self.player_proc and self.player_proc.stdin:
            try:
                self.player_proc.stdin.write(pcm_data)
                self.player_proc.stdin.flush()
            except Exception:
                pass

    async def connect(self):
        import websockets
        uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}"
        self.ws = await websockets.connect(uri)
        self.running = True

        if self.play_audio:
            self.player_proc = self._start_audio_player()

        # Send initial initiation handshake
        init_data = {"type": "conversation_initiation_client_data"}
        await self.ws.send(json.dumps(init_data))

    async def _listen_loop(self):
        try:
            async for raw_msg in self.ws:
                if not self.running:
                    break
                data = json.loads(raw_msg)
                event_type = data.get("type")

                if event_type == "agent_response":
                    agent_text = data.get("agent_response_event", {}).get("agent_response", "")
                    if agent_text:
                        if self.on_text:
                            self.on_text(agent_text)
                        else:
                            print(f"\n\033[1;36mByte:\033[0m {agent_text}")

                elif event_type == "audio":
                    b64_audio = data.get("audio_event", {}).get("audio_base_64", "")
                    if b64_audio and self.player_proc:
                        pcm_bytes = base64.b64decode(b64_audio)
                        self._write_audio(pcm_bytes)

                elif event_type == "interruption":
                    # Restart player if user interrupts
                    if self.player_proc:
                        try:
                            self.player_proc.terminate()
                        except Exception:
                            pass
                        self.player_proc = self._start_audio_player()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.running:
                print(f"\n[ByteAgent] Connection closed or error: {e}")

    async def send_message(self, text: str):
        """Sends a user text message to the agent."""
        if not self.ws or not self.running:
            raise RuntimeError("Agent is not connected.")
        msg = {
            "type": "user_message",
            "text": text
        }
        await self.ws.send(json.dumps(msg))

    async def close(self):
        self.running = False
        if self._listen_task:
            self._listen_task.cancel()
        if self.ws:
            await self.ws.close()
        if self.player_proc:
            try:
                if self.player_proc.stdin:
                    self.player_proc.stdin.close()
                self.player_proc.wait(timeout=1.0)
            except Exception:
                self.player_proc.kill()


async def interactive_chat():
    print("=" * 60)
    print("  Connecting to Byte (ElevenLabs Desktop Assistant)...")
    print(f"  Agent ID: {JarvisConfig.ELEVENLABS_AGENT_ID}")
    print("=" * 60)

    client = ByteAgentClient()
    await client.connect()

    listen_task = asyncio.create_task(client._listen_loop())
    client._listen_task = listen_task

    # Allow initial greeting to come through
    await asyncio.sleep(1.5)

    print("\nType your message below (or 'exit' to quit):")
    loop = asyncio.get_running_loop()

    try:
        while True:
            user_input = await loop.run_in_executor(None, input, "\n\033[1;32mYou:\033[0m ")
            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nEnding session with Byte. Goodbye!")
                break
            await client.send_message(user_input)
            # Give short moment for response to start streaming
            await asyncio.sleep(0.5)

    finally:
        await client.close()
        listen_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\nSession aborted by user.")
