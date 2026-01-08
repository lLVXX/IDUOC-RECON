import os
import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reconocimiento.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_SUPERUSER')
email = os.environ.get('DJANGO_SUPEREMAIL')
password = os.environ.get('DJANGO_SUPERPASSWORD')

if not username or not email or not password:
    raise ValueError("❌ Las variables DJANGO_SUPERUSER, DJANGO_SUPEREMAIL o DJANGO_SUPERPASSWORD no están definidas!")

if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("✅ Superusuario creado")
else:
    print("✅ Superusuario ya existe")
