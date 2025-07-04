#core/urls.py
from django.urls import path
from .views import redirigir_por_rol, dashboard_admin_zona
from core import views as core_views
from . import views

urlpatterns = [
    path('', views.portal_inicio, name='portal_inicio'),  # Muestra el login siempre
    path('redirigir/', redirigir_por_rol, name='redirigir_por_rol'),

    path('dashboard/', views.dashboard_admin_global, name='dashboard_admin_global'),
    path('logout/', views.cerrar_sesion, name='logout'),

    path('admin-zona/', views.dashboard_admin_zona, name='dashboard_admin_zona'),
    path('admin-global/gestionar_admin_zona/', views.gestionar_admin_zona, name='gestionar_admin_zona'),

    path('calendario/', views.gestionar_calendario, name='gestionar_calendario'),

    path('dashboard/exportar-pdf/', core_views.exportar_dashboard_pdf, name='exportar_dashboard_pdf'),
    

]