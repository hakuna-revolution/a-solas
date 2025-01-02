# turnos/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError
# from django.core.mail import send_mail  # Comentado temporalmente
from django.conf import settings


# turnos/models.py

class Turno(models.Model):
    DIA_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
    ]

    HORA_INICIO = 9
    HORA_FIN = 19

    dia = models.IntegerField(choices=DIA_SEMANA)
    hora = models.IntegerField()
    max_inscripciones = models.PositiveIntegerField(default=5)  # Ajusta según tus necesidades
    es_completo_calculado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_dia_display()} {self.hora}:00 - {self.hora + 1}:00"

    class Meta:
        unique_together = ('dia', 'hora')
        ordering = ['dia', 'hora']

    @property
    def inscripciones_count(self):
        return self.inscripciones.count()

    @property
    def ausencia_notificada(self):
        # Accede a SolicitudBaja a través de Inscripcion
        return SolicitudBaja.objects.filter(
            inscripcion__turno=self,
            aprobado=True
        ).first()

    @property
    def has_pending_bajas(self):
        return self.solicitudes_baja.filter(aprobado=False, rechazado=False).exists()
    
    @property
    def pending_bajas_count(self):
        return self.solicitudes_baja.filter(aprobado=False, rechazado=False).count()

    def ya_inscrito(self, user):
        return self.inscripciones.filter(usuario=user).exists()

    def clean(self):
        super().clean()
        if not (self.HORA_INICIO <= self.hora < self.HORA_FIN):
            raise ValidationError({'hora': f'La hora debe estar entre {self.HORA_INICIO}:00 y {self.HORA_FIN - 1}:00.'})


class Inscripcion(models.Model):
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, related_name='inscripciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inscripciones', null=True, blank=True)
    nombre_suplente = models.CharField(max_length=150, null=True, blank=True)
    telefono_suplente = models.CharField(max_length=20, null=True, blank=True)  # Nuevo campo para suplentes
    fecha_inscripcion = models.DateTimeField(default=timezone.now)
    is_canceled = models.BooleanField(default=False)  # Nuevo campo para marcar la inscripción como cancelada

    def __str__(self):
        if self.usuario:
            return f"{self.usuario.username} inscrito en {self.turno}"
        return f"{self.nombre_suplente} (Suplente) inscrito en {self.turno}"

    def clean(self):
        if not self.usuario and not self.nombre_suplente:
            raise ValidationError('Debe proporcionar un usuario o un nombre de suplente.')
        if self.usuario and self.nombre_suplente:
            raise ValidationError('No puede proporcionar un usuario y un nombre de suplente al mismo tiempo.')
        if self.nombre_suplente and not self.telefono_suplente:
            raise ValidationError('Debe proporcionar un número de teléfono para el suplente.')


class SolicitudBaja(models.Model):
    inscripcion = models.ForeignKey(Inscripcion, related_name='solicitudes_baja', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    aprobado = models.BooleanField(default=False)
    rechazado = models.BooleanField(default=False)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    notificada_admin = models.BooleanField(default=False)
    
    # Campos adicionales
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    notificada_usuario = models.BooleanField(default=False)

    def __str__(self):
        if self.inscripcion.usuario:
            return f"Solicitud de baja de {self.inscripcion.usuario.username} en {self.inscripcion.turno}"
        return f"Solicitud de baja de Suplente: {self.inscripcion.nombre_suplente} en {self.inscripcion.turno}"
    
    def clean(self):
        super().clean()
        if self.aprobado and not self.inscripcion:
            raise ValidationError('Debe haber una inscripción asociada para aprobar la solicitud.')

    class Meta:
        # Eliminamos la restricción única para permitir múltiples solicitudes por inscripción
        constraints = [
            # models.UniqueConstraint(
            #     fields=['inscripcion'],
            #     name='unique_solicitud_baja_per_inscripcion'
            # )
        ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.profile.save()


# @receiver(post_save, sender=SolicitudBaja)
# def enviar_notificaciones_solicitud_baja(sender, instance, created, **kwargs):
#     # Comentado temporalmente para no enviar correos
#     if created:
#         # Enviar notificación al administrador
#         admin_emails = [admin.email for admin in User.objects.filter(is_staff=True, is_superuser=True)]
#         if admin_emails:
#             send_mail(
#                 subject='Nueva Solicitud de Baja de Turno',
#                 message=f'El usuario {instance.inscripcion.usuario.username if instance.inscripcion.usuario else instance.inscripcion.nombre_suplente} ha solicitado la baja del turno {instance.inscripcion.turno}.',
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 recipient_list=admin_emails,
#                 fail_silently=False,
#             )
#     else:
#         # Enviar notificación al usuario si la solicitud fue aprobada o rechazada
#         if instance.aprobado:
#             if instance.inscripcion.usuario and instance.inscripcion.usuario.email:
#                 send_mail(
#                     subject='Solicitud de Baja Aprobada',
#                     message=f'Hola {instance.inscripcion.usuario.username},\n\nTu solicitud de baja del turno {instance.inscripcion.turno} ha sido aprobada.',
#                     from_email=settings.DEFAULT_FROM_EMAIL,
#                     recipient_list=[instance.inscripcion.usuario.email],
#                     fail_silently=False,
#                 )
#         elif instance.rechazado:
#             if instance.inscripcion.usuario and instance.inscripcion.usuario.email:
#                 send_mail(
#                     subject='Solicitud de Baja Rechazada',
#                     message=f'Hola {instance.inscripcion.usuario.username},\n\nTu solicitud de baja del turno {instance.inscripcion.turno} ha sido rechazada.',
#                     from_email=settings.DEFAULT_FROM_EMAIL,
#                     recipient_list=[instance.inscripcion.usuario.email],
#                     fail_silently=False,
#                 )
