from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import login

class MicrosoftSocialAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        token = sociallogin.token.token

        request.session["microsoft_access_token"] = token

        if sociallogin.token.token_secret:
            request.session["microsoft_refresh_token"] = sociallogin.token.token_secret