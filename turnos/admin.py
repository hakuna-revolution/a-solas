# turnos/admin.py

from django.contrib import admin
from .models import Turno, Inscripcion, SolicitudBaja

class SolicitudBajaAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'fecha_solicitud', 'aprobado')
    actions = ['aprobar_solicitud']

    def aprobar_solicitud(self, request, queryset):
        for solicitud in queryset:
            solicitud.aprobado = True
            solicitud.save()
            # Eliminar la inscripción
            solicitud.inscripcion.delete()
        self.message_user(request, "Solicitudes aprobadas y turnos liberados.")
    aprobar_solicitud.short_description = "Aprobar solicitudes seleccionadas"

admin.site.register(Turno)
admin.site.register(Inscripcion)
admin.site.register(SolicitudBaja, SolicitudBajaAdmin)
