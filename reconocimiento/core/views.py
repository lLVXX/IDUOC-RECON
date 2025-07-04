# CORE/VIEWS.PY
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from clases.models import AsistenciaClase, ClaseInstancia
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, F
import io
import pandas as pd

from xhtml2pdf import pisa

from django.template.loader  import render_to_string

# Formularios propios
from .forms import CalendarioGlobalForm, EditarCalendarioForm, EditarSemanaForm
from .forms import CustomLoginForm, AdminZonaForm, CalendarioWizardForm
from personas.forms import EstudianteForm
from .models import CalendarioAcademico, SemanaAcademica, Sede
# Modelos propios
from .models import CustomUser
from sedes.models import Seccion
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.utils import timezone


from sedes.models import Sede, Carrera, Asignatura, Seccion
from core.models import CustomUser
from clases.models import Clase, AsistenciaClase
from personas.models import EstudianteAsignaturaSeccion


# Decoradores y utilidades personalizadas
from core.decorators import admin_zona_required
from core.decorators import admin_global_required

@login_required
def redirigir_por_rol(request):
    user = request.user
    if user.is_superuser:
        return redirect('/admin/')  # panel normal de Django
    elif user.user_type == 'admin_global':
        return redirect('dashboard_admin_global')
    elif user.user_type == 'admin_zona':
        return redirect('dashboard_admin_zona')
    else:
        return redirect('logout')


def is_admin_zona(user):
    return user.is_authenticated and user.user_type == 'admin_zona'




def portal_inicio(request):
    if request.method == "POST":
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            if user.user_type == 'admin_global':
                return redirect('dashboard_admin_global')
            # puedes agregar más redirecciones aquí
    else:
        form = CustomLoginForm()
    return render(request, 'core/portal_inicio.html', {'form': form})























@login_required
@admin_global_required
def dashboard_admin_global(request):
    now      = timezone.now()
    sedes_qs = Sede.objects.all()
    sede_sel = request.GET.get('sede', 'all')

    if sede_sel != 'all':
        sedes_qs = sedes_qs.filter(id=sede_sel)
        sede_obj = sedes_qs.first()
    else:
        sede_obj = None

    sedes_data = []
    for sede in sedes_qs:
        profs = CustomUser.objects.filter(user_type='profesor', sede=sede)
        ests  = CustomUser.objects.filter(user_type='estudiante', sede=sede)
        insts = ClaseInstancia.objects.filter(
            finalizada=True,
            version__plantilla__profesor__sede=sede
        )

        total_prof  = profs.count()
        total_est   = ests.count()
        total_cls   = insts.count()

        # % asistencia global
        pos, pres = 0, 0
        for inst in insts:
            cnt = EstudianteAsignaturaSeccion.objects.filter(
                seccion=inst.version.plantilla.seccion
            ).values('estudiante').distinct().count()
            pos  += cnt
            pres += inst.asistencias.filter(presente=True).count()
        pct_global = round((pres * 100.0 / pos), 1) if pos else 0

        # Resumen por carrera
        carreras_stats = []
        for ca in Carrera.objects.filter(sede=sede):
            insts_ca = insts.filter(
                version__plantilla__profesor__carrera=ca
            )
            tot_cl_ca = insts_ca.count()
            pos_ca, pres_ca = 0, 0
            for inst in insts_ca:
                cnt = EstudianteAsignaturaSeccion.objects.filter(
                    seccion=inst.version.plantilla.seccion
                ).values('estudiante').distinct().count()
                pos_ca  += cnt
                pres_ca += inst.asistencias.filter(presente=True).count()
            pct_ca = round((pres_ca * 100.0 / pos_ca), 1) if pos_ca else 0
            carreras_stats.append({
                'nombre':     ca.nombre,
                'sede':       sede.nombre,
                'clases':     tot_cl_ca,
                'porcentaje': pct_ca,
            })

        # Resumen por asignatura
        asignaturas_stats = []
        for a in Asignatura.objects.filter(carrera__sede=sede).distinct():
            insts_a = insts.filter(
                version__plantilla__seccion__asignatura=a
            )
            tot_cl_a = insts_a.count()
            pos_a, pres_a = 0, 0
            for inst in insts_a:
                cnt = EstudianteAsignaturaSeccion.objects.filter(
                    seccion=inst.version.plantilla.seccion
                ).values('estudiante').distinct().count()
                pos_a  += cnt
                pres_a += inst.asistencias.filter(presente=True).count()
            pct_a = round((pres_a * 100.0 / pos_a), 1) if pos_a else 0
            asignaturas_stats.append({
                'nombre':     a.nombre,
                'sede':       sede.nombre,
                'clases':     tot_cl_a,
                'porcentaje': pct_a,
            })

        # Estudiantes por carrera
        estudiantes_stats = []
        for ca in Carrera.objects.filter(sede=sede):
            cnt = EstudianteAsignaturaSeccion.objects.filter(
                seccion__asignatura__carrera=ca
            ).values('estudiante').distinct().count()
            estudiantes_stats.append({
                'nombre': ca.nombre,
                'alumnos': cnt,
            })

        sedes_data.append({
            'sede':               sede,
            'total_profesores':   total_prof,
            'total_estudiantes':  total_est,
            'total_clases':       total_cls,
            'pct_global':         pct_global,
            'carreras_stats':     carreras_stats,
            'asignaturas_stats':  asignaturas_stats,
            'estudiantes_stats':  estudiantes_stats,
        })

    # Exportar a PDF
    if request.GET.get('format') == 'pdf':
        context = {
            'sede_sel':   sede_obj.nombre if sede_obj else 'Todas las sedes',
            'sedes_data': sedes_data,
            'now':        now,
        }
        return export_to_pdf(
            'exports/pdf_admin_global_full.html',
            context,
            filename=f"dashboard_global_{sede_obj.nombre if sede_obj else 'todas'}"
        )

    # Render web
    return render(request, 'core/dashboard_admin_global.html', {
        'sedes':      Sede.objects.all(),
        'sede_sel':   sede_obj,
        'sedes_data': sedes_data,
    })






def cerrar_sesion(request):
    logout(request)
    return redirect('portal_inicio')



##################################################}
##############################################
# GESTION ADMIN ZONA /SEDES
##############################################


@login_required
@admin_global_required
def gestionar_admin_zona(request):
    editar_id = request.GET.get("editar")
    eliminar_id = request.GET.get("eliminar")

    # Eliminar usuario
    if eliminar_id:
        usuario = get_object_or_404(CustomUser, id=eliminar_id, user_type='admin_zona')
        usuario.delete()
        messages.success(request, "Administrador de zona eliminado correctamente.")
        return redirect("gestionar_admin_zona")

    # Editar usuario
    if editar_id:
        instance = get_object_or_404(CustomUser, id=editar_id, user_type='admin_zona')
        form = AdminZonaForm(request.POST or None, instance=instance)
    else:
        form = AdminZonaForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            instance = form.save(commit=False)
            nombre = form.cleaned_data['nombre']
            apellido = form.cleaned_data['apellido']
            rut = form.cleaned_data['rut']
            sede = form.cleaned_data['sede']

            nombre_corto = nombre[:2].lower()
            apellido_lower = apellido.lower()
            sede_nombre = sede.nombre.lower().replace(" ", "")
            email_generado = f"{nombre_corto}.{apellido_lower}@{sede_nombre}.com"
            username_base = f"{nombre_corto}{apellido_lower}"

            # Evitar colisiones de username/email
            username_final = username_base
            i = 1
            while CustomUser.objects.filter(username=username_final).exists():
                username_final = f"{username_base}{i}"
                i += 1

            email_final = email_generado
            i = 1
            while CustomUser.objects.filter(email=email_final).exists():
                email_final = f"{nombre_corto}.{apellido_lower}{i}@{sede_nombre}.com"
                i += 1

            instance.email = email_final
            instance.username = username_final
            instance.first_name = nombre
            instance.last_name = apellido
            instance.user_type = 'admin_zona'
            instance.workzone = sede
            instance.rut = rut

            if not editar_id:
                instance.set_password('12345678')

            instance.save()
            messages.success(request, f"{'Actualizado' if editar_id else 'Creado'} correctamente: {username_final}")
            return redirect("gestionar_admin_zona")
        else:
            messages.error(request, "Revisa los errores del formulario.")

    adminzonas = CustomUser.objects.filter(user_type='admin_zona').select_related('workzone')

    return render(request, "core/gestionar_admin_zona.html", {
        'form': form,
        'adminzonas': adminzonas,
        'editar_id': editar_id
    })

##############################################
# EXPORT EXCEL / DEPRICATED
##############################################



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
    resp = HttpResponse(result.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return resp

##############################################
# DASHBOARD ADMIN ZONA 
##############################################





@login_required
@admin_zona_required
def dashboard_admin_zona(request):
    sede         = request.user.sede
    admin_nombre = request.user.get_full_name()
    now          = timezone.now()

    # Totales generales
    total_profesores  = CustomUser.objects.filter(user_type='profesor', sede=sede).count()
    total_estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=sede).count()
    total_clases      = ClaseInstancia.objects.filter(
        finalizada=True,
        version__plantilla__profesor__sede=sede
    ).count()

    # Resumen por Carrera
    carreras_stats = []
    for carrera in Carrera.objects.filter(sede=sede):
        insts = ClaseInstancia.objects.filter(
            finalizada=True,
            version__plantilla__profesor__carrera=carrera,
            version__plantilla__profesor__sede=sede
        )
        total_cl = insts.count()
        tot_pos, tot_pres = 0, 0
        for inst in insts:
            sec = inst.version.plantilla.seccion
            cnt = EstudianteAsignaturaSeccion.objects.filter(
                seccion=sec
            ).values('estudiante').distinct().count()
            tot_pos  += cnt
            tot_pres += inst.asistencias.filter(presente=True).count()
        pct = round((tot_pres * 100.0 / tot_pos), 1) if tot_pos else 0
        carreras_stats.append({
            'nombre':     carrera.nombre,
            'clases':     total_cl,
            'porcentaje': pct,
        })

    # Resumen por Profesor
    profes = CustomUser.objects.filter(user_type='profesor', sede=sede)
    # Clases dadas y asistencias
    cp = (ClaseInstancia.objects
          .filter(finalizada=True, version__plantilla__profesor__in=profes)
          .values('version__plantilla__profesor')
          .annotate(dadas=Count('id')))
    ap = (AsistenciaClase.objects
          .filter(instancia__version__plantilla__profesor__in=profes)
          .values('instancia__version__plantilla__profesor')
          .annotate(
              registros=Count('id'),
              presentes=Count('id', filter=Q(presente=True))
          ))
    clases_map = {e['version__plantilla__profesor']: e['dadas'] for e in cp}
    asist_map  = {e['instancia__version__plantilla__profesor']: e for e in ap}

    prof_stats = []
    for p in profes:
        dadas = clases_map.get(p.id, 0)
        regs  = asist_map.get(p.id, {}).get('registros', 0)
        pres  = asist_map.get(p.id, {}).get('presentes', 0)
        pct   = round((pres * 100.0 / regs), 2) if regs else 0.00

        # Detalle por asignatura/sección
        detalle_map = {}
        insts = ClaseInstancia.objects.filter(
            finalizada=True,
            version__plantilla__profesor=p
        ).select_related('version__plantilla__seccion__asignatura')
        for inst in insts:
            asig = inst.version.plantilla.seccion.asignatura.nombre
            secc = inst.version.plantilla.seccion.nombre
            key = (asig, secc)
            detalle_map.setdefault(key, {'manual': 0, 'automatico': 0})
            for a in inst.asistencias.filter(presente=True):
                if a.manual:
                    detalle_map[key]['manual'] += 1
                else:
                    detalle_map[key]['automatico'] += 1

        detalle = [
            {'asignatura': asig, 'seccion': secc,
             'manual': d['manual'], 'automatico': d['automatico']}
            for (asig, secc), d in detalle_map.items()
        ]

        prof_stats.append({
            'nombre':       p.get_full_name(),
            'clases_dadas': dadas,
            'estudiantes':  EstudianteAsignaturaSeccion.objects
                                 .filter(seccion__in=[i.version.plantilla.seccion for i in insts])
                                 .values('estudiante').distinct().count(),
            'porcentaje':   f"{pct:.2f}",
            'detalle':      detalle,
        })

    # Exportación
    fmt = request.GET.get('format')
    if fmt == 'excel':
        rows = []
        for r in prof_stats:
            for d in r['detalle']:
                rows.append({
                    'Administrador': admin_nombre,
                    'Profesor':      r['nombre'],
                    'Asignatura':    d['asignatura'],
                    'Sección':       d['seccion'],
                    'Manual':        d['manual'],
                    'Automático':    d['automatico'],
                    '% Asistencia':  r['porcentaje'],
                })
        return export_to_excel(rows, filename=f"dashboard_zona_{sede.nombre}")

    if fmt == 'pdf':
        context = {
            'zona':              sede.nombre,
            'admin_nombre':      admin_nombre,
            'total_profesores':  total_profesores,
            'total_estudiantes': total_estudiantes,
            'total_clases':      total_clases,
            'carreras_stats':    carreras_stats,
            'prof_stats':        prof_stats,
            'now':               now,
        }
        return export_to_pdf(
            'exports/pdf_adminzona.html',
            context,
            filename=f"dashboard_zona_{sede.nombre}"
        )

    # Render web
    return render(request, 'core/dashboard_admin_zona.html', {
        'total_profesores':  total_profesores,
        'total_estudiantes': total_estudiantes,
        'total_clases':      total_clases,
        'carreras_stats':    carreras_stats,
        'resumen_profs':     prof_stats,
    })


##############################################
# GESTION CALENDARIO ACADEMICO
##############################################



@login_required
def gestionar_calendario(request):
    user = request.user
    es_admin_global = user.user_type == 'admin_global'
    es_admin_zona = user.user_type == 'admin_zona'

    # CREAR CALENDARIO - Solo admin_global
    if es_admin_global and request.method == "POST" and 'crear' in request.POST:
        form = CalendarioGlobalForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            fecha_inicio = form.cleaned_data['fecha_inicio']
            semanas = form.cleaned_data['semanas']
            fecha_fin = fecha_inicio + timedelta(weeks=semanas) - timedelta(days=1)
            sedes = Sede.objects.all()
            for sede in sedes:
                calendario = CalendarioAcademico.objects.create(
                    sede=sede,
                    nombre=nombre,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                for i in range(semanas):
                    ini = fecha_inicio + timedelta(weeks=i)
                    fin = ini + timedelta(days=6)
                    SemanaAcademica.objects.create(
                        calendario=calendario,
                        numero=i + 1,
                        fecha_inicio=ini,
                        fecha_fin=fin,
                        tipo='clases'
                    )
            messages.success(request, f"Calendario '{nombre}' creado para todas las sedes.")
            return redirect('gestionar_calendario')
    else:
        form = CalendarioGlobalForm()

    # ELIMINAR CALENDARIO - Solo admin_global
    if es_admin_global and request.method == "POST" and 'eliminar' in request.POST:
        calendario_id = request.POST.get('eliminar')
        calendario = get_object_or_404(CalendarioAcademico, id=calendario_id)
        calendario.delete()
        messages.success(request, "Calendario eliminado correctamente.")
        return redirect('gestionar_calendario')

    # EDITAR SEMANAS (para ambos, según permisos)
    if request.method == "POST" and 'guardar_semanas' in request.POST:
        calendario_id = request.POST.get('calendario_id')
        calendario = get_object_or_404(CalendarioAcademico, id=calendario_id)
        if es_admin_global or (es_admin_zona and calendario.sede == user.sede):
            semanas = SemanaAcademica.objects.filter(calendario=calendario).order_by('numero')
            for semana in semanas:
                prefix = f"semana_{semana.pk}_"
                semana.numero = request.POST.get(f'{prefix}numero', semana.numero)
                semana.fecha_inicio = request.POST.get(f'{prefix}fecha_inicio', semana.fecha_inicio)
                semana.fecha_fin = request.POST.get(f'{prefix}fecha_fin', semana.fecha_fin)
                semana.tipo = request.POST.get(f'{prefix}tipo', semana.tipo)
                semana.descripcion = request.POST.get(f'{prefix}descripcion', semana.descripcion)
                semana.save()
            messages.success(request, "Semanas actualizadas correctamente.")
            return redirect('gestionar_calendario')

    # LISTADO
    if es_admin_global:
        calendarios = CalendarioAcademico.objects.select_related('sede').all().order_by('nombre', 'sede__nombre')
    elif es_admin_zona:
        calendarios = CalendarioAcademico.objects.filter(sede=user.sede).order_by('nombre')
    else:
        calendarios = []

    # Semana para editar (si existe query param ?edit=XX)
    calendario_editar = None
    semanas = []
    edit_id = request.GET.get('edit')
    if edit_id:
        calendario_editar = get_object_or_404(CalendarioAcademico, id=edit_id)
        if es_admin_global or (es_admin_zona and calendario_editar.sede == user.sede):
            semanas = SemanaAcademica.objects.filter(calendario=calendario_editar).order_by('numero')
        else:
            calendario_editar = None

    context = {
        'form': form,
        'calendarios': calendarios,
        'calendario_editar': calendario_editar,
        'semanas': semanas,
        'es_admin_global': es_admin_global,
        'es_admin_zona': es_admin_zona,
    }
    return render(request, "core/gestionar_calendario.html", context)



##############################################
# EXPORTS DASHBOARD PDF
##############################################

@login_required
@user_passes_test(admin_global_required)
def exportar_dashboard_pdf(request):
    # Copia la lógica de métricas y filtros EXACTA al dashboard_admin_global
    sede_id = request.GET.get("sede")
    carrera_id = request.GET.get("carrera")
    sede_actual = Sede.objects.filter(id=sede_id).first() if sede_id else None
    carrera_actual = Carrera.objects.filter(id=carrera_id).first() if carrera_id else None

    sedes = Sede.objects.all().order_by('nombre')
    total_sedes = sedes.count()
    total_carreras = Carrera.objects.count()
    total_asignaturas = Asignatura.objects.count()
    total_secciones = Seccion.objects.count()
    total_profesores = CustomUser.objects.filter(user_type="profesor").count()
    total_estudiantes = CustomUser.objects.filter(user_type="estudiante").count()
    total_clases = Clase.objects.count()
    total_clases_finalizadas = Clase.objects.filter(finalizada=True).count()
    total_asistencias = AsistenciaClase.objects.filter(presente=True).count()
    porcentaje_asistencia = (
        100 * total_asistencias / AsistenciaClase.objects.count()
        if AsistenciaClase.objects.exists() else 0
    )

    # Estadísticas por sede
    sedes_stats = []
    for sede in sedes:
        carreras = sede.carreras.count()
        asignaturas = Asignatura.objects.filter(carrera__sede=sede).count()
        secciones = Seccion.objects.filter(asignatura__carrera__sede=sede).count()
        profesores = CustomUser.objects.filter(user_type='profesor', sede=sede).count()
        estudiantes = CustomUser.objects.filter(user_type='estudiante', sede=sede).count()
        clases = Clase.objects.filter(aula__sede=sede).count()
        clases_finalizadas = Clase.objects.filter(aula__sede=sede, finalizada=True).count()
        asistencia_total = AsistenciaClase.objects.filter(clase__aula__sede=sede, presente=True).count()
        asistencia_total_registros = AsistenciaClase.objects.filter(clase__aula__sede=sede).count()
        porc_asistencia = (
            100 * asistencia_total / asistencia_total_registros if asistencia_total_registros else 0
        )
        sedes_stats.append({
            "sede": sede,
            "carreras": carreras,
            "asignaturas": asignaturas,
            "secciones": secciones,
            "profesores": profesores,
            "estudiantes": estudiantes,
            "clases": clases,
            "clases_finalizadas": clases_finalizadas,
            "porc_asistencia": porc_asistencia,
        })

    asignaturas_qs = Asignatura.objects.all()
    if sede_actual:
        asignaturas_qs = asignaturas_qs.filter(carrera__sede=sede_actual)
    if carrera_actual:
        asignaturas_qs = asignaturas_qs.filter(carrera=carrera_actual)
    asignaturas_ranking = (
        asignaturas_qs.annotate(
            num_estudiantes=Count('secciones__relaciones_estudiantes_asignatura', distinct=True)
        )
        .order_by('-num_estudiantes')[:10]
    )

    context = {
        "total_sedes": total_sedes,
        "total_carreras": total_carreras,
        "total_asignaturas": total_asignaturas,
        "total_secciones": total_secciones,
        "total_profesores": total_profesores,
        "total_estudiantes": total_estudiantes,
        "total_clases": total_clases,
        "total_clases_finalizadas": total_clases_finalizadas,
        "total_asistencias": total_asistencias,
        "porcentaje_asistencia": porcentaje_asistencia,
        "sedes_stats": sedes_stats,
        "asignaturas_ranking": asignaturas_ranking,
        "fecha_generacion": timezone.now(),
        "sede_actual": sede_actual,
        "carrera_actual": carrera_actual,
        "admin_user": request.user,
    }

    template = get_template("core/dashboard_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="dashboard_reporte.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response




