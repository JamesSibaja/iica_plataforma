from django.shortcuts import render, get_object_or_404, redirect
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from secap.models import Proyecto

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

    iniciativas = OKRIniciativa.objects.all()
    proyectos = Proyecto.objects.all()

    context = {

        "vista": "kanban",
        "iniciativas": iniciativas,
        "proyectos": proyectos,
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

@require_GET
def tareas_prioridad(request):

    tareas = (
        Tarea.objects
        .order_by("-updated_at")[:20]
        .values("id","titulo","proyecto__nombre")
    )

    data = []

    for t in tareas:
        data.append({
            "id":t["id"],
            "titulo":t["titulo"],
            "proyecto":t["proyecto__nombre"]
        })

    return JsonResponse(data,safe=False)

@login_required
@transaction.atomic
def tarea_crear(request):

    if request.method == "POST":

        iniciativa = get_object_or_404(
            OKRIniciativa,
            id=request.POST.get("iniciativa")
        )

        tarea = Tarea.objects.create(
            titulo=request.POST.get("titulo"),
            descripcion=request.POST.get("descripcion", ""),
            iniciativa=iniciativa,
            responsable=request.user,
            fecha_limite=request.POST.get("fecha_limite") or None,
            proyecto=request.POST.get("proyecto") or None,
        )

        # # redirección
        # if iniciativa.proyecto:
        #     return redirect(
        #         "proyectos_ejecucion",
        #         iniciativa.proyecto.id
        #     )

        # fallback si no hay proyecto
        return redirect("okr_kanban")
    
def calendario(request):

    dias = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

    horas = [f"{h}:00" for h in range(8, 19)]

    eventos = [
        {"titulo":"Reunión", "dia":"Lun", "hora":"10:00"},
        {"titulo":"Entrega", "dia":"Mié", "hora":"14:00"},
    ]

    return render(request, "iica_coworking/calendar.html", {
        "dias": dias,
        "horas": horas,
        "eventos": eventos
    })