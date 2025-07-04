@echo off
echo -------------------------------------
echo 👤 Ejecutando script para crear superusuario...
echo -------------------------------------

:: Ejecutar el script dentro del contenedor Django
docker compose exec django python core/scripts/crear_superusuario.py

echo -------------------------------------
echo ✅ Proceso finalizado.
echo -------------------------------------
pause
