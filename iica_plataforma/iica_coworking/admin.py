from django.contrib import admin
from .models import (
    OKRObjetivo,
    OKRResultadoClave,
    OKRActualizacion,
    OKRIniciativa,
    Tarea
)


# =============================
# ACTUALIZACIONES INLINE
# =============================
class OKRActualizacionInline(admin.TabularInline):
    model = OKRActualizacion
    extra = 1


# =============================
# RESULTADOS CLAVE INLINE
# =============================
class OKRResultadoClaveInline(admin.TabularInline):
    model = OKRResultadoClave
    extra = 1


# =============================
# TAREAS INLINE (KANBAN)
# =============================
class TareaInline(admin.TabularInline):
    model = Tarea
    extra = 1
    fields = (
        "titulo",
        "responsable",
        "estado",
        "fecha_limite",
        "proyecto"
    )


# =============================
# RESULTADOS CLAVE
# =============================
@admin.register(OKRResultadoClave)
class OKRResultadoClaveAdmin(admin.ModelAdmin):

    list_display = (
        "descripcion",
        "objetivo",
        "valor_actual",
        "valor_objetivo",
        "progreso_porcentaje",
    )

    list_filter = ("objetivo",)

    search_fields = ("descripcion",)

    inlines = [OKRActualizacionInline]

    def progreso_porcentaje(self, obj):
        return f"{obj.progreso():.1f}%"

    progreso_porcentaje.short_description = "Progreso"


# =============================
# OBJETIVOS
# =============================
@admin.register(OKRObjetivo)
class OKRObjetivoAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "responsable",
        "fecha_inicio",
        "fecha_fin",
    )

    list_filter = (
        "responsable",
        "fecha_inicio"
    )

    search_fields = (
        "titulo",
        "descripcion"
    )

    inlines = [
        OKRResultadoClaveInline
    ]


# =============================
# ACTUALIZACIONES
# =============================
@admin.register(OKRActualizacion)
class OKRActualizacionAdmin(admin.ModelAdmin):

    list_display = (
        "resultado",
        "fecha",
        "valor"
    )

    list_filter = ("fecha",)


# =============================
# INICIATIVAS
# =============================
@admin.register(OKRIniciativa)
class OKRIniciativaAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "objetivo",
        "prioridad",
        "fecha_fin",
        "total_tareas",
        "tareas_ejecucion",
        "tareas_completadas",
    )

    list_filter = (
        "prioridad",
        "objetivo"
    )

    search_fields = (
        "nombre",
        "descripcion"
    )

    filter_horizontal = ("resultados",)

    inlines = [TareaInline]

    def total_tareas(self, obj):
        return obj.tareas_totales()

    def tareas_ejecucion(self, obj):
        return obj.tareas_ejecucion()

    def tareas_completadas(self, obj):
        return obj.tareas_completadas()

    total_tareas.short_description = "Tareas"
    tareas_ejecucion.short_description = "En ejecución"
    tareas_completadas.short_description = "Completadas"


# =============================
# TAREAS (KANBAN)
# =============================
@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "iniciativa",
        "estado",
        "responsable",
        "proyecto",
        "fecha_limite"
    )

    list_filter = (
        "estado",
        "responsable",
        "proyecto"
    )

    search_fields = (
        "titulo",
        "descripcion"
    )

    autocomplete_fields = (
        "iniciativa",
        "responsable",
        "proyecto"
    )