#!/usr/bin/env python3
"""
JARVIS Autonomous Agent Engine
Powered by OpenAI with full host system access, Gmail, Google Calendar, WhatsApp, and ElevenLabs voice output.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from jarvis_system.config import JarvisConfig
from jarvis_system.tools import TOOL_REGISTRY, get_openai_tools, execute_tool
from jarvis_system.voice.elevenlabs_tts import ElevenLabsVoiceService

logger = logging.getLogger("JARVIS.Agent")

SYSTEM_PROMPT = """You are JARVIS, an advanced personal AI assistant running directly on the user's local machine with full system access and communication tools.

You have real tools to perform actions on the computer:
- System Control: run terminal commands, inspect hardware status (CPU, RAM, GPU, disk, battery), manage processes, control volume, open apps/URLs, and send desktop notifications.
- Filesystem: read files, write files, search directory trees.
- Communication:
  * Gmail: check unread emails, send emails.
  * Google Calendar: check upcoming schedule, create events.
  * WhatsApp: draft and send WhatsApp messages, open WhatsApp Web.
- Python: execute python code for calculations and data processing.

Guidelines:
1. Always execute the appropriate tool rather than explaining how the user could do it manually.
2. Be concise, accurate, and direct.
3. If an action has completed, confirm with a brief, clear summary.
"""

class JarvisAgent:
    def __init__(self, voice_enabled: bool = True):
        JarvisConfig.reload()
        self.api_key = JarvisConfig.OPENAI_API_KEY
        self.model = JarvisConfig.OPENAI_MODEL or "gpt-4o"
        self.voice_enabled = voice_enabled and JarvisConfig.PLAY_AUDIO_LOCALLY
        self.voice_service = ElevenLabsVoiceService() if self.voice_enabled else None
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        if not self.api_key or self.api_key == "your_openai_api_key_here":
            # Fall back to local Ollama if OpenAI key is missing
            self.client = None
            self.use_ollama = True
        else:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=JarvisConfig.OPENAI_BASE_URL or None
            )
            self.use_ollama = False

    def speak(self, text: str):
        """Speak response using ElevenLabs voice if configured."""
        if self.voice_service and self.voice_service.is_configured():
            try:
                # Clean text of code blocks and markdown for clean speech
                speech_text = text.replace("```", "").strip()
                if len(speech_text) > 400:
                    speech_text = speech_text[:400] + "... and more details displayed on screen."
                self.voice_service.synthesize_speech(speech_text)
            except Exception as e:
                logger.warning(f"Voice synthesis skipped: {e}")

    def execute_instruction(self, user_prompt: str) -> str:
        """Executes a user request through the ReAct tool calling loop."""
        self.messages.append({"role": "user", "content": user_prompt})

        if self.use_ollama:
            return self._run_ollama_fallback(user_prompt)

        tools = get_openai_tools()
        max_turns = 10

        for _ in range(max_turns):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools,
                    tool_choice="auto"
                )
            except Exception as e:
                # Fallback to local Ollama engine on quota/rate limit errors
                err_msg = str(e).lower()
                if "rate" in err_msg or "credit" in err_msg or "429" in err_msg or "auth" in err_msg:
                    print(f"\033[33m⚠️ OpenAI quota/error encountered ({e}). Falling back to local Ollama engine (RTX 4050)...\033[0m")
                    from openai import OpenAI
                    self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
                    self.model = "qwen3.5:2b"
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.messages,
                        tools=tools,
                        tool_choice="auto"
                    )
                else:
                    raise e

            msg = response.choices[0].message
            self.messages.append(msg)

            # If tool calls were requested, execute them
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except Exception:
                        fn_args = {}

                    print(f"\033[33m⚡ [Executing Tool: {fn_name}]\033[0m")
                    result_str = execute_tool(fn_name, fn_args)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": fn_name,
                        "content": result_str
                    })
            else:
                final_text = msg.content or "(Done)"
                if self.voice_enabled:
                    self.speak(final_text)
                return final_text

        return "Reached maximum tool execution turns."

    def _run_ollama_fallback(self, prompt: str) -> str:
        import httpx
        try:
            res = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "qwen3.5:2b", "prompt": f"{SYSTEM_PROMPT}\nUser: {prompt}\nJarvis:", "stream": False},
                timeout=30.0
            )
            return res.json().get("response", "No response from local engine.")
        except Exception as e:
            return f"Error connecting to local engine: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: jarvis-ai <prompt> | voice | chat | byte | status")
        sys.exit(0)

    arg = sys.argv[1].lower()

    if arg in ("voice", "listen"):
        from jarvis_system.agent.voice_listener import run_voice_commander
        run_voice_commander()

    elif arg == "chat":
        print("\033[1;36m=== JARVIS System AI — Interactive Terminal ===\033[0m")
        print("Type your instructions or questions. Type 'exit' to quit.\n")
        agent = JarvisAgent(voice_enabled=True)
        while True:
            try:
                user_msg = input("\033[1;32mYou > \033[0m").strip()
                if not user_msg:
                    continue
                if user_msg in ("exit", "quit", "q"):
                    print("Goodbye!")
                    break
                reply = agent.execute_instruction(user_msg)
                print(f"\n\033[1;34mJARVIS >\033[0m {reply}\n")
            except (KeyboardInterrupt, EOFError):
                print("\nSession ended.")
                break

    elif arg == "byte":
        # Launch ElevenLabs Conversational Voice Agent
        from jarvis_system.agent.byte_agent import interactive_chat
        import asyncio
        asyncio.run(interactive_chat())

    elif arg == "status":
        from jarvis_system.tools.system_tools import get_system_status
        print(get_system_status())

    else:
        # Single prompt execution
        user_prompt = " ".join(sys.argv[1:])
        agent = JarvisAgent(voice_enabled=True)
        reply = agent.execute_instruction(user_prompt)
        print(f"\n\033[1;34mJARVIS >\033[0m {reply}")


if __name__ == "__main__":
    main()
