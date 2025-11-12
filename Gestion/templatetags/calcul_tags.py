"""
Template tags pour les calculs dans les templates
À placer dans: Gestion/templatetags/calcul_tags.py (ou Utilisateur/templatetags/)

N'oubliez pas de créer __init__.py dans le dossier templatetags/
"""

from django import template

register = template.Library()


@register.filter
def sum_attr(objects_list, attribute):
    """
    Calcule la somme d'un attribut pour une liste d'objets/dictionnaires
    
    Usage: {{ matieres|sum_attr:'volume_cm' }}
    """
    if not objects_list:
        return 0
    
    total = 0
    for obj in objects_list:
        if isinstance(obj, dict):
            value = obj.get(attribute, 0)
        else:
            value = getattr(obj, attribute, 0)
        
        try:
            total += float(value) if value else 0
        except (ValueError, TypeError):
            continue
    
    return total


@register.filter
def multiply(value, arg):
    """
    Multiplie deux valeurs
    
    Usage: {{ volume_cm|multiply:taux_cm }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def get_item(dictionary, key):
    """
    Récupère un élément d'un dictionnaire
    
    Usage: {{ mydict|get_item:'key' }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None