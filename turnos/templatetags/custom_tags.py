# turnos/templatetags/custom_tags.py

from django import template

register = template.Library()

@register.filter
def range_filter(value, arg):
    """
    Retorna un rango de números desde 'value' hasta 'arg'.
    Uso: {% for hora in 9|range_filter:19 %}
    """
    try:
        start = int(value)
        end = int(arg)
        return range(start, end)
    except (ValueError, TypeError):
        return []

#añade victor para progreso lineal
@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(part, whole):
    try:
        part = float(part)
        whole = float(whole)
        return (part / whole) * 100 if whole != 0 else 0
    except (ValueError, TypeError):
        return 0