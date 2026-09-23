from email.utils import parsedate_to_datetime
from datetime import datetime
from django.utils import timezone
from celery import shared_task
from .service.rss_service import obtener_noticias
from .models import Noticia

@shared_task
def actualizar_noticias():
    noticias = obtener_noticias(max_items=50)

    creadas = 0
    actualizadas = 0

    for noticia in noticias:
        link = noticia.get("link", "").strip()
        if not link:
            continue

        raw_fecha = noticia.get("fecha")
        fecha_publicacion = None

        if raw_fecha:
            try:
                # Intenta parsear ISO
                fecha_publicacion = datetime.fromisoformat(raw_fecha)
            except (ValueError, TypeError):
                try:
                    # Intenta parsear formato estándar RSS (RFC 822)
                    fecha_publicacion = parsedate_to_datetime(raw_fecha)
                except Exception:
                    fecha_publicacion = timezone.now()

        defaults = {
            "titulo": noticia.get("titulo", "")[:500],
            "resumen": noticia.get("resumen", ""),
            "imagen": noticia.get("imagen", ""),
            "imagen_origen": noticia.get("imagen_origen", ""),
            "fuente": noticia.get("fuente_configurada", noticia.get("fuente", "")),
            "fecha_publicacion": fecha_publicacion,
            "tipo": noticia.get("tipo", Noticia.TIPO_NOTICIA),
            "score": noticia.get("score", 0),
            "hash_noticia": noticia.get("hash_noticia", ""),
            "activa": True,
        }

        objeto, creado = Noticia.objects.update_or_create(
            link=link,
            defaults=defaults,
        )

        if creado:
            creadas += 1
        else:
            actualizadas += 1

    return f"Procesadas: {len(noticias)} | Nuevas: {creadas} | Actualizadas: {actualizadas}"