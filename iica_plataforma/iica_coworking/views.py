from django.shortcuts import render
from datetime import timedelta
from django.utils import timezone

from .models import (
    OKRObjetivo,
    OKRResultadoClave,
    OKRIniciativa,
    Tarea
)


# =====================================================
# TABLERO OKR
# =====================================================

def okr_tablero(request):

    objetivos = OKRObjetivo.objects.all()

    objetivo_id = request.GET.get("objetivo")
    kr_id = request.GET.get("kr")

    objetivo_sel = None
    kr_sel = None
    resultados = []
    iniciativas = []

    hoy = timezone.now().date()

    semanas = []
    for i in range(-2, 4):
        semanas.append(hoy + timedelta(days=i * 7))

    tabla = []

    # -------------------------
    # OBJETIVO SELECCIONADO
    # -------------------------

    if objetivo_id:
        objetivo_sel = OKRObjetivo.objects.filter(id=objetivo_id).first()

    if objetivo_sel:
        resultados = objetivo_sel.resultados.all()

    # -------------------------
    # KR SELECCIONADO
    # -------------------------

    if kr_id:
        kr_sel = OKRResultadoClave.objects.filter(id=kr_id).first()

    if kr_sel:

        iniciativas = kr_sel.iniciativas.all()

    # -------------------------
    # MATRIZ SEMANAL KR
    # -------------------------

    if objetivo_sel:

        for r in resultados:

            fila = {
                "resultado": r,
                "semanas": []
            }

            for s in semanas:

                act = r.actualizaciones.filter(
                    fecha__week=s.isocalendar()[1]
                ).first()

                if act:
                    estado = act.estado()
                else:
                    estado = r.estado_color()

                fila["semanas"].append({
                    "estado": estado,
                    "es_actual": s.isocalendar()[1] == hoy.isocalendar()[1],
                    "es_futuro": s > hoy
                })

            tabla.append(fila)

    context = {

        "vista": "okr",

        "objetivos": objetivos,

        "objetivo_sel": objetivo_sel,
        "kr_sel": kr_sel,

        "resultados": resultados,
        "iniciativas": iniciativas,

        "tabla": tabla,
        "semanas": semanas,
        "hoy": hoy
    }

    return render(
        request,
        "iica_coworking/okr_tablero.html",
        context
    )


# =====================================================
# TABLERO KANBAN
# =====================================================

def okr_kanban(request):

    tareas_pendientes = Tarea.objects.filter(estado="pendiente")
    tareas_ejecucion = Tarea.objects.filter(estado="ejecucion")
    tareas_espera = Tarea.objects.filter(estado="espera")
    tareas_terminadas = Tarea.objects.filter(estado="terminada")

    context = {

        "vista": "kanban",

        "tareas_pendientes": tareas_pendientes,
        "tareas_ejecucion": tareas_ejecucion,
        "tareas_espera": tareas_espera,
        "tareas_terminadas": tareas_terminadas
    }

    return render(
        request,
        "iica_coworking/kanban.html",
        context
    )