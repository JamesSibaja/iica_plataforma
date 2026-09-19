from datetime import datetime
from iica_coworking.models import EventoCalendario
from website_management.models import PerfilMicrosoft
import requests


def sync_microsoft_events(user):

    try:
        perfil = user.perfil_microsoft
    except PerfilMicrosoft.DoesNotExist:
        return

    headers = {
        "Authorization": f"Bearer {perfil.access_token}"
    }

    url = "https://graph.microsoft.com/v1.0/me/events"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Error Microsoft:", response.text)
        return

    data = response.json()

    for ev in data.get("value", []):

        try:
            start = datetime.fromisoformat(ev["start"]["dateTime"])
            end = datetime.fromisoformat(ev["end"]["dateTime"])
        except:
            continue

        EventoCalendario.objects.update_or_create(
            usuario=user,
            titulo=ev.get("subject", "Sin título"),
            fecha=start.date(),
            hora_inicio=start.time(),
            defaults={
                "hora_fin": end.time(),
                "detalle": ev.get("bodyPreview", ""),
                "ubicacion": ev.get("location", {}).get("displayName", ""),
                "categoria": "reunion",
            }
        )