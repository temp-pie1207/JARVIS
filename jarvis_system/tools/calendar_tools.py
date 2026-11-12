import json
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

from jarvis_system.tools.registry import tool

_GOOGLE_CALENDAR_TOKEN_FILE = Path.home() / ".openjarvis" / "connectors" / "gcalendar.json"
_GOOGLE_GMAIL_TOKEN_FILE = Path.home() / ".openjarvis" / "connectors" / "gmail.json"


def _get_calendar_token() -> Optional[str]:
    for path in (_GOOGLE_CALENDAR_TOKEN_FILE, _GOOGLE_GMAIL_TOKEN_FILE):
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if "access_token" in data:
                    return data["access_token"]
            except Exception:
                pass
    return None


@tool(
    name="get_calendar_events",
    description="Fetch upcoming events and meetings from your Google Calendar. Shows event summary, start time, end time, and location."
)
def get_calendar_events(days_ahead: int = 7) -> str:
    """Fetch calendar events for the upcoming days."""
    token = _get_calendar_token()
    if not token:
        return (
            "Google Calendar is not yet authorized.\n"
            "To connect your Google Calendar in 1-click:\n"
            "Run `jarvis connect gcalendar` in your terminal to sign in with your Google account."
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    time_min = now.isoformat()
    time_max = (now + datetime.timedelta(days=days_ahead)).isoformat()

    try:
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events"
            f"?timeMin={time_min}&timeMax={time_max}&singleEvents=true&orderBy=startTime"
        )
        headers = {"Authorization": f"Bearer {token}"}
        res = httpx.get(url, headers=headers, timeout=10.0)

        if res.status_code == 200:
            items = res.json().get("items", [])
            if not items:
                return f"No events scheduled for the next {days_ahead} days."

            events = []
            for item in items:
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                events.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "(No Title)"),
                    "start": start,
                    "end": end,
                    "location": item.get("location", ""),
                    "description": item.get("description", "")
                })
            return json.dumps(events, indent=2)
        elif res.status_code == 401:
            return "Google Calendar token expired. Please run `jarvis connect gcalendar` to refresh authorization."
        else:
            return f"Error querying Google Calendar API: HTTP {res.status_code} - {res.text}"
    except Exception as e:
        return f"Calendar query error: {str(e)}"


@tool(
    name="create_calendar_event",
    description="Add a new event, reminder, or meeting to your Google Calendar."
)
def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = ""
) -> str:
    """
    Creates an event on Google Calendar.
    Format for start_time/end_time: 'YYYY-MM-DDTHH:MM:SS' or 'YYYY-MM-DD'.
    """
    token = _get_calendar_token()
    if not token:
        return (
            "Google Calendar is not yet authorized.\n"
            "Run `jarvis connect gcalendar` in your terminal to authenticate your Google account."
        )

    payload = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start_time if "T" in start_time else f"{start_time}T09:00:00Z"},
        "end": {"dateTime": end_time if "T" in end_time else f"{end_time}T10:00:00Z"},
    }

    try:
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        res = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if res.status_code in (200, 201):
            created = res.json()
            return f"Event '{title}' successfully created on your Google Calendar! Link: {created.get('htmlLink')}"
        return f"Failed to create event: HTTP {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error creating calendar event: {str(e)}"
