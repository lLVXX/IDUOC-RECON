# 🎓 Reconocimiento Facial Académico

**Reconocimiento Facial Académico** es una plataforma educativa basada en **Django + FastAPI** que implementa un flujo completo de **asistencia facial en tiempo real**, utilizando visión computacional, embeddings faciales y procesamiento asíncrono en una arquitectura moderna y desacoplada.

---

## 📌 Arquitectura General

La plataforma se compone de dos servicios principales, totalmente contenedorizados:

### 🧠 Django (Backend principal)
- Autenticación y control de roles:
  - `admin_global`
  - `admin_zona`
  - `profesor`
  - `estudiante`
- Gestión académica completa.
- Interfaz web para asistencia facial en tiempo real.
- Orquestación de tareas con **Celery**.

### ⚡ FastAPI (Microservicio ArcFace)
- Generación de embeddings faciales con **InsightFace (ONNX)**.
- Comparación vectorial usando **pgvector**.
- Streaming de video en tiempo real vía **WebSocket**.
- Recarga dinámica de embeddings.

---

## 🧰 Tecnologías

- Python 3.10  
- Django 5.2.3  
- FastAPI 0.95  
- InsightFace (ONNX – buffalo_l)  
- PostgreSQL ≥ 14 + pgvector  
- Celery 5.5.3  
- RabbitMQ 3.9  
- Docker CE 24.x  
- Docker Compose 3.9  

---

## 🚀 Despliegue Local (Docker)

##  Hacer .env igual o similar a (raiz proyecto)

```bash

# =========================
# DJANGO
# =========================

DJANGO_SECRET_KEY= GENERAR PROPIA 


DJANGO_ALLOWED_HOSTS=*


DJANGO_SUPERUSER=admin
DJANGO_SUPEREMAIL=admin@Valkyria.clS
DJANGO_SUPERPASSWORD=cambiameporfavor


DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0


# =========================
# POSTGRES / PGVECTOR
# =========================
PG_DB=DB_SCOUT
PG_USER=postgres
PG_PASSWORD=12345678
PG_HOST=db
PG_PORT=5432


# =========================
# ARCFACE
# =========================
# Backend Django → servicio Docker
ARC_FACE_URL=http://arcface:8001
ARC_FACE_WS=ws://arcface:8001/stream/


# =========================
# CELERY / RABBITMQ
# =========================
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=django-dbyyz


```


### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/lLVXX/IDUOC-RECON.git
cd IDUOC-RECON

- generar .env

- deploy.bat

```

