import feedparser
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from django.utils import timezone

# Lista de fuentes RSS del sector agro y cooperación
RSS_SOURCES = [
    {"name": "IICA Noticias", "url": "https://www.iica.int/es/rss.xml"},
    {"name": "FAO Noticias", "url": "https://www.fao.org/fao-stories/rss/en/"},
    # Puedes agregar más fuentes institucionales o del agro aquí
]

HARD_DISCARDS = [
    'deportes', 'fútbol', 'fubtol', 'partido', 'goles', 'grammy', 'farandula', 
    'espectáculos', 'cine', 'horóscopo', 'salsa', 'reggaeton', 'concierto', 'streaming'
]

AGRO_KEYWORDS = [
    'agricultura', 'agropecuaria', 'rural', 'innovación', 'sostenibilidad',
    'cambio climático', 'seguridad alimentaria', 'tecnología', 'riego', 'café',
    'cacao', 'ganadería', 'producción', 'cosecha', 'mercados', 'cooperación', 'iica'
]

def limpiar_texto(texto):
    if not texto:
        return ""
    return re.sub('<.*?>', '', texto).strip()

def es_valida(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    for palabra in HARD_DISCARDS:
        if re.search(r'\b' + re.escape(palabra) + r'\b', texto):
            return False
    return True

def calcular_score(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    score = 1
    for palabra in AGRO_KEYWORDS:
        if palabra in texto:
            score += 2
    if 'iica' in texto:
        score += 5
    return score

def obtener_noticias(max_items=50):
    todas_las_noticias = []

    for fuente_info in RSS_SOURCES:
        try:
            feed = feedparser.parse(fuente_info["url"])
            for entry in feed.entries[:max_items]:
                titulo = limpiar_texto(entry.get('title', ''))
                descripcion = limpiar_texto(entry.get('summary', entry.get('description', '')))
                link = entry.get('link', '')

                if not titulo or not link:
                    continue

                if not es_valida(titulo, descripcion):
                    continue

                # Extraer imagen si viene en media_content o en el texto
                imagen = ""
                if hasattr(entry, 'media_content') and entry.media_content:
                    imagen = entry.media_content[0].get('url', '')

                fecha_str = entry.get('published', entry.get('updated', ''))
                
                todas_las_noticias.append({
                    "titulo": titulo,
                    "resumen": descripcion,
                    "link": link,
                    "imagen": imagen,
                    "fuente": fuente_info["name"],
                    "fecha": fecha_str,
                    "score": calcular_score(titulo, descripcion)
                })
        except Exception as e:
            print(f"Error procesando fuente {fuente_info['name']}: {e}")

    # Ordenar por score descendente
    todas_las_noticias.sort(key=lambda x: x['score'], reverse=True)
    return todas_las_noticias