Proyecto de Reconocimiento Facial Académico

Este repositorio contiene una solución completa de asistencia académica basada en reconocimiento facial.

📖 Descripción

Un sistema que permite a los profesores iniciar clases manualmente, capturar rostros en tiempo real, compararlos contra una base de datos de embeddings, y registrar la asistencia. Incorpora una política FIFO para el almacenamiento de imágenes dinámicas (máximo 3 por estudiante).

🏗 Arquitectura

Django: Gestión central de usuarios (admin_global, admin_zona, profesor, estudiante), clases y CRUD unificado.

FastAPI (ArcFace Service): Generación y comparación de embeddings usando ONNX.

PostgreSQL + pgvector: Almacena vectores de embeddings y permite consultas de similitud.

Celery + RabbitMQ: Orquestación asíncrona de tareas (generación/recarga de embeddings, guardado de imágenes).

Docker & Docker Compose: Contenerización de todos los servicios.

Diagrama ASCII

+----------------+      +-------------+      +----------+
|    Browser     | <--> | Django App  | <--> | PostgreSQL (pgvector)
+----------------+      +-------------+      +----------+
        |                    |                   /
        | WebSocket          | Celery            /
        v                    v                 /
   +------------+      +-----------+         /   
   |  FastAPI   | <--> | RabbitMQ  |<--------    
   |  arcface   |      |  Broker   |               
   +------------+      +-----------+               

🛠 Instalación detallada

Clonar el repositorio

git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo

Variables de entorno

cp .env.example .env

Edita .env con tus credenciales:

PG_DB=SCOUT_DB
PG_USER=postgres
PG_PASSWORD=12345678
PG_HOST=db
PG_PORT=5432

ARC_FACE_URL=http://arcface:8001
ARC_FACE_WS=ws://arcface:8001/stream/

DJANGO_SECRET_KEY=tu_clave_secreta
DEBUG=True

Levantamiento con Docker

docker compose up -d --build

Migraciones y superusuario

docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser

Verificación

Django: http://localhost:8000

FastAPI: http://localhost:8001/docs

RabbitMQ UI: http://localhost:15672 (guest/guest)

📚 SDKs y Dependencias

Python 3.10

Django 5.2.3

FastAPI 0.95

InsightFace ONNX (buffalo_l)

pgvector

Celery 5.5.3

RabbitMQ 3.9

Docker 24.x

Docker Compose 3.9

🔧 FIFO de Imágenes Dinámicas

Al hacer match:

Se guarda la imagen en PostgreSQL.

Si hay más de 3, se elimina la más antigua.

Permite análisis completo post-clase.

📄 Contribuciones

Para contribuir:

Fork del repositorio

Crear una rama feature/x

Commit y PR sobre main

📝 Licencia

MIT © Tu Nombre
