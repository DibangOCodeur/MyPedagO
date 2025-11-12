"""
Décorateurs de permissions pour l'application Gestion
Vérifie les rôles des utilisateurs avant d'autoriser l'accès aux vues

Rôles disponibles dans CustomUser :
- ADMIN : Administrateur
- RESP_PEDA : Responsable Pédagogique
- RESP_RH : Responsable Ressources Humaines
- PROFESSEUR : Professeur
- INFORMATICIEN : Service Informatique
- COMPTABLE : Comptable
- SERVICE_DATA : Service Data
"""

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps


def role_required(allowed_roles=[]):
    """
    Décorateur pour vérifier le rôle de l'utilisateur
    
    Usage:
        @role_required(['RESP_RH', 'ADMIN'])
        def ma_vue(request):
            # ...
    
    Args:
        allowed_roles: Liste des rôles autorisés (utiliser les valeurs exactes de ROLE_CHOICES)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Vous devez être connecté pour accéder à cette page")
            
            # Vérifier que l'utilisateur est actif
            if not request.user.is_active or not request.user.is_active_user:
                raise PermissionDenied("Votre compte n'est pas actif")
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied(
                    f"Vous n'avez pas les permissions nécessaires. "
                    f"Rôles autorisés : {', '.join(allowed_roles)}"
                )
        
        return _wrapped_view
    return decorator


# ============================================================================
# DÉCORATEURS SPÉCIFIQUES PAR RÔLE
# ============================================================================

def admin_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement aux Administrateurs
    
    Usage:
        @admin_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN'])(view_func)


def resp_peda_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement aux Responsables Pédagogiques
    
    Usage:
        @resp_peda_required
        def ma_vue(request):
            # ...
    """
    return role_required(['RESP_PEDA'])(view_func)


def resp_rh_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement aux Responsables RH
    
    Usage:
        @resp_rh_required
        def ma_vue(request):
            # ...
    """
    return role_required(['RESP_RH'])(view_func)


def professeur_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement aux Professeurs
    
    Usage:
        @professeur_required
        def ma_vue(request):
            # ...
    """
    return role_required(['PROFESSEUR'])(view_func)


def informaticien_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement au Service Informatique
    
    Usage:
        @informaticien_required
        def ma_vue(request):
            # ...
    """
    return role_required(['INFORMATICIEN'])(view_func)


def comptable_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement aux Comptables
    
    Usage:
        @comptable_required
        def ma_vue(request):
            # ...
    """
    return role_required(['COMPTABLE'])(view_func)


def service_data_required(view_func):
    """
    Décorateur pour les vues accessibles uniquement au Service Data
    
    Usage:
        @service_data_required
        def ma_vue(request):
            # ...
    """
    return role_required(['SERVICE_DATA'])(view_func)


# ============================================================================
# DÉCORATEURS COMBINÉS (PLUSIEURS RÔLES)
# ============================================================================

def management_required(view_func):
    """
    Décorateur pour les vues accessibles aux Responsables (Pédagogiques et RH) et Administrateurs
    
    Usage:
        @management_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN', 'RESP_PEDA', 'RESP_RH'])(view_func)


def pedagogie_required(view_func):
    """
    Décorateur pour les vues liées à la pédagogie
    Accessible aux Responsables Pédagogiques, Professeurs et Administrateurs
    
    Usage:
        @pedagogie_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN', 'RESP_PEDA', 'PROFESSEUR'])(view_func)


def rh_management_required(view_func):
    """
    Décorateur pour les vues de gestion RH
    Accessible aux Responsables RH et Administrateurs
    
    Usage:
        @rh_management_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN', 'RESP_RH'])(view_func)


def financial_required(view_func):
    """
    Décorateur pour les vues financières
    Accessible aux Comptables, Responsables RH et Administrateurs
    
    Usage:
        @financial_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN', 'RESP_RH', 'COMPTABLE'])(view_func)


def tech_required(view_func):
    """
    Décorateur pour les vues techniques
    Accessible aux Informaticiens, Service Data et Administrateurs
    
    Usage:
        @tech_required
        def ma_vue(request):
            # ...
    """
    return role_required(['ADMIN', 'INFORMATICIEN', 'SERVICE_DATA'])(view_func)


def staff_required(view_func):
    """
    Décorateur pour les vues accessibles à tout le personnel (sauf professeurs)
    
    Usage:
        @staff_required
        def ma_vue(request):
            # ...
    """
    return role_required([
        'ADMIN',
        'RESP_PEDA',
        'RESP_RH',
        'INFORMATICIEN',
        'COMPTABLE',
        'SERVICE_DATA'
    ])(view_func)


def all_roles_required(view_func):
    """
    Décorateur pour les vues accessibles à tous les rôles authentifiés
    
    Usage:
        @all_roles_required
        def ma_vue(request):
            # ...
    """
    return role_required([
        'ADMIN',
        'RESP_PEDA',
        'RESP_RH',
        'PROFESSEUR',
        'INFORMATICIEN',
        'COMPTABLE',
        'SERVICE_DATA'
    ])(view_func)


# ============================================================================
# DÉCORATEURS POUR LA GESTION DES CONTRATS (SPÉCIFIQUE À L'APP GESTION)
# ============================================================================

def can_create_precontrat(view_func):
    """
    Décorateur pour les vues de création de précontrats
    Accessible aux Responsables Pédagogiques, RH et Administrateurs
    """
    return role_required(['ADMIN', 'RESP_PEDA', 'RESP_RH'])(view_func)


def can_validate_contrat(view_func):
    """
    Décorateur pour les vues de validation de contrats
    Accessible aux Responsables RH et Administrateurs uniquement
    """
    return role_required(['ADMIN', 'RESP_RH'])(view_func)


def can_manage_paiement(view_func):
    """
    Décorateur pour les vues de gestion des paiements
    Accessible aux Comptables, Responsables RH et Administrateurs
    """
    return role_required(['ADMIN', 'RESP_RH', 'COMPTABLE'])(view_func)


def can_view_own_contrat(view_func):
    """
    Décorateur pour les vues où les professeurs peuvent voir leurs propres contrats
    Accessible aux Professeurs et à tout le management
    """
    return role_required(['ADMIN', 'RESP_PEDA', 'RESP_RH', 'PROFESSEUR'])(view_func)


# ============================================================================
# UTILITAIRES DE VÉRIFICATION DE PERMISSIONS
# ============================================================================

def user_has_role(user, roles):
    """
    Vérifie si un utilisateur a l'un des rôles spécifiés
    
    Args:
        user: Instance de l'utilisateur
        roles: Liste des rôles à vérifier
    
    Returns:
        bool: True si l'utilisateur a l'un des rôles
    
    Usage:
        if user_has_role(request.user, ['ADMIN', 'RESP_RH']):
            # faire quelque chose
    """
    if not user.is_authenticated:
        return False
    
    if not user.is_active or not user.is_active_user:
        return False
    
    return user.role in roles


def user_is_admin(user):
    """Vérifie si l'utilisateur est administrateur"""
    return user_has_role(user, ['ADMIN'])


def user_is_management(user):
    """Vérifie si l'utilisateur fait partie du management"""
    return user_has_role(user, ['ADMIN', 'RESP_PEDA', 'RESP_RH'])


def user_is_professeur(user):
    """Vérifie si l'utilisateur est professeur"""
    return user_has_role(user, ['PROFESSEUR'])


def user_can_manage_finances(user):
    """Vérifie si l'utilisateur peut gérer les finances"""
    return user_has_role(user, ['ADMIN', 'RESP_RH', 'COMPTABLE'])


# ============================================================================
# EXEMPLES D'UTILISATION DANS LES VUES
# ============================================================================

"""
# Exemple 1 : Vue accessible uniquement aux administrateurs
@admin_required
def dashboard_admin(request):
    # ...
    pass

# Exemple 2 : Vue accessible aux responsables pédagogiques et administrateurs
@role_required(['ADMIN', 'RESP_PEDA'])
def create_maquette(request):
    # ...
    pass

# Exemple 3 : Vue avec vérification conditionnelle
@can_view_own_contrat
def detail_contrat(request, pk):
    contrat = get_object_or_404(Contrat, pk=pk)
    
    # Si c'est un professeur, il ne peut voir que ses propres contrats
    if user_is_professeur(request.user):
        if contrat.professeur != request.user:
            raise PermissionDenied("Vous ne pouvez voir que vos propres contrats")
    
    # Le management peut tout voir
    return render(request, 'contrat_detail.html', {'contrat': contrat})

# Exemple 4 : Vue accessible à tous les rôles authentifiés
@all_roles_required
def profile(request):
    # ...
    pass

# Exemple 5 : Vérification dans une vue sans décorateur
def ma_vue(request):
    if not user_has_role(request.user, ['ADMIN', 'RESP_RH']):
        raise PermissionDenied("Accès refusé")
    
    # ...
"""