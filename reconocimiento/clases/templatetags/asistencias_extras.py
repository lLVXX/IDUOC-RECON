# clases/templatetags/asistencias_extras.py
from django import template

register = template.Library()

@register.filter
def dict_get(d, k):
    """Obtiene d[k] o None si no existe."""
    return d.get(k)

@register.filter
def has_key(d, k):
    """True si d tiene la key k."""
    return k in d

@register.filter
def is_presente(asistencia):
    """True si el objeto asistencia indica presente."""
    return getattr(asistencia, "presente", None)
