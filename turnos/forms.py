# turnos/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Turno, Inscripcion, SolicitudBaja, Profile
from django.db import transaction
import logging

my_logger = logging.getLogger('my_logger')



class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico'
        }),
        label='Correo Electrónico'
    )
    telefono = forms.CharField(
        max_length=20,
        required=True,
        help_text='Número de teléfono obligatorio.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
        label='Teléfono'
    )  
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        }),
        label='Nombre de Usuario'
    )  
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label='Contraseña'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        }),
        label='Confirmar Contraseña'
    )  
    class Meta:
        model = User
        fields = ['username', 'email', 'telefono', 'password1', 'password2']
    
    def save(self, commit=True):
        my_logger.debug("Iniciando el método save para el registro del usuario.")
        
        # Crear el objeto de usuario, sin guardar aún en la base de datos
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            with transaction.atomic():  # Aseguramos que todo se guarde en una transacción
                user.save()
                my_logger.debug(f"Usuario {user.username} guardado.")

                # Obtener el teléfono del formulario
                telefono = self.cleaned_data.get('telefono')
                my_logger.debug(f"Teléfono recibido: {telefono}")

                # Validar y asignar el teléfono al perfil
                if telefono:
                    try:
                        profile, created = Profile.objects.update_or_create(
                            user=user,
                            defaults={'telefono': telefono}
                        )
                        my_logger.debug(f"Perfil {'creado' if created else 'actualizado'} para el usuario {user.username}. Teléfono guardado: {profile.telefono}")
                    except Exception as e:
                        my_logger.error(f"Error al guardar el teléfono para el usuario {user.username}: {str(e)}")
                else:
                    my_logger.warning(f"No se proporcionó teléfono para el usuario {user.username}.")
        else:
            my_logger.debug("El commit es False, no se guarda el usuario ni el perfil.")
        
        return user





class TurnoForm(forms.ModelForm):
    """
    Formulario para crear o editar turnos.
    Solo accesible para administradores.
    """
    class Meta:
        model = Turno
        fields = ['dia', 'hora', 'max_inscripciones']
        widgets = {
            'dia': forms.Select(choices=Turno.DIA_SEMANA, attrs={'class': 'form-control'}),
            'hora': forms.NumberInput(attrs={'class': 'form-control', 'min': Turno.HORA_INICIO, 'max': Turno.HORA_FIN - 1}),
            'max_inscripciones': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'dia': 'Día de la Semana',
            'hora': 'Hora',
            'max_inscripciones': 'Máximo de Inscripciones',
        }

    def clean_hora(self):
        """
        Valida que la hora esté dentro del rango permitido.
        """
        hora = self.cleaned_data.get('hora')
        if hora < Turno.HORA_INICIO or hora >= Turno.HORA_FIN:
            raise forms.ValidationError(f'La hora debe estar entre {Turno.HORA_INICIO}:00 y {Turno.HORA_FIN - 1}:00.')
        return hora


class InscribirSuplenteForm(forms.ModelForm):
    """
    Formulario para que usuarios no autenticados se inscriban como suplentes.
    """
    nombre_suplente = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre completo'}),
        label='Nombre Completo'
    )
    telefono_suplente = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su número de teléfono'}),
        label='Teléfono'
    )
    dia = forms.IntegerField(widget=forms.HiddenInput())
    hora = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = Inscripcion
        fields = ['nombre_suplente', 'telefono_suplente', 'dia', 'hora']

    def clean(self):
        """
        Valida que no se proporcionen simultáneamente un usuario y un nombre de suplente.
        """
        cleaned_data = super().clean()
        usuario = cleaned_data.get('usuario')
        nombre_suplente = cleaned_data.get('nombre_suplente')

        if usuario and nombre_suplente:
            raise forms.ValidationError('No puedes proporcionar un usuario y un nombre de suplente al mismo tiempo.')

        if not usuario and not nombre_suplente:
            raise forms.ValidationError('Debes proporcionar un nombre de suplente.')

        return cleaned_data


class SolicitudBajaForm(forms.ModelForm):
    """
    Formulario para que los usuarios soliciten la baja de un turno.
    Este formulario no incluye campos visibles y se utiliza para crear una SolicitudBaja en estado pendiente.
    """
    class Meta:
        model = SolicitudBaja
        fields = []

    def save(self, commit=True, user=None, turno=None):
        """
        Crea una solicitud de baja para el usuario y turno específicos.
        """
        solicitud = super().save(commit=False)
        if user and turno:
            inscripcion = Inscripcion.objects.filter(turno=turno, usuario=user).first()
            if not inscripcion:
                raise forms.ValidationError('No estás inscrito en este turno.')
            solicitud.inscripcion = inscripcion
            solicitud.aprobado = False  # La solicitud queda pendiente
            solicitud.rechazado = False
            solicitud.notificada_admin = False
        if commit:
            solicitud.save()
        return solicitud


class MarcarSolicitudRecibidaForm(forms.ModelForm):
    """
    Formulario para que los administradores marquen una solicitud de baja como recibida.
    """
    class Meta:
        model = SolicitudBaja
        fields = []

    def save(self, commit=True):
        """
        Marca la solicitud como notificada al administrador.
        """
        solicitud = super().save(commit=False)
        solicitud.notificada_admin = True
        if commit:
            solicitud.save()
        return solicitud
