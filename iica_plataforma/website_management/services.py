import requests

def get_calendar_events(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/events",
        headers=headers
    )

    return response.json()