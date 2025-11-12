from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from . import views



urlpatterns = [
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    path(
        '',
        login_required(views.dashboard),
        name='dashboard'
    ),

    # ========================================================================
    # PRÉCONTRATS
    # ========================================================================
    path('precontrats/nouveau/',
         login_required(views.precontrat_create),
         name='precontrat_create'),

    path('precontrats/<int:pk>/',
         views.precontrat_detail,
         name='precontrat_detail'),

    path('precontrat/<uuid:pk>/recapitulatif/',
         views.precontrat_recapitulatif,
         name='precontrat_recapitulatif'),

    # Actions sur les précontrats
    path('precontrat/<uuid:pk>/soumettre/',
         views.precontrat_soumettre,
         name='precontrat_soumettre'),

    path('precontrat/<uuid:pk>/valider/',
         views.precontrat_valider,
         name='precontrat_valider'),

    path('precontrat/<uuid:pk>/rejeter/',
         views.precontrat_rejeter,
         name='precontrat_rejeter'),

    path('precontrats/<int:pk>/soumettre/',
         views.precontrat_submit,
         name='precontrat_submit'),

    path('precontrats/<int:pk>/supprimer/',
         views.precontrat_delete,
         name='precontrat_delete'),

    # ========================================================================
    # MODULES
    # ========================================================================
    path('modules/<int:pk>/valider/',
         views.module_validate,
         name='module_validate'),

    # ========================================================================
    # DOCUMENTS
    # ========================================================================
    path('contrats/<int:contrat_id>/documents/upload/',
         login_required(views.document_upload),
         name='document_upload'),

    # ========================================================================
    # PAIEMENTS
    # ========================================================================
    path('paiements/',
         login_required(views.paiement_list),
         name='paiement_list'),

    path('paiements/<int:pk>/approuver/',
         login_required(views.paiement_approve),
         name='paiement_approve'),

    path('paiements/<int:pk>/executer/',
         login_required(views.paiement_execute),
         name='paiement_execute'),

    # ========================================================================
    # ⭐ API ENDPOINTS (AJAX) - CORRECTION APPLIQUÉE
    # ========================================================================
    # Récupérer les modules d'une classe
    # ✅ Cette URL est correcte et fonctionne
    path('api/classes/<int:classe_id>/modules/',
         views.api_get_classe_modules,
         name='api_get_classe_modules'),

    # Récupérer les maquettes d'une classe
    path('api/maquettes/',
         login_required(views.api_get_maquettes),
         name='api_get_maquettes'),
     
     # Endpoints pour les modules dans le précontrat
     path('precontrat/classes/<int:classe_id>/modules/', views.get_modules_par_classe, name='get_modules_par_classe')
]






# urlpatterns = [
#     # ========================================================================
#     # DASHBOARD
#     # ========================================================================
#     path(
#         '',
#         login_required(views.dashboard),
#         name='dashboard'
#     ),

#     # ========================================================================
#     # PRÉCONTRATS
#     # ========================================================================
#     path('precontrats/nouveau/',
#          login_required(views.precontrat_create),
#          name='precontrat_create'),

#     path('precontrats/<int:pk>/',
#          views.precontrat_detail,
#          name='precontrat_detail'),

#     path('precontrat/<uuid:pk>/recapitulatif/',
#          views.precontrat_recapitulatif,
#          name='precontrat_recapitulatif'),

#     # Actions sur les précontrats
#     path('precontrat/<uuid:pk>/soumettre/',
#          views.precontrat_soumettre,
#          name='precontrat_soumettre'),

#     path('precontrat/<uuid:pk>/valider/',
#          views.precontrat_valider,
#          name='precontrat_valider'),

#     path('precontrat/<uuid:pk>/rejeter/',
#          views.precontrat_rejeter,
#          name='precontrat_rejeter'),

#     path('precontrats/<int:pk>/soumettre/',
#          views.precontrat_submit,
#          name='precontrat_submit'),

#     path('precontrats/<int:pk>/supprimer/',
#          views.precontrat_delete,
#          name='precontrat_delete'),

#     # ========================================================================
#     # MODULES
#     # ========================================================================
#     path('modules/<int:pk>/valider/',
#          views.module_validate,
#          name='module_validate'),

#     # ========================================================================
#     # DOCUMENTS
#     # ========================================================================
#     path('contrats/<int:contrat_id>/documents/upload/',
#          login_required(views.document_upload),
#          name='document_upload'),

#     # ========================================================================
#     # PAIEMENTS
#     # ========================================================================
#     path('paiements/',
#          login_required(views.paiement_list),
#          name='paiement_list'),

#     path('paiements/<int:pk>/approuver/',
#          login_required(views.paiement_approve),
#          name='paiement_approve'),

#     path('paiements/<int:pk>/executer/',
#          login_required(views.paiement_execute),
#          name='paiement_execute'),

#     # ========================================================================
#     # ⭐ API ENDPOINTS (AJAX) - CORRECTION APPLIQUÉE
#     # ========================================================================
#     # Récupérer les modules d'une classe
#     # ✅ Cette URL est correcte et fonctionne
#     path('api/classes/<int:classe_id>/modules/',
#          views.api_get_classe_modules,
#          name='api_get_classe_modules'),

#     # Récupérer les maquettes d'une classe
#     path('api/maquettes/',
#          login_required(views.api_get_maquettes),
#          name='api_get_maquettes'),
     
#      # Endpoints pour les modules dans le précontrat
#      path('precontrat/classes/<int:classe_id>/modules/', views.get_modules_par_classe, name='get_modules_par_classe')
# ]