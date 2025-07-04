from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
import pandas as pd
from django.core.files.base import ContentFile
import base64
from django.conf import settings
import os
from django.utils.timezone import now
from personas.models import EstudianteFoto
from django.utils import timezone
from django.template.loader import render_to_string
from django.db.models import F
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models     import Count
from core.decorators import admin_zona_required, admin_global_required, profesor_required
from core.models import CustomUser, SemanaAcademica
from django.http import JsonResponse, HttpResponseBadRequest
from personas.models import EstudianteFoto
from django.middleware.csrf import get_token
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Avg, F, Q
from django.http import HttpResponse

import logging
from xhtml2pdf import pisa           # <<< sólo xhtml2pdf


from personas.tasks import guardar_imagen_dinamica_post_clase
from sedes.models import Asignatura, Seccion
from personas.models import EstudianteAsignaturaSeccion, EstudianteAsignaturaSeccion

from .models import (
    BloqueHorario,
    Aula,
    Clase,
    ClasePlantillaVersion,
    ClaseInstancia,
    AsistenciaClase,
    AuditoriaAsistencia,
    HistorialAsistenciaClase,
)

from .forms import BloqueHorarioForm, AulaForm, ClaseForm
from collections import defaultdict
import io, json
from django.conf import settings
from personas.tasks import guardar_imagen_dinamica_post_clase
from personas.models import EstudianteFoto



# ========== CONFIGURACIÓN ARC FACE ==========
ARCFACE_URL = os.getenv("ARC_FACE_URL", "http://arcface:8001/match_faces/")



logger = logging.getLogger('clases')

### ESTABLECE PARAMETROS PARA BLOQUE HORARIO ###
DIAS_SEMANA = [
    ('LU', 'Lunes'),
    ('MA', 'Martes'),
    ('MI', 'Miércoles'),
    ('JU', 'Jueves'),
    ('VI', 'Viernes'),
    ('SA', 'Sábado'),
]

##############################################
# CRUD BLOQUES HORARIOS
##############################################
@login_required
@admin_zona_required
def gestionar_bloques_horarios(request):
    editar_id    = request.GET.get("editar")
    eliminar_id  = request.POST.get("eliminar_id")  # ahora proviene del modal

    # 1) Si viene POST de eliminación desde el modal
    if request.method == "POST" and eliminar_id:
        BloqueHorario.objects.filter(id=eliminar_id).delete()
        messages.success(request, "Bloque eliminado correctamente.")
        return redirect("clases:gestionar_bloques_horarios")

    # 2) Cargar formulario de edición o creación
    if editar_id:
        bloque = get_object_or_404(BloqueHorario, id=editar_id)
        form   = BloqueHorarioForm(request.POST or None, instance=bloque)
    else:
        form   = BloqueHorarioForm(request.POST or None)

    # 3) Procesar creación/edición
    if request.method == "POST" and not eliminar_id and form.is_valid():
        form.save()
        action = "Actualizado" if editar_id else "Creado"
        messages.success(request, f"{action} correctamente.")
        return redirect("clases:gestionar_bloques_horarios")

    # 4) Listado de bloques
    bloques = BloqueHorario.objects.all().order_by("hora_inicio")

    return render(request, "clases/gestionar_bloques_horarios.html", {
        "form":      form,
        "bloques":   bloques,
        "editar_id": editar_id,
    })


##############################################
# CRUD AULAS
##############################################

@login_required
@admin_zona_required
def gestionar_aulas(request):
    # Obtener parámetros de edición/eliminación
    editar_id   = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    # ELIMINAR
    if eliminar_id:
        aula = get_object_or_404(Aula, id=eliminar_id, sede=request.user.sede)
        aula.delete()
        messages.success(request, "Aula eliminada correctamente.")
        return redirect("clases:gestionar_aulas")

    # EDITAR: cargar instancia en el form
    if editar_id:
        instancia = get_object_or_404(Aula, id=editar_id, sede=request.user.sede)
        form = AulaForm(request.POST or None, instance=instancia)
    else:
        # CREAR: form vacío con valor inicial camara_ip="0"
        form = AulaForm(request.POST or None)

    # PROCESAR FORM
    if request.method == 'POST' and form.is_valid():
        aula = form.save(commit=False)
        aula.sede = request.user.sede
        # Si el usuario dejó camara_ip vacío, forzar "0"
        if not aula.camara_ip:
            aula.camara_ip = "0"
        aula.save()
        accion = "Actualizada" if editar_id else "Creada"
        messages.success(request, f"Aula {accion} correctamente.")
        return redirect("clases:gestionar_aulas")

    # LISTADO: solo aulas de la sede del usuario
    aulas = Aula.objects.filter(sede=request.user.sede).order_by('numero_sala')

    return render(request, 'clases/gestionar_aulas.html', {
        'form':      form,
        'aulas':     aulas,
        'editar_id': editar_id,
    })

##############################################
# CRUD CLASES — VISUAL / TABLERO SEMANAL
##############################################

@login_required
@admin_zona_required
def gestionar_clases(request):
    user = request.user

    # 1) Profesores y selección
    profesores = CustomUser.objects.filter(
        user_type='profesor',
        sede=user.sede
    ).order_by('last_name')
    prof_id = request.GET.get('profesor')
    selected_profesor = (
        get_object_or_404(profesores, pk=prof_id)
        if prof_id else None
    )

    # 2) Semanas y estado publicado
    semanas = list(
        SemanaAcademica.objects.filter(calendario__sede=user.sede)
                              .order_by('numero')
    )
    any_publicada = (
        selected_profesor and
        Clase.objects.filter(profesor=selected_profesor, publicada=True).exists()
    )
    sem_act = None
    if any_publicada and semanas:
        sid = request.GET.get('semana') or semanas[0].id
        sem_act = get_object_or_404(SemanaAcademica, pk=sid)

    # 3) Crear nueva plantilla + generar instancias
    if selected_profesor:
        form = ClaseForm(request.POST or None, user=user)
        # ** Filtrar asignaturas según la carrera del profesor **
        form.fields['asignatura'].queryset = Asignatura.objects.filter(
            carrera=selected_profesor.carrera
        )
    else:
        form = None

    if selected_profesor and request.method == 'POST' and 'agregar' in request.POST:
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.profesor = selected_profesor
            nueva.save()
            if semanas:
                version = ClasePlantillaVersion.objects.create(
                    plantilla=nueva,
                    effective_from=semanas[0]
                )
                for sem in semanas:
                    ClaseInstancia.objects.update_or_create(
                        version=version,
                        semana_academica=sem,
                        defaults={'fecha': sem.fecha_inicio + nueva.get_dia_semana_delta()}
                    )
            messages.success(request, "Plantilla creada y aplicada a todo el semestre.")
            return redirect(
                reverse('clases:gestionar_clases') + f"?profesor={selected_profesor.id}"
            )
        messages.error(request, "Corrige los errores del formulario.")

    # 4) Publicar semestre
    if selected_profesor and request.method == 'POST' and 'publicar' in request.POST:
        if semanas:
            for pl in Clase.objects.filter(profesor=selected_profesor, publicada=False):
                ver, _ = ClasePlantillaVersion.objects.get_or_create(
                    plantilla=pl, effective_from=semanas[0]
                )
                for sem in semanas:
                    ClaseInstancia.objects.update_or_create(
                        version=ver,
                        semana_academica=sem,
                        defaults={'fecha': sem.fecha_inicio + pl.get_dia_semana_delta()}
                    )
                pl.publicada = True
                pl.save()
            messages.success(request, "Todas las plantillas publicadas.")
        else:
            messages.warning(request, "No hay semanas académicas definidas.")
        return redirect(
            reverse('clases:gestionar_clases') + f"?profesor={selected_profesor.id}"
        )

    # 5) Editar / Eliminar con alcance
    if selected_profesor and request.method == 'POST' and request.POST.get('action') in (
        'editar_plantilla', 'eliminar_plantilla', 'eliminar_inst'
    ):
        action = request.POST['action']
        target = int(request.POST['target_id'])
        scope = request.POST.get('scope')

        # EDITAR PLANTILLA
        if action == 'editar_plantilla':
            nueva_seccion = get_object_or_404(Seccion, pk=request.POST['seccion'])
            nueva_aula = get_object_or_404(Aula, pk=request.POST['aula'])

            if any_publicada and scope == 'week':
                pl_orig = get_object_or_404(Clase, pk=target, profesor=selected_profesor)
                inst = get_object_or_404(
                    ClaseInstancia,
                    version__plantilla=pl_orig,
                    semana_academica=sem_act
                )
                clone = Clase.objects.create(
                    profesor=pl_orig.profesor,
                    seccion=nueva_seccion,
                    aula=nueva_aula,
                    dia_semana=pl_orig.dia_semana,
                    bloque_horario=pl_orig.bloque_horario,
                    publicada=True
                )
                ver_clone = ClasePlantillaVersion.objects.create(
                    plantilla=clone, effective_from=sem_act
                )
                inst.version = ver_clone
                inst.save()
            else:
                pl = get_object_or_404(Clase, pk=target, profesor=selected_profesor)
                if any_publicada and scope != 'week':
                    ver, _ = ClasePlantillaVersion.objects.get_or_create(
                        plantilla=pl, effective_from=sem_act
                    )
                    pl.seccion = nueva_seccion
                    pl.aula = nueva_aula
                    pl.save()
                    for sem in semanas:
                        if sem.numero >= sem_act.numero:
                            ClaseInstancia.objects.update_or_create(
                                version=ver,
                                semana_academica=sem,
                                defaults={'fecha': sem.fecha_inicio + pl.get_dia_semana_delta()}
                            )
                else:
                    pl.seccion = nueva_seccion
                    pl.aula = nueva_aula
                    pl.save()
            messages.success(request, "Plantilla editada correctamente.")

        # ELIMINAR INSTANCIA
        elif action == 'eliminar_inst':
            if scope == 'week':
                ClaseInstancia.objects.filter(pk=target).delete()
            else:
                inst = get_object_or_404(
                    ClaseInstancia,
                    pk=target,
                    version__plantilla__profesor=selected_profesor
                )
                for sem in semanas:
                    if sem.numero >= sem_act.numero:
                        ClaseInstancia.objects.filter(
                            version=inst.version,
                            semana_academica=sem
                        ).delete()
            messages.success(request, "Instancia eliminada correctamente.")

        # ELIMINAR PLANTILLA
        else:
            if any_publicada and scope == 'week':
                ver = get_object_or_404(
                    ClasePlantillaVersion,
                    plantilla__pk=target,
                    effective_from=sem_act
                )
                ClaseInstancia.objects.filter(version=ver, semana_academica=sem_act).delete()
            else:
                versiones = ClasePlantillaVersion.objects.filter(
                    plantilla__profesor=selected_profesor,
                    effective_from__gte=sem_act
                )
                for ver in versiones:
                    ver.instancias.filter(semana_academica__numero__gte=sem_act.numero).delete()
                    ver.delete()
            messages.success(request, "Plantilla eliminada correctamente.")

        return redirect(
            reverse('clases:gestionar_clases')
            + f"?profesor={selected_profesor.id}&semana={sem_act.id}"
        )

    # 6) Construir matriz
    bloques = BloqueHorario.objects.order_by('hora_inicio')
    dias = [d for d, _ in DIAS_SEMANA]
    dias_nombres = [n for _, n in DIAS_SEMANA]
    matriz = {d: {b.id: None for b in bloques} for d in dias}

    instancias = []
    if selected_profesor and any_publicada:
        instancias = ClaseInstancia.objects.filter(
            version__plantilla__profesor=selected_profesor,
            semana_academica=sem_act
        ).select_related(
            'version__plantilla__bloque_horario',
            'version__plantilla__seccion',
            'version__plantilla__aula'
        )
        for inst in instancias:
            pl = inst.version.plantilla
            matriz[pl.dia_semana][pl.bloque_horario.id] = inst

    # 7) Contar estudiantes por sección
    section_ids = {inst.version.plantilla.seccion.id for inst in instancias}
    qs_counts = (
        EstudianteAsignaturaSeccion.objects
        .filter(seccion_id__in=section_ids)
        .values('seccion_id')
        .annotate(cnt=Count('id'))
    )
    counts_map = {entry['seccion_id']: entry['cnt'] for entry in qs_counts}

    return render(request, 'clases/gestionar_clases.html', {
        'profesores':       profesores,
        'selected_profesor': selected_profesor,
        'semanas':          semanas,
        'sem_act':          sem_act,
        'any_publicada':    any_publicada,
        'form':             form,
        'bloques':          bloques,
        'dias':             dias,
        'dias_nombres':     dias_nombres,
        'matriz':           matriz,
        'counts_map':       counts_map,
    })

# Endpoints AJAX para poblar selectores
@require_GET
@login_required
@admin_zona_required
def get_asignaturas_ajax(request):
    prof_id = request.GET.get('profesor')
    prof = get_object_or_404(
        CustomUser,
        pk=prof_id,
        user_type='profesor',
        sede=request.user.sede
    )
    qs = Asignatura.objects.filter(carrera=prof.carrera)
    data = [{'id': a.id, 'nombre': a.nombre} for a in qs]
    return JsonResponse(data, safe=False)

@require_GET
@login_required
@admin_zona_required
def get_secciones_ajax(request):
    aid = request.GET.get('asignatura_id')
    qs = Seccion.objects.filter(asignatura_id=aid).values('id','nombre')
    return JsonResponse(list(qs), safe=False)




##############################################
# HORARIO PROFESOR
##############################################

@login_required
@profesor_required
def horario_profesor(request):
    user = request.user

    # 1) Semanas de la sede del profesor
    semanas = (SemanaAcademica.objects
               .filter(calendario__sede=user.sede)
               .order_by('numero'))
    semana_id = request.GET.get('semana')
    if semana_id:
        sem_sel = get_object_or_404(semanas, pk=semana_id)
    else:
        sem_sel = semanas.first()

    # 2) Bloques y días
    bloques      = BloqueHorario.objects.order_by('hora_inicio')
    dias_codes   = [code for code, _ in DIAS_SEMANA]
    dias_nombres = [name for _, name in DIAS_SEMANA]

    # 3) Instancias de clase del profesor en la semana seleccionada
    instancias = (ClaseInstancia.objects
                  .filter(version__plantilla__profesor=user,
                          semana_academica=sem_sel)
                  .select_related(
                      'version__plantilla__bloque_horario',
                      'version__plantilla__seccion',
                      'version__plantilla__aula'
                  ))

    # 4) Construir la matriz[dia][bloque_id] = instancia
    matriz = {dia: {b.id: None for b in bloques} for dia in dias_codes}
    for inst in instancias:
        dia   = inst.version.plantilla.dia_semana
        bid   = inst.version.plantilla.bloque_horario.id
        matriz[dia][bid] = inst

    # 5) Contar estudiantes por sección (misma lógica que en gestionar_clases)
    section_ids = {
        inst.version.plantilla.seccion.id
        for inst in instancias
    }
    qs_counts = (
        EstudianteAsignaturaSeccion.objects
        .filter(seccion_id__in=section_ids)
        .values('seccion_id')
        .annotate(cnt=Count('id'))
    )
    counts_map = {entry['seccion_id']: entry['cnt'] for entry in qs_counts}

    return render(request, 'clases/horario_profesor.html', {
        'semanas':      semanas,
        'semana_sel':   sem_sel,
        'bloques':      bloques,
        'dias':         dias_codes,
        'dias_nombres': dias_nombres,
        'matriz':       matriz,
        'counts_map':   counts_map,
    })

##############################################
# DETALLE DE CLASE Y ASISTENCIA
##############################################
@login_required
@profesor_required
def detalle_instancia(request, inst_id):
    # Definición de URLs AJAX / WS al inicio
    
    asistencia_url = reverse('clases:asistencia_live', args=[inst_id])
    finish_url     = reverse('clases:finalizar_clase', args=[inst_id])
    captura_url    = reverse('personas:capturar_foto')

    print(f"[DETALLE] captura_url en contexto: {captura_url}")
    print(f"[DETALLE] asistencia_url={asistencia_url}, finish_url={finish_url}")

    instancia = get_object_or_404(ClaseInstancia, id=inst_id)

    # Permisos
    if instancia.version.plantilla.profesor != request.user:
        print(f"[DETALLE] Acceso denegado para user {request.user.username}")
        raise PermissionDenied

    # IDs de estudiantes en la sección
    est_ids = EstudianteAsignaturaSeccion.objects.filter(
        seccion=instancia.version.plantilla.seccion
    ).values_list('estudiante_id', flat=True)
    estudiantes = CustomUser.objects.filter(
        id__in=est_ids, user_type='estudiante'
    )
    print(f"[DETALLE] Estudiantes: {[e.username for e in estudiantes]}")

    # Asistencias ya registradas
    asis_qs = AsistenciaClase.objects.filter(instancia=instancia)
    asistencias = {a.estudiante_id: a.presente for a in asis_qs}
    print(f"[DETALLE] Asistencias previas: {asistencias}")

    # Construir WS URL
    ws_base = settings.ARC_FACE_WS.rstrip('/')
    if ws_base.startswith('https://'):
        ws_base = 'wss://' + ws_base[len('https://'):]
    elif ws_base.startswith('http://'):
        ws_base = 'ws://'  + ws_base[len('http://'):]
    ws_url = ws_base + '/stream/'
    print(f"[DETALLE] ws_url={ws_url}")

    # Manejar POST (finalizar clase)
    if request.method == "POST":
        print(f"[DETALLE] POST de finalizar clase inst_id={inst_id}")
        inscritos = CustomUser.objects.filter(
            seccion=instancia.version.plantilla.seccion,
            user_type='estudiante'
        )
        for est in inscritos:
            AsistenciaClase.objects.get_or_create(
                instancia=instancia,
                estudiante=est,
                defaults={'presente': False}
            )
        url_reporte = reverse('clases:reporte_instancia', args=[inst_id])
        return JsonResponse({'ok': True, 'url_reporte': url_reporte})

    # GET: renderizado normal
    context = {
        'instancia':       instancia,
        'estudiantes':     estudiantes,
        'asistencias':     asistencias,
        'ws_url': settings.ARC_FACE_WS,  
        'asistencia_url':  asistencia_url,
        'finish_url':      finish_url,
        'captura_url':     captura_url,  # <-- aquí lo incluyes
    }
    return render(request, 'clases/detalle_instancia.html', context)



@login_required
@profesor_required
@csrf_exempt
def asistencia_live(request, inst_id):
    if request.method != 'POST':
        print(f"[ASISTENCIA_LIVE] Método no permitido: {request.method}")
        return HttpResponseBadRequest('Only POST allowed')
    try:
        payload  = json.loads(request.body)
        est_id   = payload['estudiante']
        manual   = bool(payload.get('manual', False))
        presente = bool(payload.get('presente', True))
        print(f"[ASISTENCIA_LIVE] Recibido: estudiante={est_id}, manual={manual}, presente={presente}")
    except (ValueError, KeyError):
        
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    instancia  = get_object_or_404(ClaseInstancia, id=inst_id)
    estudiante = get_object_or_404(CustomUser, id=est_id, user_type='estudiante')

    obj, created = AsistenciaClase.objects.get_or_create(
        instancia=instancia,
        estudiante=estudiante,
        defaults={
            'presente':  presente,
            'manual':    manual,
            'timestamp': timezone.now()
        }
    )
    if not created and manual:
        # Si ya existía pero ahora viene clic manual, lo sobrescribimos
        obj.presente   = presente
        obj.manual     = True
        obj.timestamp  = timezone.now()
        obj.save(update_fields=['presente', 'manual', 'timestamp'])

    return JsonResponse({'ok': True})




@login_required
@profesor_required
def finalizar_clase(request, inst_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Solo POST permitido')

    instancia = get_object_or_404(ClaseInstancia, id=inst_id)
    if instancia.version.plantilla.profesor != request.user:
        raise PermissionDenied

    # 1) Obtener todos los estudiantes de la sección
    estudiantes = instancia.version.plantilla.seccion.estudiantes.filter(user_type='estudiante')

    # 2) Crear ausencias automáticas donde no exista registro
    faltantes = []
    for est in estudiantes:
        obj, created = AsistenciaClase.objects.get_or_create(
            instancia=instancia,
            estudiante=est,
            defaults={'presente': False, 'manual': False}
        )
        if created:
            faltantes.append(obj)

    # 3) Contar asistentes y ausentes
    total_presentes = AsistenciaClase.objects.filter(instancia=instancia, presente=True).count()
    total_ausentes = AsistenciaClase.objects.filter(instancia=instancia, presente=False).count()

    # 4) Registrar auditoría
    AuditoriaAsistencia.objects.create(
        instancia=instancia,
        evento=f"Clase finalizada: {total_presentes} presentes, {total_ausentes} ausentes."
    )

    # 5) Historial de ausencias
    for ausencia in faltantes:
        HistorialAsistenciaClase.objects.create(
            asistencia=ausencia,
            cambio='Creada como ausente'
        )

    # 6) Enviar tareas Celery por cada asistente presente
    asistencias = AsistenciaClase.objects.filter(instancia=instancia, presente=True)
    for asistencia in asistencias:
        estudiante = asistencia.estudiante

        # Buscar la última foto dinámica (no base)
        foto = EstudianteFoto.objects.filter(estudiante=estudiante, es_base=False).order_by('-created_at').first()
        if not foto:
            print(f"⚠️ No se encontró imagen dinámica para estudiante {estudiante.id}")
            continue

        try:
            # Construir ruta absoluta
            ruta_foto = os.path.normpath(os.path.join(settings.MEDIA_ROOT, str(foto.imagen)))

            # Leer imagen
            with open(ruta_foto, 'rb') as f:
                imagen_bytes = f.read()

            # Extraer embedding si existe
            embedding = foto.embedding if foto.embedding else []
            if not embedding:
                print(f"⚠️ Embedding vacío para estudiante {estudiante.id}, se omite.")
                continue

            # Enviar tarea Celery
            guardar_imagen_dinamica_post_clase.delay(estudiante.id, embedding, imagen_bytes)
            print(f"📦 Enviada tarea post-clase a Celery para estudiante {estudiante.id}")

        except Exception as e:
            print(f"❌ Error al procesar estudiante {estudiante.id}: {e}")

    # 7) Marcar como finalizada
    instancia.finalizada = True
    instancia.save(update_fields=['finalizada'])

    url_reporte = reverse('clases:reporte_instancia', args=[inst_id])
    return JsonResponse({'ok': True, 'url_reporte': url_reporte})

@login_required
@profesor_required
def reporte_instancia(request, inst_id):
    instancia = get_object_or_404(ClaseInstancia, id=inst_id, finalizada=True)
    seccion = instancia.version.plantilla.seccion
    relaciones = EstudianteAsignaturaSeccion.objects.filter(seccion=seccion)
    estudiantes = CustomUser.objects.filter(
        id__in=relaciones.values_list('estudiante_id', flat=True),
        user_type='estudiante'
    ).order_by('last_name', 'first_name')

    detalle = []
    presentes = 0
    for est in estudiantes:
        try:
            asis = AsistenciaClase.objects.get(instancia=instancia, estudiante=est)
            presente = asis.presente
            tipo = 'Manual' if asis.manual else 'Automático'
        except AsistenciaClase.DoesNotExist:
            presente = False
            tipo = '—'
        if presente:
            presentes += 1
        detalle.append({
            'nombre':   est.get_full_name(),
            'rut':      est.rut,
            'presente': presente,
            'tipo':     tipo,
        })

    total = len(detalle)
    ausentes = total - presentes
    pct = round(presentes * 100 / total, 1) if total else 0

    return render(request, 'clases/reporte_instancia.html', {
        'instancia': instancia,
        'presentes':  presentes,
        'ausentes':   ausentes,
        'total':      total,
        'pct_total':  pct,
        'detalle':    detalle,
    })


##############################################
# VISTA TESTEO /// NO ACCEDIBLE - FULL
##############################################

@login_required
@profesor_required
def listado_instancias(request):
    # Solo las instancias que:
    # 1) estén finalizadas (finalizada=True)
    # 2) pertenezcan al profesor que está logeado
    instancias = (
        ClaseInstancia.objects
        .filter(
            finalizada=True,
            version__plantilla__profesor=request.user
        )
        .select_related('version__plantilla__seccion__asignatura')
        .order_by('-fecha')
    )
    return render(request, 'clases/listado_instancias.html', {
        'instancias': instancias,
    })



##############################################
# DETALLE DE CLASE Y ASISTENCIA
##############################################


def registrar_foto_automatica(estudiante, imagen_file, embedding_list):
    """
    Guarda una nueva foto automática (es_base=False) si el estudiante tiene < 5 fotos.
    embedding_list: lista de floats.
    imagen_file: InMemoryUploadedFile o archivo leído en memoria.
    """
    qs = EstudianteFoto.objects.filter(estudiante=estudiante)
    if qs.count() >= 5:
        return None

    # Si recibimos raw bytes en lugar de UploadedFile lo convertimos:
    if not hasattr(imagen_file, 'name'):
        bio = io.BytesIO(imagen_file)
        imagen_file = InMemoryUploadedFile(
            file=bio,
            field_name='imagen',
            name=f"auto_{estudiante.id}.jpg",
            content_type='image/jpeg',
            size=bio.getbuffer().nbytes,
            charset=None
        )

    foto = EstudianteFoto(
        estudiante=estudiante,
        imagen=imagen_file,
        embedding=embedding_list,
        es_base=False
    )
    # valida (limpia) y guarda
    foto.full_clean()
    foto.save()
    return foto


###################################################################
###################################################################
###################################################################
###################################################################


@login_required
@require_GET
def get_secciones_ajax(request):
    """
    Devuelve JSON con las secciones de una asignatura dada.
    Parámetro GET: ?asignatura_id=<id>
    """
    asignatura_id = request.GET.get('asignatura_id')
    if not asignatura_id:
        return JsonResponse({'error': 'Falta asignatura_id'}, status=400)

    secciones = Seccion.objects.filter(asignatura_id=asignatura_id).values('id', 'nombre')
    # output: [ {'id':1,'nombre':'001A'}, ... ]
    return JsonResponse(list(secciones), safe=False)


def registrar_foto_automatica(estudiante, imagen_file, embedding):
    """
    Guarda una nueva foto automática (es_base=False) si el estudiante
    tiene menos de 5 fotos en total.
    """
    fotos_existentes = EstudianteFoto.objects.filter(estudiante=estudiante).count()
    if fotos_existentes >= 5:
        return None

    foto = EstudianteFoto(
        estudiante=estudiante,
        imagen=imagen_file,
        embedding=bytes(embedding),
        es_base=False
    )
    # valida campos (por ejemplo, tamaño de imagen, embedding correcto…)
    foto.full_clean()
    foto.save()
    return foto




###################################################################
#########                    EXPORTS                    ###########
###################################################################


def export_to_excel(rows, filename):
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    resp = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return resp

def export_to_pdf(template_src, context, filename):
    html = render_to_string(template_src, context)
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return response

@login_required
@profesor_required
def dashboard_profesor(request):
    user = request.user
    now  = timezone.now()

    # Todas las clases del profesor
    all_qs = ClaseInstancia.objects.filter(
        version__plantilla__profesor=user
    )
    total_clases      = all_qs.count()
    total_finalizadas = all_qs.filter(finalizada=True).count()
    total_pendientes  = total_clases - total_finalizadas

    # Sólo finalizadas para calcular asistencia
    final_qs = all_qs.filter(finalizada=True)
    total_posibles, total_presentes = 0, 0
    for inst in final_qs:
        sec = inst.version.plantilla.seccion
        cnt = EstudianteAsignaturaSeccion.objects.filter(
            seccion=sec
        ).values('estudiante').distinct().count()
        total_posibles  += cnt
        total_presentes += inst.asistencias.filter(presente=True).count()
    asist_prom    = round((total_presentes * 100.0 / total_posibles), 2) if total_posibles else 0
    auto_total    = AsistenciaClase.objects.filter(
                        Q(instancia__version__plantilla__profesor=user) &
                        Q(presente=True, manual=False)
                    ).count()
    man_total     = AsistenciaClase.objects.filter(
                        Q(instancia__version__plantilla__profesor=user) &
                        Q(presente=True, manual=True)
                    ).count()
    absent_total  = total_posibles - total_presentes

    # Historial de últimas 10 finalizadas
    historial = []
    for inst in final_qs.select_related('version__plantilla__seccion__asignatura')\
                        .order_by('-fecha')[:10]:
        sec     = inst.version.plantilla.seccion
        tot_est = EstudianteAsignaturaSeccion.objects.filter(
                      seccion=sec
                  ).values('estudiante').distinct().count()
        auto    = inst.asistencias.filter(presente=True, manual=False).count()
        man     = inst.asistencias.filter(presente=True, manual=True).count()
        pct     = round(((auto + man) * 100.0 / tot_est), 1) if tot_est else 0
        historial.append({
            'fecha'     : inst.fecha,
            'asignatura': sec.asignatura.nombre,
            'seccion'   : sec.nombre,
            'total'     : tot_est,
            'auto'      : auto,
            'manual'    : man,
            'pct'       : pct,
        })

    # Exportación PDF
    if request.GET.get('format') == 'pdf':
        context = {
            'profesor':          user.get_full_name(),
            'sede':              getattr(user, 'sede', None) and user.sede.nombre,
            'total_clases':      total_clases,
            'total_finalizadas': total_finalizadas,
            'total_pendientes':  total_pendientes,
            'auto_total':        auto_total,
            'man_total':         man_total,
            'absent_total':      absent_total,
            'historial':         historial,
            'now':               now,
        }
        # Fíjate que aquí coincida con tu ruta y nombre de archivo:
        return export_to_pdf(
            'exports/pdf_dashboard.html',
            context,
            filename=f"dashboard_{user.username}"
        )

    # Render web normal
    return render(request, 'clases/dashboard_profesor.html', {
        'total_clases':      total_clases,
        'total_finalizadas': total_finalizadas,
        'total_pendientes':  total_pendientes,
        'asist_prom':        asist_prom,
        'auto_total':        auto_total,
        'man_total':         man_total,
        'absent_total':      absent_total,
        'historial':         historial,
    })

@csrf_exempt  # Si estás usando CSRF en producción, mejor proteger con @login_required y csrf_token
@require_POST
def capturar_foto(request):
    """
    Recibe una imagen en base64 desde el cliente (JS), la guarda como ImageField
    y aplica política FIFO (solo se guardan las últimas 3 por estudiante).
    """
    try:
        # Parseamos JSON recibido
        data = json.loads(request.body)
        estudiante_id = data.get('estudiante_id')
        imagen_b64 = data.get('imagen_b64')

        if not estudiante_id or not imagen_b64:
            return JsonResponse({"ok": False, "msg": "Datos incompletos"}, status=400)

        # Decodificamos la imagen base64 → bytes
        format, imgstr = imagen_b64.split(';base64,')  # ej: data:image/jpeg;base64,...
        ext = format.split('/')[-1]  # jpeg
        img_bytes = base64.b64decode(imgstr)

        # Convertimos a archivo Django-compatible
        file_name = f"dinamica_{now().strftime('%Y%m%d%H%M%S')}.{ext}"
        django_file = ContentFile(img_bytes, name=file_name)

        # Creamos instancia de EstudianteFoto
        nueva_foto = EstudianteFoto.objects.create(
            estudiante_id=estudiante_id,
            imagen=django_file,
            es_base=False,
            created_at=now()
        )

        print(f"📸 Nueva imagen dinámica guardada para estudiante {estudiante_id}")

        # Aplicamos política FIFO: si hay más de 3 fotos dinámicas, borramos la más antigua
        fotos_dinamicas = EstudianteFoto.objects.filter(
            estudiante_id=estudiante_id,
            es_base=False
        ).order_by('created_at')

        if fotos_dinamicas.count() > 3:
            for extra in fotos_dinamicas[:-3]:  # mantenemos las 3 más recientes
                print(f"🗑️ Eliminando imagen antigua {extra.imagen.name}")
                extra.imagen.delete(save=False)  # borra el archivo del sistema
                extra.delete()  # borra la fila de la base de datos

        return JsonResponse({"ok": True, "msg": "Foto dinámica guardada exitosamente"})

    except Exception as e:
        print(f"❌ Error en capturar_foto: {e}")
        return JsonResponse({"ok": False, "msg": str(e)}, status=500)