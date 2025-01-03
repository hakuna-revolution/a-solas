# turnos/urls.py

from django.urls import path
from . import views

app_name = 'turnos'

urlpatterns = [
    path('', views.calendario, name='calendario'),
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('mis_turnos/', views.mis_turnos, name='mis_turnos'),
    path('inscribir/<int:turno_id>/', views.inscribir_turno, name='inscribir_turno'),
    path('inscribir_suplente/', views.inscribir_suplente, name='inscribir_suplente'),
    path('baja/<int:inscripcion_id>/', views.baja_turno, name='baja_turno'),
    path('anadir_turno/', views.anadir_turno, name='anadir_turno'),
    path('limpiar_suplentes/', views.limpiar_suplentes, name='limpiar_suplentes'),
    path('eliminar_suplente/<int:inscripcion_id>/', views.eliminar_suplente, name='eliminar_suplente'),
    path('eliminar_turno/<int:turno_id>/', views.eliminar_turno, name='eliminar_turno'),
    path('solicitudes_baja/', views.solicitudes_baja, name='solicitudes_baja'),
    path('solicitudes_baja/<int:solicitud_id>/aprobar/', views.aprobar_solicitud_baja, name='aprobar_solicitud_baja'),
    path('solicitudes_baja/<int:solicitud_id>/rechazar/', views.rechazar_solicitud_baja, name='rechazar_solicitud_baja'),
    path('notificar_ausencia/<int:turno_id>/', views.notificar_ausencia, name='notificar_ausencia'),
    path('notificaciones_admin/', views.notificaciones_admin, name='notificaciones_admin'),
    path('turnos_vacios/', views.turnos_vacios, name='turnos_vacios'),
    
    # URLs para la administración de usuarios
    path('gestion-usuarios/', views.admin_usuarios, name='admin_usuarios'),
    path('gestion-usuarios/<int:usuario_id>/', views.admin_usuario_detalle, name='admin_usuario_detalle'),
    path('gestion-usuarios/<int:usuario_id>/toggle_staff/', views.admin_usuario_toggle_staff, name='admin_usuario_toggle_staff'),
    path('gestion-usuarios/<int:usuario_id>/toggle_activo/', views.admin_usuario_toggle_activo, name='admin_usuario_toggle_activo'),
]
