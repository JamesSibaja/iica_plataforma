from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import PerfilMicrosoft


class MicrosoftSocialAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """
        🔥 SE EJECUTA SIEMPRE en login (no solo en creación)
        """

        user = sociallogin.user
        extra_data = sociallogin.account.extra_data
        token = sociallogin.token

        print("🔥 PRE SOCIAL LOGIN EJECUTADO 🔥")

        PerfilMicrosoft.objects.update_or_create(
            usuario=user,
            defaults={
                "microsoft_id": extra_data.get("id"),
                "email": extra_data.get("mail") or extra_data.get("userPrincipalName"),
                "access_token": token.token,
                "refresh_token": getattr(token, "token_secret", "") or "",
            }
        )