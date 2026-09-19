from django.shortcuts import render, get_object_or_404, redirect
from datetime import timedelta, datetime, date
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
from .services import sync_microsoft_events
from .service.microsoft import sincronizar_eventos

from .models import (
    OKRObjetivo,
    OKRResultadoClave,
    OKRIniciativa,
    Tarea,
    EventoCalendario
)

@login_required
def calendario(request):

    if request.user.is_authenticated:
        try:
            perfil = request.user.perfilmicrosoft
            sincronizar_eventos(perfil)  # 👈 AQUÍ
        except:
            pass


    fecha_str = request.GET.get("fecha")
     # 🔥 SINCRONIZA ANTES DE MOSTRAR
    sync_microsoft_events(request.user)

    hoy = timezone.localdate()
    if fecha_str:
        fecha_actual = datetime.strptime(
            fecha_str,
            "%Y-%m-%d"
        ).date()
    else:
        fecha_actual = hoy

    inicio_semana = fecha_actual - timedelta(
        days=fecha_actual.weekday()
    )

    nombres = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo"
    ]

    dias_semana = []

    for i in range(7):
        dia = inicio_semana + timedelta(days=i)

        dias_semana.append({
            "fecha": dia,
            "nombre": nombres[i],
            "activo": dia == fecha_actual
        })

    usuarios = User.objects.filter(
        is_active=True
    ).order_by("first_name", "username")

    eventos_db = EventoCalendario.objects.filter(
        fecha=fecha_actual
    ).select_related("usuario")

    horas = list(range(8, 18))

    JORNADA_INICIO = 8
    JORNADA_FIN = 18
    TOTAL_HORAS = JORNADA_FIN - JORNADA_INICIO

    eventos = []

    for ev in eventos_db:

        inicio_decimal = ev.hora_inicio.hour + ev.hora_inicio.minute / 60
        fin_decimal = ev.hora_fin.hour + ev.hora_fin.minute / 60

        # clamp (evita que se rompa el layout)
        inicio_decimal = max(inicio_decimal, JORNADA_INICIO)
        fin_decimal = min(fin_decimal, JORNADA_FIN)

        left = ((inicio_decimal - JORNADA_INICIO) / TOTAL_HORAS) * 100
        width = ((fin_decimal - inicio_decimal) / TOTAL_HORAS) * 100

        eventos.append({
            "usuario_id": ev.usuario.id,
            "usuario": ev.usuario.get_full_name() or ev.usuario.username,
            "titulo": ev.titulo,
            "detalle": ev.detalle,
            "categoria": ev.categoria,
            "ubicacion": ev.ubicacion,
            "hora_inicio": ev.hora_inicio.strftime("%H:%M"),
            "hora_fin": ev.hora_fin.strftime("%H:%M"),
            "left": f"{left:.2f}",
            "width": f"{max(width, 2):.2f}", # mínimo visible
        })

    return render(
        request,
        "iica_coworking/calendar.html",
        {
            "usuarios": usuarios,
            "eventos": eventos,
            "dias_semana": dias_semana,
            "fecha_actual": fecha_actual,
            "horas": horas
        }
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
        return redirect("okr_kanban")
    
