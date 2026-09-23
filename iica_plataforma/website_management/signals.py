from allauth.socialaccount.signals import social_account_updated
from django.dispatch import receiver
from .models import PerfilMicrosoft

@receiver(social_account_updated)
def guardar_microsoft(sender, request, sociallogin, **kwargs):

    user = sociallogin.user
    extra_data = sociallogin.account.extra_data

    PerfilMicrosoft.objects.update_or_create(
        usuario=user,
        defaults={
            "microsoft_id": extra_data.get("id"),
            "email": extra_data.get("mail") or extra_data.get("userPrincipalName"),
            "access_token": sociallogin.token.token,
            "refresh_token": sociallogin.token.token_secret or "",
        }
    )