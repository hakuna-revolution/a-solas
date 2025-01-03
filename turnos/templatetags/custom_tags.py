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
