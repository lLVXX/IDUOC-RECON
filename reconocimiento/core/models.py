# CORE/MODELS.PY
from django.contrib.auth.models import AbstractUser
from django.db import models
from sedes.models import Sede
from sedes.models import Asignatura
from django.contrib.postgres.fields import ArrayField  # PostgreSQL requerido
from sedes.models import Seccion


from django.contrib.auth.models import AbstractUser
from django.db import models
from sedes.models import Sede, Carrera, Asignatura

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin_global', 'Administrador Global'),
        ('admin_zona', 'Administrador Zona'),
        ('profesor', 'Profesor'),
        ('estudiante', 'Estudiante'),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    carrera = models.ForeignKey(Carrera, null=True, blank=True, on_delete=models.SET_NULL)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_sede')
    workzone = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_workzone')
    asignaturas = models.ManyToManyField(Asignatura, blank=True, related_name='profesores')
    seccion = models.ForeignKey(Seccion, null=True, blank=True, on_delete=models.SET_NULL, related_name="estudiantes")
    imagen = models.ImageField(upload_to='estudiantes/', blank=True, null=True)  # Solo la foto base
    motivo_cambio = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


##################################################################

######## CALENDARIO ACADEMICO ###############


class CalendarioAcademico(models.Model):
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='calendarios')
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    def __str__(self):
        return f"{self.nombre} - {self.sede.nombre}"

######## SEMANA ACADEMICA ###############

class SemanaAcademica(models.Model):
    calendario = models.ForeignKey(CalendarioAcademico, on_delete=models.CASCADE, related_name='semanas')
    numero = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('clases', 'Clases'),
            ('receso', 'Receso'),
            ('examenes', 'Exámenes'),
            ('feriado', 'Feriado')
        ],
        default='clases'
    )
    descripcion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.calendario} - Semana {self.numero} ({self.get_tipo_display()})"