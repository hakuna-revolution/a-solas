# turnos/views.py

from django.shortcuts import render, redirect, get_object_or_404
from .models import Turno, Inscripcion, SolicitudBaja
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from datetime import timedelta
from collections import OrderedDict
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.forms import ValidationError
import json
from django.db.models import Prefetch, Count
from .forms import (
    UserRegistrationForm,
    TurnoForm,
    SolicitudBajaForm,
    MarcarSolicitudRecibidaForm
)
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings


def registro_usuario(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registro exitoso. ¡Bienvenido!')
            return redirect('turnos:calendario')
        else:
            messages.error(request, 'Hubo un error en el registro. Por favor, revisa los datos ingresados.')
    else:
        form = UserRegistrationForm()
    return render(request, 'turnos/registro.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            messages.success(request, f'Bienvenido, {usuario.username}!')
            return redirect('turnos:calendario')
        else:
            messages.error(request, 'Credenciales inválidas. Por favor, intenta de nuevo.')
    else:
        form = AuthenticationForm()
    return render(request, 'turnos/login.html', {'form': form})

def logout_usuario(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('turnos:calendario')


@login_required
def calendario(request):
    # Obtener la semana actual
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Lunes
    end_of_week = start_of_week + timedelta(days=4)  # Viernes

    # Generar una lista de fechas para la semana actual (lunes a viernes)
    fechas_semana = [start_of_week + timedelta(days=i) for i in range(5)]  # 0: Lunes, 4: Viernes

    # Crear un diccionario ordenado con el nombre del día y la fecha
    dias_semana = OrderedDict()
    traduccion = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
    }
    for fecha in fechas_semana:
        nombre_dia = fecha.strftime('%A')  # Nombre del día en inglés
        nombre_dia_es = traduccion.get(nombre_dia, nombre_dia)
        dias_semana[nombre_dia_es] = fecha.day  # Asignar el número del día

    # Obtener todos los turnos de la semana actual con prefetch_related
    turnos = Turno.objects.filter(dia__gte=0, dia__lte=4).prefetch_related(
        Prefetch('inscripciones', queryset=Inscripcion.objects.select_related('usuario').all())
    ).order_by('dia', 'hora')

    mostrar_telefonos = request.user.is_authenticated and request.user.is_staff

    # Organizar los turnos en un diccionario ordenado con día como clave
    calendario = OrderedDict()
    for dia in dias_semana.keys():
        calendario[dia] = []

    # Añadir turnos al calendario
    for turno in turnos:
        dia = turno.get_dia_display()
        # Asignar si el usuario está inscrito en este turno
        turno.ya_inscrito = False
        inscripcion_usuario = None
        if request.user.is_authenticated:
            inscripcion_usuario = turno.inscripciones.filter(usuario=request.user).first()
            if inscripcion_usuario:
                turno.ya_inscrito = True
                turno.inscripcion_usuario_id = inscripcion_usuario.id  # Añadir atributo para la plantilla
            else:
                turno.inscripcion_usuario_id = None
        else:
            turno.inscripcion_usuario_id = None  # Para usuarios no autenticados

        # No asignar a 'has_pending_bajas'; usar la propiedad directamente en la plantilla
        # Si necesitas el conteo, puedes usar 'pending_bajas_count'

        calendario[dia].append(turno)

    # Obtener el número de solicitudes de baja pendientes para mostrar en el badge
    if request.user.is_authenticated and request.user.is_staff:
        solicitudes_pendientes_count = SolicitudBaja.objects.filter(aprobado=False, rechazado=False).count()
    else:
        solicitudes_pendientes_count = 0

    context = {
        'calendario': calendario,
        'semana_actual': f"{start_of_week.strftime('%d/%m/%Y')} - {end_of_week.strftime('%d/%m/%Y')}",
        'mostrar_telefonos': mostrar_telefonos,
        'solicitudes_pendientes_count': solicitudes_pendientes_count,
        'dias_semana': dias_semana,  # Añadir al contexto
    }

    return render(request, 'turnos/calendario.html', context)

@login_required
def mis_turnos(request):
    inscripciones = request.user.inscripciones.all()
    return render(request, 'turnos/mis_turnos.html', {'inscripciones': inscripciones})


@require_POST
def inscribir_suplente(request):
    try:
        data = json.loads(request.body)
        dia = data.get('dia')
        hora = data.get('hora')
        nombre_suplente = data.get('nombre_suplente')
        telefono_suplente = data.get('telefono_suplente')  # Obtener teléfono
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Datos inválidos.'})

    if dia is None or hora is None or not nombre_suplente or not telefono_suplente:
        return JsonResponse({'success': False, 'message': 'Faltan datos.'})

    try:
        turno = Turno.objects.get(dia=dia, hora=hora)
    except Turno.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Turno no encontrado.'})

    if turno.es_completo_calculado:
        return JsonResponse({'success': False, 'message': 'El turno ya está completo.'})

    # Verificar si el suplente ya está inscrito en este turno
    if Inscripcion.objects.filter(turno=turno, nombre_suplente=nombre_suplente).exists():
        return JsonResponse({'success': False, 'message': 'Ya estás inscrito en este turno como suplente.'})

    # **Nueva Validación: Si el usuario es fijo y ya está inscrito en el turno, no puede inscribirse como suplente**
    if request.user.is_authenticated:
        ya_fijo = Inscripcion.objects.filter(turno=turno, usuario=request.user).exists()
        if ya_fijo:
            return JsonResponse({'success': False, 'message': 'Ya estás inscrito en este turno como fijo. No puedes inscribirte como suplente.'})

    # Crear la inscripción como suplente
    Inscripcion.objects.create(
        turno=turno,
        nombre_suplente=nombre_suplente,
        telefono_suplente=telefono_suplente
    )

    # Actualizar si el turno está completo
    inscripciones_count = Inscripcion.objects.filter(turno=turno).count()
    if inscripciones_count >= turno.max_inscripciones:
        turno.es_completo_calculado = True
        turno.save()

    return JsonResponse({'success': True, 'message': 'Te has inscrito como suplente en el turno.'})


@login_required
def inscribir_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)

    if turno.es_completo_calculado:
        messages.error(request, 'El turno ya está completo.')
        return redirect('turnos:calendario')

    # Evitar duplicados
    if Inscripcion.objects.filter(turno=turno, usuario=request.user).exists():
        messages.warning(request, 'Ya estás inscrito en este turno.')
    else:
        Inscripcion.objects.create(turno=turno, usuario=request.user)
        messages.success(request, 'Te has inscrito al turno correctamente.')

        # Actualizar si el turno está completo
        inscripciones_count = Inscripcion.objects.filter(turno=turno).count()
        if inscripciones_count >= turno.max_inscripciones:
            turno.es_completo_calculado = True
            turno.save()

    return redirect('turnos:calendario')

@staff_member_required
def turnos_vacios(request):
    """
    Vista para que los administradores vean los turnos sin inscripciones.
    """
    # Obtener la semana actual
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Lunes
    end_of_week = start_of_week + timedelta(days=4)  # Viernes

    # Filtrar los turnos que no tienen ninguna inscripción
    turnos_sin_inscripciones = Turno.objects.filter(dia__gte=0, dia__lte=4).annotate(
        num_inscripciones=Count('inscripciones')
    ).filter(num_inscripciones=0).order_by('dia', 'hora')

    # Organizar los turnos sin inscripciones por día
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    turnos_por_dia = {dia: [] for dia in dias_semana}

    for turno in turnos_sin_inscripciones:
        dia = turno.get_dia_display()
        turnos_por_dia[dia].append(turno)

    context = {
        'turnos_por_dia': turnos_por_dia,
        'semana_actual': f"{start_of_week.strftime('%d/%m/%Y')} - {end_of_week.strftime('%d/%m/%Y')}",
    }

    return render(request, 'turnos/turnos_vacios.html', context)

@staff_member_required
def anadir_turno(request):
    if request.method == 'POST':
        form = TurnoForm(request.POST)
        if form.is_valid():
            turno = form.save(commit=False)
            # Validar que la hora esté dentro del rango permitido
            if turno.hora < Turno.HORA_INICIO or turno.hora >= Turno.HORA_FIN:
                messages.error(
                    request,
                    f'La hora debe estar entre {Turno.HORA_INICIO}:00 y {Turno.HORA_FIN - 1}:00.'
                )
                return redirect('turnos:anadir_turno')

            turno.es_completo_calculado = False
            turno.save()

            messages.success(request, f'Turno añadido: {turno}')
            return redirect('turnos:calendario')
        else:
            messages.error(request, 'Hubo un error al añadir el turno. Por favor, revisa los datos ingresados.')
    else:
        form = TurnoForm()

    context = {
        'form': form,
    }
    return render(request, 'turnos/anadir_turno.html', {'form': form})


@staff_member_required
def limpiar_suplentes(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Eliminar todas las inscripciones que no son de usuarios autenticados
                suplentes_eliminados, _ = Inscripcion.objects.filter(usuario__isnull=True).delete()
                # También puedes eliminar los turnos que no tengan inscripciones si es necesario
            messages.success(request, f'Todas las inscripciones de suplentes han sido eliminadas exitosamente. ({suplentes_eliminados} inscripciones eliminadas)')
        except Exception:
            messages.error(request, 'Ocurrió un error al eliminar las inscripciones de suplentes.')
    else:
        messages.error(request, 'Método de solicitud inválido.')

    return redirect('turnos:calendario')

@staff_member_required
def solicitudes_baja(request):
    solicitudes = SolicitudBaja.objects.filter(aprobado=False, rechazado=False).order_by('-fecha_solicitud')

    if request.method == 'POST':
        solicitud_ids = request.POST.getlist('solicitud_ids')
        action = request.POST.get('action')

        if action == 'aprobar':
            for solicitud_id in solicitud_ids:
                solicitud = get_object_or_404(SolicitudBaja, id=solicitud_id)
                solicitud.aprobado = True
                solicitud.fecha_aprobacion = timezone.now()
                solicitud.save()

                # Eliminar la inscripción asociada
                inscripcion = solicitud.inscripcion
                inscripcion.delete()

                # La señal `enviar_notificaciones_solicitud_baja` enviará la notificación al usuario
            messages.success(request, 'Solicitudes aprobadas correctamente.')
            return redirect('turnos:solicitudes_baja')

        elif action == 'rechazar':
            for solicitud_id in solicitud_ids:
                solicitud = get_object_or_404(SolicitudBaja, id=solicitud_id)
                solicitud.rechazado = True
                solicitud.fecha_aprobacion = timezone.now()
                solicitud.save()

                # La señal `enviar_notificaciones_solicitud_baja` enviará la notificación al usuario
            messages.success(request, 'Solicitudes rechazadas correctamente.')
            return redirect('turnos:solicitudes_baja')

    context = {
        'solicitudes_pendientes': solicitudes,
    }
    return render(request, 'turnos/notificaciones_admin.html', context)

@staff_member_required
def aprobar_solicitud_baja(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudBaja, id=solicitud_id, aprobado=False, rechazado=False)
    inscripcion = solicitud.inscripcion

    if request.method == 'POST':
        # Marcar la inscripción como cancelada
        inscripcion.is_canceled = True
        inscripcion.save()

        # Marcar la solicitud como aprobada
        solicitud.aprobado = True
        solicitud.rechazado = False
        solicitud.save()

        # Enviar correo electrónico de aprobación (comentado)
        # asunto = 'Solicitud de Baja Aprobada'
        # mensaje = f'Hola {nombre_usuario},\n\nTu solicitud de baja para el turno "{solicitud.inscripcion.turno}" ha sido aprobada.'
        # remitente = settings.EMAIL_HOST_USER

        # try:
        #     send_mail(asunto, mensaje, remitente, [email_destino])
        # except Exception as e:
        #     messages.error(request, f'La solicitud de baja ha sido aprobada y la inscripción cancelada, pero hubo un error al enviar el correo electrónico: {e}')

        messages.success(request, 'La solicitud de baja ha sido aprobada y la inscripción cancelada.')
        return redirect('turnos:notificaciones_admin')
    
    # Si no es POST, redirigir
    messages.error(request, 'Método de solicitud inválido.')
    return redirect('turnos:notificaciones_admin')

@staff_member_required
def rechazar_solicitud_baja(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudBaja, id=solicitud_id, aprobado=False, rechazado=False)

    if request.method == 'POST':
        # Marcar la solicitud como rechazada
        solicitud.aprobado = False
        solicitud.rechazado = True
        solicitud.save()

        # Enviar correo electrónico de rechazo (comentado)
        # asunto = 'Solicitud de Baja Rechazada'
        # mensaje = f'Hola {nombre_usuario},\n\nTu solicitud de baja para el turno "{solicitud.inscripcion.turno}" ha sido rechazada.'
        # remitente = settings.EMAIL_HOST_USER

        # try:
        #     send_mail(asunto, mensaje, remitente, [email_destino])
        # except Exception as e:
        #     messages.error(request, f'La solicitud de baja ha sido rechazada, pero hubo un error al enviar el correo electrónico: {e}')

        messages.success(request, 'La solicitud de baja ha sido rechazada.')
        return redirect('turnos:notificaciones_admin')
    
    # Si no es POST, redirigir
    messages.error(request, 'Método de solicitud inválido.')
    return redirect('turnos:notificaciones_admin')

@login_required
def baja_turno(request, inscripcion_id):
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if request.method == 'POST':
        if request.user.is_staff:
            # **Caso 1: Administrador elimina cualquier inscripción (incluyendo suplentes)**
            inscripcion.delete()
            messages.success(request, f'La inscripción de {inscripcion} ha sido eliminada correctamente.')
        elif inscripcion.usuario == request.user:
            # **Caso 2: Usuario fijo solicita baja de su propia inscripción**
            existing_solicitud = SolicitudBaja.objects.filter(inscripcion=inscripcion, aprobado=False, rechazado=False).first()
            if existing_solicitud:
                messages.warning(request, 'Ya has solicitado la baja de este turno. Espera la aprobación del administrador.')
            else:
                form = SolicitudBajaForm(request.POST)
                if form.is_valid():
                    try:
                        # Crear la solicitud de baja en estado pendiente
                        solicitud = form.save(commit=False)
                        solicitud.usuario = request.user
                        solicitud.inscripcion = inscripcion  # Asignar correctamente la inscripción
                        solicitud.save()
                        messages.success(request, 'Has solicitado la baja de tu turno. Un administrador revisará tu solicitud pronto.')
                        return redirect('turnos:calendario')
                    except ValidationError as e:
                        form.add_error(None, e)
                        messages.error(request, 'Hubo un error al procesar tu solicitud de baja.')
                else:
                    messages.error(request, 'Hubo un error al procesar tu solicitud de baja.')
        else:
            messages.error(request, 'No tienes permiso para realizar esta acción.')
            return redirect('turnos:calendario')

        # **Actualizar el estado del turno si es necesario**
        turno = inscripcion.turno
        inscripciones_count = Inscripcion.objects.filter(turno=turno).count()
        turno.es_completo_calculado = inscripciones_count >= turno.max_inscripciones
        turno.save()

        return redirect('turnos:calendario')
    else:
        messages.error(request, 'Método de solicitud inválido.')
        return redirect('turnos:calendario')

@staff_member_required
def eliminar_suplente(request, inscripcion_id):
    """
    Vista para que un administrador elimine una inscripción de suplente.
    """
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id, usuario__isnull=True)
    
    if request.method == 'POST':
        inscripcion.delete()
        messages.success(request, 'Suplente eliminado correctamente.')
        return redirect('turnos:calendario')
    
    # Si se accede vía GET, redirigir al calendario
    return redirect('turnos:calendario')

@staff_member_required
def eliminar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)
    turno.delete()
    messages.success(request, 'Turno eliminado correctamente.')
    return redirect('turnos:calendario')


@login_required
def notificar_ausencia(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id)
    inscripcion = get_object_or_404(Inscripcion, turno=turno, usuario=request.user)

    if request.method == 'POST':
        form = SolicitudBajaForm(request.POST)
        if form.is_valid():
            try:
                # Intentar crear una nueva solicitud de baja
                solicitud = form.save(commit=False)
                solicitud.usuario = request.user
                solicitud.inscripcion = inscripcion  # Asegurar que se asigna la inscripción
                solicitud.save()
                messages.success(request, 'Has solicitado la baja de tu turno. Un administrador revisará tu solicitud pronto.')
                return redirect('turnos:calendario')
            except ValidationError as e:
                form.add_error(None, e)
                messages.error(request, 'Hubo un error al procesar tu solicitud de baja.')
        else:
            messages.error(request, 'Hubo un error al procesar tu solicitud de baja.')
    else:
        form = SolicitudBajaForm()

    return render(request, 'turnos/notificar_ausencia.html', {'form': form, 'turno': turno})

from django.db import transaction

@staff_member_required
def notificaciones_admin(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        solicitud_ids = request.POST.getlist('solicitud_ids')
        
        if not solicitud_ids:
            messages.warning(request, 'No se seleccionaron solicitudes.')
            return redirect('turnos:notificaciones_admin')
        
        # Filtrar solo las solicitudes pendientes
        solicitudes = SolicitudBaja.objects.filter(id__in=solicitud_ids, aprobado=False, rechazado=False)
        
        if action == 'aprobar':
            with transaction.atomic():
                for solicitud in solicitudes:
                    inscripcion = solicitud.inscripcion
                    # Marcar la inscripción como cancelada
                    inscripcion.is_canceled = True
                    inscripcion.save()
                    
                    # Marcar la solicitud como aprobada
                    solicitud.aprobado = True
                    solicitud.rechazado = False
                    solicitud.save()
            messages.success(request, f'{solicitudes.count()} solicitudes aprobadas y sus inscripciones canceladas.')
        
        elif action == 'rechazar':
            for solicitud in solicitudes:
                solicitud.aprobado = False
                solicitud.rechazado = True
                solicitud.save()
            messages.success(request, f'{solicitudes.count()} solicitudes rechazadas.')
        
        else:
            messages.error(request, 'Acción inválida.')
        
        return redirect('turnos:notificaciones_admin')
    
    else:
        # Manejar solicitudes GET
        solicitudes_pendientes = SolicitudBaja.objects.filter(aprobado=False, rechazado=False).select_related('inscripcion__turno', 'inscripcion__usuario')
        solicitudes_pendientes_count = solicitudes_pendientes.count()
        context = {
            'solicitudes_pendientes': solicitudes_pendientes,
            'solicitudes_pendientes_count': solicitudes_pendientes_count,
        }
        return render(request, 'turnos/notificaciones_admin.html', context)


# Amdmin usuarios 
# turnos/views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from .models import Inscripcion, Profile
from django.core.paginator import Paginator

# Vista para listar y gestionar usuarios

@staff_member_required
def admin_usuarios(request):
    # Obtener todos los usuarios con sus perfiles y conteo de inscripciones
    usuarios = User.objects.annotate(
        total_inscripciones=Count('inscripciones'),
        inscripciones_activas=Count('inscripciones', filter=Q(inscripciones__turno__dia__gte=0))
    ).select_related('profile').order_by('-is_staff', 'username')

    # Filtrado de usuarios
    query = request.GET.get('q')
    if query:
        usuarios = usuarios.filter(
            Q(username__icontains=query) | 
            Q(email__icontains=query) | 
            Q(profile__telefono__icontains=query)
        )

    # Paginación
    paginator = Paginator(usuarios, 20)  # 20 usuarios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Contexto para la plantilla
    context = {
        'usuarios': page_obj,  # Actualizar a page_obj
        'total_usuarios': usuarios.count(),
        'total_staff': usuarios.filter(is_staff=True).count(),
        'total_activos': usuarios.filter(is_active=True).count(),
    }

    return render(request, 'turnos/admin_usuarios.html', context)


# Vista para ver detalles de un usuario específico
@staff_member_required
def admin_usuario_detalle(request, usuario_id):
    usuario = get_object_or_404(User.objects.select_related('profile'), id=usuario_id)
    
    # Obtener inscripciones del usuario
    inscripciones = usuario.inscripciones.select_related('turno').order_by('turno__dia', 'turno__hora')

    context = {
        'usuario': usuario,
        'inscripciones': inscripciones,
    }

    return render(request, 'turnos/admin_usuario_detalle.html', context)

# Vista para toggling de estatus de staff
@staff_member_required
def admin_usuario_toggle_staff(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    
    if request.method == 'POST':
        usuario.is_staff = not usuario.is_staff
        usuario.save()
        
        status = "administrador" if usuario.is_staff else "usuario normal"
        messages.success(request, f'{usuario.username} ahora es un {status}.')
    
    return redirect('turnos:admin_usuarios')

# Vista para toggling de estatus activo
@staff_member_required
def admin_usuario_toggle_activo(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    
    if request.method == 'POST':
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        status = "activado" if usuario.is_active else "desactivado"
        messages.success(request, f'El usuario {usuario.username} ha sido {status}.')
    
    return redirect('turnos:admin_usuarios')
