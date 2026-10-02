from django.contrib import admin
from .models import (
    WorkflowTemplate,
    DocumentTemplate,
    StageTemplate,
    StageTemplateResource,
    FormField,
    DocumentFieldMapping,
    WorkflowExecution,
    StageExecution,
    FormSubmission,
    FieldValue,
    ExecutionAttachment,
    GeneratedDocument,
)


class DocumentTemplateInline(admin.TabularInline):
    """Permite asociar documentos Word (.docx) directamente a la plantilla de flujo."""
    model = DocumentTemplate
    extra = 1
    fields = ('name', 'file', 'created_at')
    readonly_fields = ('created_at',)


class StageTemplateResourceInline(admin.TabularInline):
    """Permite adjuntar insumos o guías a una etapa específica."""
    model = StageTemplateResource
    extra = 1
    fields = ('title', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class StageTemplateInline(admin.TabularInline):
    """Permite agregar las etapas directamente al crear/editar un WorkflowTemplate."""
    model = StageTemplate
    extra = 1
    fields = ('order', 'name', 'instructions', 'requires_signature', 'isolate_previous_history', 'is_dynamic_assignee')


class FormFieldInline(admin.TabularInline):
    """Permite configurar campos generales en la etapa."""
    model = FormField
    extra = 1
    fields = ('order', 'label', 'placeholder_key', 'field_type', 'is_required', 'document_template')


class DocumentFieldMappingInline(admin.TabularInline):
    """Permite mapear las etiquetas de los documentos Word a preguntas de la etapa."""
    model = DocumentFieldMapping
    extra = 1
    fields = ('order', 'label', 'placeholder_key', 'field_type', 'is_required')


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    inlines = [DocumentTemplateInline, StageTemplateInline]


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow_template', 'created_at')
    list_filter = ('workflow_template', 'created_at')
    search_fields = ('name', 'workflow_template__name')
    inlines = [DocumentFieldMappingInline]


@admin.register(StageTemplate)
class StageTemplateAdmin(admin.ModelAdmin):
    """Administración independiente para etapas, con asignación de usuarios, insumos y campos."""
    list_display = ('workflow', 'order', 'name', 'requires_signature', 'isolate_previous_history', 'is_dynamic_assignee')
    list_filter = ('workflow', 'requires_signature', 'isolate_previous_history', 'is_dynamic_assignee')
    search_fields = ('name', 'workflow__name')
    filter_horizontal = ('assigned_users',)
    inlines = [StageTemplateResourceInline, FormFieldInline, DocumentFieldMappingInline]


@admin.register(StageTemplateResource)
class StageTemplateResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'stage_template', 'uploaded_at')
    list_filter = ('uploaded_at', 'stage_template__workflow')
    search_fields = ('title', 'stage_template__name')


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'placeholder_key', 'field_type', 'stage_template', 'order', 'is_required')
    list_filter = ('field_type', 'is_required', 'stage_template__workflow')
    search_fields = ('label', 'placeholder_key', 'stage_template__name')


@admin.register(DocumentFieldMapping)
class DocumentFieldMappingAdmin(admin.ModelAdmin):
    list_display = ('label', 'placeholder_key', 'document_template', 'stage_template', 'field_type', 'order')
    list_filter = ('field_type', 'document_template__workflow_template')
    search_fields = ('label', 'placeholder_key', 'document_template__name')


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
    readonly_fields = ('form_field', 'document_field_mapping', 'text_value', 'file_value', 'filled_in_stage', 'updated_at')
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


class GeneratedDocumentInline(admin.TabularInline):
    """Muestra los documentos generados durante la ejecución."""
    model = GeneratedDocument
    extra = 0
    readonly_fields = ('document_template', 'name', 'file_path', 'created_at')
    can_delete = False


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'workflow_template', 'initiated_by', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'workflow_template', 'started_at')
    search_fields = ('id', 'name', 'workflow_template__name', 'initiated_by__username', 'docuseal_envelope_id')
    readonly_fields = ('started_at', 'completed_at', 'docuseal_envelope_id', 'generated_pdf')
    inlines = [StageExecutionInline, FormSubmissionInline, ExecutionAttachmentInline, GeneratedDocumentInline]


@admin.register(StageExecution)
class StageExecutionAdmin(admin.ModelAdmin):
    list_display = ('workflow_execution', 'sequence_number', 'name', 'status', 'completed_by', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('name', 'workflow_execution__id', 'completed_by__username')
    filter_horizontal = ('assigned_users',)


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow_execution', 'document_template', 'created_at')
    list_filter = ('created_at', 'document_template')
    search_fields = ('name', 'workflow_execution__id')