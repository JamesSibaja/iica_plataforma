from django.db import models
from django.contrib.auth.models import User

# -------------------------------------------------------
# PROYECTO BASE
# -------------------------------------------------------
class Proyecto(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)

    # EXISTENTE
    fecha_creacion = models.DateField(auto_now_add=True)
    encargado = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proyectos_encargado")
    monto = models.IntegerField(default=0)

    # ===== NUEVO (FICHA TÉCNICA) =====
    contraparte = models.CharField(max_length=255, blank=True)
    pais = models.CharField(max_length=100, blank=True)

    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    objetivo_general = models.TextField(blank=True)
    objetivos_especificos = models.TextField(blank=True)

    estado = models.CharField(
        max_length=50,
        choices=[
            ("formulacion", "Formulación"),
            ("ejecucion", "Ejecución"),
            ("cerrado", "Cerrado"),
        ],
        default="formulacion"
    )

    presupuesto_aprobado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # FUTURO
    # carpeta_sharepoint = models.URLField(blank=True)

    def __str__(self):
        return self.nombre

# -------------------------------------------------------
# COMITÉ ASOCIADO AL PROYECTO (TABLA INTERMEDIA)
# -------------------------------------------------------
class MiembroComite(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    comentario = models.TextField(blank=True)
    aprobado = models.BooleanField(default=False)
    alerta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} → {self.proyecto.nombre}"


# -------------------------------------------------------
# PROYECTO NUEVO
# -------------------------------------------------------
class ProyectoNuevo(models.Model):
    proyecto = models.OneToOneField(Proyecto, on_delete=models.CASCADE, related_name="nuevo")

    def __str__(self):
        return f"Nuevo: {self.proyecto.nombre}"


# -------------------------------------------------------
# CRITERIOS DE EVALUACIÓN
# -------------------------------------------------------
class Criterio(models.Model):
    premisa = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.premisa

# -------------------------------------------------------
# GRUPO CRITERIOS(Criterios)
# -------------------------------------------------------
class GrupoCriterios(models.Model):
    nombre = models.CharField(max_length=255)

    criterios = models.ManyToManyField(
        Criterio,
        through="GrupoCriterio",
        related_name="grupos"
    )

# -------------------------------------------------------
# TABLA INTERMEDIA GRUPO ↔ CRITERIO
# -------------------------------------------------------
class GrupoCriterio(models.Model):
    grupo = models.ForeignKey(GrupoCriterios, on_delete=models.CASCADE)
    criterio = models.ForeignKey(Criterio, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("grupo", "criterio")

    def __str__(self):
        return f"{self.grupo.nombre} – {self.criterio.premisa}"


# -------------------------------------------------------
# FORMULARIO (ProyectoNuevo ↔ Criterio)
# -------------------------------------------------------
class Formulario(models.Model):
    criterio = models.ForeignKey(Criterio, on_delete=models.CASCADE)
    proyecto_nuevo = models.ForeignKey(ProyectoNuevo, on_delete=models.CASCADE)

    calificacion = models.IntegerField(default=0)   # 1–5
    justificacion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.proyecto_nuevo} – {self.criterio}"


# -------------------------------------------------------
# PROYECTO EN EJECUCIÓN
# -------------------------------------------------------
class ProyectoEjecucion(models.Model):
    proyecto = models.OneToOneField(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="ejecucion"
    )

    def __str__(self):
        return f"Ejecución: {self.proyecto.nombre}"


# -------------------------------------------------------
# INDICADORES
# -------------------------------------------------------
from django.core.exceptions import ValidationError
from django.db import models

class Indicador(models.Model):
    proyecto = models.ForeignKey(
        ProyectoEjecucion,
        on_delete=models.CASCADE,
        related_name="indicadores"
    )

    premisa = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)

    valor_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100,
        help_text="Valor máximo permitido para el indicador"
    )

    valor_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Valor actual del indicador"
    )

    def clean(self):
        """
        Validación de dominio:
        el valor actual no puede superar el valor máximo.
        """
        if self.valor_actual > self.valor_maximo:
            raise ValidationError({
                "valor_actual": (
                    "El valor actual no puede ser mayor "
                    "al valor máximo definido."
                )
            })

    def save(self, *args, **kwargs):
        # Garantiza que la validación se ejecute siempre
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.premisa} ({self.valor_actual}/{self.valor_maximo})"
    
    @property
    def porcentaje_actual(self):
        if not self.valor_maximo:
            return 0
        return (self.valor_actual * 100) / self.valor_maximo




# -------------------------------------------------------
# META INDICADOR
# -------------------------------------------------------
class MetaIndicador(models.Model):
    indicador = models.ForeignKey(
        Indicador,
        on_delete=models.CASCADE,
        related_name="metas"
    )

    fecha = models.DateField()
    valor_objetivo = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    comentario = models.TextField(blank=True)

    class Meta:
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.indicador} → {self.valor_objetivo}% ({self.fecha})"


