@echo off
echo -------------------------------------
echo 🚀 Iniciando despliegue en Docker...
echo -------------------------------------

:: 1. Borrar contenedores anteriores (opcional)
docker compose down

:: 2. Levantar servicios en segundo plano
docker compose up --build -d

:: 3. Esperar a que la base de datos esté lista (espera 10 segundos)
echo Esperando a que la base de datos se inicie...
timeout /t 10 > nul

:: 4. Crear extensión pgvector en la base de datos
echo ✅ Creando extensión pgvector en la base de datos...
docker compose exec db psql -U postgres -d SCOUT_DB -c "CREATE EXTENSION IF NOT EXISTS vector;"

:: 5. Ejecutar migraciones
echo ✅ Ejecutando migraciones Django...
docker compose exec django python manage.py migrate



:: 6. Fin
echo -------------------------------------
echo ✅ Despliegue completo. Accede a http://localhost:8000/
echo -------------------------------------



pause
