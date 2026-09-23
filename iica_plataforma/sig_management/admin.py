from django.contrib import admin
from .models import (
    WorkflowTemplate,
    StageTemplate,
    FormField,
    WorkflowExecution,
    StageExecution,
    FormSubmission,
    FieldValue,
    ExecutionAttachment,
)


class StageTemplateInline(admin.TabularInline):
    """Permite agregar las etapas directamente al crear/editar un WorkflowTemplate."""
    model = StageTemplate
    extra = 1
    fields = ('order', 'name', 'instructions', 'requires_signature', 'assigned_users')


class FormFieldInline(admin.TabularInline):
    """Permite configurar las preguntas/campos directamente."""
    model = FormField
    extra = 1
    fields = ('order', 'label', 'placeholder_key', 'field_type', 'stage_template', 'is_required')


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    inlines = [StageTemplateInline]


@admin.register(StageTemplate)
class StageTemplateAdmin(admin.ModelAdmin):
    """Administración independiente para etapas, donde el filter_horizontal sí funciona perfecto."""
    list_display = ('workflow', 'order', 'name', 'requires_signature')
    list_filter = ('workflow', 'requires_signature')
    search_fields = ('name', 'workflow__name')
    filter_horizontal = ('assigned_users',)


class StageExecutionInline(admin.TabularInline):
    """Muestra el historial de etapas recorridas dentro de una ejecución de flujo."""
    model = StageExecution
    extra = 0
    readonly_fields = ('stage_template', 'name', 'instructions', 'status', 'sequence_number', 'completed_by', 'started_at', 'completed_at', 'comments')
    can_delete = False


class FieldValueInline(admin.TabularInline):
    """Muestra los valores y respuestas ingresadas en el campo dentro del envío."""
    model = FieldValue
    extra = 0
    readonly_fields = ('form_field', 'text_value', 'file_value', 'filled_in_stage', 'updated_at')
    can_delete = False


class FormSubmissionInline(admin.StackedInline):
    """Muestra la información general del formulario enviado en la ejecución."""
    model = FormSubmission
    can_delete = False
    readonly_fields = ('created_at',)
    show_change_link = True
    extra = 0


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    """Permite ver el detalle completo de las respuestas del formulario de forma independiente."""
    list_display = ('id', 'workflow_execution', 'created_at')
    inlines = [FieldValueInline]
    readonly_fields = ('workflow_execution', 'created_at')


class ExecutionAttachmentInline(admin.TabularInline):
    """Muestra los archivos adjuntos generales del flujo."""
    model = ExecutionAttachment
    extra = 0
    readonly_fields = ('uploaded_by', 'stage_template_rel', 'file', 'description', 'uploaded_at')

    def stage_template_rel(self, obj):
        if obj.stage_execution:
            return obj.stage_execution.name
        return "-"
    stage_template_rel.short_description = "Etapa"


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow_template', 'initiated_by', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'workflow_template', 'started_at')
    search_fields = ('id', 'workflow_template__name', 'initiated_by__username', 'docuseal_envelope_id')
    readonly_fields = ('started_at', 'completed_at', 'docuseal_envelope_id', 'generated_pdf')
    inlines = [StageExecutionInline, FormSubmissionInline, ExecutionAttachmentInline]


@admin.register(StageExecution)
class StageExecutionAdmin(admin.ModelAdmin):
    list_display = ('workflow_execution', 'sequence_number', 'name', 'status', 'completed_by', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('name', 'workflow_execution__id', 'completed_by__username')
    filter_horizontal = ('assigned_users',)