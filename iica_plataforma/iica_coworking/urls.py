from django.urls import path
from . import views

urlpatterns = [
    # OKR y Tableros
    path("okr/", views.okr_tablero, name="okr_tablero"),
    path("okr/kanban/", views.okr_kanban, name="okr_kanban"),
    path("okr/calendario/", views.calendario, name="calendario"),

    # Tareas y Kanban
    path("api/tareas/prioridad/", views.tareas_prioridad, name="tareas_prioridad"),
    path("tarea/crear/", views.tarea_crear, name="tarea_kanban_crear"),
    path("tarea/<int:tarea_id>/detalle/", views.tarea_detalle_json, name="tarea_detalle_json"),

    # Gestión interna de la tarjeta (Checklist, Archivos, Bitácora)
    path("tarea/<int:tarea_id>/checklist/agregar/", views.tarea_agregar_checklist, name="tarea_agregar_checklist"),
    path("checklist/<int:item_id>/toggle/", views.tarea_toggle_checklist, name="tarea_toggle_checklist"),
    path("tarea/<int:tarea_id>/archivo/subir/", views.tarea_subir_archivo, name="tarea_subir_archivo"),
    path("tarea/<int:tarea_id>/bitacora/crear/", views.tarea_crear_bitacora, name="tarea_crear_bitacora"),

    # Endpoints OKR de Creación y Edición
    path("okr/objetivo/crear/", views.okr_crear_objetivo, name="okr_crear_objetivo"),
    path("okr/kr/crear/", views.okr_crear_kr, name="okr_crear_kr"),
    path("okr/iniciativa/crear/", views.okr_crear_iniciativa, name="okr_crear_iniciativa"),
    path("okr/objetivo/<int:objetivo_id>/responsable/", views.okr_actualizar_responsable_objetivo, name="okr_actualizar_responsable_objetivo"),
]