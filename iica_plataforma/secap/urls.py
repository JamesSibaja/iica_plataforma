from django.urls import path
from . import views

def admin_required(view_func):
    """
    Decorador que restringe el acceso a administradores.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Acceso denegado. Debes ser administrador para acceder a esta página.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

urlpatterns = [
    path('proyectos/', views.proyecto_menu, name="proyecto_menu"),
    path('proyectos/nuevos/', views.proyectos_nuevos, name="proyectos_nuevos"),
    path('proyectos/ejecucion/', views.proyectos_ejecucion, name="proyectos_ejecucion"),
    path("proyectos/ejecucion/<int:proyecto_id>/", views.proyectos_ejecucion, name="proyectos_ejecucion"),
    path("proyectos/detalle/<int:proyecto_id>/", views.proyecto_detalle_panel,name="proyecto_detalle_panel"),
    path("proyectos/guardar-calificaciones/<int:proyecto_id>/", views.guardar_calificaciones,name="guardar_calificaciones"),
    path("proyectos/decision-comite/<int:proyecto_id>/", views.decision_comite, name="decision_comite"),
    path("proyectos/crear/", views.proyecto_crear, name="proyecto_crear"),
    path("proyectos/iniciar/<int:proyecto_id>/", views.proyecto_iniciar, name="proyecto_iniciar"),
    path("ejecucion/", views.proyectos_ejecucion, name="proyectos_ejecucion"),
    path("ejecucion/<int:proyecto_id>/", views.proyectos_ejecucion, name="proyectos_ejecucion"),
    path("proyectos/indicador/<int:indicador_id>/", views.indicador_detalle, name="indicador_detalle"),
    path("indicador/<int:indicador_id>/actualizar/", views.indicador_actualizar, name="indicador_actualizar"),
    path("indicador/<int:indicador_id>/meta/crear/", views.meta_indicador_crear, name="meta_indicador_crear"),
    path("meta/<int:meta_id>/eliminar/", views.meta_indicador_eliminar, name="meta_indicador_eliminar"),
]
