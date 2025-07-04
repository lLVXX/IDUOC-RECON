# clases/urls.py

from django.urls import path
from . import views

app_name = "clases"

urlpatterns = [
    # Dashboard y gestión
    path('dashboard-profesor/',views.dashboard_profesor,name='dashboard_profesor'),

    path('gestionar_aulas/',        views.gestionar_aulas,     name='gestionar_aulas'),
    path('gestionar_bloques_horarios/', views.gestionar_bloques_horarios, name='gestionar_bloques_horarios'),
    path('gestionar_clases/',       views.gestionar_clases,    name='gestionar_clases'),
    path('get_asignaturas_ajax/',   views.get_asignaturas_ajax,name='get_asignaturas_ajax'),
    path('get_secciones_ajax/',     views.get_secciones_ajax,  name='get_secciones_ajax'),
    path('ajax/secciones/', views.get_secciones_ajax, name='get_secciones_ajax'),
    path('ajax/secciones/', views.get_secciones_ajax, name='get_secciones_ajax'),
    # Horario del profesor
    path('mi-horario/', views.horario_profesor, name='horario_profesor'),

    path('instancia/<int:inst_id>/', views.detalle_instancia, name='detalle_instancia'),
    path('instancia/<int:inst_id>/asistencia_live/', views.asistencia_live, name='asistencia_live'),
    path('instancia/<int:inst_id>/finalizar/',       views.finalizar_clase, name='finalizar_clase'),
    


    path('instancia/<int:inst_id>/reporte/',views.reporte_instancia,name='reporte_instancia'),
    path('',views.listado_instancias,name='listado_instancias'),
    path('historial/', views.listado_instancias, name='historial_instancias'),

    path('capturar_foto/',views.capturar_foto, name='capturar_foto'),


]


    
    

  
