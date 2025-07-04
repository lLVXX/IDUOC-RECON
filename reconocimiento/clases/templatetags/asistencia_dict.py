from django import template

register = template.Library()

@register.filter
def dict_get(diccionario, clave):
    try:
        return diccionario.get(clave)
    except Exception:
        return None
