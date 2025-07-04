# reconocimiento/__init__.py
# reconocimiento/__init__.py
from __future__ import absolute_import, unicode_literals

# Importa celery app al inicializar Django
from .celery import app as celery_app
__all__ = ('celery_app',)




