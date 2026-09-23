from datetime import datetime
from email.utils import parsedate_to_datetime
from django.utils import timezone
from celery import shared_task
from .service.rss_service import obtener_noticias
from .models import Noticia

@shared_task
def actualizar_noticias():
    noticias = obtener_noticias(max_items=30)
    creadas = 0
    actualizadas = 0

    for noticia in noticias:
        link = noticia.get("link", "").strip()
        if not link:
            continue

        raw_fecha = noticia.get("fecha")
        fecha_publicacion = timezone.now()

        if raw_fecha:
            try:
                fecha_publicacion = parsedate_to_datetime(raw_fecha)
            except Exception:
                pass

        defaults = {
            "titulo": noticia.get("titulo", "")[:500],
            "resumen": noticia.get("resumen", ""),
            "imagen": noticia.get("imagen", ""),
            "fuente": noticia.get("fuente", ""),
            "fecha_publicacion": fecha_publicacion,
            "score": noticia.get("score", 0),
            "activa": True,
        }

        _, creado = Noticia.objects.update_or_create(
            link=link,
            defaults=defaults,
        )

        if creado:
            creadas += 1
        else:
            actualizadas += 1

    return f"Procesadas | Nuevas: {creadas} | Actualizadas: {actualizadas}"