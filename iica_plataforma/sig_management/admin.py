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
    DocuSealSettings,
)

@admin.register(DocuSealSettings)
class DocuSealSettingsAdmin(admin.ModelAdmin):
    list_display = ('api_url', 'is_active', 'updated_at')
    
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


class DocumentTemplateInline(admin.TabularInline):
    model = DocumentTemplate
    extra = 1
    fields = ('name', 'file', 'requires_signature', 'created_at')
    readonly_fields = ('created_at',)


class StageTemplateResourceInline(admin.TabularInline):
    model = StageTemplateResource
    extra = 1
    fields = ('title', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class StageTemplateInline(admin.TabularInline):
    model = StageTemplate
    extra = 1
    fields = ('order', 'name', 'instructions', 'isolate_previous_history', 'is_dynamic_assignee')


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1
    fields = ('order', 'label', 'placeholder_key', 'field_type', 'is_required', 'document_template')


class DocumentFieldMappingInline(admin.TabularInline):
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
    list_display = ('name', 'workflow_template', 'requires_signature', 'created_at')
    list_filter = ('workflow_template', 'requires_signature', 'created_at')
    search_fields = ('name', 'workflow_template__name')
    inlines = [DocumentFieldMappingInline]


@admin.register(StageTemplate)
class StageTemplateAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'order', 'name', 'isolate_previous_history', 'is_dynamic_assignee')
    list_filter = ('workflow', 'isolate_previous_history', 'is_dynamic_assignee')
    search_fields = ('name', 'workflow__name')
    filter_horizontal = ('assigned_users',)
    inlines = [StageTemplateResourceInline, FormFieldInline, DocumentFieldMappingInline]


@admin.register(StageTemplateResource)
class StageTemplateResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'stage_template', 'uploaded_at')


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'placeholder_key', 'field_type', 'stage_template', 'order', 'is_required')


@admin.register(DocumentFieldMapping)
class DocumentFieldMappingAdmin(admin.ModelAdmin):
    list_display = ('label', 'placeholder_key', 'document_template', 'stage_template', 'field_type', 'order')


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'workflow_template', 'initiated_by', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'workflow_template', 'started_at')
    search_fields = ('id', 'name', 'workflow_template__name')
    readonly_fields = ('started_at', 'completed_at', 'docuseal_envelope_id', 'docuseal_embed_slug', 'generated_pdf')


@admin.register(StageExecution)
class StageExecutionAdmin(admin.ModelAdmin):
    list_display = ('workflow_execution', 'sequence_number', 'name', 'status')


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow_execution', 'document_template', 'created_at')