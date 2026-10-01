import os
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def basename(value):
    """Devuelve únicamente el nombre del archivo eliminando las rutas relativas o absolutas."""
    if not value:
        return ""
    return os.path.basename(str(value))