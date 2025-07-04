# clases/models.py

from django.db import models
from django.utils import timezone
from core.models import CustomUser
from sedes.models import Sede  
from core.models import SemanaAcademica


# Bloques horarios predefinidos (ej: Diurno 08:30-09:15)
class BloqueHorario(models.Model):
    nombre = models.CharField(max_length=100)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')})"

# Aulas con cámara IP asociada
class Aula(models.Model):
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)
    numero_sala = models.CharField(max_length=20)
    descripcion = models.TextField(blank=True)
    camara_ip = models.CharField(
        max_length=200,
        help_text='URL de la cámara o "0" para usar la cámara local',
        default='0',
        blank=True
    )

    def __str__(self):
        return f"Sala {self.numero_sala} ({self.sede.nombre})"

# Plantilla semanal de clase
datetime = timezone.datetime
from datetime import timedelta

class Clase(models.Model):
    DIA_MAP = {
        'LU': 0,  # Lunes
        'MA': 1,
        'MI': 2,
        'JU': 3,
        'VI': 4,
        'SA': 5,
    }
    DIAS_SEMANA = [
        ('LU', 'Lunes'), ('MA', 'Martes'), ('MI', 'Miércoles'),
        ('JU', 'Jueves'), ('VI', 'Viernes'), ('SA', 'Sábado')
    ]

    dia_semana = models.CharField(max_length=2, choices=DIAS_SEMANA)
    bloque_horario = models.ForeignKey(BloqueHorario, on_delete=models.CASCADE)
    profesor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'profesor'})
    seccion = models.ForeignKey('sedes.Seccion', on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    publicada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_dia_semana_display()} - {self.bloque_horario} - {self.seccion}"

    def get_dia_semana_delta(self):
        """
        Devuelve un timedelta para sumar a la fecha de inicio de la semana,
        según el día de la semana de la plantilla.
        """
        dias = self.DIA_MAP.get(self.dia_semana, 0)
        return timedelta(days=dias)

# Versionado de plantillas para historial
class ClasePlantillaVersion(models.Model):
    plantilla = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='versions')
    effective_from = models.ForeignKey(SemanaAcademica, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Version de {self.plantilla} desde semana {self.effective_from.numero}"

# Instancia concreta en una semana académica
class ClaseInstancia(models.Model):
    version = models.ForeignKey(ClasePlantillaVersion, on_delete=models.CASCADE, related_name='instancias')
    semana_academica = models.ForeignKey(SemanaAcademica, on_delete=models.CASCADE)
    fecha = models.DateField()
    finalizada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('version', 'semana_academica')

    def __str__(self):
        return f"Instancia: {self.version.plantilla} @ {self.fecha}"

# Registro de asistencia (facial/manual) para cada instancia
class AsistenciaClase(models.Model):
    instancia = models.ForeignKey(ClaseInstancia, on_delete=models.CASCADE, related_name='asistencias')
    estudiante = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'user_type':'estudiante'})
    presente = models.BooleanField()
    manual = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('instancia', 'estudiante')

    def __str__(self):
        estado = 'Presente' if self.presente else 'Ausente'
        return f"{self.estudiante.get_full_name()} - {estado} en {self.instancia.fecha}"

# Auditoría de cambios en asistencia
tz = timezone.now
class HistorialAsistenciaClase(models.Model):
    asistencia = models.ForeignKey(AsistenciaClase, on_delete=models.CASCADE, related_name='historial')
    cambio = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asistencia} cambió: {self.cambio} @ {self.timestamp}"

class AuditoriaAsistencia(models.Model):
    instancia = models.ForeignKey(ClaseInstancia, on_delete=models.CASCADE)
    evento = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Auditoría [{self.instancia.fecha}]: {self.evento[:20]}..."
