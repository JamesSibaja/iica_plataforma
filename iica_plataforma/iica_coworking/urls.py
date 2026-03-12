from django.urls import path
from . import views

urlpatterns = [

    path(
        "okr/",
        views.okr_tablero,
        name="okr_tablero"
    ),

    path(
        "okr/kanban/",
        views.okr_kanban,
        name="okr_kanban"
    ),
]
path(
    "api/tareas/prioridad/",
    views.tareas_prioridad,
    name="tareas_prioridad"
),