# PERSONAS/MODELS.PY

from django.db import models
from pgvector.django import VectorField
from django.utils.timezone import now
from core.models import CustomUser
from sedes.models import Asignatura, Seccion, Carrera
from django.core.exceptions import ValidationError
from pgvector.django import VectorField
from django.conf import settings
from django.db.models import Q

#############################################################


def ruta_imagen_estudiante(instance, filename):
    return f"estudiantes/{instance.rut}_{filename}"



class EstudianteAsignaturaSeccion(models.Model):
    estudiante = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="relaciones_asignatura_seccion"
    )
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    seccion = models.ForeignKey(
        Seccion, 
        on_delete=models.CASCADE, 
        related_name="relaciones_estudiantes_asignatura"
    )

    class Meta:
        unique_together = ('estudiante', 'asignatura')

    def __str__(self):
        return f"{self.estudiante.get_full_name()} - {self.asignatura.nombre} ({self.seccion.nombre})"
    


############################ ARCFACE ########################################3

class EstudianteFoto(models.Model):
    estudiante    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fotos'
    )
    imagen        = models.ImageField(upload_to='estudiantes/fotos_extra/')
    embedding     = VectorField(dimensions=512, blank=True, null=True)
    es_base       = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ['-es_base', '-created_at']
        ordering = ['-es_base', '-created_at']
        constraints = [
            # Solo UNA foto con es_base=True por estudiante
            models.UniqueConstraint(
                fields=['estudiante'],
                condition=Q(es_base=True),
                name='unique_foto_base_per_estudiante'
            )
        ]

    def __str__(self):
        flag = 'BASE' if self.es_base else 'DINÁMICA'
        return f"{self.estudiante.username} – {flag} @ {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"






class EstudianteEmbedding(models.Model):
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='embeddings'
    )
    embedding = VectorField(dimensions=512)
    origen = models.CharField(
        max_length=20,
        choices=[("base", "Base"), ("dinamica", "Dinámica")],
        default="base"
    )
    imagen = models.CharField(max_length=255)  # Guardamos el path relativo
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.estudiante.username} – {self.origen.upper()} – {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"