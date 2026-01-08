@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: -------------------------------
:: Cargar variables del .env
:: -------------------------------
for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    set "%%A=%%B"
)

:: -------------------------------
:: Configuración de contenedores
:: -------------------------------
set PG_SERVICE=db
set PG_CONTAINER=postgres_pgvector

:: -------------------------------
:: Levantar solo la DB primero
:: -------------------------------
echo 🔹 Levantando solo Postgres...
docker compose up -d %PG_SERVICE%

echo 🔹 Esperando a que Postgres acepte conexiones...
:WAIT_PG
docker exec -e PGPASSWORD=%PG_PASSWORD% %PG_CONTAINER% psql -U %PG_USER% -d postgres -c "\q" 2>nul
if %errorlevel% neq 0 (
    timeout /t 2 >nul
    goto WAIT_PG
)
echo ✅ Postgres listo

:: -------------------------------
:: Crear base de datos si no existe
:: -------------------------------
echo 🔹 Verificando existencia de %PG_DB%...
docker exec -e PGPASSWORD=%PG_PASSWORD% %PG_CONTAINER% psql -U %PG_USER% -tAc "SELECT 1 FROM pg_database WHERE datname='%PG_DB%';" | findstr 1 >nul
if %errorlevel% neq 0 (
    echo 🔹 Base de datos %PG_DB% no existe, creando...
    docker exec -e PGPASSWORD=%PG_PASSWORD% %PG_CONTAINER% psql -U %PG_USER% -c "CREATE DATABASE %PG_DB%;"
) else (
    echo ✅ Base de datos %PG_DB% ya existe
)

:: -------------------------------
:: Crear extensión vector si no existe
:: -------------------------------
echo 🔹 Creando extensión vector si no existe...
docker exec -e PGPASSWORD=%PG_PASSWORD% %PG_CONTAINER% psql -U %PG_USER% -d %PG_DB% -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo ✅ Extensión vector lista

:: -------------------------------
:: Levantar el resto de servicios
:: -------------------------------
echo 🔹 Levantando Django, ArcFace, RabbitMQ y Celery...
docker compose up -d django arcface rabbitmq celery

:: -------------------------------
:: Esperar Django
:: -------------------------------
echo 🔹 Esperando a que Django acepte conexiones...
:WAIT_DJANGO
docker exec -e PGPASSWORD=%PG_PASSWORD% reconocimiento-django python manage.py check >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 >nul
    goto WAIT_DJANGO
)
echo ✅ Django listo

:: -------------------------------
:: Aplicar migraciones de Django
:: -------------------------------
echo 🔹 Aplicando migraciones Django...
docker exec -e PGPASSWORD=%PG_PASSWORD% reconocimiento-django python manage.py migrate --noinput

:: -------------------------------
:: Crear superusuario Django
:: -------------------------------
echo 🔹 Creando superusuario Django...
docker cp create_superuser.py reconocimiento-django:/app/create_superuser.py

docker exec -e PGPASSWORD=%PG_PASSWORD% ^
    -e "DJANGO_SUPERUSER=%DJANGO_SUPERUSER%" ^
    -e "DJANGO_SUPEREMAIL=%DJANGO_SUPEREMAIL%" ^
    -e "DJANGO_SUPERPASSWORD=%DJANGO_SUPERPASSWORD%" ^
    reconocimiento-django python /app/create_superuser.py

echo ✅ Superusuario listo

:: -------------------------------
:: Mostrar logs en tiempo real
:: -------------------------------
echo 🔹 Mostrando logs de todos los servicios...
docker compose logs -f

echo 🔹 Despliegue completo ✅
pause
