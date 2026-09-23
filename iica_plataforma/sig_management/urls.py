from django.urls import path
from . import views

urlpatterns = [
    path('flujos/', views.workflows_ejecucion, name='workflows_ejecucion'),
    path('flujos/<int:execution_id>/', views.workflows_ejecucion, name='workflows_ejecucion_detalle'),
    path('flujos/iniciar/', views.iniciar_nuevo_flujo, name='iniciar_nuevo_flujo'),
    path('flujos/<int:execution_id>/avanzar/', views.avanzar_etapa, name='avanzar_etapa'),
    path('flujos/<int:execution_id>/retroceder/', views.retroceder_etapa, name='retroceder_etapa'),
    path('flujos/plantilla/nueva/', views.crear_plantilla_flujo, name='crear_plantilla_flujo'),
    path('flujos/<int:execution_id>/romper/', views.romper_flujo_ad_hoc, name='romper_flujo_ad_hoc'),
]