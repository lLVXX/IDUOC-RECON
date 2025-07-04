# personas/urls.py
from django.urls import path
from . import views


app_name = 'personas'


urlpatterns = [
    path('listar-estudiantes-secciones/', views.listar_estudiantes_con_secciones, name='listar_estudiantes_secciones'),
    path('capturar_foto/', views.capturar_foto, name='capturar_foto'),
]