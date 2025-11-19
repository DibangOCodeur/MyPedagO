from django.urls import path
from django.contrib.auth import views as auth_views
from . import views



urlpatterns = [
    # ========================================
    # Dashboard principal - Redirige automatiquement selon le rôle
    # ========================================
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard'),    
    # Dashboards spécifiques
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='dashboard_admin'),
    path('dashboard/resp-peda/', views.RespPedaDashboardView.as_view(), name='dashboard_resp_peda'),
    path('dashboard/resp-rh/', views.RespRHDashboardView.as_view(), name='dashboard_resp_rh'),
    path('dashboard/professeur/', views.ProfesseurDashboardView.as_view(), name='dashboard_professeur'),
    path('dashboard/informaticien/', views.InformaticienDashboardView.as_view(), name='dashboard_informaticien'),
    path('dashboard/comptable/', views.ComptableDashboardView.as_view(), name='dashboard_comptable'),
    path('dashboard/service-data/', views.ServiceDataDashboardView.as_view(), name='dashboard_service_data'),
    path('dashboard/default/', views.DefaultDashboardView.as_view(), name='dashboard_default'),

    # ========================================
    # PROFIL UTILISATEUR
    # ========================================
    path('profil/', views.mon_profil, name='mon_profil'),
    
    # ========================================
    # SECTIONS
    # ========================================
    path('sections/', views.SectionListView.as_view(), name='section_list'),
    path('sections/<int:pk>/', views.SectionDetailView.as_view(), name='section_detail'),
    path('sections/creer/', views.SectionCreateView.as_view(), name='section_create'),
    path('sections/<int:pk>/modifier/', views.SectionUpdateView.as_view(), name='section_update'),
    path('sections/<int:pk>/supprimer/', views.SectionDeleteView.as_view(), name='section_delete'),
  
    # ==========================================
    # UTILISATEURS
    # ==========================================
    path('utilisateurs/', views.UserListView.as_view(), name='user_list'),
    path('utilisateurs/creer/', views.create_user, name='user_create'),
    path('utilisateurs/<int:pk>/', views.UserCompleteDetailView.as_view(), name='user_detail'),
    path('utilisateurs/<int:pk>/supprimer/', views.UserCompleteDeleteView.as_view(), name='user_delete'),
    
    # Actions AJAX sur utilisateurs
    path('utilisateurs/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('utilisateurs/<int:pk>/changer-mot-de-passe/', views.user_change_password, name='user_change_password'),
    
    
    # ========================================
    # PROFESSEURS
    # ========================================
    path('professeurs/', views.ProfesseurListView.as_view(), name='professeur_list'),
    path('professeurs/<int:pk>/', views.ProfesseurDetailView.as_view(), name='professeur_detail'),
    path('professeurs/<int:pk>/modifier/', views.ProfesseurUpdateView.as_view(), name='professeur_update'),
    path('professeurs/<int:pk>/supprimer/', views.ProfesseurDeleteView.as_view(), name='professeur_delete'),
    path('professeurs/<int:pk>/imprimer/', views.professeur_print_view, name='professeur_print'),



    path('prof/<int:pk>/', views.professeur_detail, name='prof_detail'),
    path('prof/<int:pk>/dossiers/', views.professeur_dossiers, name='prof_dossier'),
    path('prof/<int:pk>/contrats/', views.professeur_contrats, name='prof_contrat'),


    # Actions sur professeurs
    path('professeurs/<int:pk>/toggle-status/', views.professeur_toggle_status, name='professeur_toggle_status'),
    
    # Gestion des documents professeurs
    path('professeurs/<int:professeur_id>/documents/modifier/', 
         views.update_professeur_documents, 
         name='professeur_documents_update'),
    path('professeurs/<int:professeur_id>/documents/<str:document_type>/telecharger/', 
         views.download_professeur_document, 
         name='professeur_document_download'),
    
    # ========================================
    # DOSSIERS PROFESSEURS
    # ========================================

    # ========================================
    # COMPTABLES
    # ========================================
    path('comptables/', views.ComptableListView.as_view(), name='comptable_list'),
    path('comptables/creer/', views.ComptableCreateView.as_view(), name='comptable_create'),
    path('comptables/<int:pk>/', views.ComptableDetailView.as_view(), name='comptable_detail'),
    path('comptables/<int:pk>/modifier/', views.ComptableUpdateView.as_view(), name='comptable_update'),
    path('comptables/<int:pk>/supprimer/', views.ComptableDeleteView.as_view(), name='comptable_delete'),
    
    # Actions sur comptables
    path('comptables/<int:pk>/toggle-status/', views.comptable_toggle_status, name='comptable_toggle_status'),
    
    # Profil comptable    


    
    # ==========================================
    # STATISTIQUES ET RAPPORTS
    # ==========================================
    path('statistiques/', views.StatistiquesView.as_view(), name='statistiques'),
    path('export-data/', views.export_data, name='export_data'),
    
    
    # ==========================================
    # RECHERCHE
    # ==========================================
    path('recherche/', views.recherche_globale, name='recherche_globale'),


    # ========================================
    # URLS DE L'APPLICATION GESTION
    # ========================================
    path('classes/', views.ClasseListView.as_view(), name='classe_list'),
    path('classes/<int:pk>/', views.ClasseDetailView.as_view(), name='classe_detail'),
    path('classes/creer/', views.ClasseCreateView.as_view(), name='classe_create'),
    path('classes/<int:pk>/modifier/', views.ClasseUpdateView.as_view(), name='classe_update'),
    path('classes/<int:pk>/supprimer/', views.ClasseDeleteView.as_view(), name='classe_delete'),
    path('classes/<int:pk>/synchroniser/', views.classe_sync, name='classe_sync'),
    
    # ==========================================
    # MAQUETTES (API)
    # ==========================================
    path('maquettes/', views.MaquetteListView.as_view(), name='maquette_list'),
    path('maquettes/<int:pk>/', views.MaquetteDetailView.as_view(), name='maquette_detail'),
    path('maquettes/<int:pk>/modifier/', views.MaquetteUpdateView.as_view(), name='maquette_update'),
    path('maquette/<int:pk>/matieres/', views.maquette_matieres_view, name='maquette_matieres'),

    path('maquettes/sync/<int:maquette_id>/', views.sync_single_maquette_view, name='sync_single_maquette'),
    path('maquettes/sync/', views.sync_maquettes_view, name='sync_maquettes'),
    
    # ==========================================
    # SYNCHRONISATION API
    # ==========================================
    path('sync/dashboard/', views.SyncDashboardView.as_view(), name='sync_dashboard'),
    path('sync/all/', views.sync_all_api_data, name='sync_all_api_data'),


    path('groupes/', views.liste_groupes, name='liste_groupes'),
    path('api/sync/groupes/', views.sync_groupes, name='sync_groupes'),
    path('api/groupes/statut/', views.get_statut_groupes, name='statut_groupes'),

]




















# ========================================
# EXEMPLE D'UTILISATION DANS LES TEMPLATES
# ========================================

"""
<!-- Dans un template, pour créer des liens selon le rôle : -->

{% if user.role == 'ADMIN' %}
    <a href="{% url 'dashboard_admin' %}">Mon Dashboard Admin</a>
{% elif user.role == 'PROFESSEUR' %}
    <a href="{% url 'dashboard_professeur' %}">Mon Dashboard Professeur</a>
{% elif user.role == 'COMPTABLE' %}
    <a href="{% url 'dashboard_comptable' %}">Mon Dashboard Comptable</a>
{% endif %}

<!-- Lien vers le dashboard automatique (redirige selon le rôle) : -->
<a href="{% url 'dashboard' %}">Tableau de bord</a>
"""

