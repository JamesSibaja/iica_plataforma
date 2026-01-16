import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "virtual_microscope.settings")
django.setup()

from django.contrib.auth.models import User

# Obtener el correo electrónico proporcionado
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

# Obtener la contraseña del superusuario desde la variable de entorno
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

# Definir el nombre de usuario del superusuario
username = "admin"

# Verificar si ya existe un superusuario con el nombre de usuario dado
if not User.objects.filter(username=username).exists():
    # Crear un superusuario con el correo electrónico y la contraseña proporcionados
    User.objects.create_superuser(username, email, password)
    print('Superuser created successfully')
else:
    print('Superuser already exists')


