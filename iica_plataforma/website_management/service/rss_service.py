from __future__ import annotations

import html
import re
import unicodedata
import feedparser
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


# ============================================================================
# CONFIGURACIÓN GENERAL
# ============================================================================

MIN_SCORE = 28
MAX_ITEMS_DEFAULT = 12

# Cuánto tiempo considerar "reciente".
# No elimina automáticamente noticias antiguas, pero sí afecta el ranking.
RECENCIA_MAX_DIAS = 30



RSS_SOURCES = [

    # ---------------------------------------------------------------------
    # COSTA RICA - MEDIOS
    # ---------------------------------------------------------------------

    {
        "url": "https://semanariouniversidad.com/feed",
        "nombre": "Semanario Universidad",
        "tipo": "medio",
        "peso": 5,
        "pais": ["Costa Rica"],
    },
    {
        "url": "https://elperiodicocr.com/feed/",
        "nombre": "El Periodico CR",
        "tipo": "medio",
        "peso": 4,
        "pais": ["Costa Rica"],
    },
    {
        "url": "https://www.elmundo.cr/feed/",
        "nombre": "El Mundo CR",
        "tipo": "medio",
        "peso": 4,
        "pais": ["Costa Rica"],
    },
    {
        # Feed actual de La Nación.
        # El endpoint /rss general que tenías no es el que queremos usar.
        "url": "https://www.nacion.com/arc/outboundfeeds/rss/?outputType=xml",
        "nombre": "La Nación",
        "tipo": "medio",
        "peso": 5,
        "pais": ["Costa Rica"],
    },

    {
        "url": "https://observador.cr/feed/",
        "nombre": "El Observador CR",
        "tipo": "medio",
        "peso": 4,
        "pais": ["Costa Rica"],
    },

    {
        "url": "https://delfino.cr/feed",
        "nombre": "Delfino",
        "tipo": "medio",
        "peso": 4,
        "pais": ["Costa Rica"],
    },

    # ---------------------------------------------------------------------
    # INTERNACIONALES / REGIONALES
    # ---------------------------------------------------------------------

    {
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "nombre": "El País",
        "tipo": "medio_internacional",
        "peso": 2,
        "pais": [],
    },

    {
        "url": "https://rss.dw.com/rdf/rss-sp-top",
        "nombre": "DW Español",
        "tipo": "medio_internacional",
        "peso": 2,
        "pais": [],
    },

    # ---------------------------------------------------------------------
    # HUMANITARIO / DESARROLLO
    # ---------------------------------------------------------------------

    {
        "url": "https://reliefweb.int/updates/rss.xml",
        "nombre": "ReliefWeb",
        "tipo": "organismo_internacional",
        "peso": 5,
        "pais": [],
    },

    # ---------------------------------------------------------------------
    # USDA
    # ---------------------------------------------------------------------

    {
        "url": "https://www.usda.gov/rss/latest-blogs.xml",
        "nombre": "USDA",
        "tipo": "organismo_agropecuario",
        "peso": 6,
        "pais": ["Estados Unidos"],
    },
    # ---------------------------------------------------------------------
    # Otros
    # ---------------------------------------------------------------------

    {
        "url": "https://vinv.ucr.ac.cr/es/rss.xml",
        "nombre": "Vicerrectoría de Investigación - (UCR)",
        "tipo": "Universidad",
        "peso": 3,
        "pais": ["Costa Rica"],
    },
]


# ============================================================================
# PERFIL TEMÁTICO IICA
# ============================================================================

SECTORES_PRINCIPALES = {

    "agricultura": [
        "agricultura",
        "agricola",
        "agropecuario",
        "agropecuaria",
        "agroalimentario",
        "agroalimentaria",
        "sector agropecuario",
        "sector agricola",
        "produccion agricola",
        "produccion agropecuaria",
        "sistemas alimentarios",
        "sistema alimentario",
    ],

    "cultivos": [
        "banano",
        "banana",
        "musaceas",
        "platano",
        "cafe",
        "arroz",
        "frijol",
        "maiz",
        "piña",
        "pina",
        "caña",
        "cana",
        "caña de azucar",
        "hortalizas",
        "frutas",
        "tuberculos",
        "cacao",
        "palma",
        "papa",
        "cebolla",
        "tomate",
        "yuca",
    ],

    "ganaderia": [
        "ganaderia",
        "ganadero",
        "ganadera",
        "bovino",
        "bovina",
        "ganado",
        "leche",
        "lacteo",
        "lacteos",
        "carne",
        "porcino",
        "porcina",
        "cerdo",
        "avicultura",
        "avicola",
        "apicultura",
        "abejas",
    ],

    "pesca": [
        "pesca",
        "pesquero",
        "pesquera",
        "acuicultura",
        "acuicola",
        "acuicultura",
        "maricultura",
        "recursos pesqueros",
    ],

    "desarrollo_rural": [
        "desarrollo rural",
        "territorios rurales",
        "territorio rural",
        "ruralidad",
        "comunidades rurales",
        "productores rurales",
        "familias rurales",
        "agricultura familiar",
        "pequeños productores",
        "pequeñas productoras",
        "economia rural",
        "economía rural",
    ],

    "seguridad_alimentaria": [
        "seguridad alimentaria",
        "inseguridad alimentaria",
        "soberania alimentaria",
        "sistemas alimentarios",
        "nutricion",
        "nutricional",
        "alimentacion",
        "alimentos",
        "abastecimiento alimentario",
    ],

    "cambio_climatico": [
        "cambio climatico",
        "cambio climático",
        "adaptacion climatica",
        "adaptación climática",
        "mitigacion climatica",
        "mitigación climática",
        "resiliencia climatica",
        "resiliencia climática",
        "eventos extremos",
        "sequía",
        "sequia",
        "inundacion",
        "inundación",
        "lluvias",
        "el niño",
        "el nino",
        "la niña",
        "la nina",
    ],

    "biodiversidad": [
        "biodiversidad",
        "ecosistemas",
        "bosques",
        "restauracion",
        "restauración",
        "servicios ecosistemicos",
        "servicios ecosistémicos",
        "conservacion",
        "conservación",
        "paisajes",
        "agroecosistemas",
    ],

    "sanidad_agropecuaria": [
        "sanidad agropecuaria",
        "sanidad vegetal",
        "sanidad animal",
        "plaga",
        "plagas",
        "enfermedad vegetal",
        "enfermedades vegetales",
        "enfermedad animal",
        "enfermedades animales",
        "fitosanitario",
        "fitosanitaria",
        "zoosanitario",
        "zoosanitaria",
        "bioseguridad",
        "cuarentena",
        "riesgo fitosanitario",
        "riesgo zoosanitario",
        "control de plagas",
        "vigilancia fitosanitaria",
        "vigilancia epidemiologica",
        "vigilancia epidemiológica",
        "foc r4t",
        "fusarium",
        "fusarium r4t",
        "sigatoka",
        "gusano barrenador",
        "moko",
    ],

    "innovacion": [
        "innovacion agricola",
        "innovación agrícola",
        "innovacion agropecuaria",
        "innovación agropecuaria",
        "agricultura de precision",
        "agricultura de precisión",
        "agtech",
        "tecnologia agricola",
        "tecnología agrícola",
        "digitalizacion agricola",
        "digitalización agrícola",
        "tecnologias digitales",
        "tecnologías digitales",
        "biotecnologia",
        "biotecnología",
    ],

    "comercio_agropecuario": [
        "exportacion agricola",
        "exportación agrícola",
        "exportaciones agropecuarias",
        "exportacion agropecuaria",
        "exportación agropecuaria",
        "agroexportacion",
        "agroexportación",
        "mercados agricolas",
        "mercados agrícolas",
        "comercio agropecuario",
        "comercio agricola",
        "comercio agrícola",
        "cadena de valor",
        "cadenas de valor",
        "acceso a mercados",
        "competitividad agropecuaria",
    ],
}


# ============================================================================
# COOPERACIÓN INTERNACIONAL
# ============================================================================

INSTITUCIONES_COOPERACION = {

    "AECID": [
        "aecid",
        "agencia española de cooperación internacional",
        "agencia española de cooperacion internacional",
    ],

    "Union Europea": [
        "union europea",
        "unión europea",
        "comision europea",
        "comisión europea",
        "delegacion de la union europea",
        "delegación de la unión europea",
        "eeas",
        "european union",
        "eu",
    ],

    "GIZ": [
        "giz",
        "deutsche gesellschaft für internationale zusammenarbeit",
        "deutsche gesellschaft fur internationale zusammenarbeit",
    ],

    "FAO": [
        "fao",
        "organizacion de las naciones unidas para la alimentacion",
        "organización de las naciones unidas para la alimentación",
    ],

    "BID": [
        "bid",
        "banco interamericano de desarrollo",
        "inter-american development bank",
        "iadb",
    ],

    "BCIE": [
        "bcie",
        "banco centroamericano de integracion economica",
        "banco centroamericano de integración económica",
        "central american bank for economic integration",
    ],

    "CAF": [
        "caf",
        "banco de desarrollo de america latina",
        "banco de desarrollo de américa latina",
    ],

    "Banco Mundial": [
        "banco mundial",
        "world bank",
    ],

    "JICA": [
        "jica",
        "agencia de cooperacion internacional de japon",
        "agencia de cooperación internacional de japón",
    ],

    "KOICA": [
        "koica",
        "agencia de cooperacion internacional de corea",
        "agencia de cooperación internacional de corea",
    ],

    "USAID": [
        "usaid",
        "agencia de los estados unidos para el desarrollo internacional",
    ],

    "OIRSA": [
        "oirsa",
        "organismo internacional regional de sanidad agropecuaria",
    ],

    "SIECA": [
        "sieca",
        "secretaria de integracion economica centroamericana",
        "secretaría de integración económica centroamericana",
    ],
}


# ============================================================================
# OPORTUNIDADES
# ============================================================================

OPORTUNIDADES = {

    "convocatoria": [
        "convocatoria",
        "convocatorias",
        "llamada a propuestas",
        "llamado a propuestas",
        "call for proposals",
        "call for applications",
        "open call",
        "convocatoria de proyectos",
        "convocatoria abierta",
    ],

    "fondo": [
        "fondo concursable",
        "fondo competitivo",
        "fondo de financiamiento",
        "fondo",
        "fondos disponibles",
        "ventana de financiamiento",
        "financing window",
        "fund",
        "funding opportunity",
    ],

    "financiamiento": [
        "financiamiento",
        "financiacion",
        "financiación",
        "financiar proyectos",
        "financia proyectos",
        "recursos financieros",
        "apoyo financiero",
        "financial support",
        "financing",
        "funding",
        "grant",
        "grants",
        "subvencion",
        "subvención",
        "subvenciones",
        "donacion",
        "donación",
    ],

    "propuesta": [
        "presentar propuestas",
        "presentacion de propuestas",
        "presentación de propuestas",
        "solicitud de propuestas",
        "request for proposals",
        "request for applications",
        "expression of interest",
        "expressions of interest",
        "expresion de interes",
        "expresión de interés",
    ],

    "consultoria": [
        "consultoria",
        "consultoría",
        "servicios de consultoria",
        "servicios de consultoría",
        "consultor internacional",
        "consultora internacional",
        "consultoria tecnica",
        "consultoría técnica",
        "technical assistance",
    ],

    "licitacion": [
        "licitacion",
        "licitación",
        "concurso publico",
        "concurso público",
        "tender",
        "procurement",
        "contratacion",
        "contratación",
        "solicitud de cotizacion",
        "solicitud de cotización",
    ],

    "beca": [
        "beca",
        "becas",
        "scholarship",
        "scholarships",
        "fellowship",
        "fellowships",
    ],

    "pasantia": [
        "pasantia",
        "pasantía",
        "internship",
        "traineeship",
    ],

    "fecha_limite": [
        "fecha limite",
        "fecha límite",
        "deadline",
        "closing date",
        "cierre de convocatoria",
        "plazo de postulacion",
        "plazo de postulación",
    ],
}


# ============================================================================
# GEOGRAFÍA
# ============================================================================

GEOGRAFIA = {

    "Costa Rica": [
        "costa rica",
        "costarricense",
        "costarricenses",
        "san jose",
        "san josé",
        "limon",
        "limón",
        "guanacaste",
        "puntarenas",
        "alajuela",
        "cartago",
        "heredia",
        "turrialba",
        "sixaola",
        "sarquí",
        "sarchi",
    ],

    "Centroamerica": [
        "centroamerica",
        "centroamérica",
        "centroamericano",
        "centroamericana",
        "centroamericanos",
        "centroamericanas",
        "mesoamerica",
        "mesoamérica",
        "istmo centroamericano",
    ],

    "America Latina": [
        "america latina",
        "américa latina",
        "latinoamerica",
        "latinoamérica",
        "latinoamericano",
        "latinoamericana",
        "america latina y el caribe",
        "américa latina y el caribe",
        "lac",
    ],

    "Caribe": [
        "caribe",
        "caribbean",
    ],
}


# ============================================================================
# ENTIDADES DE ALTO VALOR
# ============================================================================

ENTIDADES_CRITICAS = {

    "MAG": [
        "mag",
        "ministerio de agricultura y ganaderia",
        "ministerio de agricultura y ganadería",
    ],

    "SFE": [
        "sfe",
        "servicio fitosanitario del estado",
    ],

    "SENASA": [
        "senasa",
        "servicio nacional de salud animal",
    ],

    "INDER": [
        "inder",
        "instituto de desarrollo rural",
    ],

    "PROCOMER": [
        "procomer",
        "promotora del comercio exterior",
    ],

    "OIRSA": [
        "oirsa",
    ],

    "IICA": [
        "iica",
        "instituto interamericano de cooperacion para la agricultura",
        "instituto interamericano de cooperación para la agricultura",
    ],
}


# ============================================================================
# TÉRMINOS NEGATIVOS
# ============================================================================
#
# No significa que una noticia que contenga una de estas palabras sea siempre
# irrelevante. Funcionan como penalizaciones contextuales.
# ============================================================================

NEGATIVOS = {

    "gastronomia": [
        "receta",
        "recetas",
        "pastel",
        "postre",
        "reposteria",
        "repostería",
        "ingredientes",
        "cocina",
        "cocinar",
        "gastronomia",
        "gastronomía",
        "restaurante",
        "chef",
        "menu",
        "menú",
    ],

    "entretenimiento": [
        "celebridad",
        "celebridades",
        "farándula",
        "farandula",
        "pelicula",
        "película",
        "serie",
        "television",
        "televisión",
        "actor",
        "actriz",
        "cantante",
        "musica",
        "música",
    ],

    "deportes": [
        "futbol",
        "fútbol",
        "baloncesto",
        "beisbol",
        "béisbol",
        "tenis",
        "formula 1",
        "fórmula 1",
        "mundial de futbol",
        "mundial de fútbol",
    ],

    "automoviles": [
        "automovil",
        "automóvil",
        "automoviles",
        "automóviles",
        "vehiculo",
        "vehículo",
        "vehiculos",
        "vehículos",
        "concesionario",
        "motor",
        "motorizado",
    ],

    "tecnologia_general": [
        "smartphone",
        "celular",
        "iphone",
        "android",
        "videojuego",
        "videojuegos",
    ],
}


# ============================================================================
# COMBINACIONES CONTEXTUALES
# ============================================================================

COMBINACIONES = [

    # ---------------------------------------------------------------------
    # COSTA RICA + AGRICULTURA
    # ---------------------------------------------------------------------

    (
        ["costa rica", "agricultura"],
        22,
        "Costa Rica + agricultura",
    ),

    (
        ["costa rica", "agropecuario"],
        22,
        "Costa Rica + sector agropecuario",
    ),

    (
        ["costa rica", "productores"],
        18,
        "Costa Rica + productores",
    ),

    (
        ["costa rica", "desarrollo rural"],
        22,
        "Costa Rica + desarrollo rural",
    ),

    (
        ["costa rica", "seguridad alimentaria"],
        24,
        "Costa Rica + seguridad alimentaria",
    ),

    # ---------------------------------------------------------------------
    # SANIDAD
    # ---------------------------------------------------------------------

    (
        ["costa rica", "plaga"],
        28,
        "Costa Rica + plaga",
    ),

    (
        ["costa rica", "fusarium"],
        35,
        "Costa Rica + Fusarium",
    ),

    (
        ["limon", "banano", "plaga"],
        40,
        "Limón + banano + plaga",
    ),

    (
        ["limon", "fusarium"],
        45,
        "Limón + Fusarium",
    ),

    (
        ["sanidad vegetal", "costa rica"],
        30,
        "Sanidad vegetal + Costa Rica",
    ),

    (
        ["sanidad animal", "costa rica"],
        30,
        "Sanidad animal + Costa Rica",
    ),

    # ---------------------------------------------------------------------
    # CENTROAMÉRICA
    # ---------------------------------------------------------------------

    (
        ["centroamerica", "agricultura"],
        24,
        "Centroamérica + agricultura",
    ),

    (
        ["centroamerica", "seguridad alimentaria"],
        26,
        "Centroamérica + seguridad alimentaria",
    ),

    (
        ["centroamerica", "desarrollo rural"],
        26,
        "Centroamérica + desarrollo rural",
    ),

    (
        ["centroamerica", "plaga"],
        30,
        "Centroamérica + plaga",
    ),

    # ---------------------------------------------------------------------
    # COOPERACIÓN
    # ---------------------------------------------------------------------

    (
        ["aecid", "convocatoria"],
        25,
        "AECID + convocatoria",
    ),

    (
        ["aecid", "fondo"],
        30,
        "AECID + fondo",
    ),

    (
        ["aecid", "financiamiento"],
        30,
        "AECID + financiamiento",
    ),

    (
        ["aecid", "agricultura"],
        22,
        "AECID + agricultura",
    ),

    (
        ["aecid", "centroamerica"],
        25,
        "AECID + Centroamérica",
    ),

    (
        ["union europea", "agricultura"],
        20,
        "UE + agricultura",
    ),

    (
        ["union europea", "convocatoria"],
        22,
        "UE + convocatoria",
    ),

    (
        ["union europea", "fondo"],
        25,
        "UE + fondo",
    ),

    (
        ["giz", "agricultura"],
        25,
        "GIZ + agricultura",
    ),

    (
        ["giz", "costa rica"],
        25,
        "GIZ + Costa Rica",
    ),

    (
        ["fao", "agricultura"],
        20,
        "FAO + agricultura",
    ),

    (
        ["oirsa", "plaga"],
        35,
        "OIRSA + plaga",
    ),

    (
        ["oirsa", "sanidad vegetal"],
        35,
        "OIRSA + sanidad vegetal",
    ),

    # ---------------------------------------------------------------------
    # FINANCIAMIENTO
    # ---------------------------------------------------------------------

    (
        ["fondo concursable", "centroamerica"],
        40,
        "Fondo concursable + Centroamérica",
    ),

    (
        ["fondo concursable", "agricultura"],
        38,
        "Fondo concursable + agricultura",
    ),

    (
        ["financiamiento", "agricultura"],
        32,
        "Financiamiento + agricultura",
    ),

    (
        ["grant", "agricultura"],
        32,
        "Grant + agricultura",
    ),

    (
        ["subvencion", "agricultura"],
        32,
        "Subvención + agricultura",
    ),

    (
        ["convocatoria", "agricultura"],
        34,
        "Convocatoria + agricultura",
    ),

    (
        ["convocatoria", "desarrollo rural"],
        35,
        "Convocatoria + desarrollo rural",
    ),

    (
        ["convocatoria", "seguridad alimentaria"],
        35,
        "Convocatoria + seguridad alimentaria",
    ),

    # ---------------------------------------------------------------------
    # COOPERACIÓN TRIANGULAR
    # ---------------------------------------------------------------------

    (
        ["cooperacion triangular", "costa rica"],
        40,
        "Cooperación triangular + Costa Rica",
    ),

    (
        ["cooperacion triangular", "agricultura"],
        38,
        "Cooperación triangular + agricultura",
    ),

    (
        ["cooperacion triangular", "centroamerica"],
        40,
        "Cooperación triangular + Centroamérica",
    ),

    # ---------------------------------------------------------------------
    # CAMBIO CLIMÁTICO
    # ---------------------------------------------------------------------

    (
        ["cambio climatico", "agricultura"],
        28,
        "Cambio climático + agricultura",
    ),

    (
        ["sequia", "agricultura"],
        25,
        "Sequía + agricultura",
    ),

    (
        ["inundacion", "agricultura"],
        25,
        "Inundación + agricultura",
    ),

    (
        ["el nino", "agricultura"],
        25,
        "El Niño + agricultura",
    ),

    # ---------------------------------------------------------------------
    # COMERCIO AGROPECUARIO
    # ---------------------------------------------------------------------

    (
        ["exportacion", "agricultura"],
        25,
        "Exportación + agricultura",
    ),

    (
        ["comercio agricola", "centroamerica"],
        30,
        "Comercio agrícola + Centroamérica",
    ),

    (
        ["acceso a mercados", "agricultura"],
        28,
        "Acceso a mercados + agricultura",
    ),
]


# ============================================================================
# NORMALIZACIÓN
# ============================================================================

def normalizar_texto(texto: str) -> str:
    """
    Convierte el texto a una forma más fácil de comparar.

    - HTML entities
    - HTML tags
    - minúsculas
    - elimina acentos
    - normaliza espacios
    """

    if not texto:
        return ""

    texto = html.unescape(str(texto))

    texto = re.sub(
        r"<script.*?>.*?</script>",
        " ",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    texto = re.sub(
        r"<style.*?>.*?</style>",
        " ",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    texto = re.sub(r"<[^>]+>", " ", texto)

    texto = texto.lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        char
        for char in texto
        if unicodedata.category(char) != "Mn"
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpiar_html(texto: str) -> str:
    if not texto:
        return ""

    texto = html.unescape(str(texto))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


# ============================================================================
# MATCHING
# ============================================================================

def contiene(texto: str, termino: str) -> bool:
    """
    Matching sencillo pero evitando falsos positivos obvios.

    Ejemplo:
        "mag" no debería coincidir dentro de "imagen".
    """

    termino = normalizar_texto(termino)

    if not termino:
        return False

    if " " in termino:
        return termino in texto

    return re.search(
        rf"\b{re.escape(termino)}\b",
        texto,
        flags=re.IGNORECASE,
    ) is not None


def coincidencias(texto: str, terminos: list[str]) -> list[str]:
    encontrados = []

    for termino in terminos:
        if contiene(texto, termino):
            encontrados.append(termino)

    return encontrados


# ============================================================================
# FECHA
# ============================================================================

def obtener_fecha(entry: Any) -> datetime | None:
    """
    Intenta obtener la fecha del RSS en distintos formatos.
    """

    posibles = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]

    for valor in posibles:

        if not valor:
            continue

        # feedparser puede proporcionar parsed time.
        for campo in ("published_parsed", "updated_parsed", "created_parsed"):

            estructura = entry.get(campo)

            if estructura:
                try:
                    return datetime(
                        estructura.tm_year,
                        estructura.tm_mon,
                        estructura.tm_mday,
                        estructura.tm_hour,
                        estructura.tm_min,
                        estructura.tm_sec,
                        tzinfo=timezone.utc,
                    )
                except Exception:
                    pass

        # Texto RFC / RSS.
        try:
            fecha = parsedate_to_datetime(str(valor))

            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)

            return fecha
        except Exception:
            pass

        # ISO.
        try:
            valor_iso = str(valor).replace("Z", "+00:00")
            fecha = datetime.fromisoformat(valor_iso)

            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)

            return fecha
        except Exception:
            pass

    return None


def dias_desde_publicacion(fecha: datetime | None) -> int | None:

    if not fecha:
        return None

    ahora = datetime.now(timezone.utc)

    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    diferencia = ahora - fecha

    return max(0, diferencia.days)


def calcular_bonus_recencia(fecha: datetime | None) -> int:

    dias = dias_desde_publicacion(fecha)

    if dias is None:
        return 0

    if dias <= 1:
        return 10

    if dias <= 3:
        return 8

    if dias <= 7:
        return 6

    if dias <= 14:
        return 4

    if dias <= 30:
        return 2

    return 0


# ============================================================================
# IMÁGENES
# ============================================================================

import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup


PLACEHOLDER_IMAGEN = "/static/img/news-placeholder.jpg"


def extraer_imagen(entry):
    """
    Intenta obtener la imagen de una noticia usando varias fuentes:

    1. media_content
    2. media_thumbnail
    3. enclosure
    4. HTML del summary/content
    5. og:image de la página original
    6. twitter:image de la página original
    7. placeholder local
    """

    # ---------------------------------------------------------
    # 1. media_content
    # ---------------------------------------------------------
    media_content = entry.get("media_content", [])

    if media_content:
        for media in media_content:
            url = media.get("url")

            if url and es_url_imagen_valida(url):
                return url


    # ---------------------------------------------------------
    # 2. media_thumbnail
    # ---------------------------------------------------------
    media_thumbnail = entry.get("media_thumbnail", [])

    if media_thumbnail:
        for media in media_thumbnail:
            url = media.get("url")

            if url and es_url_imagen_valida(url):
                return url


    # ---------------------------------------------------------
    # 3. enclosure
    # ---------------------------------------------------------
    enclosures = entry.get("enclosures", [])

    for enclosure in enclosures:
        url = enclosure.get("href") or enclosure.get("url")
        tipo = enclosure.get("type", "")

        if url and (
            tipo.startswith("image/")
            or es_url_imagen_valida(url)
        ):
            return url


    # ---------------------------------------------------------
    # 4. Buscar <img> dentro del RSS
    # ---------------------------------------------------------
    html = ""

    if entry.get("summary"):
        html += entry.get("summary", "")

    if entry.get("description"):
        html += entry.get("description", "")

    if entry.get("content"):
        for content in entry.get("content", []):
            html += content.get("value", "")


    if html:
        soup = BeautifulSoup(html, "html.parser")

        for img in soup.find_all("img"):
            url = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("data-original")
            )

            if url and es_url_imagen_valida(url):
                return url


    # ---------------------------------------------------------
    # 5 y 6. Buscar imagen en la página original
    # ---------------------------------------------------------
    link = entry.get("link")

    if link:
        imagen = extraer_imagen_desde_pagina(link)

        if imagen:
            return imagen


    # ---------------------------------------------------------
    # 7. Placeholder
    # ---------------------------------------------------------
    return PLACEHOLDER_IMAGEN


def extraer_imagen_desde_pagina(url):
    """
    Visita la página original y busca:

    - og:image
    - twitter:image
    - imágenes <img>
    """

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/130.0 Safari/537.36"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=8,
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # -----------------------------------------------------
        # Open Graph
        # -----------------------------------------------------
        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if og_image and og_image.get("content"):
            imagen = urljoin(
                url,
                og_image["content"]
            )

            if es_url_imagen_valida(imagen):
                return imagen


        # -----------------------------------------------------
        # Twitter Card
        # -----------------------------------------------------
        twitter_image = soup.find(
            "meta",
            attrs={
                "name": "twitter:image"
            }
        )

        if twitter_image and twitter_image.get("content"):
            imagen = urljoin(
                url,
                twitter_image["content"]
            )

            if es_url_imagen_valida(imagen):
                return imagen


        # -----------------------------------------------------
        # Buscar imágenes de la página
        # -----------------------------------------------------
        for img in soup.find_all("img"):

            imagen = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("data-original")
            )

            if not imagen:
                continue

            imagen = urljoin(url, imagen)

            if es_url_imagen_valida(imagen):
                return imagen


    except requests.RequestException:
        pass

    except Exception:
        pass


    return None


def es_url_imagen_valida(url):
    """
    Verifica que la URL tenga apariencia de imagen.
    """

    if not url:
        return False

    url = url.lower()

    # Evitar imágenes diminutas, trackers, iconos, etc.
    extensiones = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".avif",
    )

    if any(extension in url for extension in extensiones):
        return True

    # Muchas imágenes usan URLs sin extensión.
    # En ese caso permitimos la URL si parece provenir
    # de un servicio de imágenes.
    patrones = (
        "image",
        "images",
        "img",
        "media",
        "photo",
        "foto",
        "picture",
        "cdn",
    )

    return any(
        patron in url
        for patron in patrones
    )

# ============================================================================
# CLASIFICACIÓN
# ============================================================================

def detectar_sectores(texto: str) -> dict[str, list[str]]:

    resultado = {}

    for sector, terminos in SECTORES_PRINCIPALES.items():

        encontrados = coincidencias(texto, terminos)

        if encontrados:
            resultado[sector] = encontrados

    return resultado


def detectar_geografia(texto: str) -> dict[str, list[str]]:

    resultado = {}

    for region, terminos in GEOGRAFIA.items():

        encontrados = coincidencias(texto, terminos)

        if encontrados:
            resultado[region] = encontrados

    return resultado


def detectar_instituciones(texto: str) -> dict[str, list[str]]:

    resultado = {}

    todos = {
        **INSTITUCIONES_COOPERACION,
        **ENTIDADES_CRITICAS,
    }

    for institucion, terminos in todos.items():

        encontrados = coincidencias(texto, terminos)

        if encontrados:
            resultado[institucion] = encontrados

    return resultado


def detectar_oportunidades(texto: str) -> dict[str, list[str]]:

    resultado = {}

    for tipo, terminos in OPORTUNIDADES.items():

        encontrados = coincidencias(texto, terminos)

        if encontrados:
            resultado[tipo] = encontrados

    return resultado


def detectar_negativos(texto: str) -> dict[str, list[str]]:

    resultado = {}

    for categoria, terminos in NEGATIVOS.items():

        encontrados = coincidencias(texto, terminos)

        if encontrados:
            resultado[categoria] = encontrados

    return resultado


# ============================================================================
# SCORE TEMÁTICO
# ============================================================================

PESO_SECTOR = {

    "agricultura": 12,
    "cultivos": 8,
    "ganaderia": 10,
    "pesca": 10,
    "desarrollo_rural": 12,
    "seguridad_alimentaria": 12,
    "cambio_climatico": 8,
    "biodiversidad": 7,
    "sanidad_agropecuaria": 15,
    "innovacion": 8,
    "comercio_agropecuario": 8,
}


def score_sectores(
    titulo: str,
    resumen: str,
) -> tuple[int, list[str]]:

    score = 0
    motivos = []

    titulo_n = normalizar_texto(titulo)
    resumen_n = normalizar_texto(resumen)

    for sector, terminos in SECTORES_PRINCIPALES.items():

        encontrados_titulo = coincidencias(
            titulo_n,
            terminos,
        )

        encontrados_resumen = coincidencias(
            resumen_n,
            terminos,
        )

        if not encontrados_titulo and not encontrados_resumen:
            continue

        peso = PESO_SECTOR.get(sector, 5)

        if encontrados_titulo:
            score += peso * 2

            motivos.append(
                f"Sector en título: {sector}"
            )

        else:
            score += peso

            motivos.append(
                f"Sector en resumen: {sector}"
            )

    return score, motivos


# ============================================================================
# SCORE GEOGRÁFICO
# ============================================================================

def score_geografia(
    titulo: str,
    resumen: str,
) -> tuple[int, list[str]]:

    score = 0
    motivos = []

    titulo_n = normalizar_texto(titulo)
    resumen_n = normalizar_texto(resumen)

    encontrados = detectar_geografia(
        f"{titulo_n} {resumen_n}"
    )

    if "Costa Rica" in encontrados:

        score += 15
        motivos.append("Costa Rica")

        if coincidencias(titulo_n, GEOGRAFIA["Costa Rica"]):
            score += 8
            motivos.append("Costa Rica aparece en título")

    if "Centroamerica" in encontrados:

        score += 12
        motivos.append("Centroamérica")

        if coincidencias(
            titulo_n,
            GEOGRAFIA["Centroamerica"],
        ):
            score += 5
            motivos.append("Centroamérica aparece en título")

    if "America Latina" in encontrados:

        score += 5
        motivos.append("América Latina")

    if "Caribe" in encontrados:

        score += 3
        motivos.append("Caribe")

    return score, motivos


# ============================================================================
# SCORE DE COOPERACIÓN
# ============================================================================

def score_cooperacion(
    titulo: str,
    resumen: str,
) -> tuple[int, list[str]]:

    score = 0
    motivos = []

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    instituciones = detectar_instituciones(texto)

    for institucion in instituciones:

        # Institución sola = señal moderada.
        score += 2

        motivos.append(
            f"Institución: {institucion}"
        )

    return score, motivos


# ============================================================================
# SCORE DE OPORTUNIDAD
# ============================================================================

PESO_OPORTUNIDAD = {

    "convocatoria": 18,
    "fondo": 20,
    "financiamiento": 20,
    "propuesta": 18,
    "consultoria": 12,
    "licitacion": 8,
    "beca": 8,
    "pasantia": 5,
    "fecha_limite": 8,
}


def score_oportunidad(
    titulo: str,
    resumen: str,
) -> tuple[int, list[str], bool]:

    score = 0
    motivos = []

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    oportunidades = detectar_oportunidades(texto)

    for tipo, encontrados in oportunidades.items():

        peso = PESO_OPORTUNIDAD.get(tipo, 0)

        if not peso:
            continue

        score += peso

        motivos.append(
            f"Oportunidad: {tipo}"
        )

    es_oportunidad = bool(oportunidades)

    return score, motivos, es_oportunidad


# ============================================================================
# COMBINACIONES
# ============================================================================

def score_combinaciones(
    texto: str,
) -> tuple[int, list[str]]:

    score = 0
    motivos = []

    for terminos, peso, descripcion in COMBINACIONES:

        if all(
            contiene(texto, termino)
            for termino in terminos
        ):
            score += peso

            motivos.append(
                f"Contexto: {descripcion}"
            )

    return score, motivos


# ============================================================================
# PENALIZACIONES
# ============================================================================

PENALIZACIONES = {

    "gastronomia": 15,
    "entretenimiento": 20,
    "deportes": 25,
    "automoviles": 18,
    "tecnologia_general": 8,
}


def score_penalizaciones(
    titulo: str,
    resumen: str,
) -> tuple[int, list[str]]:

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    negativos = detectar_negativos(texto)

    penalizacion = 0
    motivos = []

    for categoria, encontrados in negativos.items():

        puntos = PENALIZACIONES.get(
            categoria,
            0,
        )

        if not puntos:
            continue

        # No todas las apariciones se acumulan.
        # Una categoría negativa tiene una sola penalización.
        penalizacion += puntos

        motivos.append(
            f"Penalización: {categoria}"
        )

    return penalizacion, motivos


# ============================================================================
# REGLAS ESPECIALES
# ============================================================================

def es_receta_o_gastronomia_irrelevante(
    titulo: str,
    resumen: str,
) -> bool:

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    tiene_agro = any(
        contiene(texto, termino)
        for terminos in SECTORES_PRINCIPALES.values()
        for termino in terminos
    )

    tiene_gastronomia = any(
        contiene(texto, termino)
        for termino in NEGATIVOS["gastronomia"]
    )

    tiene_receta = any(
        contiene(texto, termino)
        for termino in [
            "receta",
            "pastel",
            "postre",
            "ingredientes",
            "cocinar",
        ]
    )

    # Si es claramente gastronómico y no tiene contexto
    # agropecuario relevante, descartamos.
    if tiene_gastronomia and tiene_receta and not tiene_agro:
        return True

    return False


def es_deporte_irrelevante(
    titulo: str,
    resumen: str,
) -> bool:

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    tiene_deporte = any(
        contiene(texto, termino)
        for termino in NEGATIVOS["deportes"]
    )

    tiene_contexto_iica = any(
        contiene(texto, termino)
        for terminos in [
            SECTORES_PRINCIPALES["agricultura"],
            SECTORES_PRINCIPALES["desarrollo_rural"],
            SECTORES_PRINCIPALES["seguridad_alimentaria"],
        ]
        for termino in terminos
    )

    return tiene_deporte and not tiene_contexto_iica


# ============================================================================
# CLASIFICACIÓN DEL TIPO DE CONTENIDO
# ============================================================================

def clasificar_tipo(
    titulo: str,
    resumen: str,
) -> str:

    texto = normalizar_texto(
        f"{titulo} {resumen}"
    )

    oportunidades = detectar_oportunidades(texto)

    if "fondo" in oportunidades:
        return "fondo"

    if "convocatoria" in oportunidades:
        return "convocatoria"

    if "financiamiento" in oportunidades:
        return "financiamiento"

    if "consultoria" in oportunidades:
        return "consultoria"

    if "licitacion" in oportunidades:
        return "licitacion"

    if "beca" in oportunidades:
        return "beca"

    if "pasantia" in oportunidades:
        return "pasantia"

    if any(
        contiene(texto, termino)
        for termino in [
            "fusarium",
            "plaga",
            "enfermedad vegetal",
            "enfermedad animal",
            "sanidad vegetal",
            "sanidad animal",
            "fitosanitario",
            "zoosanitario",
        ]
    ):
        return "alerta_sanitaria"

    if any(
        contiene(texto, termino)
        for termino in [
            "cooperacion",
            "cooperación",
            "cooperacion triangular",
            "cooperación triangular",
        ]
    ):
        return "cooperacion"

    if any(
        contiene(texto, termino)
        for termino in [
            "proyecto",
            "programa",
            "iniciativa",
        ]
    ):
        return "proyecto"

    return "noticia"


# ============================================================================
# PRIORIDAD
# ============================================================================

def determinar_prioridad(
    score: int,
    es_oportunidad: bool,
    tipo: str,
) -> str:

    if tipo in {
        "fondo",
        "convocatoria",
        "financiamiento",
    } and score >= 65:
        return "critica"

    if tipo == "alerta_sanitaria" and score >= 65:
        return "critica"

    if score >= 75:
        return "critica"

    if score >= 55:
        return "alta"

    if score >= 35:
        return "media"

    return "baja"


# ============================================================================
# SCORE PRINCIPAL
# ============================================================================

def analizar_noticia(
    titulo: str,
    resumen: str,
    fuente: dict,
    fecha: datetime | None = None,
) -> dict:

    titulo_limpio = limpiar_html(titulo)
    resumen_limpio = limpiar_html(resumen)

    texto = normalizar_texto(
        f"{titulo_limpio} {resumen_limpio}"
    )

    motivos = []

    # ---------------------------------------------------------------------
    # DESCARTES DUROS
    # ---------------------------------------------------------------------

    if es_receta_o_gastronomia_irrelevante(
        titulo_limpio,
        resumen_limpio,
    ):

        return {
            "aceptada": False,
            "score": 0,
            "motivos": [
                "Contenido gastronómico/receta sin contexto agropecuario"
            ],
        }

    if es_deporte_irrelevante(
        titulo_limpio,
        resumen_limpio,
    ):

        return {
            "aceptada": False,
            "score": 0,
            "motivos": [
                "Contenido deportivo sin contexto IICA"
            ],
        }

    # ---------------------------------------------------------------------
    # SECTORES
    # ---------------------------------------------------------------------

    score_sector, motivos_sector = score_sectores(
        titulo_limpio,
        resumen_limpio,
    )

    motivos.extend(motivos_sector)

    # ---------------------------------------------------------------------
    # GEOGRAFÍA
    # ---------------------------------------------------------------------

    score_geo, motivos_geo = score_geografia(
        titulo_limpio,
        resumen_limpio,
    )

    motivos.extend(motivos_geo)

    # ---------------------------------------------------------------------
    # COOPERACIÓN
    # ---------------------------------------------------------------------

    score_coop, motivos_coop = score_cooperacion(
        titulo_limpio,
        resumen_limpio,
    )

    motivos.extend(motivos_coop)

    # ---------------------------------------------------------------------
    # OPORTUNIDAD
    # ---------------------------------------------------------------------

    (
        score_oportunidad_total,
        motivos_oportunidad,
        es_oportunidad,
    ) = score_oportunidad(
        titulo_limpio,
        resumen_limpio,
    )

    motivos.extend(motivos_oportunidad)

    # ---------------------------------------------------------------------
    # CONTEXTO
    # ---------------------------------------------------------------------

    (
        score_contexto,
        motivos_contexto,
    ) = score_combinaciones(
        texto
    )

    motivos.extend(motivos_contexto)

    # ---------------------------------------------------------------------
    # PENALIZACIONES
    # ---------------------------------------------------------------------

    (
        penalizacion,
        motivos_penalizacion,
    ) = score_penalizaciones(
        titulo_limpio,
        resumen_limpio,
    )

    motivos.extend(motivos_penalizacion)

    # ---------------------------------------------------------------------
    # FUENTE
    # ---------------------------------------------------------------------

    peso_fuente = fuente.get("peso", 0)

    score_fuente = peso_fuente

    if score_fuente:
        motivos.append(
            f"Fuente prioritaria: {fuente.get('nombre', 'Fuente')}"
        )

    # ---------------------------------------------------------------------
    # RECENCIA
    # ---------------------------------------------------------------------

    bonus_recencia = calcular_bonus_recencia(
        fecha
    )

    if bonus_recencia:
        motivos.append(
            f"Contenido reciente: +{bonus_recencia}"
        )

    # ---------------------------------------------------------------------
    # SCORE
    # ---------------------------------------------------------------------

    score = (
        score_sector
        + score_geo
        + score_coop
        + score_oportunidad_total
        + score_contexto
        + score_fuente
        + bonus_recencia
        - penalizacion
    )

    # ---------------------------------------------------------------------
    # TIPO
    # ---------------------------------------------------------------------

    tipo = clasificar_tipo(
        titulo_limpio,
        resumen_limpio,
    )

    # ---------------------------------------------------------------------
    # REGLAS DE ELEGIBILIDAD
    # ---------------------------------------------------------------------

    tiene_contexto_agro = (
        score_sector >= 8
    )

    tiene_contexto_geografico = (
        score_geo >= 12
    )

    tiene_oportunidad_fuerte = (
        score_oportunidad_total >= 18
    )

    tiene_cooperacion_relevante = (
        score_coop >= 4
        and (
            score_sector >= 8
            or score_geo >= 12
            or score_contexto >= 15
        )
    )

    # Una oportunidad no debería entrar solo porque diga
    # "convocatoria".
    #
    # Necesita contexto.
    if es_oportunidad:

        oportunidad_valida = (
            tiene_contexto_agro
            or tiene_contexto_geografico
            or score_contexto >= 20
        )

        if not oportunidad_valida:

            return {
                "aceptada": False,
                "score": score,
                "tipo": tipo,
                "motivos": motivos + [
                    "Oportunidad sin contexto suficientemente relevante para IICA"
                ],
            }

    # Para noticias normales:
    #
    # No basta con una institución internacional.
    #
    # AECID + noticia genérica = no necesariamente relevante.
    if not es_oportunidad:

        noticia_valida = (
            (
                tiene_contexto_agro
                and tiene_contexto_geografico
            )
            or (
                tiene_contexto_agro
                and score_contexto >= 20
            )
            or (
                tipo == "alerta_sanitaria"
                and (
                    tiene_contexto_agro
                    or tiene_contexto_geografico
                )
            )
            or tiene_cooperacion_relevante
        )

        if not noticia_valida:

            return {
                "aceptada": False,
                "score": score,
                "tipo": tipo,
                "motivos": motivos + [
                    "Noticia sin contexto IICA suficientemente fuerte"
                ],
            }

    # ---------------------------------------------------------------------
    # RESULTADO
    # ---------------------------------------------------------------------

    prioridad = determinar_prioridad(
        score,
        es_oportunidad,
        tipo,
    )

    return {
        "aceptada": score >= MIN_SCORE,
        "score": score,
        "prioridad": prioridad,
        "tipo": tipo,
        "es_oportunidad": es_oportunidad,
        "motivos": motivos,
    }


# ============================================================================
# DEDUPLICACIÓN
# ============================================================================

def clave_deduplicacion(titulo: str) -> str:

    texto = normalizar_texto(titulo)

    # Eliminamos palabras muy comunes para detectar titulares
    # ligeramente modificados.
    stopwords = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "de",
        "del",
        "en",
        "para",
        "con",
        "por",
        "y",
        "a",
        "que",
    }

    palabras = [
        palabra
        for palabra in texto.split()
        if palabra not in stopwords
    ]

    return " ".join(palabras)


def deduplicar(noticias: list[dict]) -> list[dict]:

    resultado = {}

    for noticia in noticias:

        clave = clave_deduplicacion(
            noticia["titulo"]
        )

        existente = resultado.get(clave)

        if not existente:

            resultado[clave] = noticia
            continue

        # Conservamos el artículo con mayor score.
        if noticia["score"] > existente["score"]:

            resultado[clave] = noticia

    return list(resultado.values())


# ============================================================================
# OBTENER FEED
# ============================================================================

def cargar_feed(url: str):
    """
    Carga un feed utilizando feedparser.

    Importación local para que el archivo pueda cargarse aunque
    feedparser todavía no esté instalado durante determinadas
    tareas administrativas.
    """

    import feedparser

    return feedparser.parse(url)


# ============================================================================
# OBTENER NOTICIAS
# ============================================================================

def obtener_noticias(
    max_items: int = MAX_ITEMS_DEFAULT,
) -> list[dict]:

    noticias = []

    for fuente in RSS_SOURCES:

        url = fuente["url"]

        try:
            feed = cargar_feed(url)

        except Exception as exc:

            print(
                f"[RSS] Error cargando {fuente['nombre']}: {exc}"
            )

            continue

        if getattr(feed, "bozo", False):

            print(
                f"[RSS] Advertencia en {fuente['nombre']}: "
                f"{getattr(feed, 'bozo_exception', '')}"
            )

        titulo_fuente = (
            feed.feed.get("title")
            or fuente["nombre"]
        )

        for entry in feed.entries:

            titulo = limpiar_html(
                entry.get("title", "")
            )

            if not titulo:
                continue

            resumen = limpiar_html(
                entry.get("summary", "")
                or entry.get("description", "")
            )

            # Si content existe y el summary es muy pequeño,
            # aprovechamos también content.
            contenido = entry.get("content", "")

            if isinstance(contenido, list):

                contenido = " ".join(
                    item.get("value", "")
                    for item in contenido
                    if isinstance(item, dict)
                )

            if len(resumen) < 100 and contenido:

                resumen = limpiar_html(
                    contenido
                )

            fecha = obtener_fecha(entry)

            analisis = analizar_noticia(
                titulo=titulo,
                resumen=resumen,
                fuente=fuente,
                fecha=fecha,
            )

            if not analisis.get("aceptada"):
                continue

            link = (
                entry.get("link")
                or entry.get("id")
                or ""
            )

            imagen = extraer_imagen(entry)

            noticias.append(
                {
                    "titulo": titulo,

                    "imagen": imagen,

                    "link": link,

                    "fecha": (
                        fecha.isoformat()
                        if fecha
                        else entry.get("published", "")
                    ),

                    "resumen": resumen[:400],

                    "fuente": titulo_fuente,

                    "fuente_configurada": fuente["nombre"],

                    "tipo_fuente": fuente["tipo"],

                    "score": analisis["score"],

                    "prioridad": analisis["prioridad"],

                    "tipo": analisis["tipo"],

                    "es_oportunidad": analisis[
                        "es_oportunidad"
                    ],

                    "motivos": analisis["motivos"],

                    "pais": fuente.get("pais", []),
                }
            )

    # ---------------------------------------------------------------------
    # DEDUPLICAR
    # ---------------------------------------------------------------------

    noticias = deduplicar(noticias)

    # ---------------------------------------------------------------------
    # ORDEN
    # ---------------------------------------------------------------------
    #
    # Primero score.
    # Después fecha.
    #
    # IMPORTANTE:
    # Antes tenías reverse=False.
    # Eso colocaba lo menos relevante arriba.
    # ---------------------------------------------------------------------

    noticias.sort(
        key=lambda noticia: (
            noticia.get("score", 0),
            noticia.get("fecha", ""),
        ),
        reverse=True,
    )

    return noticias[:max_items]


# ============================================================================
# FUNCIONES ESPECÍFICAS
# ============================================================================

def obtener_oportunidades(
    max_items: int = 12,
) -> list[dict]:

    noticias = obtener_noticias(
        max_items=max_items * 3
    )

    oportunidades = [
        noticia
        for noticia in noticias
        if noticia.get("es_oportunidad")
    ]

    oportunidades.sort(
        key=lambda noticia: (
            noticia.get("score", 0),
            noticia.get("fecha", ""),
        ),
        reverse=True,
    )

    return oportunidades[:max_items]


def obtener_alertas_agropecuarias(
    max_items: int = 12,
) -> list[dict]:

    noticias = obtener_noticias(
        max_items=max_items * 3
    )

    alertas = [
        noticia
        for noticia in noticias
        if noticia.get("tipo")
        == "alerta_sanitaria"
    ]

    alertas.sort(
        key=lambda noticia: (
            noticia.get("score", 0),
            noticia.get("fecha", ""),
        ),
        reverse=True,
    )

    return alertas[:max_items]


# ============================================================================
# DEBUG
# ============================================================================

def analizar_texto_manual(
    titulo: str,
    resumen: str = "",
) -> dict:
    """
    Permite probar manualmente el algoritmo.

    Ejemplo:

        resultado = analizar_texto_manual(
            "Nueva plaga amenaza al banano en Limón"
        )

    Útil para ir afinando el algoritmo sin consultar RSS.
    """

    fuente_prueba = {
        "nombre": "Prueba",
        "tipo": "prueba",
        "peso": 0,
    }

    return analizar_noticia(
        titulo=titulo,
        resumen=resumen,
        fuente=fuente_prueba,
        fecha=datetime.now(timezone.utc),
    )


# ============================================================================
# EJEMPLOS DE PRUEBA
# ============================================================================

if __name__ == "__main__":

    ejemplos = [

        (
            "Cómo preparar un delicioso pastel de banano",
            "Receta sencilla con banano, harina, huevos y azúcar.",
        ),

        (
            "Nueva plaga amenaza cultivos de banano en Limón",
            "Autoridades agrícolas refuerzan la vigilancia fitosanitaria "
            "ante el riesgo de Fusarium R4T.",
        ),

        (
            "AECID abre fondo concursable para países de Centroamérica",
            "Las organizaciones podrán presentar propuestas para financiar "
            "proyectos de agricultura sostenible y desarrollo rural.",
        ),

        (
            "Unión Europea pide a China limitar exportaciones de vehículos híbridos",
            "Bruselas busca frenar el repunte de importaciones desde Pekín.",
        ),

        (
            "AECID presenta nuevo proyecto cultural",
            "La cooperación española apoyará actividades culturales.",
        ),

        (
            "Costa Rica y la Unión Europea fortalecen cooperación triangular",
            "Los nuevos proyectos incluyen agricultura sostenible, "
            "acción climática y desarrollo regional.",
        ),
    ]

    for titulo, resumen in ejemplos:

        resultado = analizar_texto_manual(
            titulo,
            resumen,
        )

        print("\n" + "=" * 80)
        print(titulo)
        print("=" * 80)

        print(
            "Aceptada:",
            resultado.get("aceptada"),
        )

        print(
            "Score:",
            resultado.get("score"),
        )

        print(
            "Prioridad:",
            resultado.get("prioridad"),
        )

        print(
            "Tipo:",
            resultado.get("tipo"),
        )

        print(
            "Oportunidad:",
            resultado.get("es_oportunidad"),
        )

        print("Motivos:")

        for motivo in resultado.get("motivos", []):
            print("  -", motivo)