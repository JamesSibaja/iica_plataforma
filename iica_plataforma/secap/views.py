import calendar
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from .utils import calcular_estado_indicador, estado_general_proyecto
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.views.decorators.http import require_POST


from .models import (
    Proyecto,
    ProyectoNuevo,
    Criterio,
    GrupoCriterios,
    Formulario,
    Indicador,
    MetaIndicador,
    ProyectoEjecucion,
    MiembroComite,
)

@require_POST
@login_required
def crear_indicador(request, proyecto_id):
    proyecto = get_object_or_404(ProyectoEjecucion, id=proyecto_id)

    try:
        indicador = Indicador.objects.create(
            proyecto=proyecto,
            premisa=request.POST["premisa"],
            descripcion=request.POST.get("descripcion", ""),
            valor_maximo=request.POST["valor_maximo"],
            valor_actual=request.POST["valor_actual"],
        )
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

@login_required
def proyectos_ejecucion(request, proyecto_id=None):

    modo = request.GET.get("modo", "cartera")

    proyectos_propios = ProyectoEjecucion.objects.filter(
        proyecto__encargado=request.user
    )

    proyectos_comite = ProyectoEjecucion.objects.filter(
        proyecto__miembrocomite__usuario=request.user
    ).distinct()

    proyecto_sel = None
    if proyecto_id:
        proyecto_sel = get_object_or_404(ProyectoEjecucion, id=proyecto_id)
    elif modo == "comite" and proyectos_comite.exists():
        proyecto_sel = proyectos_comite.first()
    elif proyectos_propios.exists():
        proyecto_sel = proyectos_propios.first()

    es_encargado = (
    proyecto_sel
        and proyecto_sel.proyecto.encargado == request.user
    )

    es_comite = (
        proyecto_sel
        and proyecto_sel.proyecto.miembrocomite_set
            .filter(usuario=request.user)
            .exists()
    )


    hoy = timezone.now().date()

    # Ventana: 3 pasadas + actual + 5 futuras
    semanas = [hoy + timedelta(weeks=i - 3) for i in range(9)]

    tabla = []

    if proyecto_sel:
        for indicador in proyecto_sel.indicadores.prefetch_related("metas"):
            fila = {
                "indicador": indicador,
                "valor_actual": indicador.valor_actual,
                "semanas": []
            }

            for fecha in semanas:
                estado = calcular_estado_indicador(indicador, fecha)

                fila["semanas"].append({
                    "fecha": fecha,
                    "estado": estado,
                    "es_actual": fecha.isocalendar()[1] == hoy.isocalendar()[1],
                    "es_futuro": fecha > hoy,
                })

            tabla.append(fila)

    # 🔹 Estado general por proyecto (para el panel izquierdo)
    # estados_proyectos = {}

    for p in proyectos_propios:
        p.estado_general = estado_general_proyecto(p, hoy)

    for p in proyectos_comite:
        p.estado_general = estado_general_proyecto(p, hoy)


    return render(request, "secap/proyectos_ejecucion.html", {
        "proyectos_propios": proyectos_propios,
        "proyectos_comite": proyectos_comite,
        "proyecto_sel": proyecto_sel,
        "es_encargado": es_encargado,
        "es_comite": es_comite,
        "tabla": tabla,
        "modo": modo,
        "semanas": semanas,
        "hoy": hoy,
    })


@login_required
def indicador_detalle(request, indicador_id):
    indicador = get_object_or_404(Indicador, id=indicador_id)
    proyecto = indicador.proyecto.proyecto
    es_encargado = proyecto.encargado == request.user

    es_comite = proyecto.miembrocomite_set.filter(
        usuario=request.user
    ).exists()

    return render(request,
        "secap/partials/panel_indicador.html",
        {
            "indicador": indicador,
            "es_encargado": es_encargado,
            "es_comite": es_comite,
        }
    )
   

@login_required
def indicador_actualizar(request, indicador_id):
    indicador = get_object_or_404(Indicador, id=indicador_id)

    if request.method == "POST":
        if indicador.proyecto.proyecto.encargado != request.user:
            return HttpResponseForbidden()
    
        valor = request.POST.get("valor_actual")

        if valor is not None:
            indicador.valor_actual = valor
            indicador.save()

    

    # Volver a la matriz del proyecto
    return redirect(
        "proyectos_ejecucion",
        proyecto_id=indicador.proyecto.id
    )


def proyecto_menu(request):
    """Menú inicial con dos opciones: nuevos y en ejecución"""
    return render(request, "secap/catalogo.html")

@login_required
def proyectos_nuevos(request):
    user = request.user
    formularios = Formulario.objects
    mi_cartera = Proyecto.objects.filter(
        encargado=user
    ).exclude(
        id__in=ProyectoEjecucion.objects.values("proyecto_id")
    )
    comite = Proyecto.objects.filter(
        miembrocomite__usuario=user
    ).exclude(encargado=user).distinct()
    otros = Proyecto.objects.exclude(
        Q(encargado=user) |
        Q(miembrocomite__usuario=user)
    )

    # Agregamos info de comité a cada proyecto
    for queryset in (mi_cartera, comite, otros):
        for p in queryset:
            # Comité
            total = p.miembrocomite_set.count()
            aprobados = p.miembrocomite_set.filter(aprobado=True).count()

            # Calificación
            calificacion = None

            if hasattr(p, "nuevo"):
                formularios = p.nuevo.formulario_set.all()
                total_criterios = formularios.count()

                if total_criterios > 0:
                    suma = sum(f.calificacion for f in formularios)
                    calificacion = (suma * 100) / (5 * total_criterios)

            p.total_comite = total
            p.aprobados_comite = aprobados
            p.calificacion = calificacion


    return render(request, "secap/proyectos_nuevos.html", {
        "mi_cartera": mi_cartera,
        "comite": comite,
        "otros": otros,
    })

@login_required
def proyecto_detalle_panel(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    es_mi_cartera = proyecto.encargado == request.user

    es_comite = MiembroComite.objects.filter(
        proyecto=proyecto,
        usuario=request.user
    ).exists()

    formularios = []
    miembros = []

    if hasattr(proyecto, "nuevo"):
        formularios = (
            Formulario.objects
            .filter(proyecto_nuevo=proyecto.nuevo)
            .select_related("criterio")
        )

    if hasattr(proyecto, "nuevo"):
        miembros = (
            MiembroComite.objects
            .filter(proyecto=proyecto)
        )

    return render(
        request,
        "secap/partials/panel_detalle_contenido.html",
        {
            "proyecto": proyecto,
            "formularios": formularios,
            "es_mi_cartera": es_mi_cartera,
            "es_comite": es_comite,
            "miembros": miembros,
        }
    )

@login_required
def guardar_calificaciones(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    # Seguridad: solo el encargado puede editar
    if proyecto.encargado != request.user:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith("criterio_"):
                formulario_id = key.replace("criterio_", "")
                formulario = get_object_or_404(Formulario, id=formulario_id)

                try:
                    formulario.calificacion = int(value)
                    formulario.save()
                except ValueError:
                    pass

    return redirect("proyectos_nuevos")

@login_required
def decision_comite(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    miembro = get_object_or_404(
        MiembroComite,
        proyecto=proyecto,
        usuario=request.user
    )

    if request.method == "POST":
        decision = request.POST.get("decision")
        comentario = request.POST.get("comentario", "")

        miembro.comentario = comentario
        miembro.aprobado = (decision == "aprobar")
        miembro.save()

    return redirect("proyectos_nuevos")


@login_required
@transaction.atomic
def proyecto_crear(request):

    if request.method == "POST":

        # ================= DATOS BÁSICOS =================
        nombre = request.POST.get("nombre")
        descripcion = request.POST.get("descripcion", "")
        monto = request.POST.get("monto") or 0

        # ================= CREAR PROYECTO =================
        proyecto = Proyecto.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            monto=monto,
            encargado=request.user
        )

        proyecto_nuevo = ProyectoNuevo.objects.create(
            proyecto=proyecto
        )

        # ================= CRITERIOS =================
        criterios_ids = set()

        # --- desde plantilla ---
        grupo_id = request.POST.get("grupo_criterios")
        if grupo_id:
            grupo = GrupoCriterios.objects.get(id=grupo_id)
            criterios_ids.update(
                grupo.criterios.values_list("id", flat=True)
            )

        # --- criterios existentes seleccionados ---
        criterios_manual = request.POST.getlist("criterios_manual")
        criterios_ids.update(criterios_manual)

        # --- criterios nuevos ---
        criterios_nuevos = {}

        for key, value in request.POST.items():
            if key.startswith("criterios_nuevos["):
                index = key.split("[")[1].split("]")[0]
                campo = key.split("[")[2].replace("]", "")
                criterios_nuevos.setdefault(index, {})
                criterios_nuevos[index][campo] = value

        for data in criterios_nuevos.values():
            if data.get("premisa"):
                criterio = Criterio.objects.create(
                    premisa=data["premisa"],
                    descripcion=data.get("descripcion", "")
                )
                criterios_ids.add(criterio.id)

        # --- crear formularios ---
        for criterio_id in criterios_ids:
            Formulario.objects.create(
                proyecto_nuevo=proyecto_nuevo,
                criterio_id=criterio_id
            )

        # ================= COMITÉ =================
        usuarios_comite = request.POST.getlist("comite")
        for user_id in usuarios_comite:
            MiembroComite.objects.create(
                proyecto=proyecto,
                usuario_id=user_id
            )

        return redirect("proyectos_nuevos")

    # ================= GET =================
    return render(request, "secap/proyecto_crear.html", {
        "grupos": GrupoCriterios.objects.all(),
        "criterios": Criterio.objects.all(),
        "usuarios": User.objects.exclude(id=request.user.id),
    })

@login_required
@transaction.atomic
def proyecto_iniciar(request, proyecto_id):

    proyecto = get_object_or_404(
        Proyecto,
        id=proyecto_id,
        encargado=request.user
    )

    # ================= SEGURIDAD: EVITAR DUPLICADOS =================
    if hasattr(proyecto, "proyectoejecucion"):
        messages.warning(
            request,
            "Este proyecto ya se encuentra en ejecución."
        )
        return redirect("proyectos_ejecucion")

    if request.method == "POST":

        # ================= PROYECTO EN EJECUCIÓN =================
        proyecto_ejecucion = ProyectoEjecucion.objects.create(
            proyecto=proyecto
        )

        # ================= INDICADOR BASE (EJECUCIÓN) =================
        Indicador.objects.create(
            proyecto=proyecto_ejecucion,
            premisa="Ejecución financiera",
            descripcion=(
                "Nivel de ejecución del presupuesto aprobado "
                "en relación con el monto total del proyecto."
            ),
            valor_actual=0,
            valor_maximo=proyecto.monto
        )

        messages.success(
            request,
            "El proyecto fue iniciado en ejecución correctamente."
        )

        return redirect("proyectos_ejecucion")

    return redirect("proyectos_nuevos")

@login_required
@transaction.atomic
def meta_indicador_crear(request, indicador_id):
    indicador = get_object_or_404(Indicador, id=indicador_id)

    # Seguridad: solo usuarios relacionados al proyecto
    if request.user != indicador.proyecto.proyecto.encargado:
        return HttpResponseForbidden()

    if request.method == "POST":
        MetaIndicador.objects.create(
            indicador=indicador,
            fecha=request.POST.get("fecha"),
            valor_objetivo=request.POST.get("valor_objetivo"),
            comentario=request.POST.get("comentario", "")
        )

    return redirect(
        "proyectos_ejecucion",
        indicador.proyecto.id
    )

@login_required
@transaction.atomic
def meta_indicador_eliminar(request, meta_id):
    meta = get_object_or_404(MetaIndicador, id=meta_id)
    indicador = meta.indicador

    if request.user != indicador.proyecto.proyecto.encargado:
        return HttpResponseForbidden()

    if request.method == "POST":
        meta.delete()

    return redirect(
        "proyectos_ejecucion",
        indicador.proyecto.id
    )





