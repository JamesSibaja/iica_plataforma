from django.db import models
from django.contrib.auth.models import User
from secap.models import Proyecto


# -------------------------------------------------------
# OBJETIVO OKR
# -------------------------------------------------------
class OKRObjetivo(models.Model):

    titulo = models.CharField(max_length=250)
    descripcion = models.TextField(blank=True)

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="objetivos_okr"
    )

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    def __str__(self):
        return self.titulo


# -------------------------------------------------------
# RESULTADOS CLAVE
# -------------------------------------------------------
class OKRResultadoClave(models.Model):

    objetivo = models.ForeignKey(
        OKRObjetivo,
        on_delete=models.CASCADE,
        related_name="resultados"
    )

    descripcion = models.CharField(max_length=300)

    valor_inicial = models.FloatField(default=0)
    valor_objetivo = models.FloatField()
    valor_actual = models.FloatField(default=0)

    def progreso(self):
        if self.valor_objetivo == 0:
            return 0
        return (self.valor_actual / self.valor_objetivo) * 100

    def estado_color(self):

        p = self.progreso()

        if p >= 80:
            return 0
        elif p >= 60:
            return 1
        elif p >= 40:
            return 2
        elif p >= 20:
            return 3
        else:
            return 4

    def __str__(self):
        return self.descripcion


# -------------------------------------------------------
# ACTUALIZACIONES DE RESULTADO CLAVE
# -------------------------------------------------------
class OKRActualizacion(models.Model):

    resultado = models.ForeignKey(
        OKRResultadoClave,
        on_delete=models.CASCADE,
        related_name="actualizaciones"
    )

    fecha = models.DateField()
    valor = models.FloatField()

    comentario = models.TextField(blank=True)

    def estado(self):

        if self.resultado.valor_objetivo == 0:
            return 4

        progreso = (self.valor / self.resultado.valor_objetivo) * 100

        if progreso >= 80:
            return 0
        elif progreso >= 60:
            return 1
        elif progreso >= 40:
            return 2
        elif progreso >= 20:
            return 3
        else:
            return 4


# -------------------------------------------------------
# INICIATIVAS
# -------------------------------------------------------
class OKRIniciativa(models.Model):

    nombre = models.CharField(max_length=200)

    descripcion = models.TextField(blank=True)

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="iniciativas_responsable"
    )

    prioridad = models.CharField(
        max_length=20,
        choices=[
            ("Alta", "Alta"),
            ("Media", "Media"),
            ("Baja", "Baja")
        ]
    )

    fecha_fin = models.DateField(null=True, blank=True)

    # relación con objetivos
    objetivo = models.ForeignKey(
        OKRObjetivo,
        on_delete=models.CASCADE,
        related_name="iniciativas"
    )

    # relación muchos a muchos con KR
    resultados = models.ManyToManyField(
        OKRResultadoClave,
        related_name="iniciativas"
    )

    def __str__(self):
        return self.nombre

    # -------------------------
    # MÉTRICAS DE TAREAS
    # -------------------------

    def tareas_totales(self):
        return self.tareas.count()

    def tareas_completadas(self):
        return self.tareas.filter(estado="terminada").count()

    def tareas_ejecucion(self):
        return self.tareas.filter(estado="ejecucion").count()

    def tareas_pendientes(self):
        return self.tareas.filter(estado="pendiente").count()

    def tareas_espera(self):
        return self.tareas.filter(estado="espera").count()


# -------------------------------------------------------
# TAREAS (KANBAN)
# -------------------------------------------------------
class Tarea(models.Model):

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("ejecucion", "En ejecución"),
        ("espera", "En espera"),
        ("terminada", "Terminada"),
    ]

    titulo = models.CharField(max_length=250)

    descripcion = models.TextField(blank=True)

    iniciativa = models.ForeignKey(
        OKRIniciativa,
        on_delete=models.CASCADE,
        related_name="tareas"
    )

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas"
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente"
    )

    fecha_creacion = models.DateField(auto_now_add=True)

    fecha_limite = models.DateField(null=True, blank=True)

    # relación opcional con proyecto de SECAP
    proyecto = models.ForeignKey(
    Proyecto,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="tareas_kanban"
)

    def __str__(self):
        return self.titulo