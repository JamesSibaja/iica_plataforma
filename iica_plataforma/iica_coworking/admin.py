from django.contrib import admin
from .models import (
    OKRObjetivo,
    OKRResultadoClave,
    OKRActualizacion,
    OKRIniciativa,
    Tarea,
    EventoCalendario,
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
        "proyecto",
    )


# =============================
# EVENTOS INLINE (CALENDARIO)
# =============================
class EventoCalendarioInline(admin.TabularInline):
    model = EventoCalendario
    extra = 1
    fields = (
        "titulo",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "categoria",
        "ubicacion",
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

    autocomplete_fields = ("objetivo",)

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
        "fecha_inicio",
    )

    search_fields = (
        "titulo",
        "descripcion",
    )

    autocomplete_fields = ("responsable",)

    inlines = [
        OKRResultadoClaveInline,
    ]


# =============================
# ACTUALIZACIONES
# =============================
@admin.register(OKRActualizacion)
class OKRActualizacionAdmin(admin.ModelAdmin):

    list_display = (
        "resultado",
        "fecha",
        "valor",
    )

    list_filter = ("fecha",)

    search_fields = ("resultado__descripcion",)

    autocomplete_fields = ("resultado",)


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
        "mostrar_total_tareas",
        "mostrar_tareas_ejecucion",
        "mostrar_tareas_completadas",
    )

    list_filter = (
        "prioridad",
        "objetivo",
    )

    search_fields = (
        "nombre",
        "descripcion",
    )

    filter_horizontal = ("resultados",)

    autocomplete_fields = (
        "objetivo",
        "responsable",
    )

    inlines = [TareaInline]

    def mostrar_total_tareas(self, obj):
        return obj.tareas_totales()

    def mostrar_tareas_ejecucion(self, obj):
        return obj.tareas_ejecucion()

    def mostrar_tareas_completadas(self, obj):
        return obj.tareas_completadas()

    mostrar_total_tareas.short_description = "Tareas"
    mostrar_tareas_ejecucion.short_description = "En ejecución"
    mostrar_tareas_completadas.short_description = "Completadas"


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
        "fecha_limite",
        "fecha_creacion",
    )

    list_filter = (
        "estado",
        "responsable",
        "proyecto",
    )

    search_fields = (
        "titulo",
        "descripcion",
    )

    autocomplete_fields = (
        "iniciativa",
        "responsable",
        "proyecto",
    )

    ordering = ("estado", "-fecha_creacion")


# =============================
# EVENTOS CALENDARIO
# =============================
@admin.register(EventoCalendario)
class EventoCalendarioAdmin(admin.ModelAdmin):

    list_display = (
        "titulo",
        "usuario",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "categoria",
        "ubicacion",
    )

    list_filter = (
        "categoria",
        "fecha",
        "usuario",
    )

    search_fields = (
        "titulo",
        "detalle",
        "ubicacion",
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    )

    autocomplete_fields = ("usuario",)

    ordering = ("-fecha", "hora_inicio")

    date_hierarchy = "fecha"