import os
import requests
import base64
import json
import jwt
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.files import File
from django.http import JsonResponse
import mimetypes
from django.http import Http404, HttpResponse
from django.db.models import Q
import logging

# Configurar el logger para la aplicación
logger = logging.getLogger(__name__)

from .utils import extraer_etiquetas_docx, rellenar_y_generar_documentos

from .models import (
    WorkflowTemplate,
    StageTemplate,
    StageTemplateResource,
    WorkflowExecution,
    StageExecution,
    FormSubmission,
    FormField,
    GeneratedDocument,
    FieldValue,
    DocumentFieldMapping,
    DocumentTemplate,
    DocuSealSettings
)


@login_required
def workflows_ejecucion(request, execution_id=None):
    modo = request.GET.get("modo", "asignados")
    estado_filtro = request.GET.get("estado", "en_curso")
    busqueda = request.GET.get("q", "").strip()

    base_mis = WorkflowExecution.objects.filter(initiated_by=request.user)
    base_asignados = WorkflowExecution.objects.filter(current_stage_execution__assigned_users=request.user)

    count_asignados = base_asignados.filter(status='IN_PROGRESS').count()
    count_mis_activos = base_mis.filter(status='IN_PROGRESS').count()
    count_mis_historial = base_mis.filter(status__in=['COMPLETED', 'REJECTED']).count()

    if modo == "asignados":
        mis_flujos = WorkflowExecution.objects.none()
        flujos_asignados = base_asignados.filter(status='IN_PROGRESS')
    else:
        flujos_asignados = WorkflowExecution.objects.none()
        if estado_filtro == "finalizados":
            mis_flujos = base_mis.filter(status__in=['COMPLETED', 'REJECTED'])
        else:
            mis_flujos = base_mis.filter(status='IN_PROGRESS')

    if busqueda:
        if modo == "asignados":
            flujos_asignados = flujos_asignados.filter(
                Q(id__icontains=busqueda) | Q(name__icontains=busqueda) | Q(workflow_template__name__icontains=busqueda)
            )
        else:
            mis_flujos = mis_flujos.filter(
                Q(id__icontains=busqueda) | Q(name__icontains=busqueda) | Q(workflow_template__name__icontains=busqueda)
            )

    available_templates = WorkflowTemplate.objects.filter(is_active=True)
    all_users = User.objects.select_related('userprofile').all()

    execution_sel = None
    if execution_id:
        execution_qs = WorkflowExecution.objects.filter(id=execution_id)
        if not request.user.is_staff:
            execution_qs = execution_qs.filter(
                Q(initiated_by=request.user) | Q(stage_history__assigned_users=request.user)
            ).distinct()
        execution_sel = get_object_or_404(execution_qs, id=execution_id)
    elif modo == "asignados" and flujos_asignados.exists():
        execution_sel = flujos_asignados.first()
    elif mis_flujos.exists():
        execution_sel = mis_flujos.first()

    es_iniciador = execution_sel and execution_sel.initiated_by == request.user
    es_asignado_actual = (
        execution_sel 
        and execution_sel.current_stage_execution 
        and execution_sel.current_stage_execution.assigned_users.filter(id=request.user.id).exists()
    )
    puede_ver_actual = es_iniciador or es_asignado_actual or request.user.is_staff

    etapas_historial_completo = []
    historial_respuestas = []
    form_fields = []
    doc_mappings = []
    form_values_map = {}
    stage_resources = []
    ocultar_historial_respuestas = False

    if execution_sel:
        etapas_historial_completo = execution_sel.stage_history.all().order_by('sequence_number')
        current_st_tmpl = execution_sel.current_stage_execution.stage_template if execution_sel.current_stage_execution else None
        
        if es_iniciador or request.user.is_staff or execution_sel.status in ['COMPLETED', 'REJECTED']:
            form_sub = FormSubmission.objects.filter(workflow_execution=execution_sel).first()
            if form_sub:
                historial_respuestas = form_sub.values.all().select_related('form_field', 'document_field_mapping', 'filled_in_stage')
        else:
            is_isolated_stage = (
                current_st_tmpl and current_st_tmpl.isolate_previous_history
            ) or (
                execution_sel.status == 'IN_PROGRESS' and not es_asignado_actual
            )

            if is_isolated_stage:
                ocultar_historial_respuestas = True
                historial_respuestas = FormSubmission.objects.none()
            else:
                form_sub = FormSubmission.objects.filter(workflow_execution=execution_sel).first()
                if form_sub:
                    historial_respuestas = form_sub.values.all().select_related('form_field', 'document_field_mapping', 'filled_in_stage')

        if current_st_tmpl and puede_ver_actual:
            stage_resources = current_st_tmpl.resources.all()

        if execution_sel.status == 'IN_PROGRESS' and es_asignado_actual and current_st_tmpl:
            form_fields = FormField.objects.filter(
                workflow_template=execution_sel.workflow_template, stage_template=current_st_tmpl
            )
            doc_mappings = DocumentFieldMapping.objects.filter(
                document_template__workflow_template=execution_sel.workflow_template, stage_template=current_st_tmpl
            )
        elif execution_sel.status in ['COMPLETED', 'REJECTED'] and (es_iniciador or request.user.is_staff):
            form_fields = FormField.objects.filter(workflow_template=execution_sel.workflow_template)
            doc_mappings = DocumentFieldMapping.objects.filter(document_template__workflow_template=execution_sel.workflow_template)
        else:
            form_fields = []
            doc_mappings = []
        
        for field in form_fields:
            f_val = FieldValue.objects.filter(form_submission__workflow_execution=execution_sel, form_field=field).first()
            if f_val:
                form_values_map[field.id] = f_val
                
        for mapping in doc_mappings:
            f_val = FieldValue.objects.filter(form_submission__workflow_execution=execution_sel, document_field_mapping=mapping).first()
            if f_val:
                form_values_map[mapping.id] = f_val

    return render(request, "sig_management/workflows_ejecucion.html", {
        "mis_flujos": mis_flujos,
        "flujos_asignados": flujos_asignados,
        "count_asignados": count_asignados,
        "count_mis_activos": count_mis_activos,
        "count_mis_historial": count_mis_historial,
        "available_templates": available_templates,
        "all_users": all_users,
        "execution_sel": execution_sel,
        "es_iniciador": es_iniciador,
        "es_asignado_actual": es_asignado_actual,
        "puede_ver_actual": puede_ver_actual,
        "etapas_historial_completo": etapas_historial_completo,
        "historial_respuestas": historial_respuestas,
        "ocultar_historial_respuestas": ocultar_historial_respuestas,
        "modo": modo,
        "estado_filtro": estado_filtro,
        "form_fields": form_fields,
        "doc_mappings": doc_mappings,
        "form_values_map": form_values_map,
        "stage_resources": stage_resources,
    })


@require_POST
@login_required
def retroceder_etapa(request, execution_id):
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    current_stage = execution.current_stage_execution

    with transaction.atomic():
        current_stage.status = 'RETURNED'
        current_stage.completed_at = timezone.now()
        current_stage.comments = request.POST.get("comments", "Devuelto para corrección.")
        current_stage.save()

        prev_template = current_stage.stage_template.previous_stage if current_stage.stage_template else None

        if prev_template:
            new_stage = StageExecution.objects.create(
                workflow_execution=execution, stage_template=prev_template,
                name=f"[Devuelto] {prev_template.name}", instructions=prev_template.instructions,
                status='PENDING', sequence_number=current_stage.sequence_number + 1
            )
            current_stage.save()
            new_stage.assigned_users.set(prev_template.assigned_users.all())
            execution.current_stage_execution = new_stage
            execution.save()
            messages.warning(request, "El flujo ha sido devuelto a la etapa anterior para correcciones.")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)


@require_POST
@login_required
def romper_flujo_ad_hoc(request, execution_id):
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    with transaction.atomic():
        execution.status = 'REJECTED'
        execution.completed_at = timezone.now()
        if execution.current_stage_execution:
            execution.current_stage_execution.status = 'SKIPPED'
            execution.current_stage_execution.completed_at = timezone.now()
            execution.current_stage_execution.comments = request.POST.get("comments", "Flujo interrumpido.")
            execution.current_stage_execution.save()
        execution.current_stage_execution = None
        execution.save()
        messages.warning(request, f"La instancia de flujo #{execution.id} ha sido interrumpida.")

    return redirect("workflows_ejecucion")


@require_POST
@login_required
def iniciar_nuevo_flujo(request):
    template_id = request.POST.get("workflow_template_id")
    workflow_template = get_object_or_404(WorkflowTemplate, id=template_id)
    instance_name = request.POST.get("instance_name", "").strip() or workflow_template.name

    with transaction.atomic():
        execution = WorkflowExecution.objects.create(
            workflow_template=workflow_template, initiated_by=request.user,
            name=instance_name, status='IN_PROGRESS'
        )

        stage_templates = workflow_template.stages.all().order_by('order')
        if not stage_templates.exists():
            messages.warning(request, "La plantilla seleccionada no tiene etapas configuradas.")
            return redirect("workflows_ejecucion")

        first_stage_exec = None
        for st in stage_templates:
            is_first = (st.order == 1)
            stage_exec = StageExecution.objects.create(
                workflow_execution=execution, stage_template=st,
                name=st.name, instructions=st.instructions,
                status='PENDING', sequence_number=st.order,
                started_at=timezone.now() if is_first else None
            )
            if st.is_dynamic_assignee:
                selected_users = request.POST.getlist(f"dynamic_users_{st.id}[]")
                if selected_users:
                    stage_exec.assigned_users.set(selected_users)
            else:
                stage_exec.assigned_users.set(st.assigned_users.all())

            if is_first:
                first_stage_exec = stage_exec

        if first_stage_exec:
            execution.current_stage_execution = first_stage_exec
            execution.save()
            messages.success(request, f"Se ha iniciado el trámite '{instance_name}'.")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)



def intentar_crear_sobre_docuseal(execution, pdf_path, user):
    """
    Crea una solicitud de firma de DocuSeal a partir de un PDF.

    Devuelve:
        {
            "envelope_id": "...",
            "embed_url": "https://docuseal.com/s/...",
            "embed_slug": "..."
        }

    Devuelve None si no puede crear la solicitud.

    IMPORTANTE:
    Esta versión utiliza el usuario recibido como firmante.
    El llamador debe pasar el usuario que realmente debe firmar.
    """

    settings_ds = DocuSealSettings.get_settings()

    prefix = f"[DocuSeal][Trámite #{execution.id}]"

    if not settings_ds.is_active:
        logger.warning("%s Integración desactivada.", prefix)
        return None

    api_key = (settings_ds.api_key or "").strip()

    if not api_key:
        logger.error("%s No hay API Key configurada.", prefix)
        return None

    if not user.email:
        logger.error(
            "%s El usuario %s no tiene correo electrónico.",
            prefix,
            user.pk,
        )
        return None

    if not pdf_path or not os.path.isfile(pdf_path):
        logger.error(
            "%s El PDF no existe o la ruta es inválida: %s",
            prefix,
            pdf_path,
        )
        return None

    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_base64 = base64.b64encode(
                pdf_file.read()
            ).decode("ascii")

        api_url = settings_ds.api_url.rstrip("/")

        # Endpoint documentado para solicitudes de firma desde PDF.
        url = f"{api_url}/submissions/pdf"

        payload = {
            "name": f"Trámite #{execution.id} - {execution.name}",
            "documents": [
                {
                    "name": os.path.basename(pdf_path),
                    "file": pdf_base64,
                }
            ],
            "submitters": [
                {
                    "email": user.email,
                    "name": user.get_full_name() or user.username,
                    "role": "First Party",
                }
            ],
        }

        headers = {
            "X-Auth-Token": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        logger.info(
            "%s Enviando PDF para firma. Usuario=%s, archivo=%s",
            prefix,
            user.pk,
            os.path.basename(pdf_path),
        )

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(10, 60),
        )

        if not response.ok:
            # No registrar la API Key ni el contenido del PDF.
            logger.error(
                "%s DocuSeal devolvió HTTP %s. Respuesta=%s",
                prefix,
                response.status_code,
                response.text[:2000],
            )
            return None

        try:
            data = response.json()
        except ValueError:
            logger.error(
                "%s DocuSeal devolvió una respuesta que no es JSON.",
                prefix,
            )
            return None

        envelope_id = data.get("id")
        submitters = data.get("submitters") or []

        if not envelope_id:
            logger.error(
                "%s La respuesta no contiene el identificador del sobre.",
                prefix,
            )
            return None

        if not submitters:
            logger.error(
                "%s La respuesta no contiene información de firmantes.",
                prefix,
            )
            return None

        # Localizar al firmante correspondiente al usuario.
        submitter = next(
            (
                item
                for item in submitters
                if (item.get("email") or "").lower()
                == user.email.lower()
            ),
            None,
        )

        if not submitter:
            logger.error(
                "%s No se encontró el firmante esperado en la respuesta.",
                prefix,
            )
            return None

        # DocuSeal puede proporcionar directamente embed_src.
        embed_url = submitter.get("embed_src")

        # Compatibilidad con respuestas que incluyen slug.
        if not embed_url and submitter.get("slug"):
            embed_url = (
                f"https://docuseal.com/s/{submitter['slug']}"
            )

        if not embed_url:
            logger.error(
                "%s La respuesta no contiene embed_src ni slug.",
                prefix,
            )
            return None

        logger.info(
            "%s Solicitud creada correctamente. Sobre=%s, usuario=%s",
            prefix,
            envelope_id,
            user.pk,
        )

        return {
            "envelope_id": str(envelope_id),
            "embed_url": embed_url,
            "embed_slug": submitter.get("slug", ""),
        }

    except requests.Timeout:
        logger.exception(
            "%s Tiempo de espera agotado al contactar DocuSeal.",
            prefix,
        )

    except requests.RequestException:
        logger.exception(
            "%s Error de comunicación con DocuSeal.",
            prefix,
        )

    except OSError:
        logger.exception(
            "%s Error al leer el PDF.",
            prefix,
        )

    except Exception:
        logger.exception(
            "%s Error inesperado al crear la solicitud de firma.",
            prefix,
        )

    return None

@require_POST
@login_required
def crear_plantilla_flujo(request):
    """Crea la plantilla y avisa claramente en pantalla si el orden de la firma es incorrecto."""
    nombre = request.POST.get("template_name")
    descripcion = request.POST.get("template_description", "")
    
    if not nombre:
        messages.error(request, "El nombre de la plantilla es obligatorio.")
        return redirect("workflows_ejecucion")

    with transaction.atomic():
        template = WorkflowTemplate.objects.create(name=nombre, description=descripcion, owner=request.user, is_active=True)

        nombres_etapas = request.POST.getlist("stage_name[]")
        instrucciones_etapas = request.POST.getlist("stage_instructions[]")
        etapas_creadas = []
        
        if nombres_etapas:
            for index, est_nombre in enumerate(nombres_etapas):
                if not est_nombre.strip():
                    continue
                instruccion = instrucciones_etapas[index] if index < len(instrucciones_etapas) else ""
                order_num = index + 1
                is_dynamic = request.POST.get(f"stage_dynamic_{order_num}") == "on"
                is_isolated = request.POST.get(f"stage_isolate_{order_num}") == "on"
                
                stage = StageTemplate.objects.create(
                    workflow=template, name=est_nombre, instructions=instruccion,
                    order=order_num, is_dynamic_assignee=is_dynamic, isolate_previous_history=is_isolated
                )
                if not is_dynamic:
                    user_ids = request.POST.getlist(f"stage_users_{order_num}[]")
                    if user_ids:
                        stage.assigned_users.set(user_ids)
                    else:
                        stage.assigned_users.add(request.user)
                etapas_creadas.append(stage)

        if not etapas_creadas:
            messages.error(request, "Debe configurar al menos una etapa válida.")
            return redirect("workflows_ejecucion")

        doc_names = request.POST.getlist("doc_name[]")
        doc_files = request.FILES.getlist("doc_file[]")
        
        map_keys = request.POST.getlist("map_key[]")
        map_labels = request.POST.getlist("map_label[]")
        map_stages = request.POST.getlist("map_stage_index[]")

        # Calcular etapa máxima de llenado
        max_llenado_stage = 1
        for idx, s_idx in enumerate(map_stages):
            try:
                s_num = int(s_idx)
                if map_keys[idx] != "__SIGNATURE_FIELD__":
                    if s_num > max_llenado_stage:
                        max_llenado_stage = s_num
            except ValueError:
                pass

        # VALIDACIÓN ESTRICTA CON MENSAJE VISIBLE EN PANTALLA
        for idx, key in enumerate(map_keys):
            if key == "__SIGNATURE_FIELD__":
                sig_stage = int(map_stages[idx]) if map_stages[idx].isdigit() else 1
                if sig_stage <= max_llenado_stage:
                    # CORREGIDO: Muestra un error visible de Django y revierte la transacción
                    messages.error(
                        request, 
                        f"❌ Error de validación: La etapa de 'Revisar y Firmar' (Etapa {sig_stage}) no puede ser igual ni anterior a las etapas de llenado de datos (Etapa {max_llenado_stage})."
                    )
                    transaction.set_rollback(True)
                    return redirect("workflows_ejecucion")

        doc_template = None
        for idx, archivo in enumerate(doc_files):
            doc_titulo = doc_names[idx] if idx < len(doc_names) and doc_names[idx].strip() else archivo.name
            req_sig = request.POST.get(f"doc_requires_signature_{idx}") == "on"

            doc_template = DocumentTemplate.objects.create(
                workflow_template=template, file=archivo, name=doc_titulo, requires_signature=req_sig
            )

        for idx, key in enumerate(map_keys):
            label = map_labels[idx] if idx < len(map_labels) else key
            st_index = int(map_stages[idx]) if idx < len(map_stages) and map_stages[idx].isdigit() else 1
            st_obj = etapas_creadas[st_index - 1] if st_index <= len(etapas_creadas) else etapas_creadas[-1]

            if doc_template:
                DocumentFieldMapping.objects.create(
                    document_template=doc_template,
                    stage_template=st_obj,
                    placeholder_key=key,
                    label=label,
                    field_type='TEXT' if key != "__SIGNATURE_FIELD__" else 'SIGNATURE',
                    is_required=True
                )

        messages.success(request, f"¡Plantilla '{nombre}' creada exitosamente!")

    return redirect("workflows_ejecucion")

@require_POST
@login_required
def avanzar_etapa(request, execution_id):
    """Guarda respuestas, avanza el flujo y dispara el widget interactivo de DocuSeal al llegar a la etapa de firma."""
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    current_stage = execution.current_stage_execution

    if not current_stage or execution.status != 'IN_PROGRESS' or not current_stage.assigned_users.filter(id=request.user.id).exists():
        messages.error(request, "No tienes permisos para modificar o avanzar esta etapa.")
        return redirect("workflows_ejecucion")

    with transaction.atomic():
        form_sub, _ = FormSubmission.objects.get_or_create(workflow_execution=execution)
        
        # Guardar valores de formularios manuales
        form_fields = FormField.objects.filter(workflow_template=execution.workflow_template, stage_template=current_stage.stage_template)
        for field in form_fields:
            field_key = f"field_{field.id}"
            if field_key in request.POST or field_key in request.FILES:
                val_text = request.POST.get(field_key, "")
                val_file = request.FILES.get(field_key, None)
                FieldValue.objects.update_or_create(
                    form_submission=form_sub, form_field=field,
                    defaults={'text_value': val_text if not val_file else "", 'file_value': val_file if val_file else None, 'filled_in_stage': current_stage}
                )

        # Guardar valores de mapeos de documentos
        doc_mappings = DocumentFieldMapping.objects.filter(document_template__workflow_template=execution.workflow_template, stage_template=current_stage.stage_template)
        for mapping in doc_mappings:
            map_key = f"mapping_{mapping.id}"
            if map_key in request.POST or map_key in request.FILES:
                val_text = request.POST.get(map_key, "")
                val_file = request.FILES.get(map_key, None)
                FieldValue.objects.update_or_create(
                    form_submission=form_sub, document_field_mapping=mapping,
                    defaults={'text_value': val_text if not val_file else "", 'file_value': val_file if val_file else None, 'filled_in_stage': current_stage}
                )

        current_stage.status = 'COMPLETED'
        current_stage.completed_by = request.user
        current_stage.completed_at = timezone.now()
        current_stage.comments = request.POST.get("comments", "")
        current_stage.save()

        # Verificar si la etapa ACTUAL o la SIGUIENTE es la de firma
        is_signature_stage = DocumentFieldMapping.objects.filter(
            document_template__workflow_template=execution.workflow_template,
            stage_template=current_stage.stage_template,
            placeholder_key="__SIGNATURE_FIELD__"
        ).exists()

        siguiente_sequence_num = current_stage.sequence_number + 1
        next_stage = execution.stage_history.filter(sequence_number=siguiente_sequence_num).first()

        if next_stage:
            # Comprobar si la siguiente etapa también requiere firma
            next_has_sig = DocumentFieldMapping.objects.filter(
                document_template__workflow_template=execution.workflow_template,
                stage_template=next_stage.stage_template,
                placeholder_key="__SIGNATURE_FIELD__"
            ).exists() or execution.workflow_template.document_templates.filter(requires_signature=True).exists()

            # Si estamos entrando o pasando por una etapa de firma, generar el PDF y abrir DocuSeal
            if (is_signature_stage or next_has_sig) and not execution.docuseal_embed_slug:
                rellenar_y_generar_documentos(execution)
                gen_doc = execution.generated_documents.first()
                if gen_doc and os.path.exists(gen_doc.file_path):
                    res_ds = intentar_crear_sobre_docuseal(execution, gen_doc.file_path, request.user)
                    if res_ds:
                        execution.docuseal_envelope_id = res_ds["envelope_id"]

                        # Guardamos la URL completa para usarla directamente
                        # como data-src del componente oficial de DocuSeal.
                        execution.docuseal_embed_slug = res_ds["embed_url"]

                        execution.signature_completed = False
                        execution.save(
                            update_fields=[
                                "docuseal_envelope_id",
                                "docuseal_embed_slug",
                                "signature_completed",
                            ]
                        )

                        logger.info(
                            "[DocuSeal][Trámite #%s] Estado de firma inicializado.",
                            execution.id,
                        )

                        messages.success(
                            request,
                            "Solicitud de firma creada correctamente."
                        )

                    else:
                        logger.error(
                            "[DocuSeal][Trámite #%s] No se pudo crear la solicitud.",
                            execution.id,
                        )

                        messages.error(
                            request,
                            "No se pudo crear la solicitud de firma. "
                            "El administrador puede consultar los registros del servidor."
                        )
                else:
                    messages.warning(request, "Aviso: El trámite avanzó, pero DocuSeal no generó el sobre. Revise su API Key.")

            next_stage.started_at = timezone.now()
            next_stage.save()
            execution.current_stage_execution = next_stage
            execution.save()
            messages.success(request, f"Etapa completada. Avanzado a: {next_stage.name}")
        else:
            # Fin del flujo
            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.current_stage_execution = None
            
            if not execution.generated_documents.exists():
                rellenar_y_generar_documentos(execution)

            execution.save()
            messages.success(request, "¡El trámite ha finalizado exitosamente!")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)

@login_required
def descargar_documento_generado(request, doc_id):
    gen_doc = get_object_or_404(GeneratedDocument, id=doc_id)
    execution = gen_doc.workflow_execution
    es_participante = execution.initiated_by == request.user or execution.stage_history.filter(assigned_users=request.user).exists()
    
    if not es_participante and not request.user.is_staff:
        raise Http404("No tienes permisos para descargar este archivo.")

    file_path = gen_doc.file_path
    if os.path.exists(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type or 'application/octet-stream')
            nombre_tramite = f"Tramite_{execution.id}"
            nombre_doc = gen_doc.name or "documento"
            import re
            limpiar_texto = lambda t: re.sub(r'[\/*?:"<>|\\#]', '', t).strip().replace(' ', '_')
            filename = f"{limpiar_texto(nombre_tramite)}_{limpiar_texto(nombre_doc)}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    raise Http404("El archivo físico no se encuentra en el servidor.")



@require_POST
@login_required
def extraer_etiquetas_ajax(request):
    archivo = request.FILES.get('doc_file')
    if not archivo:
        return JsonResponse({'etiquetas': []})
    return JsonResponse({'etiquetas': list(extraer_etiquetas_docx(archivo))})


import jwt

from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.exceptions import ImproperlyConfigured

from .models import DocuSealSettings

@login_required
def probar_docuseal_builder(request):
    """
    Prueba controlada del editor visual de DocuSeal.

    Solo permite el acceso a administradores de Django.
    El JWT se genera en el backend y nunca se envía la API Key
    al navegador.
    """

    # Solo administradores pueden abrir la prueba del editor.
    if not request.user.is_staff:
        return HttpResponse(
            "No tienes permisos para acceder al editor de prueba.",
            status=403,
        )

    ds = DocuSealSettings.get_settings()

    # Validar la configuración de DocuSeal.
    if not ds.is_active:
        return HttpResponse(
            "La integración con DocuSeal está desactivada en Django Admin.",
            status=400,
        )

    api_key = (ds.api_key or "").strip()
    admin_email = (ds.admin_email or "").strip()
    integration_email = (request.user.email or "").strip()

    if not api_key:
        return HttpResponse(
            "Falta configurar la API Key de DocuSeal en Django Admin.",
            status=400,
        )

    if not admin_email:
        return HttpResponse(
            "Falta configurar el correo administrador de DocuSeal.",
            status=400,
        )

    if not integration_email:
        return HttpResponse(
            "Tu usuario de Django no tiene un correo electrónico configurado.",
            status=400,
        )

    # Documento público de ejemplo, utilizado exclusivamente para la prueba.
    document_url = "https://www.irs.gov/pub/irs-pdf/fw9.pdf"

    timestamp = int(timezone.now().timestamp())

    payload = {
        "user_email": admin_email,
        "integration_email": integration_email,
        "name": f"PRUEBA GET DocuSeal {timestamp}",
        "external_id": (
            f"get-docuseal-demo-{request.user.pk}-{timestamp}"
        ),
        "document_urls": [document_url],
    }

    try:
        builder_token = jwt.encode(
            payload,
            api_key,
            algorithm="HS256",
        )
    except Exception:
        logger.exception(
            "[DocuSeal] Error al generar el token del editor."
        )
        return HttpResponse(
            "No se pudo preparar el editor de DocuSeal. "
            "Revisa los registros del servidor.",
            status=500,
        )

    return render(
        request,
        "sig_management/docuseal_builder_demo.html",
        {
            "builder_token": builder_token,
        },
    )