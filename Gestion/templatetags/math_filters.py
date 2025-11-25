# Gestion/templatetags/math_filters.py
from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Soustrait arg de value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calcule le pourcentage de value par rapport à total"""
    try:
        if total > 0:
            return round((float(value) / float(total)) * 100, 1)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    return dictionary.get(key, 0)