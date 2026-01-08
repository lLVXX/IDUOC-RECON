# personas/views.py

from django.contrib.auth.decorators import login_required
from core.decorators import admin_zona_required
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache

from core.models import CustomUser
from personas.models import EstudianteAsignaturaSeccion, EstudianteFoto
from personas.tasks import procesar_captura

import json
import base64
import os





MAX_FOTOS_DINAMICAS = 3        # FIFO
COOLDOWN_SEGUNDOS = 8  




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














def puede_capturar(estudiante_id):
    """
    Cooldown simple por estudiante
    """
    key = f"captura_lock_{estudiante_id}"
    if cache.get(key):
        return False
    cache.set(key, True, timeout=COOLDOWN_SEGUNDOS)
    return True


def aplicar_fifo_estudiante(estudiante_id):
    """
    Mantiene solo las últimas N fotos dinámicas
    """
    fotos = EstudianteFoto.objects.filter(
        estudiante_id=estudiante_id,
        es_base=False
    ).order_by("created_at")

    exceso = fotos.count() - MAX_FOTOS_DINAMICAS + 1

    if exceso > 0:
        for foto in fotos[:exceso]:
            try:
                if foto.imagen and os.path.exists(foto.imagen.path):
                    os.remove(foto.imagen.path)
            except Exception as e:
                print(f"[FIFO] Error eliminando archivo: {e}")

            foto.delete()









################# Sistema FIFO de captura de fotos #################
@require_POST
def capturar_foto(request):
    # 1️⃣ Parseo JSON
    try:
        payload = json.loads(request.body)
        est_id  = payload['estudiante_id']
        img_b64 = payload['imagen_b64']
    except (KeyError, json.JSONDecodeError):
        return HttpResponseBadRequest("Formato JSON inválido")

    # 2️⃣ Cooldown (NO rompe frontend)
    if not puede_capturar(est_id):
        return JsonResponse({
            "ok": False,
            "motivo": "cooldown"
        })

    # 3️⃣ Decode base64
    try:
        header, img_str = img_b64.split(';base64,')
        ext = header.split('/')[-1]
        data = base64.b64decode(img_str)
    except Exception:
        return HttpResponseBadRequest("Imagen base64 inválida")

    # 4️⃣ FIFO ANTES de guardar (clave del sistema)
    aplicar_fifo_estudiante(est_id)

    # 5️⃣ Guardado inmediato (IGUAL QUE ANTES)
    nombre = f"{est_id}_{timezone.now():%Y%m%d%H%M%S}.{ext}"

    foto = EstudianteFoto.objects.create(
        estudiante_id=est_id,
        imagen=ContentFile(data, name=nombre),
        es_base=False
    )

    print(f"[CAPTURA] Foto dinámica creada: {foto.imagen.name} para estudiante {est_id}")

    # 6️⃣ Celery EXACTAMENTE como lo tenías
    procesar_captura.apply_async(
        args=[foto.id, img_b64],
        queue='captures'
    )

    print(f"[CAPTURA] Embedding encolado para foto ID={foto.id}")

    # 7️⃣ Respuesta idéntica
    return JsonResponse({
        'ok': True,
        'tarea_encolada': foto.id
    })
