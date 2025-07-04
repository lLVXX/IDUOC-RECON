from django import template
register = template.Library()

@register.filter
def get_asistencia(asistencias, estudiante):
    """Dado el dict de asistencias y el estudiante, retorna la asistencia (o None)"""
    return asistencias.get(estudiante.id, None)



