from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.utils import ProgrammingError


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    profile_image = models.ImageField(
        upload_to="profile_images/",
        default="default_profile_image.png",
        blank=True
    )

    microsoft_oid = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except ProgrammingError:
            pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "userprofile"):
        instance.userprofile.save()


class MicrosoftToken(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    access_token = models.TextField()

    refresh_token = models.TextField(
        null=True,
        blank=True
    )


class PerfilMicrosoft(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_microsoft"
    )

    microsoft_id = models.CharField(
        max_length=255,
        unique=True
    )

    email = models.EmailField()

    access_token = models.TextField(blank=True)

    refresh_token = models.TextField(blank=True)

    ultimo_sync = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.usuario.username
    
class Noticia(models.Model):
    TIPO_NOTICIA = 'noticia'
    
    titulo = models.CharField(max_length=500)
    link = models.URLField(unique=True, max_length=500)
    resumen = models.TextField(blank=True, null=True)
    imagen = models.URLField(max_length=1000, blank=True, null=True)
    imagen_origen = models.URLField(max_length=1000, blank=True, null=True)
    fuente = models.CharField(max_length=200, blank=True, null=True)
    fecha_publicacion = models.DateTimeField(blank=True, null=True)
    tipo = models.CharField(max_length=50, default=TIPO_NOTICIA)
    score = models.IntegerField(default=0)
    hash_noticia = models.CharField(max_length=64, blank=True, null=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo