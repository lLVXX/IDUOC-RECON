# clases/templatetags/dict_extras.py
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@register.filter
def dict_get(d, key):
    """Obtiene el valor de un diccionario por clave"""
    if d and key in d:
        return d[key]
    return None


@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})
