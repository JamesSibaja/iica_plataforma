import requests
from django.utils import timezone
from datetime import timedelta

def get_calendar_events(token):
    

    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    url = (
    "https://graph.microsoft.com/v1.0/me/calendar/calendarView"
        f"?startDateTime={start.isoformat()}"
        f"&endDateTime={end.isoformat()}"
    )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    data = response.json()

    return data.get("value", [])
