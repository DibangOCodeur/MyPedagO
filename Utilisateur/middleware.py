# ========================================
# MIDDLEWARE PERSONNALISÉ (optionnel)
# ========================================
from django.shortcuts import redirect
from django.urls import reverse

class RoleBasedRedirectMiddleware:
    '''
    Middleware qui redirige automatiquement vers le bon dashboard
    après chaque connexion
    '''
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Vérifier si l'utilisateur vient de se connecter
        if request.user.is_authenticated and request.path == reverse('dashboard'):
            # Rediriger vers le dashboard approprié
            role_urls = {
                'ADMIN': 'dashboard_admin',
                'RESP_PEDA': 'dashboard_resp_peda',
                'RESP_RH': 'dashboard_resp_rh',
                'PROFESSEUR': 'dashboard_professeur',
                'INFORMATICIEN': 'dashboard_informaticien',
                'COMPTABLE': 'dashboard_comptable',
                'SERVICE_DATA': 'dashboard_service_data',
            }
            
            dashboard_url = role_urls.get(request.user.role, 'dashboard_default')
            return redirect(dashboard_url)
        
        return None