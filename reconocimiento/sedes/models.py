# SEDES/MODELS.PY

from django.db import models
import string

class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Carrera(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    sede = models.ForeignKey("sedes.Sede", on_delete=models.CASCADE, related_name='carreras')

    class Meta:
        unique_together = ('nombre', 'sede')  # Permite repetir el nombre, pero no en la misma sede
        verbose_name_plural = "Carreras"

    def __str__(self):
        return f"{self.nombre} ({self.sede.nombre})"


class Asignatura(models.Model):
    nombre = models.CharField(max_length=100)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    

class Seccion(models.Model):
    asignatura = models.ForeignKey('Asignatura', on_delete=models.CASCADE, related_name="secciones")
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre}"
    
    def cantidad_estudiantes(self):
        return self.estudiantes.count()  # Solo si tienes related_name="estudiantes" en CustomUser
    

def generar_nombre_seccion(asignatura):
    """
    Genera el nombre de la siguiente sección para una asignatura.
    Ejemplo: '001A', '001B', ..., '002A', etc.
    """
    base_nombre = asignatura.nombre[:3].upper()
    secciones_existentes = asignatura.secciones.order_by('nombre').values_list('nombre', flat=True)
    if not secciones_existentes:
        return '001A'
    codigos = [s for s in secciones_existentes if s[:3].isdigit() and s[3:].isalpha()]
    if not codigos:
        return '001A'
    ult_codigo = sorted(codigos)[-1]
    num = int(ult_codigo[:3])
    letra = ult_codigo[3]
    if letra == 'Z':
        num += 1
        letra = 'A'
    else:
        letra = chr(ord(letra) + 1)
    return f"{num:03d}{letra}"