from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# ==========================================
# 1. PLANTILLAS / DEFINICIÓN DEL FLUJO
# ==========================================

class WorkflowTemplate(models.Model):
    """Definición estática de un flujo de trabajo."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_workflows")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DocumentTemplate(models.Model):
    """Permite asociar múltiples documentos Word (.docx con etiquetas) a una plantilla de flujo."""
    workflow_template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="document_templates")
    file = models.FileField(upload_to="templates/word/")
    name = models.CharField(max_length=255, help_text="Nombre descriptivo del documento")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.workflow_template.name})"


class StageTemplate(models.Model):
    """Etapa individual dentro de un diseño de flujo."""
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=255)
    instructions = models.TextField(help_text="Instrucciones de lo que el usuario debe hacer.")
    order = models.PositiveIntegerField(help_text="Secuencia de la etapa (1, 2, 3...)")
    assigned_users = models.ManyToManyField(User, related_name="stage_templates", blank=True)
    is_dynamic_assignee = models.BooleanField(default=False, help_text="Participante indefinido; se especifica al iniciar el trámite.")
    

    # Configuración de comportamiento
    requires_signature = models.BooleanField(default=False, help_text="¿Requiere firma vía DocuSeal?")

    class Meta:
        ordering = ['order']
        unique_together = ('workflow', 'order')

    def __str__(self):
        return f"{self.workflow.name} - Etapa {self.order}: {self.name}"


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
    placeholder_key = models.CharField(max_length=100, blank=True, null=True, help_text="Etiqueta asociada en el Word (si aplica)")
    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, blank=True, null=True, related_name="associated_fields")

class DocumentFieldMapping(models.Model):
    """Mapeo de las etiquetas {{ etiqueta }} detectadas en los documentos Word hacia preguntas del formulario."""
    FIELD_TYPES = (
        ('TEXT', 'Texto Corto'),
        ('TEXTAREA', 'Texto Largo'),
        ('DATE', 'Fecha'),
        ('NUMBER', 'Número'),
    )

    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="field_mappings")
    stage_template = models.ForeignKey(
        StageTemplate, 
        on_delete=models.CASCADE, 
        related_name="doc_field_mappings",
        help_text="Etapa donde se responderá para rellenar esta etiqueta."
    )
    label = models.CharField(max_length=255, help_text="Pregunta visible para el usuario")
    placeholder_key = models.CharField(max_length=100, help_text="Etiqueta exacta detectada en el Word (ej: nombre_cliente)")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='TEXT')
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{{{{{self.placeholder_key}}}}} -> {self.label}"


# ==========================================
# 2. EJECUCIÓN / HISTORIAL DEL FLUJO
# ==========================================

class WorkflowExecution(models.Model):
    """Instancia de un flujo iniciado."""
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

    name = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre específico de la instancia de trámite")
        
    # Documentos finales resultantes (PDFs generados u otros)
    generated_pdf = models.FileField(upload_to="executions/pdfs/", null=True, blank=True)
    docuseal_envelope_id = models.CharField(max_length=255, null=True, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name or self.workflow_template.name} (#{self.id})"



class StageExecution(models.Model):
    """Historial de ejecución de una etapa particular."""
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('COMPLETED', 'Completada'),
        ('RETURNED', 'Devuelta / Retrocedida'),
        ('SKIPPED', 'Omitida'),
    )

    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="stage_history")
    stage_template = models.ForeignKey(
        StageTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Nulo si es una etapa ad-hoc/extra creada para romper el flujo."
    )
    
    name = models.CharField(max_length=255)
    instructions = models.TextField()
    assigned_users = models.ManyToManyField(User, related_name="assigned_stage_executions")
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_stages")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sequence_number = models.PositiveIntegerField(help_text="Número correlativo de ejecución (1, 2, 3...)")
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True, null=True, help_text="Observaciones al completar o retroceder la etapa.")

    class Meta:
        ordering = ['sequence_number']

    def __str__(self):
        return f"Paso {self.sequence_number}: {self.name} (Flujo #{self.workflow_execution.id})"


class FormSubmission(models.Model):
    """Instancia del formulario o respuestas globales para una ejecución de flujo."""
    workflow_execution = models.OneToOneField(WorkflowExecution, on_delete=models.CASCADE, related_name="form_submission")
    created_at = models.DateTimeField(auto_now_add=True)


class FieldValue(models.Model):
    """Respuestas e insumos ingresados tanto en campos generales como en mapeos de documentos."""
    form_submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="values")
    
    # Relaciones opcionales dependiendo de si el valor pertenece a un campo general o a una etiqueta de documento
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE, null=True, blank=True)
    document_field_mapping = models.ForeignKey(DocumentFieldMapping, on_delete=models.CASCADE, null=True, blank=True)
    
    # Valor de la respuesta
    text_value = models.TextField(blank=True, null=True)
    file_value = models.FileField(upload_to="submissions/files/", blank=True, null=True)
    
    filled_in_stage = models.ForeignKey(StageExecution, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        label = self.form_field.label if self.form_field else (self.document_field_mapping.label if self.document_field_mapping else "Desconocido")
        return f"{label} = {self.text_value or self.file_value}"


class ExecutionAttachment(models.Model):
    """Archivos generales adjuntos al flujo a lo largo de sus etapas."""
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    stage_execution = models.ForeignKey(StageExecution, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="executions/attachments/")
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adjunto: {self.file.name} (Flujo #{self.workflow_execution.id})"
    
class GeneratedDocument(models.Model):
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name="generated_documents")
    document_template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)  # Ruta absoluta o relativa al archivo generado (PDF o DOCX)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name