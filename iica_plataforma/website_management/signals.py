# signals.py
from allauth.account.signals import user_signed_up
from django.dispatch import receiver

@receiver(user_signed_up)
def microsoft_signup_handler(request, user, **kwargs):
    user.is_active = True
    user.save()