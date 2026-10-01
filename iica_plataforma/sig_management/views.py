import os
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
from .models import GeneratedDocument

from .utils import extraer_etiquetas_docx, rellenar_y_generar_documentos

from .models import (
    WorkflowTemplate,
    StageTemplate,
    WorkflowExecution,
    StageExecution,
    FormSubmission,
    FormField,
    FieldValue,
    DocumentFieldMapping,
    DocumentTemplate  
)

@login_required
def workflows_ejecucion(request, execution_id=None):
    """Vista principal con soporte para filtrado de campos y mapeos de documentos por etapa."""
    # ... [código anterior de filtros permanece igual] ...
    modo = request.GET.get("modo", "mis_flujos")
    estado_filtro = request.GET.get("estado", "en_curso")

    base_mis = WorkflowExecution.objects.filter(initiated_by=request.user)
    base_asignados = WorkflowExecution.objects.filter(current_stage_execution__assigned_users=request.user)

    if estado_filtro == "finalizados":
        mis_flujos = base_mis.filter(status__in=['COMPLETED', 'REJECTED'])
        flujos_asignados = base_asignados.filter(status__in=['COMPLETED', 'REJECTED'])
    else:
        mis_flujos = base_mis.filter(status='IN_PROGRESS')
        flujos_asignados = base_asignados.filter(status='IN_PROGRESS')

    available_templates = WorkflowTemplate.objects.filter(is_active=True)
    all_users = User.objects.select_related('userprofile').all()

    execution_sel = None
    if execution_id:
        execution_sel = get_object_or_404(WorkflowExecution, id=execution_id)
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

    etapas_historial = []
    form_fields = []
    doc_mappings = []
    form_values_map = {}

    if execution_sel:
        etapas_historial = execution_sel.stage_history.all().order_by('sequence_number')
        
        # Si el flujo está activo y en curso, mostramos solo los de la etapa actual. 
        # Si ya está finalizado/rechazado (historial), mostramos todos los campos de la plantilla.
        if execution_sel.status == 'IN_PROGRESS' and execution_sel.current_stage_execution and execution_sel.current_stage_execution.stage_template:
            form_fields = FormField.objects.filter(
                workflow_template=execution_sel.workflow_template,
                stage_template=execution_sel.current_stage_execution.stage_template
            )
            doc_mappings = DocumentFieldMapping.objects.filter(
                document_template__workflow_template=execution_sel.workflow_template,
                stage_template=execution_sel.current_stage_execution.stage_template
            )
        else:
            # En el historial (completados o rechazados), mostramos todo el formulario histórico
            form_fields = FormField.objects.filter(workflow_template=execution_sel.workflow_template)
            doc_mappings = DocumentFieldMapping.objects.filter(document_template__workflow_template=execution_sel.workflow_template)
        
        # Recargar los valores guardados usando el ID correcto del campo/mapeo
        for field in form_fields:
            f_val = FieldValue.objects.filter(
                form_submission__workflow_execution=execution_sel,
                form_field=field
            ).first()
            if f_val:
                form_values_map[field.id] = f_val  # Usamos directamente el ID para que coincida con el template
                
        for mapping in doc_mappings:
            f_val = FieldValue.objects.filter(
                form_submission__workflow_execution=execution_sel,
                document_field_mapping=mapping
            ).first()
            if f_val:
                form_values_map[mapping.id] = f_val  # Usamos directamente el ID

    return render(request, "sig_management/workflows_ejecucion.html", {
        "mis_flujos": mis_flujos,
        "flujos_asignados": flujos_asignados,
        "available_templates": available_templates,
        "all_users": all_users,
        "execution_sel": execution_sel,
        "es_iniciador": es_iniciador,
        "es_asignado_actual": es_asignado_actual,
        "etapas_historial": etapas_historial,
        "modo": modo,
        "estado_filtro": estado_filtro,
        "form_fields": form_fields,
        "doc_mappings": doc_mappings,
        "form_values_map": form_values_map,
    })

@require_POST
@login_required
def retroceder_etapa(request, execution_id):
    """Retrocede a la etapa anterior utilizando el puntero correspondiente."""
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
                workflow_execution=execution,
                stage_template=prev_template,
                previous_execution=current_stage,
                name=f"[Devuelto] {prev_template.name}",
                instructions=prev_template.instructions,
                status='PENDING',
                sequence_number=current_stage.sequence_number + 1
            )
            current_stage.next_execution = new_stage
            current_stage.save()

            new_stage.assigned_users.set(prev_template.assigned_users.all())
            execution.current_stage_execution = new_stage
            execution.save()
            messages.warning(request, "El flujo ha sido devuelto a la etapa anterior para correcciones.")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)


@require_POST
@login_required
def romper_flujo_ad_hoc(request, execution_id):
    """Rompe, cancela o desvía una instancia de flujo de manera ad-hoc."""
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    
    with transaction.atomic():
        execution.status = 'REJECTED'
        execution.completed_at = timezone.now()
        
        if execution.current_stage_execution:
            execution.current_stage_execution.status = 'SKIPPED'
            execution.current_stage_execution.completed_at = timezone.now()
            execution.current_stage_execution.comments = request.POST.get("comments", "Flujo interrumpido/roto ad-hoc.")
            execution.current_stage_execution.save()
            
        execution.current_stage_execution = None
        execution.save()
        
        messages.warning(request, f"La instancia de flujo #{execution.id} ha sido interrumpida/rota ad-hoc.")

    return redirect("workflows_ejecucion")


@require_POST
@login_required
def iniciar_nuevo_flujo(request):
    """Crea una nueva instancia de flujo y asigna participantes dinámicos en sus respectivas etapas."""
    template_id = request.POST.get("workflow_template_id")
    workflow_template = get_object_or_404(WorkflowTemplate, id=template_id)
    instance_name = request.POST.get("instance_name", "").strip() or workflow_template.name

    with transaction.atomic():
        execution = WorkflowExecution.objects.create(
            workflow_template=workflow_template,
            initiated_by=request.user,
            name=instance_name,
            status='IN_PROGRESS'
        )

        stage_templates = workflow_template.stages.all().order_by('order')
        if not stage_templates.exists():
            messages.warning(request, "La plantilla seleccionada no tiene etapas configuradas.")
            return redirect("workflows_ejecucion")

        first_stage_exec = None

        for st in stage_templates:
            stage_exec = StageExecution.objects.create(
                workflow_execution=execution,
                stage_template=st,
                name=st.name,
                instructions=st.instructions,
                status='PENDING',
                sequence_number=st.order
            )

            # Asignar usuarios según si es dinámico o estático
            if st.is_dynamic_assignee:
                selected_users = request.POST.getlist(f"dynamic_users_{st.id}[]")
                if selected_users:
                    stage_exec.assigned_users.set(selected_users)
            else:
                stage_exec.assigned_users.set(st.assigned_users.all())

            if st.order == 1:
                first_stage_exec = stage_exec

        if first_stage_exec:
            execution.current_stage_execution = first_stage_exec
            execution.save()
            messages.success(request, f"Se ha iniciado el trámite '{instance_name}'.")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)

@login_required
def descargar_documento_generado(request, doc_id):
    """Permite descargar el documento final generado (PDF o Word con valores reemplazados)."""
    gen_doc = get_object_or_404(GeneratedDocument, id=doc_id)
    
    # Verificar que el usuario tenga permisos (sea iniciador o esté asignado en alguna etapa del flujo)
    execution = gen_doc.workflow_execution
    es_participante = (
        execution.initiated_by == request.user or
        execution.stage_history.filter(assigned_users=request.user).exists()
    )
    
    if not es_participante and not request.user.is_staff:
        raise Http404("No tienes permisos para descargar este archivo.")

    file_path = gen_doc.file_path
    if os.path.exists(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type or 'application/octet-stream')
            
            # 1. Obtener un nombre base amigable (usando el nombre descriptivo de gen_doc)
            # Si 'gen_doc' tiene un campo de nombre o está vinculado a una plantilla, úsalo:
            nombre_base = getattr(gen_doc, 'name', None) or "documento_generado"
            
            # O si el nombre viene de una relación, por ejemplo gen_doc.template.name, ajústalo aquí.
            # Limpiamos espacios y aseguramos la extensión correcta basada en el archivo real
            _, ext = os.path.splitext(file_path)
            if not ext:
                ext = ".docx"
                
            # Limpiamos caracteres extraños opcionalmente o dejamos el nombre limpio
            filename = f"{nombre_base.strip()}{ext}"

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    raise Http404("El archivo físico no se encuentra en el servidor.")

@require_POST
@login_required
def avanzar_etapa(request, execution_id):
    """Avanza la etapa completando la actual y activando la siguiente en secuencia."""
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    current_stage = execution.current_stage_execution

    if not current_stage or not current_stage.assigned_users.filter(id=request.user.id).exists():
        messages.error(request, "No tienes permisos para avanzar esta etapa.")
        return redirect("workflows_ejecucion_detalle", execution_id=execution.id)

    with transaction.atomic():
        form_sub, _ = FormSubmission.objects.get_or_create(workflow_execution=execution)
        
        # 1. Guardar campos generales
        form_fields = FormField.objects.filter(
            workflow_template=execution.workflow_template,
            stage_template=current_stage.stage_template
        )
        for field in form_fields:
            field_key = f"field_{field.id}"
            if field_key in request.POST or field_key in request.FILES:
                val_text = request.POST.get(field_key, "")
                val_file = request.FILES.get(field_key, None)
                
                FieldValue.objects.update_or_create(
                    form_submission=form_sub,
                    form_field=field,
                    defaults={
                        'text_value': val_text if not val_file else "",
                        'file_value': val_file if val_file else None,
                        'filled_in_stage': current_stage
                    }
                )

        # 2. Guardar mapeos de documentos
        doc_mappings = DocumentFieldMapping.objects.filter(
            document_template__workflow_template=execution.workflow_template,
            stage_template=current_stage.stage_template
        )
        for mapping in doc_mappings:
            map_key = f"mapping_{mapping.id}"
            if map_key in request.POST or map_key in request.FILES:
                val_text = request.POST.get(map_key, "")
                val_file = request.FILES.get(map_key, None)
                
                FieldValue.objects.update_or_create(
                    form_submission=form_sub,
                    document_field_mapping=mapping,
                    defaults={
                        'text_value': val_text if not val_file else "",
                        'file_value': val_file if val_file else None,
                        'filled_in_stage': current_stage
                    }
                )

        current_stage.status = 'COMPLETED'
        current_stage.completed_by = request.user
        current_stage.completed_at = timezone.now()
        current_stage.comments = request.POST.get("comments", "")
        current_stage.save()

        # Buscar la siguiente etapa en el historial ya creada
        next_stage = execution.stage_history.filter(sequence_number=current_stage.sequence_number + 1).first()

        if next_stage:
            current_stage.next_execution = next_stage
            current_stage.save()

            execution.current_stage_execution = next_stage
            execution.save()
            messages.success(request, f"Etapa completada. Avanzado a: {next_stage.name}")
        else:
            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.current_stage_execution = None
            
            rellenar_y_generar_documentos(execution)
            execution.save()
            messages.success(request, "¡El flujo ha finalizado exitosamente y los documentos han sido generados!")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)

@require_POST
@login_required
def crear_plantilla_flujo(request):
    """Crea plantilla procesando etapas, soporte de participantes indefinidos y documentos sin etapa global."""
    nombre = request.POST.get("template_name")
    descripcion = request.POST.get("template_description", "")
    
    if not nombre:
        messages.error(request, "El nombre de la plantilla es obligatorio.")
        return redirect("workflows_ejecucion")

    with transaction.atomic():
        template = WorkflowTemplate.objects.create(
            name=nombre,
            description=descripcion,
            owner=request.user,
            is_active=True
        )

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
                
                stage = StageTemplate.objects.create(
                    workflow=template,
                    name=est_nombre,
                    instructions=instruccion,
                    order=order_num,
                    is_dynamic_assignee=is_dynamic
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

        # Guardar Documentos Word (sin etapa global)
        doc_names = request.POST.getlist("doc_name[]")
        doc_files = request.FILES.getlist("doc_file[]")
        doc_templates_creados = []

        for idx, archivo in enumerate(doc_files):
            doc_titulo = doc_names[idx] if idx < len(doc_names) and doc_names[idx].strip() else archivo.name
            doc_template = DocumentTemplate.objects.create(
                workflow_template=template,
                file=archivo,
                name=doc_titulo
            )
            doc_templates_creados.append(doc_template)
            
            etiquetas_encontradas = extraer_etiquetas_docx(archivo)
            for tag in etiquetas_encontradas:
                DocumentFieldMapping.objects.get_or_create(
                    document_template=doc_template,
                    stage_template=etapas_creadas[0],
                    placeholder_key=tag,
                    defaults={
                        'label': f"Campo: {tag}",
                        'field_type': 'TEXT',
                        'is_required': True
                    }
                )

        # Mapeo granular manual de etiquetas por etapa
        map_doc_indices = request.POST.getlist("map_doc_index[]")
        map_keys = request.POST.getlist("map_key[]")
        map_labels = request.POST.getlist("map_label[]")
        map_stages = request.POST.getlist("map_stage_index[]")

        for m_idx, key in enumerate(map_keys):
            if not key.strip():
                continue
            d_idx = int(map_doc_indices[m_idx]) if m_idx < len(map_doc_indices) and map_doc_indices[m_idx].isdigit() else 0
            target_doc = doc_templates_creados[d_idx] if 0 <= d_idx < len(doc_templates_creados) else (doc_templates_creados[0] if doc_templates_creados else None)
            
            if not target_doc:
                continue

            st_idx = int(map_stages[m_idx]) if m_idx < len(map_stages) and map_stages[m_idx].isdigit() else 1
            target_stage = etapas_creadas[st_idx - 1] if 0 < st_idx <= len(etapas_creadas) else etapas_creadas[0]
            label = map_labels[m_idx] if m_idx < len(map_labels) and map_labels[m_idx].strip() else f"Valor para {{{key}}}"

            DocumentFieldMapping.objects.update_or_create(
                document_template=target_doc,
                placeholder_key=key.strip(),
                defaults={
                    'stage_template': target_stage,
                    'label': label,
                    'field_type': 'TEXT',
                    'is_required': True
                }
            )

        # Preguntas manuales adicionales
        labels_campos = request.POST.getlist("field_label[]")
        tipos_campos = request.POST.getlist("field_type[]")
        etapas_asociadas = request.POST.getlist("field_stage_index[]")
        
        for idx, label in enumerate(labels_campos):
            if not label.strip():
                continue
            f_type = tipos_campos[idx] if idx < len(tipos_campos) else 'TEXT'
            st_idx = int(etapas_asociadas[idx]) if idx < len(etapas_asociadas) and etapas_asociadas[idx].isdigit() else 1
            
            if 0 < st_idx <= len(etapas_creadas):
                target_stage = etapas_creadas[st_idx - 1]
            else:
                target_stage = etapas_creadas[0]

            FormField.objects.create(
                workflow_template=template,
                stage_template=target_stage,
                label=label,
                field_type=f_type,
                is_required=True,
                order=200 + idx
            )

        messages.success(request, f"¡Plantilla '{nombre}' configurada exitosamente!")

    return redirect("workflows_ejecucion")

@require_POST
@login_required
def extraer_etiquetas_ajax(request):
    """Extrae las etiquetas {{tag}} de un archivo Word subido temporalmente vía AJAX."""
    archivo = request.FILES.get('doc_file')
    if not archivo:
        return JsonResponse({'etiquetas': []})
    
    # Usa tu función existente para leer el docx
    etiquetas = extraer_etiquetas_docx(archivo)
    return JsonResponse({'etiquetas': list(etiquetas)})