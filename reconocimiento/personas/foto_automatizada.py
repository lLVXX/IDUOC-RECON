# personas/foto_automatizada.py

from personas.models import EstudianteFoto
from core.helpers.arcface_microservice import obtener_embedding_desde_microservicio

def guardar_foto_automatica(estudiante, imagen_file):
    """
    Agrega una nueva foto automática después de clase.
    - Mantiene como máximo 4 fotos automáticas.
    - Si ya hay 4, elimina la más antigua.
    - Solo debe llamarse cuando el sistema decida guardar una foto tras asistencia.
    """
    imagen_file.seek(0)
    embedding = obtener_embedding_desde_microservicio(imagen_file)
    if embedding is None:
        return False  # Si no hay rostro, no se guarda

    fotos_auto = EstudianteFoto.objects.filter(estudiante=estudiante, es_base=False).order_by('fecha_creacion')
    if fotos_auto.count() >= 4:
        fotos_auto.first().delete()  # Elimina la más antigua

    from numpy import array
    nueva_foto = EstudianteFoto.objects.create(
        estudiante=estudiante,
        imagen=imagen_file,
        embedding=array(embedding, dtype='float32').tobytes(),
        es_base=False
    )
    return True
