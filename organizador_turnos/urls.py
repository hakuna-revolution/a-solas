# organizador_turnos/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('turnos.urls', namespace='turnos')),  # Incluye las URLs de la app 'turnos'
]
