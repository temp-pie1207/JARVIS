import re
import urllib.parse
import subprocess
from typing import Optional
from jarvis_system.tools.registry import tool


@tool(
    name="send_whatsapp_message",
    description="Send a message to a WhatsApp contact or phone number. Opens the chat with the pre-filled text in WhatsApp Web/Desktop."
)
def send_whatsapp_message(phone_number: str, message: str) -> str:
    """
    Formats the phone number and launches WhatsApp Web with pre-filled text.
    Phone number should include country code (e.g. +91 9876543210 or 919876543210).
    """
    clean_number = re.sub(r"[^\d]", "", phone_number)
    if not clean_number:
        return "Invalid phone number provided. Please provide numbers with country code."

    encoded_text = urllib.parse.quote(message)
    whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_number}&text={encoded_text}"

    try:
        subprocess.Popen(
            ["xdg-open", whatsapp_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return (
            f"Opened WhatsApp chat with {clean_number}.\n"
            f"Message drafted: '{message}'\n"
            f"WhatsApp Web URL: {whatsapp_url}"
        )
    except Exception as e:
        return f"Failed to open WhatsApp Web: {str(e)}"


@tool(
    name="open_whatsapp",
    description="Launch WhatsApp Web or application on the host desktop."
)
def open_whatsapp() -> str:
    """Launches WhatsApp Web on the desktop."""
    try:
        subprocess.Popen(
            ["xdg-open", "https://web.whatsapp.com"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "WhatsApp Web opened on your desktop."
    except Exception as e:
        return f"Failed to launch WhatsApp: {str(e)}"
