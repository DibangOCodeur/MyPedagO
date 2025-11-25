# Gestion/templatetags/contrat_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplie value par arg"""
    try:
        if isinstance(value, (int, float, Decimal)) and isinstance(arg, (int, float, Decimal)):
            return Decimal(str(value)) * Decimal(str(arg))
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """Soustrait arg de value"""
    try:
        if isinstance(value, (int, float, Decimal)) and isinstance(arg, (int, float, Decimal)):
            return Decimal(str(value)) - Decimal(str(arg))
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def floatformat_currency(value):
    """Formatte un montant pour l'affichage monétaire"""
    try:
        if value is None:
            return "0"
        return f"{float(value):,.0f}".replace(",", " ")
    except (ValueError, TypeError):
        return "0"