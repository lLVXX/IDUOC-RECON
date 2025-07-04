import base64
import json
import requests
import os
import io
from django.utils.timezone import now
import numpy as np
from pgvector.django import vector
from personas.models import EstudianteFoto, EstudianteEmbedding
from PIL import Image
from celery import shared_task
from datetime import datetime
from django.conf import settings
from .models import CustomUser, EstudianteFoto
import logging
from django.core.files.base import ContentFile
from io import BytesIO
import psycopg2
from django.utils import timezone

logger = logging.getLogger(__name__)
MICRO_URL = os.getenv("ARC_FACE_URL", "http://arcface:8001")

PG_CONFIG = {
    'dbname':   os.getenv('PG_DB',       'SCOUT_DB'),
    'user':     os.getenv('PG_USER',     'postgres'),
    'password': os.getenv('PG_PASSWORD', '12345678'),
    'host':     os.getenv('PG_HOST',     'db'),
    'port':     int(os.getenv('PG_PORT', '5432')),
}

# 📌 Tarea 1: Procesar Captura Dinámica
@shared_task
def procesar_captura(estudiante_id, foto_id):
    try:
        foto = EstudianteFoto.objects.get(id=foto_id)
        imagen_path = foto.imagen.path  # Ruta completa: media/estudiantes/fotos_extra/...

        if not os.path.exists(imagen_path):
            print(f"❌ Imagen no encontrada: {imagen_path}")
            return

        print(f"🖼️ Procesando imagen: {imagen_path}")

        # Leer imagen como bytes
        with open(imagen_path, "rb") as f:
            imagen_bytes = f.read()

        # ✅ Enviar correctamente con campo 'file'
        response = requests.post(
            f"{settings.ARC_FACE_URL.rstrip('/')}/generar_embedding/",
            files={"file": ("foto.jpg", imagen_bytes, "image/jpeg")}
        )

        if response.status_code != 200:
            print(f"❌ Error al obtener embedding: {response.text}")
            return

        data = response.json()
        embedding = data.get("embedding")

        if not embedding:
            print("⚠️ No se recibió embedding.")
            return

        # Guardar embedding como Vector
        EstudianteEmbedding.objects.create(
            estudiante_id=estudiante_id,
            embedding=embedding,
            origen="dinamica",
            imagen=foto.imagen.name,
            timestamp=now(),
        )
        print(f"✅ Embedding dinámico insertado para estudiante {estudiante_id}")

        # Política FIFO
        dinamicos = EstudianteEmbedding.objects.filter(
            estudiante_id=estudiante_id,
            origen="dinamica"
        ).order_by("timestamp")

        if dinamicos.count() > 3:
            eliminar = dinamicos.first()
            print(f"♻️ Eliminando embedding antiguo ID={eliminar.id}")
            eliminar.delete()

    except Exception as e:
        print(f"❌ Error al procesar estudiante {estudiante_id}: {e}")

# 📌 Tarea 2: Recargar Embeddings del Microservicio
@shared_task(name='recargar_embeddings_microservicio')
def recargar_embeddings_microservicio():
    print("🔄 Enviando solicitud de recarga de embeddings al microservicio ArcFace...")
    try:
        r = requests.get(f"{MICRO_URL}/reload_embeddings/")
        if r.status_code == 200:
            print("✅ Embeddings recargados exitosamente en el microservicio.")
        else:
            print(f"❌ Error al recargar embeddings: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Excepción al recargar embeddings: {e}")

# 📌 Tarea 3: Procesar Nuevo Estudiante
@shared_task(name='procesar_nuevo_estudiante')
def procesar_nuevo_estudiante(estudiante_id, foto_url):
    print(f"🚀 [TASK] Iniciando procesamiento para estudiante ID={estudiante_id}")
    try:
        # Descargar imagen
        response = requests.get(foto_url)
        response.raise_for_status()
        img_bytes = BytesIO(response.content)
        print(f"📥 Imagen descargada desde: {foto_url} ({len(response.content)} bytes)")

        # Enviar al microservicio
        files = {"file": ("estudiante.jpg", img_bytes.getvalue(), "image/jpeg")}
        r = requests.post(f"{MICRO_URL}/generar_embedding/", files=files)
        if r.status_code != 200:
            print(f"❌ Error al generar embedding: {r.text}")
            return

        embedding = r.json().get("embedding")
        if not embedding:
            print("❌ No se recibió embedding.")
            return

        print(f"✅ Embedding recibido con longitud: {len(embedding)}")

        # Guardar en DB
        EstudianteFoto.objects.create(
            estudiante_id=estudiante_id,
            imagen=ContentFile(response.content, name="foto_base.jpg"),
            embedding=embedding,
            es_base=True
        )
        print(f"💾 Embedding guardado para estudiante {estudiante_id}")

        # Recargar en microservicio
        recargar_embeddings_microservicio.delay()

    except Exception as e:
        print(f"❌ Error inesperado en tarea procesar_nuevo_estudiante: {e}")

# 📌 Tarea 4: Guardar Imagen Dinámica Post Clase
@shared_task
def guardar_imagen_dinamica_post_clase(estudiante_id, embedding, nombre_archivo):
    print(f"[TASK] Guardando imagen post-clase para estudiante {estudiante_id}...")

    ruta_relativa = f"estudiantes/fotos_extra/{nombre_archivo}"
    ruta_absoluta = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

    if not os.path.exists(ruta_absoluta):
        print(f"❌ Archivo no encontrado: {ruta_absoluta}")
        return

    try:
        estudiante = CustomUser.objects.get(id=estudiante_id)
        foto = EstudianteFoto.objects.create(
            estudiante=estudiante,
            imagen=ruta_relativa,
            embedding=vector(embedding),
            es_base=False,
            created_at=timezone.now()
        )
        print(f"✅ Foto dinámica guardada para estudiante {estudiante_id} – ID Foto: {foto.id}")
    except Exception as e:
        print(f"❌ Error al guardar imagen dinámica post-clase: {e}")
