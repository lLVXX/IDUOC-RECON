
#SEDES/URLS.PY

from django.urls import path
from . import views



app_name = 'sedes' 



urlpatterns = [
    path('gestionar/', views.gestionar_sedes, name='gestionar_sedes'),
    path('gestionar_carreras/', views.gestionar_carreras, name='gestionar_carreras'),
    path('gestionar-asignaturas/', views.gestionar_asignaturas, name='gestionar_asignaturas'),
    
    path('gestionar-secciones/', views.gestionar_secciones, name='gestionar_secciones'),
    path('gestionar-profesores/', views.gestionar_profesores, name='gestionar_profesores'),
    path("gestionar-estudiantes/", views.gestionar_estudiantes, name="gestionar_estudiantes"),
    path('ajax_asignaturas_secciones/', views.ajax_asignaturas_secciones, name='ajax_asignaturas_secciones'),
    path('sync-secciones/<int:estudiante_id>/', views.sync_secciones, name='sync_secciones'),



    path(
        'gestionar-estudiantes/sync/<int:est_id>/',
        views.sync_secciones,
        name='sync_secciones'
    ),
    path(
      'gestionar-estudiantes/sync-todas/',
      views.sync_todas_secciones,
      name='sync_todas_secciones'
    ),
    
]
