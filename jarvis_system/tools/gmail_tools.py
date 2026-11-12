import os
import json
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

from jarvis_system.tools.registry import tool
from jarvis_system.config import JarvisConfig

_GOOGLE_TOKEN_FILE = Path.home() / ".openjarvis" / "connectors" / "gmail.json"


def _get_oauth_token() -> Optional[str]:
    """Check if Google OAuth token exists from OpenJarvis connect."""
    if _GOOGLE_TOKEN_FILE.exists():
        try:
            data = json.loads(_GOOGLE_TOKEN_FILE.read_text())
            return data.get("access_token")
        except Exception:
            pass
    return None


@tool(
    name="get_unread_emails",
    description="Check and fetch unread emails from your Gmail inbox. Returns sender, subject, date, and snippet."
)
def get_unread_emails(max_count: int = 5) -> str:
    """Fetch unread emails using either Google OAuth or Gmail App Password."""
    oauth_token = _get_oauth_token()
    if oauth_token:
        try:
            headers = {"Authorization": f"Bearer {oauth_token}"}
            res = httpx.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is:unread",
                headers=headers,
                timeout=10.0
            )
            if res.status_code == 200:
                messages = res.json().get("messages", [])[:max_count]
                results = []
                for m in messages:
                    msg_res = httpx.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                        headers=headers,
                        timeout=10.0
                    )
                    if msg_res.status_code == 200:
                        payload = msg_res.json()
                        headers_list = payload.get("payload", {}).get("headers", [])
                        subj = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "(No Subject)")
                        sender = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "Unknown")
                        date = next((h["value"] for h in headers_list if h["name"].lower() == "date"), "")
                        results.append({
                            "id": m["id"],
                            "from": sender,
                            "subject": subj,
                            "date": date,
                            "snippet": payload.get("snippet", "")
                        })
                return json.dumps(results, indent=2)
        except Exception as e:
            pass

    # Fallback to IMAP if configured in .env
    user = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        return (
            "Gmail is not yet connected. Two easy ways to connect:\n"
            "1. Run `jarvis connect gmail` in terminal to authorize via browser OAuth.\n"
            "2. OR add `GMAIL_ADDRESS=your@gmail.com` and `GMAIL_APP_PASSWORD=xxxx` to /home/naman1207/Projects/JARVIS/.env."
        )

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("inbox")

        status, response = mail.search(None, 'UNSEEN')
        if status != "OK":
            return "No unread messages found or search failed."

        msg_ids = response[0].split()
        if not msg_ids:
            return "You have 0 unread emails."

        latest_ids = msg_ids[-max_count:]
        emails = []

        for mid in reversed(latest_ids):
            res, msg_data = mail.fetch(mid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject, encoding = decode_header(msg.get("Subject", ""))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")

                    sender = msg.get("From", "")
                    date = msg.get("Date", "")
                    body = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")[:300]
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")[:300]

                    emails.append({
                        "id": mid.decode(),
                        "from": sender,
                        "subject": subject,
                        "date": date,
                        "snippet": body.strip()
                    })

        mail.logout()
        return json.dumps(emails, indent=2)
    except Exception as e:
        return f"Error connecting to Gmail: {str(e)}"


@tool(
    name="send_email",
    description="Send an email from your Gmail account to a recipient."
)
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send email via SMTP using Gmail App Password or OAuth."""
    user = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        return (
            "Gmail sending requires credentials. Please add `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` "
            "to /home/naman1207/Projects/JARVIS/.env (generated from Google Account > Security > App Passwords)."
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(user, password)
        server.send_message(msg)
        server.quit()

        return f"Email successfully sent to {recipient} with subject '{subject}'."
    except Exception as e:
        return f"Failed to send email: {str(e)}"
