from django.contrib import admin
from django.utils import timezone
from .models import (
    Proyecto,
    MiembroComite,
    Criterio,
    GrupoCriterios,
    GrupoCriterio,
    ProyectoNuevo,
    Formulario,
    ProyectoEjecucion,
    Indicador,
    MetaIndicador,
)

# -------------------------------
# PROYECTOS BASE
# -------------------------------

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "encargado", "fecha_creacion", "monto")
    search_fields = ("nombre", "descripcion")
    list_filter = ("encargado", "fecha_creacion")
    ordering = ("-fecha_creacion",)


# -------------------------------
# COMITÉ
# -------------------------------

@admin.register(MiembroComite)
class MiembroComiteAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "proyecto", "aprobado", "alerta")
    list_filter = ("aprobado", "alerta", "usuario", "proyecto")
    search_fields = ("usuario__username", "proyecto__nombre")
    ordering = ("id",)


# -------------------------------
# CRITERIOS
# -------------------------------

@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ("id", "premisa")
    search_fields = ("premisa",)
    ordering = ("premisa",)


# -------------------------------
# INLINE: Grupo ↔ Criterio
# -------------------------------

class GrupoCriterioInline(admin.TabularInline):
    model = GrupoCriterio
    extra = 1


# -------------------------------
# GRUPOS DE CRITERIOS
# -------------------------------

@admin.register(GrupoCriterios)
class GrupoCriteriosAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    inlines = [GrupoCriterioInline]


# -------------------------------
# PROYECTOS NUEVOS
# -------------------------------

@admin.register(ProyectoNuevo)
class ProyectoNuevoAdmin(admin.ModelAdmin):
    list_display = ("id", "proyecto")
    search_fields = ("proyecto__nombre",)
    list_filter = ("proyecto__encargado",)


# -------------------------------
# FORMULARIO
# -------------------------------

@admin.register(Formulario)
class FormularioAdmin(admin.ModelAdmin):
    list_display = ("id", "proyecto_nuevo", "criterio", "calificacion")
    list_filter = ("criterio",)
    search_fields = (
        "proyecto_nuevo__proyecto__nombre",
        "criterio__premisa",
    )


# -------------------------------
# PROYECTOS EN EJECUCIÓN
# -------------------------------

@admin.register(ProyectoEjecucion)
class ProyectoEjecucionAdmin(admin.ModelAdmin):
    list_display = ("id", "proyecto")
    search_fields = ("proyecto__nombre",)
    list_filter = ("proyecto__encargado",)


# -------------------------------------------------------
# META INDICADOR INLINE (PLAN DEL INDICADOR)
# -------------------------------------------------------

class MetaIndicadorInline(admin.TabularInline):
    model = MetaIndicador
    extra = 0
    ordering = ("fecha",)
    fields = ("fecha", "valor_objetivo", "comentario")


# -------------------------------------------------------
# INDICADORES
# -------------------------------------------------------

@admin.register(Indicador)
class IndicadorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "premisa",
        "proyecto",
        "valor_actual",
        "proxima_meta",
        "estado_actual",
    )

    search_fields = ("premisa", "descripcion")
    list_filter = ("proyecto",)
    inlines = [MetaIndicadorInline]

    def proxima_meta(self, obj):
        """
        Muestra la próxima meta futura del indicador.
        """
        hoy = timezone.now().date()
        meta = obj.metas.filter(fecha__gte=hoy).order_by("fecha").first()
        if not meta:
            return "—"
        return f"{meta.valor_objetivo}% · {meta.fecha.strftime('%d/%m')}"

    proxima_meta.short_description = "Próxima meta"


    def estado_actual(self, obj):
        """
        Evalúa el estado actual del indicador comparando
        el valor actual con la última meta vencida.
        """
        hoy = timezone.now().date()
        meta = obj.metas.filter(fecha__lte=hoy).order_by("-fecha").first()

        if not meta:
            return "🟢 Sin referencia"

        diff = obj.valor_actual - meta.valor_objetivo

        if diff >= 0:
            return "🟢 En línea"
        elif diff >= -5:
            return "🟡 Leve atraso"
        elif diff >= -15:
            return "🟠 Atraso"
        else:
            return "🔴 Crítico"

    estado_actual.short_description = "Estado actual"


# -------------------------------------------------------
# META INDICADOR (ADMIN DIRECTO)
# -------------------------------------------------------

@admin.register(MetaIndicador)
class MetaIndicadorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "indicador",
        "fecha",
        "valor_objetivo",
        "valor_actual_indicador",
        "diferencia",
    )

    list_filter = ("fecha", "indicador__proyecto")
    search_fields = ("indicador__premisa",)

    def valor_actual_indicador(self, obj):
        return f"{obj.indicador.valor_actual}%"

    valor_actual_indicador.short_description = "Valor actual"


    def diferencia(self, obj):
        diff = obj.indicador.valor_actual - obj.valor_objetivo
        if diff >= 0:
            return f"+{diff:.1f}%"
        return f"{diff:.1f}%"

    diferencia.short_description = "Δ vs meta"
