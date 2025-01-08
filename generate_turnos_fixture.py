# generate_turnos_fixture.py

import json

DIA_SEMANA = [
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
]

HORA_INICIO = 9
HORA_FIN = 20

MAX_INSCRIPCIONES_SUPLENTE = 4  # Puedes ajustar este valor
MAX_INSCRIPCIONES_FIJO = 4     # Para turnos fijos

# Asume que ya tienes usuarios con pk=1 y pk=2 en la base de datos
# Puedes crear estos usuarios manualmente o mediante otra fixture

fixture = []
pk = 1  # Clave primaria inicial

for dia, dia_nombre in DIA_SEMANA:
    for hora in range(HORA_INICIO, HORA_FIN):
        turno = {
            "model": "turnos.turno",
            "pk": pk,
            "fields": {
                "dia": dia,
                "hora": hora,
                "usuario_fijo": None,
                "max_inscripciones": MAX_INSCRIPCIONES_SUPLENTE,
                "es_completo": False
            }
        }
        fixture.append(turno)
        pk += 1


# Guardar la fixture en un archivo JSON
with open('initial_turnos.json', 'w', encoding='utf-8') as f:
    json.dump(fixture, f, ensure_ascii=False, indent=4)

print("Fixture 'initial_turnos.json' creada exitosamente.")
