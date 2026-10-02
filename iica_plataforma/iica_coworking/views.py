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
    OKRActualizacion,
    OKRIniciativa,
    Tarea,
    TareaChecklist,
    TareaArchivo,
    TareaBitacora,
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
    # Traemos las tareas pendientes u ordenadas por fecha de creación / límite
    tareas = (
        Tarea.objects
        .filter(estado="pendiente")
        .select_related("iniciativa", "proyecto")
        .order_by("-fecha_creacion")[:20]
    )

    data = []
    for t in tareas:
        data.append({
            "id": t.id,
            "titulo": t.titulo,
            "descripcion": t.descripcion or "Sin descripción detallada.",
            "iniciativa": t.iniciativa.nombre if t.iniciativa else "Sin iniciativa",
            "prioridad": t.iniciativa.prioridad if t.iniciativa else "Normal",
            "proyecto": t.proyecto.nombre if t.proyecto else "General",
            "fecha_limite": t.fecha_limite.strftime("%d/%m/%Y") if t.fecha_limite else "Sin fecha límite"
        })

    return JsonResponse(data, safe=False)
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

# =====================================================
# GESTIÓN DETALLADA DE LA TARJETA (MODAL Y COMPONENTES)
# =====================================================
def tarea_detalle_json(request, tarea_id):
    tarea = Tarea.objects.get(id=tarea_id)
    
    # Obtener los KR asociados a la iniciativa de la tarea
    krs_disponibles = []
    if tarea.iniciativa:
        for kr in tarea.iniciativa.resultados.all():
            krs_disponibles.append({
                "id": kr.id,
                "descripcion": kr.descripcion,
                "valor_actual": kr.valor_actual
            })

    # Bitácora ordenada cronológicamente (ascendente o descendente según prefieras, aquí cronológica clásica)
    bitacoras = []
    for b in tarea.bitacoras.all().order_by('fecha_creacion'):
        bitacoras.append({
            "fecha": b.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            "autor": b.autor.username if b.autor else "Sistema",
            "texto": b.texto,
            "kr_nombre": b.actualizar_kr.descripcion if b.actualizar_kr else None,
            "valor_nuevo": b.nuevo_valor_kr,
            "archivo_url": b.archivo_adjunto.url if b.archivo_adjunto else None
        })

    data = {
        "id": tarea.id,
        "titulo": tarea.titulo,
        "descripcion": tarea.descripcion,
        "estado": tarea.get_estado_display(),
        "fecha_limite": tarea.fecha_limite.strftime('%Y-%m-%d') if tarea.fecha_limite else None,
        "iniciativa": tarea.iniciativa.nombre if tarea.iniciativa else "Sin iniciativa",
        "proyecto": tarea.proyecto.nombre if tarea.proyecto else "General",
        "checklist": [{"id": c.id, "texto": c.texto, "completado": c.completado} for c in tarea.checklist.all()],
        "archivos": [{"nombre": a.nombre or a.archivo.name, "url": a.archivo.url} for a in tarea.archivos.all()],
        "krs": krs_disponibles,
        "bitacoras": bitacoras
    }
    return JsonResponse(data)

@login_required
def tarea_detalle_modal(request, tarea_id):
    """Devuelve los detalles completos de la tarea para renderizar en el modal."""
    tarea = get_object_or_404(
        Tarea.objects.select_related("iniciativa", "proyecto", "responsable")
        .prefetch_related("checklist", "archivos", "bitacoras__autor", "bitacoras__actualizar_kr"),
        id=tarea_id
    )

    # Resultados clave asociados a la iniciativa de la tarea (para el selector de la bitácora)
    krs_disponibles = tarea.iniciativa.resultados.all()

    # Si se requiere renderizar vía JSON para una SPA o HTML parcial mediante template
    data = {
        "id": tarea.id,
        "titulo": tarea.titulo,
        "descripcion": tarea.descripcion,
        "estado": tarea.estado,
        "fecha_limite": tarea.fecha_limite.strftime("%Y-%m-%d") if tarea.fecha_limite else "",
        "proyecto": tarea.proyecto.nombre if tarea.proyecto else None,
        "checklist": [{"id": c.id, "texto": c.texto, "completado": c.completado} for c in tarea.checklist.all()],
        "archivos": [{"id": a.id, "nombre": a.nombre or a.archivo.name, "url": a.archivo.url} for a in tarea.archivos.all()],
    }
    return JsonResponse(data)


@login_required
@require_POST
@transaction.atomic
def tarea_agregar_checklist(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    texto = request.POST.get("texto")
    if texto:
        TareaChecklist.objects.create(tarea=tarea, texto=texto)
    return redirect("okr_kanban")


@login_required
@require_POST
def tarea_toggle_checklist(request, item_id):
    item = get_object_or_404(TareaChecklist, id=item_id)
    item.completado = not item.completado
    item.save()
    return JsonResponse({"status": "ok", "completado": item.completado})


@login_required
@require_POST
@transaction.atomic
def tarea_subir_archivo(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    archivo = request.FILES.get("archivo")
    nombre = request.POST.get("nombre", "")
    if archivo:
        TareaArchivo.objects.create(tarea=tarea, archivo=archivo, nombre=nombre)
    return redirect("okr_kanban")


@login_required
@require_POST
@transaction.atomic
def tarea_crear_bitacora(request, tarea_id):
    """Crea una entrada en la bitácora y opcionalmente actualiza un KR del OKR."""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    texto = request.POST.get("texto")
    archivo = request.FILES.get("archivo_adjunto")
    
    kr_id = request.POST.get("actualizar_kr")
    nuevo_valor = request.POST.get("nuevo_valor_kr")
    aporte_proyecto = request.POST.get("aporte_indicador_proyecto")

    kr_obj = None
    valor_float = None

    if kr_id and nuevo_valor:
        kr_obj = get_object_or_404(OKRResultadoClave, id=kr_id)
        valor_float = float(nuevo_valor)
        
        # Actualizamos el valor actual del Resultado Clave directamente
        kr_obj.valor_actual = valor_float
        kr_obj.save()

        # Registramos también el histórico de actualización en el OKR
        OKRActualizacion.objects.create(
            resultado=kr_obj,
            fecha=timezone.now().date(),
            valor=valor_float,
            comentario=f"Actualizado desde la tarea: {tarea.titulo}"
        )

    aporte_float = float(aporte_proyecto) if aporte_proyecto else None

    # Creamos la entrada de bitácora vinculada
    TareaBitacora.objects.create(
        tarea=tarea,
        autor=request.user,
        texto=texto,
        archivo_adjunto=archivo,
        actualizar_kr=kr_obj,
        nuevo_valor_kr=valor_float,
        aporte_indicador_proyecto=aporte_float
    )

    return redirect("okr_kanban")

@login_required
@require_POST
@transaction.atomic
def okr_crear_objetivo(request):
    titulo = request.POST.get("titulo")
    descripcion = request.POST.get("descripcion", "")
    responsable_id = request.POST.get("responsable")
    fecha_inicio = request.POST.get("fecha_inicio")
    fecha_fin = request.POST.get("fecha_fin")

    responsable = User.objects.filter(id=responsable_id).first() if responsable_id else None

    if titulo and fecha_inicio and fecha_fin:
        OKRObjetivo.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            responsable=responsable,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
    return redirect("okr_tablero")


@login_required
@require_POST
@transaction.atomic
def okr_crear_kr(request):
    objetivo_id = request.POST.get("objetivo_id")
    objetivo = get_object_or_404(OKRObjetivo, id=objetivo_id)
    
    descripcion = request.POST.get("descripcion")
    valor_inicial = float(request.POST.get("valor_inicial", 0))
    valor_objetivo = float(request.POST.get("valor_objetivo", 100))
    deshabilitado = request.POST.get("deshabilitado") == "on"

    if descripcion:
        OKRResultadoClave.objects.create(
            objetivo=objetivo,
            descripcion=descripcion,
            valor_inicial=valor_inicial,
            valor_objetivo=valor_objetivo,
            valor_actual=valor_inicial,
            deshabilitado=deshabilitado
        )
    return redirect(f"/okr/?objetivo={objetivo_id}")


@login_required
@require_POST
@transaction.atomic
def okr_crear_iniciativa(request):
    objetivo_id = request.POST.get("objetivo_id")
    objetivo = get_object_or_404(OKRObjetivo, id=objetivo_id)
    
    nombre = request.POST.get("nombre")
    descripcion = request.POST.get("descripcion", "")
    responsable_id = request.POST.get("responsable")
    prioridad = request.POST.get("prioridad", "Media")
    fecha_fin = request.POST.get("fecha_fin") or None
    kr_ids = request.POST.getlist("resultados")

    responsable = User.objects.filter(id=responsable_id).first() if responsable_id else None

    if nombre:
        iniciativa = OKRIniciativa.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            responsable=responsable,
            prioridad=prioridad,
            fecha_fin=fecha_fin,
            objetivo=objetivo
        )
        if kr_ids:
            iniciativa.resultados.set(kr_ids)

    kr_actual = request.GET.get("kr", "")
    return redirect(f"/okr/?objetivo={objetivo_id}&kr={kr_actual}")


@login_required
@require_POST
@transaction.atomic
def okr_actualizar_responsable_objetivo(request, objetivo_id):
    objetivo = get_object_or_404(OKRObjetivo, id=objetivo_id)
    responsable_id = request.POST.get("responsable_id")
    
    # Si viene vacío, se borra el representante (queda null)
    objetivo.responsable = User.objects.filter(id=responsable_id).first() if responsable_id else None
    objetivo.save()
    
    return redirect(f"/okr/?objetivo={objetivo.id}")