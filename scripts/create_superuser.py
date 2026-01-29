import os
import sys
import django


sys.path.append('/app/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iica_plataforma.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if not email or not password:
    print("Email o password no definidos")
    exit(1)

if User.objects.filter(email=email).exists():
    print(f"ℹSuperusuario ya existe: {email}")
else:
    User.objects.create_superuser(
        username="admin",
        email=email,
        password=password
    )
    print(f"Superusuario creado: {email}")