"""Google Calendar API interaction module."""

import datetime
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from calendar_widget.auth import get_credentials

# Recurrence rule presets (RRULE format)
RECURRENCE_OPTIONS = {
    "Não repetir": None,
    "Diariamente": "RRULE:FREQ=DAILY",
    "Semanalmente": "RRULE:FREQ=WEEKLY",
    "Mensalmente": "RRULE:FREQ=MONTHLY",
    "Anualmente": "RRULE:FREQ=YEARLY",
    "Dias úteis (Seg-Sex)": "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
}

# Reminder presets (minutes before the event)
REMINDER_OPTIONS: dict[str, int] = {
    "No momento do evento": 0,
    "5 minutos antes": 5,
    "10 minutos antes": 10,
    "15 minutos antes": 15,
    "30 minutos antes": 30,
    "1 hora antes": 60,
    "2 horas antes": 120,
    "1 dia antes": 1440,
    "2 dias antes": 2880,
    "1 semana antes": 10080,
}

# Google Calendar standard event color palette (indexed 1-11)
GOOGLE_EVENT_COLORS = {
    "1": "#7986CB",  # Lavender
    "2": "#33B679",  # Sage
    "3": "#8E24AA",  # Grape
    "4": "#E67C73",  # Flamingo
    "5": "#F6BF26",  # Banana
    "6": "#F4511E",  # Tangerine
    "7": "#039BE5",  # Peacock
    "8": "#616161",  # Graphite
    "9": "#3F51B5",  # Blueberry
    "10": "#0B8043", # Basil
    "11": "#D50000", # Tomato
}


def get_user_timezone() -> str:
    """Detect local timezone or fallback to America/Sao_Paulo."""
    try:
        from datetime import datetime as _dt
        tz = _dt.now().astimezone().tzinfo
        if hasattr(tz, "key") and tz.key:
            return tz.key
    except Exception:
        pass
    return "America/Sao_Paulo"


def get_service(creds: Optional[Credentials] = None):
    """Build and return the Google Calendar API service."""
    if creds is None:
        creds = get_credentials()
    if creds is None:
        return None
    return build("calendar", "v3", credentials=creds)


def get_calendar_list(
    creds: Optional[Credentials] = None,
) -> list[dict]:
    """Fetch all calendars the user has access to.

    Returns list of dicts with id, summary, backgroundColor, primary, etc.
    """
    service = get_service(creds)
    if service is None:
        return []

    try:
        result = service.calendarList().list().execute()
        calendars = result.get("items", [])
        return [
            {
                "id": cal.get("id", ""),
                "summary": cal.get("summary", cal.get("id", "")),
                "backgroundColor": cal.get("backgroundColor", "#6C63FF"),
                "primary": cal.get("primary", False),
                "selected": cal.get("selected", True),
                "accessRole": cal.get("accessRole", "reader"),
            }
            for cal in calendars
        ]
    except Exception:
        return []


def get_events_for_month(
    year: int,
    month: int,
    calendar_ids: Optional[list[str]] = None,
    calendar_colors: Optional[dict[str, str]] = None,
    creds: Optional[Credentials] = None,
) -> list[dict]:
    """Fetch all events for a given month from specified calendars.

    If calendar_ids is None, fetch from primary only.
    Returns a list of event dictionaries.
    """
    service = get_service(creds)
    if service is None:
        return []

    start_date = datetime.datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_date = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_date = datetime.datetime(year, month + 1, 1, 0, 0, 0)

    time_min = start_date.isoformat() + "Z"
    time_max = end_date.isoformat() + "Z"

    if calendar_ids is None:
        calendar_ids = ["primary"]

    all_events: list[dict] = []
    for cal_id in calendar_ids:
        try:
            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=250,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])
            for item in items:
                item["_calendarId"] = cal_id
                cid = item.get("colorId")
                if cid and cid in GOOGLE_EVENT_COLORS:
                    item["_color"] = GOOGLE_EVENT_COLORS[cid]
                elif calendar_colors and cal_id in calendar_colors:
                    item["_color"] = calendar_colors[cal_id]
                else:
                    item["_color"] = "#6C63FF"
            all_events.extend(items)
        except Exception:
            pass

    all_events.sort(
        key=lambda e: e.get("start", {}).get(
            "dateTime", e.get("start", {}).get("date", "")
        )
    )
    return all_events


def get_event(
    event_id: str, creds: Optional[Credentials] = None
) -> Optional[dict]:
    """Fetch a single event by ID."""
    service = get_service(creds)
    if service is None:
        return None
    try:
        return (
            service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )
    except Exception:
        return None


def _build_reminders_body(
    reminder_minutes_list: Optional[list[int]],
) -> Optional[dict]:
    """Build the reminders dict for the Google Calendar API.

    Returns None if no custom reminders are set (use calendar default).
    """
    if reminder_minutes_list is None:
        return None
    if not reminder_minutes_list:
        return {"useDefault": False, "overrides": []}
    return {
        "useDefault": False,
        "overrides": [
            {"method": "popup", "minutes": m} for m in reminder_minutes_list
        ],
    }


def create_event(
    summary: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    description: str = "",
    location: str = "",
    recurrence: Optional[str] = None,
    reminder_minutes_list: Optional[list[int]] = None,
    calendar_id: str = "primary",
    is_all_day: bool = False,
    creds: Optional[Credentials] = None,
) -> Optional[dict]:
    """Create a new calendar event."""
    service = get_service(creds)
    if service is None:
        return None

    tz_name = get_user_timezone()

    if is_all_day:
        start_date = start_datetime.date() if hasattr(start_datetime, "date") else start_datetime
        end_date = end_datetime.date() if hasattr(end_datetime, "date") else end_datetime
        exclusive_end = end_date + datetime.timedelta(days=1)
        start_payload = {"date": start_date.strftime("%Y-%m-%d")}
        end_payload = {"date": exclusive_end.strftime("%Y-%m-%d")}
    else:
        start_payload = {
            "dateTime": start_datetime.isoformat(),
            "timeZone": tz_name,
        }
        end_payload = {
            "dateTime": end_datetime.isoformat(),
            "timeZone": tz_name,
        }

    event_body: dict = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": start_payload,
        "end": end_payload,
    }

    if recurrence:
        event_body["recurrence"] = [recurrence]

    reminders_body = _build_reminders_body(reminder_minutes_list)
    if reminders_body is not None:
        event_body["reminders"] = reminders_body

    try:
        return (
            service.events()
            .insert(calendarId=calendar_id, body=event_body)
            .execute()
        )
    except Exception:
        return None


def update_event(
    event_id: str,
    summary: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    description: str = "",
    location: str = "",
    recurrence: Optional[str] = None,
    reminder_minutes_list: Optional[list[int]] = None,
    calendar_id: str = "primary",
    is_all_day: bool = False,
    creds: Optional[Credentials] = None,
) -> Optional[dict]:
    """Update an existing calendar event."""
    service = get_service(creds)
    if service is None:
        return None

    tz_name = get_user_timezone()

    if is_all_day:
        start_date = start_datetime.date() if hasattr(start_datetime, "date") else start_datetime
        end_date = end_datetime.date() if hasattr(end_datetime, "date") else end_datetime
        exclusive_end = end_date + datetime.timedelta(days=1)
        start_payload = {"date": start_date.strftime("%Y-%m-%d")}
        end_payload = {"date": exclusive_end.strftime("%Y-%m-%d")}
    else:
        start_payload = {
            "dateTime": start_datetime.isoformat(),
            "timeZone": tz_name,
        }
        end_payload = {
            "dateTime": end_datetime.isoformat(),
            "timeZone": tz_name,
        }

    event_body: dict = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": start_payload,
        "end": end_payload,
    }

    if recurrence:
        event_body["recurrence"] = [recurrence]

    reminders_body = _build_reminders_body(reminder_minutes_list)
    if reminders_body is not None:
        event_body["reminders"] = reminders_body

    try:
        return (
            service.events()
            .update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_body,
            )
            .execute()
        )
    except Exception:
        return None


def delete_event(
    event_id: str,
    calendar_id: str = "primary",
    creds: Optional[Credentials] = None,
) -> bool:
    """Delete a calendar event."""
    service = get_service(creds)
    if service is None:
        return False
    try:
        service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        return True
    except Exception:
        return False


def parse_event_datetime(
    event: dict,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Parse start and end datetime from an event.

    Handles both dateTime and date (all-day) events.
    Always returns normalized timezone-naive datetimes in local time for safe comparison.
    """
    now = datetime.datetime.now()
    start = event.get("start", {})
    end = event.get("end", {})

    def _parse_single(d_dict: dict, fallback_dt: datetime.datetime) -> datetime.datetime:
        if not d_dict or not isinstance(d_dict, dict):
            return fallback_dt
        if "dateTime" in d_dict and d_dict["dateTime"]:
            try:
                dt_str = str(d_dict["dateTime"]).replace("Z", "+00:00")
                dt = datetime.datetime.fromisoformat(dt_str)
                if dt.tzinfo is not None:
                    return dt.astimezone().replace(tzinfo=None)
                return dt
            except Exception:
                pass
        if "date" in d_dict and d_dict["date"]:
            try:
                d_str = str(d_dict["date"])
                d = datetime.date.fromisoformat(d_str)
                return datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
            except Exception:
                pass
        return fallback_dt

    start_dt = _parse_single(start, now)
    end_dt = _parse_single(end, start_dt)
    if end_dt < start_dt:
        end_dt = start_dt
    return start_dt, end_dt


def get_event_day(event: dict) -> int:
    """Get the day of month for an event."""
    start_dt, _ = parse_event_datetime(event)
    return start_dt.day


def get_event_days(event: dict, year: int, month: int) -> list[int]:
    """Get all days of the given month that this event spans.

    For multi-day events (e.g. 24-03 to 26-03), returns [24, 25, 26].
    Clamps to the boundaries of the specified month.
    """
    start_dt, end_dt = parse_event_datetime(event)
    start_date = start_dt.date() if hasattr(start_dt, "date") else start_dt
    end_date = end_dt.date() if hasattr(end_dt, "date") else end_dt

    # For all-day events, the end date is exclusive (e.g. 24-03 to 27-03
    # means days 24, 25, 26). For timed events ending at midnight, same logic.
    # If end equals start, it's a single-day event.
    is_all_day = "date" in event.get("start", {})
    if is_all_day and end_date > start_date:
        end_date = end_date - datetime.timedelta(days=1)

    # For timed events, if end is on a later day, include all days
    # but don't subtract 1 since it genuinely spans into that day.

    # Clamp to month boundaries
    import calendar as _cal

    month_start = datetime.date(year, month, 1)
    last_day = _cal.monthrange(year, month)[1]
    month_end = datetime.date(year, month, last_day)

    clamp_start = max(start_date, month_start)
    clamp_end = min(end_date, month_end)

    days: list[int] = []
    current = clamp_start
    while current <= clamp_end:
        days.append(current.day)
        current += datetime.timedelta(days=1)

    return days if days else [start_dt.day]


def is_all_day_event(event: dict) -> bool:
    """Check if an event is an all-day event."""
    start = event.get("start", {})
    return "date" in start and "dateTime" not in start


def get_event_time_str(event: dict) -> str:
    """Get a formatted time string for an event."""
    if is_all_day_event(event):
        return "Dia inteiro"
    start_dt, _ = parse_event_datetime(event)
    return start_dt.strftime("%H:%M")


def get_event_time_range_str(event: dict) -> str:
    """Get formatted time range string (e.g. '09:00 - 10:30' or 'Dia inteiro')."""
    if is_all_day_event(event):
        return "Dia inteiro"
    start_dt, end_dt = parse_event_datetime(event)
    return f"{start_dt.strftime('%H:%M')} – {end_dt.strftime('%H:%M')}"


def get_event_recurrence_label(event: dict) -> str:
    """Get human-readable recurrence label from event."""
    recurrence = event.get("recurrence", [])
    if not recurrence:
        return "Não repetir"
    rule = recurrence[0] if recurrence else ""
    for label, rrule in RECURRENCE_OPTIONS.items():
        if rrule and rrule == rule:
            return label
    return "Personalizado"


def _minutes_to_label(minutes: int) -> str:
    """Convert a reminder minutes value to a human-readable label."""
    for label, mins in REMINDER_OPTIONS.items():
        if mins == minutes:
            return label
    if minutes < 60:
        return f"{minutes} minutos antes"
    if minutes < 1440:
        hours = minutes // 60
        return f"{hours} hora{'s' if hours > 1 else ''} antes"
    days = minutes // 1440
    return f"{days} dia{'s' if days > 1 else ''} antes"


def get_event_reminder_labels(event: dict) -> list[str]:
    """Get list of human-readable reminder labels from event."""
    reminders = event.get("reminders", {})
    if reminders.get("useDefault", True):
        return ["Padrão do calendário"]
    overrides = reminders.get("overrides", [])
    if not overrides:
        return []
    return [_minutes_to_label(o.get("minutes", 0)) for o in overrides]


def get_event_reminder_minutes(event: dict) -> Optional[list[int]]:
    """Get list of reminder minutes from event.

    Returns None if using calendar default.
    Returns empty list if reminders are explicitly disabled.
    """
    reminders = event.get("reminders", {})
    if reminders.get("useDefault", True):
        return None
    overrides = reminders.get("overrides", [])
    return [o.get("minutes", 0) for o in overrides]
