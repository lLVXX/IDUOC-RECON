import os
from celery import Celery

# Configuración de entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reconocimiento.settings")

# Crear instancia Celery
app = Celery("reconocimiento")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-descubrir tareas de todas las apps
app.autodiscover_tasks()







##############################################################################



