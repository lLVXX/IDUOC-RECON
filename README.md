Reconocimiento Facial Académico

Reconocimiento Facial Académico es una plataforma basada en Django y FastAPI que ofrece un flujo completo de asistencia en tiempo real para entornos educativos. Integra procesamiento de video por WebSocket, generación y comparación de embeddings con ArcFace (ONNX), y un sistema de almacenamiento vectorial en PostgreSQL + pgvector, todo orquestado mediante Docker y Celery.

Introducción

Este repositorio agrupa dos servicios contenedorizados:

Aplicación Django que maneja autenticación multifacética, roles (admin_global, admin_zona, profesor, estudiante) y vistas de gestión.

Microservicio FastAPI que expone endpoints para generar embeddings faciales, comparar vectores y servir streaming WebSocket.

Ambos interactúan con una base de datos PostgreSQL que utiliza pgvector para almacenar vectores de alta dimensión. Las tareas intensivas (generación de embeddings, política FIFO de imágenes dinámicas) se procesan asíncronamente mediante Celery y RabbitMQ.

Tecnologías

La plataforma emplea las siguientes tecnologías clave:

Python 3.10 como lenguaje principal.

Django 5.2.3 para la capa MVC y la interfaz administrativa.

FastAPI 0.95 para endpoints REST y WebSocket de reconocimiento.

InsightFace (ONNX buffalo_l) para extracción de embeddings faciales.

ONNX Runtime para ejecución del modelo.

PostgreSQL ≥14 + pgvector para almacenamiento y consulta de vectores.

Celery 5.5.3 y RabbitMQ 3.9 para procesar tareas en background (generación y recarga de embeddings, limpieza FIFO).

Docker CE 24.x y Docker Compose 3.9 para contenerizar y orquestar servicios.

Quick Start con Docker

Sigue estos pasos para desplegar la plataforma localmente en menos de 5 minutos:

Clona el repositorio y sitúate en la carpeta:

git clone https://github.com/lLVXX/IDUOC-RECON.git
cd IDUOC-RECON

Copia el archivo de variables de entorno y personalízalo:

cp .env.example .env
# Edita .env según tu configuración de base de datos y servicios

Construye y levanta todos los contenedores:

docker compose build --pull --no-cache
docker compose up -d

*Nota: Durante la construcción se instala automáticamente requirements.txt.

Ejecuta migraciones y crea el superusuario:

docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser

Abre tu navegador y verifica que todo funcione:

Aplicación web: http://localhost:8000

Documentación FastAPI: http://localhost:8001/docs

Panel RabbitMQ: http://localhost:15672 (guest/guest)

Contribución

Las contribuciones son bienvenidas. Para proponer cambios, crea un fork, abre una rama con tu feature o fix, y envía un pull request contra main.

Licencia

Este proyecto está licenciado bajo MIT. Para más detalles, consulta el archivo LICENSE.

