# personas/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from .models import EstudianteFoto


MAX_DINAMICAS = 5


@receiver(post_save, sender=EstudianteFoto)
def mantener_cola_fotos(sender, instance, created, **kwargs):
    """
    Tras guardar una foto dinámica, mantiene un máximo de 5 fotos dinámicas por estudiante.
    La foto base (es_base=True) nunca se elimina.
    Imprime mensajes para depuración.
    """
    if created and not instance.es_base:
        # Obtiene todas las fotos dinámicas ordenadas por fecha (más recientes primero)
        fotos_dinamicas = EstudianteFoto.objects.filter(
            estudiante=instance.estudiante,
            es_base=False
        ).order_by('-created_at')

        total = fotos_dinamicas.count()
        print(f"[FIFO] Foto dinámica agregada para {instance.estudiante.username}. "
              f"Total dinámicas antes de recorte: {total}")

        # Si hay más de 5, elimina las más antiguas
        for foto in fotos_dinamicas[5:]:
            default_storage.delete(foto.imagen.name)
            foto.delete()
            print(f"[FIFO] Foto antigua eliminada: {foto.imagen.name}")

        restantes = EstudianteFoto.objects.filter(
            estudiante=instance.estudiante,
            es_base=False
        ).count()
        print(f"[FIFO] Mantenimiento completo. Dinámicas restantes: {restantes}")






@receiver(post_save, sender=EstudianteFoto)
def mantener_fifo_dinamicas(sender, instance: EstudianteFoto, created: bool, **kwargs):
    """
    Después de crear una foto (dinámica), elimina las más antiguas si hay > MAX_DINAMICAS.
    Nunca toca las fotos con es_base=True.
    """
    if not created or instance.es_base:
        return

    est = instance.estudiante
    # Recuperar solo dinámicas (es_base=False), en orden ascendente (más antiguas primero)
    qs = EstudianteFoto.objects.filter(estudiante=est, es_base=False) \
                               .order_by('created_at')

    total = qs.count()
    # Si excede el límite, eliminar las más antiguas
    if total > MAX_DINAMICAS:
        # Cantidad a borrar
        exceso = total - MAX_DINAMICAS
        for foto in qs[:exceso]:
            foto_name = foto.imagen.name
            foto.delete()
            print(f"[FIFO] Eliminada foto dinámica antigua: {foto_name}")