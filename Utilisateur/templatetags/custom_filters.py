"""
Template tags personnalisés pour l'application
"""

from django import template

register = template.Library()


@register.filter(name='dict_get')
def dict_get(dictionary, key):
    """
    Permet d'accéder à une valeur d'un dictionnaire avec une clé variable dans un template
    
    Usage dans le template:
        {{ mon_dict|dict_get:ma_cle }}
    
    Args:
        dictionary: Le dictionnaire
        key: La clé à rechercher
        
    Returns:
        La valeur correspondante ou None
    """
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiplie deux valeurs
    
    Usage:
        {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='percentage')
def percentage(value, total):
    """
    Calcule le pourcentage d'une valeur par rapport à un total
    
    Usage:
        {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter(name='format_volume')
def format_volume(value):
    """
    Formate un volume horaire
    
    Usage:
        {{ volume|format_volume }}
    """
    try:
        vol = float(value)
        if vol == 0:
            return "-"
        return f"{vol:.0f}h"
    except (ValueError, TypeError):
        return "-"


@register.filter(name='filter_semestre')
def filter_semestre(items, semestre):
    """
    Filtre les matières/modules par semestre de manière robuste.
    
    Ce filtre est conçu pour fonctionner avec la structure de données
    de MaquetteDetailView où chaque matière est un dictionnaire avec
    une clé 'semestre'.
    
    Usage dans le template:
        {% with semestre_matieres=matieres|filter_semestre:1 %}
        
    Args:
        items: Liste de dictionnaires (matières) ou objets avec attribut semestre
        semestre: Numéro du semestre à filtrer (int ou str)
        
    Returns:
        Liste filtrée contenant uniquement les items du semestre spécifié
    
    Exemples:
        matieres = [
            {'nom': 'Math', 'semestre': 1},
            {'nom': 'Physique', 'semestre': 1},
            {'nom': 'Chimie', 'semestre': 2},
        ]
        
        matieres|filter_semestre:1  → [{'nom': 'Math', ...}, {'nom': 'Physique', ...}]
        matieres|filter_semestre:2  → [{'nom': 'Chimie', ...}]
    """
    # Cas 1: Si items est None ou vide, retourner liste vide
    if not items:
        return []
    
    # Cas 2: Convertir le semestre cible en entier de manière robuste
    try:
        semestre_cible = int(semestre)
    except (ValueError, TypeError):
        # Si la conversion échoue, retourner tous les items sans filtrage
        return list(items) if items else []
    
    # Cas 3: Filtrer les items
    resultats_filtres = []
    
    for item in items:
        # Sous-cas 3a: Si l'item est un dictionnaire (cas le plus courant)
        if isinstance(item, dict):
            # Récupérer la valeur du semestre de l'item
            item_semestre = item.get('semestre')
            
            # Convertir en entier si nécessaire
            if item_semestre is not None:
                try:
                    item_semestre = int(item_semestre)
                except (ValueError, TypeError):
                    # Si conversion échoue, ignorer cet item
                    continue
                
                # Comparer et ajouter si correspond
                if item_semestre == semestre_cible:
                    resultats_filtres.append(item)
        
        # Sous-cas 3b: Si l'item est un objet avec attribut semestre
        elif hasattr(item, 'semestre'):
            try:
                item_semestre = int(item.semestre) if item.semestre is not None else None
                if item_semestre == semestre_cible:
                    resultats_filtres.append(item)
            except (ValueError, TypeError):
                # Ignorer si conversion échoue
                continue
    
    return resultats_filtres


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permet d'accéder à un élément de dictionnaire avec une clé variable
    Alternative à dict_get pour compatibilité
    
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if not dictionary:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None