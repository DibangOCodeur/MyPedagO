from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Récupère un élément d'un dictionnaire par sa clé
    Usage: {{ mydict|get_item:key }}
    
    Exemple:
    {% for semestre in semestres %}
        {{ matieres_par_semestre|get_item:semestre }}
    {% endfor %}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def multiply(value, arg):
    """
    Multiplie deux valeurs
    Usage: {{ value|multiply:arg }}
    
    Exemple:
    {{ volume_cm|multiply:taux_cm }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calcule le pourcentage
    Usage: {{ value|percentage:total }}
    
    Exemple:
    {{ matiere_count|percentage:total_matieres }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.simple_tag
def calculate_cost(volume_cm, taux_cm, volume_td, taux_td):
    """
    Calcule le coût total: (volume_cm * taux_cm) + (volume_td * taux_td)
    Usage: {% calculate_cost volume_cm taux_cm volume_td taux_td %}
    
    Exemple:
    {% calculate_cost matiere.volume_cm matiere.taux_cm matiere.volume_td matiere.taux_td %}
    """
    try:
        cm_cost = float(volume_cm or 0) * float(taux_cm or 0)
        td_cost = float(volume_td or 0) * float(taux_td or 0)
        return cm_cost + td_cost
    except (ValueError, TypeError):
        return 0


@register.filter
def format_number(value, decimals=0):
    """
    Formate un nombre avec séparateur de milliers
    Usage: {{ number|format_number:2 }}
    
    Exemple:
    {{ 1234567.89|format_number:2 }} affiche 1 234 567,89
    """
    try:
        if value is None:
            return "0"
        value = float(value)
        if decimals == 0:
            formatted = f"{value:,.0f}".replace(",", " ")
        else:
            formatted = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
        return formatted
    except (ValueError, TypeError):
        return "0"


@register.filter
def safe_int(value):
    """
    Convertit une valeur en entier de manière sécurisée
    Usage: {{ value|safe_int }}
    """
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


@register.filter
def safe_float(value):
    """
    Convertit une valeur en float de manière sécurisée
    Usage: {{ value|safe_float }}
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


@register.filter
def dict_length(value):
    """
    Retourne la longueur d'un dictionnaire
    Usage: {{ mydict|dict_length }}
    """
    if isinstance(value, dict):
        return len(value)
    return 0