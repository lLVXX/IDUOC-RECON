# personas/views.py

from django.contrib.auth.decorators import login_required
from core.decorators import admin_zona_required
from django.shortcuts import render
from core.models import CustomUser
from personas.models import EstudianteAsignaturaSeccion
from .tasks import procesar_captura




import json
import base64
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
import requests
from django.conf import settings
from .models import EstudianteFoto









@login_required
@admin_zona_required
def listar_estudiantes_con_secciones(request):
    estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=request.user.sede)

    # Preparamos la estructura: {estudiante: [(asignatura, seccion), ...]}
    data = []
    for estudiante in estudiantes:
        relaciones = EstudianteAsignaturaSeccion.objects.filter(estudiante=estudiante).select_related('asignatura', 'seccion')
        asignaturas_y_secciones = [
            (rel.asignatura.nombre, rel.seccion.nombre) for rel in relaciones
        ]
        data.append({
            'estudiante': estudiante,
            'asignaturas_secciones': asignaturas_y_secciones
        })

    return render(request, 'personas/listar_estudiantes_con_secciones.html', {
        'data': data
    })


################# Sistema FIFO de captura de fotos #################
@require_POST
def capturar_foto(request):
    # 2) Parseo del JSON
    try:
        payload = json.loads(request.body)
        est_id  = payload['estudiante_id']
        img_b64 = payload['imagen_b64']
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest("Formato JSON inválido")

    # 3) Decode base64
    try:
        header, img_str = img_b64.split(';base64,')
        ext = header.split('/')[-1]
        data = base64.b64decode(img_str)
    except Exception:
        return HttpResponseBadRequest("Imagen base64 inválida")

    # 4) Guardado inmediato de la foto en la BD
    nombre = f"{est_id}_{timezone.now():%Y%m%d%H%M%S}.{ext}"
    foto = EstudianteFoto.objects.create(
        estudiante_id=est_id,
        imagen=ContentFile(data, name=nombre),
        es_base=False
    )
    print(f"[CAPTURA] Foto dinámica creada: {foto.imagen.name} para estudiante {est_id}")

    # 5) ¡Encolar procesamiento a Celery en cola 'captures'!
    procesar_captura.apply_async(
        args=[foto.id, img_b64],     # Le pasamos el ID de la foto y el base64
        queue='captures'
    )
    print(f"[CAPTURA] Embedding encolado para foto ID={foto.id} en queue 'captures'")

    # 6) Respuesta inmediata al navegador
    return JsonResponse({'ok': True, 'tarea_encolada': foto.id})

