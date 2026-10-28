from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# ==========================================
# 0. CONFIGURACIÓN GLOBAL DE DOCUSEAL
# ==========================================

class DocuSealSettings(models.Model):
    """Configuración global para DocuSeal administrable desde Django Admin."""
    api_key = models.CharField(max_length=255, blank=True, null=True, help_text="API Key de DocuSeal (Opcional para modo libre)")
    api_url = models.CharField(max_length=255, default="https://api.docuseal.com", help_text="URL base de la API de DocuSeal")
    is_active = models.BooleanField(default=True, help_text="Habilitar integración con DocuSeal")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de DocuSeal"
        verbose_name_plural = "Configuración de DocuSeal"

    def __str__(self):
        return f"DocuSeal Config (Activo: {self.is_active})"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ==========================================
# 1. PLANTILLAS / DEFINICIÓN DEL FLUJO
# ==========================================

class WorkflowTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_workflows")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DocumentTemplate(models.Model):
    """Permite asociar múltiples documentos Word a una plantilla, indicando si requieren firma."""
    workflow_template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="document_templates")
    file = models.FileField(upload_to="templates/word/")
    name = models.CharField(max_length=255, help_text="Nombre descriptivo del documento")
    
    # CORRECCIÓN: El documento es el que requiere firma digital
    requires_signature = models.BooleanField(default=False, help_text="¿Este documento requiere firma digital vía DocuSeal?")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sig_label = " [Requiere Firma]" if self.requires_signature else ""
        return f"{self.name}{sig_label} ({self.workflow_template.name})"


class StageTemplate(models.Model):
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=255)
    instructions = models.TextField(help_text="Instrucciones de lo que el usuario debe hacer.")
    order = models.PositiveIntegerField(help_text="Secuencia de la etapa (1, 2, 3...)")
    assigned_users = models.ManyToManyField(User, related_name="stage_templates", blank=True)
    is_dynamic_assignee = models.BooleanField(default=False, help_text="Participante indefinido.")
    
    isolate_previous_history = models.BooleanField(
        default=False, 
        help_text="Si se marca, los usuarios de esta etapa no verán respuestas anteriores."
    )

    class Meta:
        ordering = ['order']
        unique_together = ('workflow', 'order')

    def __str__(self):
        return f"{self.workflow.name} - Etapa {self.order}: {self.name}"


class StageTemplateResource(models.Model):
    stage_template = models.ForeignKey(StageTemplate, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="templates/stage_resources/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class FormField(models.Model):
    FIELD_TYPES = (
        ('TEXT', 'Texto Corto'),
        ('TEXTAREA', 'Texto Largo'),
        ('FILE', 'Archivo Adjunto'),
        ('DATE', 'Fecha'),
        ('NUMBER', 'Número'),
    )

    workflow_template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="general_fields")
    stage_template = models.ForeignKey(StageTemplate, on_delete=models.CASCADE, related_name="general_fields")
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='TEXT')
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)
    placeholder_key = models.CharField(max_length=100, blank=True, null=True)
    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, blank=True, null=True, related_name="associated_fields")


class DocumentFieldMapping(models.Model):
    FIELD_TYPES = (
        ('TEXT', 'Texto Corto'),
        ('TEXTAREA', 'Texto Largo'),
        ('DATE', 'Fecha'),
        ('NUMBER', 'Número'),
        ('SIGNATURE', 'Firma Digital'),
    )

    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="field_mappings")
    stage_template = models.ForeignKey(StageTemplate, on_delete=models.CASCADE, related_name="doc_field_mappings")
    label = models.CharField(max_length=255)
    placeholder_key = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='TEXT')
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']


# ==========================================
# 2. EJECUCIÓN / HISTORIAL
# ==========================================

class WorkflowExecution(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'En Proceso'),
        ('COMPLETED', 'Completado'),
        ('REJECTED', 'Rechazado/Cancelado'),
    )

    workflow_template = models.ForeignKey(WorkflowTemplate, on_delete=models.PROTECT)
    initiated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="initiated_executions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    
    current_stage_execution = models.OneToOneField(
        'StageExecution', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="+"
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    generated_pdf = models.FileField(upload_to="executions/pdfs/", null=True, blank=True)
    docuseal_envelope_id = models.CharField(max_length=255, null=True, blank=True)
    docuseal_embed_slug = models.CharField(max_length=255, null=True, blank=True)
    signature_completed = models.BooleanField(default=False)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name or self.workflow_template.name} (#{self.id})"


class StageExecution(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('COMPLETED', 'Completada'),
        ('RETURNED', 'Devuelta / Retrocedida'),
        ('SKIPPED', 'Omitida'),
    )

    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="stage_history")
    stage_template = models.ForeignKey(StageTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    instructions = models.TextField()
    assigned_users = models.ManyToManyField(User, related_name="assigned_stage_executions")
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_stages")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sequence_number = models.PositiveIntegerField()
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['sequence_number']


class FormSubmission(models.Model):
    workflow_execution = models.OneToOneField(WorkflowExecution, on_delete=models.CASCADE, related_name="form_submission")
    created_at = models.DateTimeField(auto_now_add=True)


class FieldValue(models.Model):
    form_submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="values")
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE, null=True, blank=True)
    document_field_mapping = models.ForeignKey(DocumentFieldMapping, on_delete=models.CASCADE, null=True, blank=True)
    text_value = models.TextField(blank=True, null=True)
    file_value = models.FileField(upload_to="submissions/files/", blank=True, null=True)
    filled_in_stage = models.ForeignKey(StageExecution, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class ExecutionAttachment(models.Model):
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    stage_execution = models.ForeignKey(StageExecution, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="executions/attachments/")
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class GeneratedDocument(models.Model):
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="generated_documents")
    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name