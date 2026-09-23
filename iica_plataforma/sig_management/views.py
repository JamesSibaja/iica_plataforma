from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from .utils import extraer_etiquetas_docx

from .models import (
    WorkflowTemplate,
    StageTemplate,
    WorkflowExecution,
    StageExecution,
    FormSubmission,
    FormField,
    FieldValue
)

@login_required
def workflows_ejecucion(request, execution_id=None):
    """Vista principal con soporte para bandejas de activos/procesados y línea de tiempo."""
    modo = request.GET.get("modo", "mis_flujos")
    estado_filtro = request.GET.get("estado", "en_curso") # en_curso o finalizados

    # Consultas base separando en curso vs finalizados/procesados
    base_mis = WorkflowExecution.objects.filter(initiated_by=request.user)
    base_asignados = WorkflowExecution.objects.filter(current_stage_execution__assigned_users=request.user)

    if estado_filtro == "finalizados":
        mis_flujos = base_mis.filter(status__in=['COMPLETED', 'REJECTED'])
        flujos_asignados = base_asignados.filter(status__in=['COMPLETED', 'REJECTED'])
    else:
        mis_flujos = base_mis.filter(status='IN_PROGRESS')
        flujos_asignados = base_asignados.filter(status='IN_PROGRESS')

    available_templates = WorkflowTemplate.objects.filter(is_active=True)
    
    # ── SECCIÓN CLAVE: Cargar usuarios de la oficina para los selectores del modal ──
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
    form_template = None
    form_fields = []
    form_values_map = {}

    if execution_sel:
        # Línea de tiempo ordenada por la secuencia de ejecución (doble enlace)
        etapas_historial = execution_sel.stage_history.all().order_by('sequence_number')
        
        if execution_sel.workflow_template.form_template:
            form_template = execution_sel.workflow_template.form_template
            form_fields = form_template.fields.all()
            
            form_sub, _ = FormSubmission.objects.get_or_create(
                workflow_execution=execution_sel,
                defaults={'form_template': form_template}
            )
            
            for f_val in form_sub.values.all():
                form_values_map[f_val.form_field_id] = f_val.text_value or f_val.file_value

    return render(request, "sig_management/workflows_ejecucion.html", {
        "mis_flujos": mis_flujos,
        "flujos_asignados": flujos_asignados,
        "available_templates": available_templates,
        "all_users": all_users,  # <--- Pasado correctamente al template HTML
        "execution_sel": execution_sel,
        "es_iniciador": es_iniciador,
        "es_asignado_actual": es_asignado_actual,
        "etapas_historial": etapas_historial,
        "modo": modo,
        "estado_filtro": estado_filtro,
        "form_template": form_template,
        "form_fields": form_fields,
        "form_values_map": form_values_map,
    })


@require_POST
@login_required
def avanzar_etapa(request, execution_id):
    """Avanza la etapa actual usando el puntero de la lista doblemente enlazada (`next_stage`)."""
    execution = get_object_or_404(WorkflowExecution, id=execution_id)
    current_stage = execution.current_stage_execution

    if not current_stage or not current_stage.assigned_users.filter(id=request.user.id).exists():
        messages.error(request, "No tienes permisos para avanzar esta etapa.")
        return redirect("workflows_ejecucion_detalle", execution_id=execution.id)

    with transaction.atomic():
        # 1. Guardar campos del formulario
        if execution.workflow_template.form_template:
            form_sub, _ = FormSubmission.objects.get_or_create(
                workflow_execution=execution,
                defaults={'form_template': execution.workflow_template.form_template}
            )
            
            for field in execution.workflow_template.form_template.fields.all():
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

        # 2. Completar etapa actual
        current_stage.status = 'COMPLETED'
        current_stage.completed_by = request.user
        current_stage.completed_at = timezone.now()
        current_stage.comments = request.POST.get("comments", "")
        current_stage.save()

        # 3. Obtener la siguiente etapa mediante lista doblemente enlazada
        next_template = current_stage.stage_template.next_stage if current_stage.stage_template else None

        if next_template:
            new_stage = StageExecution.objects.create(
                workflow_execution=execution,
                stage_template=next_template,
                previous_execution=current_stage,
                name=next_template.name,
                instructions=next_template.instructions,
                status='PENDING',
                sequence_number=current_stage.sequence_number + 1
            )
            current_stage.next_execution = new_stage
            current_stage.save()

            new_stage.assigned_users.set(next_template.assigned_users.all())
            execution.current_stage_execution = new_stage
            execution.save()
            messages.success(request, f"Etapa completada. Avanzado a: {next_template.name}")
        else:
            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.current_stage_execution = None
            execution.save()
            messages.success(request, "¡El flujo ha finalizado exitosamente!")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)


@require_POST
@login_required
def retroceder_etapa(request, execution_id):
    """Retrocede a la etapa anterior utilizando el puntero `previous_execution` o `previous_stage`."""
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
    """Crea una nueva instancia de flujo basada en una plantilla y arranca su paso 1."""
    template_id = request.POST.get("workflow_template_id")
    workflow_template = get_object_or_404(WorkflowTemplate, id=template_id)

    with transaction.atomic():
        execution = WorkflowExecution.objects.create(
            workflow_template=workflow_template,
            initiated_by=request.user,
            status='IN_PROGRESS'
        )

        first_stage_template = StageTemplate.objects.filter(
            workflow=workflow_template, 
            order=1
        ).first()

        if first_stage_template:
            first_stage_exec = StageExecution.objects.create(
                workflow_execution=execution,
                stage_template=first_stage_template,
                name=first_stage_template.name,
                instructions=first_stage_template.instructions,
                status='PENDING',
                sequence_number=1
            )
            first_stage_exec.assigned_users.set(first_stage_template.assigned_users.all())
            
            execution.current_stage_execution = first_stage_exec
            execution.save()
            messages.success(request, f"Se ha iniciado el proceso '{workflow_template.name}'.")
        else:
            messages.warning(request, "La plantilla seleccionada no tiene etapas configuradas.")

    return redirect("workflows_ejecucion_detalle", execution_id=execution.id)


from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import WorkflowTemplate, DocumentTemplate, StageTemplate, FormField, DocumentFieldMapping
from .utils import extraer_etiquetas_docx

@require_POST
@login_required
def crear_plantilla_flujo(request):
    """Crea una plantilla robusta con etapas, asignación de usuarios, campos generales, múltiples documentos Word y mapeo de etiquetas."""
    nombre = request.POST.get("template_name")
    descripcion = request.POST.get("template_description", "")
    
    if not nombre:
        messages.error(request, "El nombre de la plantilla es obligatorio.")
        return redirect("workflows_ejecucion")

    with transaction.atomic():
        # 1. Crear el WorkflowTemplate base
        template = WorkflowTemplate.objects.create(
            name=nombre,
            description=descripcion,
            owner=request.user,
            is_active=True
        )

        # 2. Recuperar y registrar las etapas del flujo
        nombres_etapas = request.POST.getlist("stage_name[]")
        instrucciones_etapas = request.POST.getlist("stage_instructions[]")
        
        etapas_creadas = []
        
        if nombres_etapas:
            for index, est_nombre in enumerate(nombres_etapas):
                if not est_nombre.strip():
                    continue
                
                instruccion = instrucciones_etapas[index] if index < len(instrucciones_etapas) else ""
                order_num = index + 1
                
                stage = StageTemplate.objects.create(
                    workflow=template,
                    name=est_nombre,
                    instructions=instruccion,
                    order=order_num
                )
                
                # Asignación de actores/usuarios específicos para esta etapa
                user_ids = request.POST.getlist(f"stage_users_{order_num}[]")
                if user_ids:
                    stage.assigned_users.set(user_ids)
                else:
                    stage.assigned_users.add(request.user)
                
                etapas_creadas.append(stage)

        # 3. Capturar y guardar múltiples archivos Word adjuntos (DocumentTemplate)
        archivos_word = request.FILES.getlist("word_template_file[]") # O el nombre del input file múltiple en tu HTML
        # Si en tu HTML solo tienes un input file simple, puedes usar request.FILES.get("word_template_file")
        if not archivos_word and "word_template_file" in request.FILES:
            archivos_word = [request.FILES["word_template_file"]]

        for archivo in archivos_word:
            doc_template = DocumentTemplate.objects.create(
                workflow_template=template,
                file=archivo,
                name=archivo.name
            )
            
            # Opcional: Extraer automáticamente las etiquetas del .docx e inicializar sus mapeos
            etiquetas_detectadas = extraer_etiquetas_docx(archivo)
            for etiqueta in etiquetas_detectadas:
                # Por defecto las asignamos a la primera etapa si existe
                stage_destino = etapas_creadas[0] if etapas_creadas else None
                if stage_destino:
                    DocumentFieldMapping.objects.get_or_create(
                        document_template=doc_template,
                        stage_template=stage_destino,
                        placeholder_key=etiqueta,
                        defaults={
                            'label': f"Ingrese valor para {etiqueta}",
                            'field_type': 'TEXT',
                            'is_required': True
                        }
                    )

        # 4. Procesar campos/preguntas generales del flujo
        labels_campos = request.POST.getlist("field_label[]")
        tipos_campos = request.POST.getlist("field_type[]")
        etapas_asociadas = request.POST.getlist("field_stage_index[]")
        
        for idx, label in enumerate(labels_campos):
            if not label.strip():
                continue
            
            f_type = tipos_campos[idx] if idx < len(tipos_campos) else 'TEXT'
            st_idx = int(etapas_asociadas[idx]) if idx < len(etapas_asociadas) and etapas_asociadas[idx].isdigit() else 1
            
            target_stage = etapas_creadas[st_idx - 1] if 0 < st_idx <= len(etapas_creadas) else (etapas_creadas[0] if etapas_creadas else None)
            
            if target_stage:
                FormField.objects.create(
                    workflow_template=template,
                    stage_template=target_stage,
                    label=label,
                    field_type=f_type,
                    is_required=True,
                    order=idx+1
                )

        messages.success(request, f"¡Plantilla '{nombre}' configurada con éxito!")

    return redirect("workflows_ejecucion")