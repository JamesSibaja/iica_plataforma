# iica_coworking/services/microsoft.py

import requests
from django.conf import settings
from iica_coworking.models import EventoCalendario


def refresh_token(perfil):

    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    data = {
        "client_id": settings.SOCIALACCOUNT_PROVIDERS["microsoft"]["APP"]["client_id"],
        "client_secret": settings.SOCIALACCOUNT_PROVIDERS["microsoft"]["APP"]["secret"],
        "grant_type": "refresh_token",
        "refresh_token": perfil.refresh_token,
        "scope": "User.Read Calendars.Read offline_access"
    }

    r = requests.post(url, data=data)
    data = r.json()

    if "access_token" in data:
        perfil.access_token = data["access_token"]
        perfil.refresh_token = data.get("refresh_token", perfil.refresh_token)
        perfil.save()
        return perfil.access_token

    return None


def obtener_eventos_ms(perfil):

    headers = {
        "Authorization": f"Bearer {perfil.access_token}"
    }

    url = "https://graph.microsoft.com/v1.0/me/events"

    r = requests.get(url, headers=headers)

    # 🔥 token vencido → refrescar
    if r.status_code == 401:
        nuevo_token = refresh_token(perfil)

        if not nuevo_token:
            return []

        headers["Authorization"] = f"Bearer {nuevo_token}"
        r = requests.get(url, headers=headers)

    return r.json()


def sincronizar_eventos(perfil):

    data = obtener_eventos_ms(perfil)

    for ev in data.get("value", []):

        EventoCalendario.objects.update_or_create(
            usuario=perfil.user,
            titulo=ev.get("subject"),
            fecha=ev.get("start", {}).get("dateTime", "")[:10],
            defaults={
                "detalle": ev.get("bodyPreview", ""),
                "hora_inicio": ev.get("start", {}).get("dateTime", "")[11:16],
                "hora_fin": ev.get("end", {}).get("dateTime", "")[11:16],
                "categoria": "reunion",
                "ubicacion": ev.get("location", {}).get("displayName", "")
            }
        )