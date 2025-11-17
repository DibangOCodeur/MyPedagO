from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, FileResponse, Http404
from django.db import transaction
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.utils import timezone
from datetime import timedelta

from django.core.exceptions import ValidationError

from .models import (
    Section, CustomUser, Professeur, Comptable, 
)
from Gestion.models import (
    Classe, Maquette 
)
from .forms import (
    LoginForm, SectionForm, CustomUserCreationWithDocumentsForm,
    ProfesseurForm, ProfesseurUpdateForm, ComptableForm,
    ComptableUpdateForm, UserPasswordChangeForm
)
import logging
logger = logging.getLogger(__name__)


# ==========================================
# MIXINS PERSONNALISÉS
# ==========================================

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin pour restreindre l'accès aux administrateurs"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'ADMIN'
    
    def handle_no_permission(self):
        messages.error(self.request, "Vous n'avez pas les permissions nécessaires.")
        return redirect('dashboard')


class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier les rôles autorisés"""
    allowed_roles = []
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return self.request.user.role in self.allowed_roles
    
    def handle_no_permission(self):
        messages.error(self.request, "Accès non autorisé pour votre rôle.")
        return redirect('dashboard')


class SectionAccessMixin:
    """Mixin pour vérifier l'accès aux sections"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('connexion')
        
        section_id = kwargs.get('section_id')
        if section_id:
            section = get_object_or_404(Section, pk=section_id)
            if not request.user.peut_acceder_section(section):
                messages.error(request, "Vous n'avez pas accès à cette section.")
                return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)


# ==========================================
# VUES D'AUTHENTIFICATION
# ==========================================

@sensitive_post_parameters()
@csrf_protect
@never_cache
def login_view(request):
    """Vue de connexion personnalisée"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_active and user.is_active_user:
                    login(request, user)
                    
                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(2592000)  # 30 jours
                    
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    
                    messages.success(
                        request,
                        f'Bienvenue {user.get_full_name() or user.email} ! '
                        f'Vous êtes connecté en tant que {user.get_role_display()}.'
                    )
                    
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    
                    return redirect('dashboard')
                else:
                    messages.error(
                        request,
                        'Votre compte a été désactivé. Contactez l\'administrateur.'
                    )
            else:
                messages.error(
                    request,
                    'Email ou mot de passe incorrect. Veuillez réessayer.'
                )
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'title': 'Connexion - MyPedago',
    }
    
    return render(request, 'connexion/connexion.html', context)


@login_required
def logout_view(request):
    """Vue de déconnexion"""
    user_name = request.user.get_full_name() or request.user.email
    logout(request)
    messages.success(request, f'Au revoir {user_name} ! Vous avez été déconnecté avec succès.')
    return redirect('connexion')


# ==========================================
# DASHBOARDS PAR RÔLE
# ==========================================

class DashboardRedirectView(LoginRequiredMixin, View):
    """Redirige automatiquement vers le dashboard spécifique selon le rôle"""
    login_url = 'connexion'
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        role_dashboard_mapping = {
            'ADMIN': 'dashboard_admin',
            'RESP_PEDA': 'dashboard_resp_peda',
            'RESP_RH': 'dashboard_resp_rh',
            'PROFESSEUR': 'dashboard_professeur',
            'INFORMATICIEN': 'dashboard_informaticien',
            'COMPTABLE': 'dashboard_comptable',
            'SERVICE_DATA': 'dashboard_service_data',
        }
        
        dashboard_url = role_dashboard_mapping.get(user.role, 'dashboard_default')
        return redirect(dashboard_url)


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour les administrateurs"""
    template_name = 'dashboards/admin.html'
    
    def test_func(self):
        return self.request.user.role == 'ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total_sections': Section.objects.filter(is_active=True).count(),
            'total_professeurs': Professeur.objects.filter(is_active=True).count(),
            'total_comptables': Comptable.objects.filter(is_active=True).count(),
            'total_utilisateurs': CustomUser.objects.filter(is_active=True).count(),
            'sections_inactives': Section.objects.filter(is_active=False).count(),
            'professeurs_inactifs': Professeur.objects.filter(is_active=False).count(),
        }
        
        context['stats_roles'] = list(CustomUser.objects.values('role').annotate(
            total=Count('id'),
            actifs=Count('id', filter=Q(is_active=True, is_active_user=True))
        ).order_by('-total'))
        
        date_limite = timezone.now() - timedelta(days=30)
        context['activites_recentes'] = {
            'nouveaux_professeurs': Professeur.objects.filter(created_at__gte=date_limite).count(),
            'nouveaux_utilisateurs': CustomUser.objects.filter(created_at__gte=date_limite).count(),
        }
        
        context['derniers_utilisateurs'] = CustomUser.objects.select_related(
            'section_principale'
        ).order_by('-created_at')[:5]
        
        context['derniers_professeurs'] = Professeur.objects.select_related(
            'user'
        ).order_by('-created_at')[:5]
        
        context['top_sections'] = Section.objects.filter(
            is_active=True
        ).annotate(
            nb_professeurs=Count('professeurs')
        ).order_by('-nb_professeurs')[:5]
        
        context['alertes'] = {
            'utilisateurs_inactifs': CustomUser.objects.filter(
                is_active_user=False
            ).count(),
        }
        
        return context


class RespPedaDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour les responsables pédagogiques"""
    template_name = 'dashboards/respo.html'
    
    def test_func(self):
        return self.request.user.role == 'RESP_PEDA'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        sections_accessibles = user.get_sections_disponibles()
        context['sections_disponibles'] = sections_accessibles
        
        context['stats_professeurs'] = {
            'total': Professeur.objects.filter(
                sections__in=sections_accessibles
            ).distinct().count(),
            'actifs': Professeur.objects.filter(
                sections__in=sections_accessibles,
                is_active=True
            ).distinct().count(),
            'par_grade': Professeur.objects.filter(
                sections__in=sections_accessibles
            ).values('grade').annotate(count=Count('id')),
            'par_statut': Professeur.objects.filter(
                sections__in=sections_accessibles
            ).values('statut').annotate(count=Count('id')),
        }
        
        context['professeurs_recents'] = Professeur.objects.filter(
            sections__in=sections_accessibles
        ).select_related('user').order_by('-created_at')[:10]
        
        return context


class RespRHDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour les responsables RH"""
    template_name = 'dashboards/rh.html'
    
    def test_func(self):
        return self.request.user.role == 'RESP_RH'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total_professeurs': Professeur.objects.count(),
            'professeurs_actifs': Professeur.objects.filter(is_active=True).count(),
            'total_comptables': Comptable.objects.count(),
            'comptables_actifs': Comptable.objects.filter(is_active=True).count(),
        }
        
        context['stats_statut'] = {
            'titulaires': Professeur.objects.filter(statut='Titulaire').count(),
            'vacataires': Professeur.objects.filter(statut='Vacataire').count(),
        }
        
        date_limite = timezone.now() - timedelta(days=30)
        context['nouveaux_recrutements'] = {
            'professeurs': Professeur.objects.filter(created_at__gte=date_limite),
            'comptables': Comptable.objects.filter(created_at__gte=date_limite),
        }
        
        avg_experience = Professeur.objects.filter(
            is_active=True
        ).aggregate(Avg('annee_experience'))
        context['experience_moyenne'] = avg_experience['annee_experience__avg'] or 0
        
        return context


class ProfesseurDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour les professeurs"""
    template_name = 'dashboards/professeur.html'
    
    def test_func(self):
        return self.request.user.role == 'PROFESSEUR'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            professeur = user.professeur
            context['professeur'] = professeur
            
            context['info'] = {
                'matricule': professeur.matricule,
                'grade': professeur.get_grade_display(),
                'statut': professeur.get_statut_display(),
                'specialite': professeur.specialite,
                'experience': professeur.annee_experience,
                'age': professeur.get_age(),
            }
            
            context['sections_enseignement'] = professeur.sections.filter(is_active=True)
            context['section_active'] = professeur.section_active
            
            context['documents'] = {
                'photo': bool(professeur.photo),
                'cv': bool(professeur.cv_document),
                'cni': bool(professeur.cni_document),
                'diplome': bool(professeur.diplome_document),
                'rib': bool(professeur.rib_document),
            }
            
            total_docs = 5
            docs_presents = sum(context['documents'].values())
            context['completude_percentage'] = (docs_presents / total_docs) * 100
            
            context['notifications'] = []
            if context['completude_percentage'] < 100:
                context['notifications'].append({
                    'type': 'warning',
                    'message': 'Votre dossier est incomplet. Veuillez compléter les documents manquants.'
                })
            
        except Professeur.DoesNotExist:
            context['professeur'] = None
            context['notifications'] = [{
                'type': 'danger',
                'message': 'Aucun profil professeur associé à votre compte.'
            }]
        
        return context


class ComptableDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour les comptables"""
    template_name = 'dashboards/comptable.html'
    
    def test_func(self):
        return self.request.user.role == 'COMPTABLE'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            comptable = user.comptable
            context['comptable'] = comptable
            
            context['info'] = {
                'matricule': comptable.matricule,
                'code_unique': comptable.code_unique,
                'age': comptable.get_age_display(),
                'anciennete': {
                    'jours': comptable.anciennete_jours,
                    'annees': round(comptable.anciennete_annees, 1)
                }
            }
            
            # Le modèle ComptableProfile n'existe pas encore
            context['profile'] = None
            context['profile_complet'] = False
            
            context['stats_accessibles'] = {
                'total_professeurs': Professeur.objects.filter(is_active=True).count(),
                'total_sections': Section.objects.filter(is_active=True).count(),
            }
            
            context['notifications'] = []
            if not context.get('profile_complet', False):
                context['notifications'].append({
                    'type': 'info',
                    'message': 'Complétez votre profil pour plus d\'informations.'
                })
            
        except Comptable.DoesNotExist:
            context['comptable'] = None
            context['notifications'] = [{
                'type': 'danger',
                'message': 'Aucun profil comptable associé à votre compte.'
            }]
        
        return context


class InformaticienDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour le service informatique"""
    template_name = 'dashboards/informaticien.html'
    
    def test_func(self):
        return self.request.user.role == 'INFORMATICIEN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats_systeme'] = {
            'total_utilisateurs': CustomUser.objects.count(),
            'utilisateurs_actifs': CustomUser.objects.filter(
                is_active=True, is_active_user=True
            ).count(),
            'utilisateurs_inactifs': CustomUser.objects.filter(
                Q(is_active=False) | Q(is_active_user=False)
            ).count(),
        }
        
        date_limite = timezone.now() - timedelta(days=7)
        context['activite_recente'] = {
            'connexions': CustomUser.objects.filter(
                last_login__gte=date_limite
            ).count(),
            'nouveaux_comptes': CustomUser.objects.filter(
                created_at__gte=date_limite
            ).count(),
        }
        
        context['utilisateurs_par_role'] = list(CustomUser.objects.values(
            'role'
        ).annotate(count=Count('id')).order_by('-count'))
        
        context['dernieres_connexions'] = CustomUser.objects.filter(
            last_login__isnull=False
        ).order_by('-last_login')[:10]
        
        return context


class ServiceDataDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard pour le service data"""
    template_name = 'dashboards/data.html'
    
    def test_func(self):
        return self.request.user.role == 'SERVICE_DATA'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats_globales'] = {
            'sections': {
                'total': Section.objects.count(),
                'actives': Section.objects.filter(is_active=True).count(),
            },
            'utilisateurs': {
                'total': CustomUser.objects.count(),
                'actifs': CustomUser.objects.filter(is_active=True).count(),
                'par_role': list(CustomUser.objects.values('role').annotate(count=Count('id')))
            },
            'professeurs': {
                'total': Professeur.objects.count(),
                'actifs': Professeur.objects.filter(is_active=True).count(),
                'par_grade': list(Professeur.objects.values('grade').annotate(count=Count('id'))),
                'experience_moyenne': Professeur.objects.aggregate(Avg('annee_experience'))['annee_experience__avg']
            },
            'comptables': {
                'total': Comptable.objects.count(),
                'actifs': Comptable.objects.filter(is_active=True).count(),
            }
        }
        
        context['chart_data'] = {
            'roles': list(CustomUser.objects.values('role').annotate(count=Count('id'))),
            'sections': list(Section.objects.annotate(
                nb_professeurs=Count('professeurs')
            ).values('nom', 'nb_professeurs')),
        }
        
        return context


class DefaultDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard par défaut pour les rôles non spécifiés"""
    template_name = 'dashboards/default.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['user_info'] = {
            'nom': user.get_full_name(),
            'email': user.email,
            'role': user.get_role_display(),
        }
        
        context['sections_disponibles'] = user.get_sections_disponibles()
        
        return context


# ==========================================
# VUES SECTIONS
# ==========================================

class SectionListView(LoginRequiredMixin, ListView):
    """Liste des sections"""
    model = Section
    template_name = 'sections/section_list.html'
    context_object_name = 'sections'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Section.objects.all()
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(adresse__icontains=search) |
                Q(responsable_nom__icontains=search)
            )
        
        return queryset.order_by('nom')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sections'] = Section.objects.count()
        context['sections_actives'] = Section.objects.filter(is_active=True).count()
        return context


class SectionDetailView(LoginRequiredMixin, SectionAccessMixin, DetailView):
    """Détail d'une section"""
    model = Section
    template_name = 'sections/section_detail.html'
    context_object_name = 'section'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section = self.object
        
        context['professeurs'] = section.professeurs.filter(is_active=True)
        context['total_professeurs'] = context['professeurs'].count()
        context['utilisateurs'] = section.users_principaux.filter(is_active=True)
        
        return context


class SectionCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Création d'une section"""
    model = Section
    form_class = SectionForm
    template_name = 'sections/section_form.html'
    success_url = reverse_lazy('section_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Section créée avec succès.')
        return super().form_valid(form)


class SectionUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Modification d'une section"""
    model = Section
    form_class = SectionForm
    template_name = 'sections/section_form.html'
    success_url = reverse_lazy('section_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Section modifiée avec succès.')
        return super().form_valid(form)


class SectionDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Suppression d'une section"""
    model = Section
    template_name = 'sections/section_confirm_delete.html'
    success_url = reverse_lazy('section_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Section supprimée avec succès.')
        return super().delete(request, *args, **kwargs)


# ==========================================
# VUES UTILISATEURS
# ==========================================

class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Liste des utilisateurs"""
    model = CustomUser
    template_name = 'utilisateurs/liste.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CustomUser.objects.all()
        
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True, is_active_user=True)
        elif status == 'inactive':
            queryset = queryset.filter(Q(is_active=False) | Q(is_active_user=False))
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total': CustomUser.objects.count(),
            'actifs': CustomUser.objects.filter(is_active=True, is_active_user=True).count(),
            'inactifs': CustomUser.objects.filter(
                Q(is_active=False) | Q(is_active_user=False)
            ).count(),
        }
        
        context['stats_roles'] = {}
        for role_code, role_name in CustomUser.ROLE_CHOICES:
            context['stats_roles'][role_code] = CustomUser.objects.filter(role=role_code).count()
        
        context['roles'] = CustomUser.ROLE_CHOICES
        context['sections'] = Section.objects.filter(is_active=True)
        
        context['current_role'] = self.request.GET.get('role', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class UserCompleteDetailView(LoginRequiredMixin, DetailView):
    """Vue détaillée d'un utilisateur avec toutes ses informations"""
    model = CustomUser
    template_name = 'utilisateurs/detail.html'
    context_object_name = 'user_detail'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        context['sections_disponibles'] = user.get_sections_disponibles()
        context['sections_autorisees'] = user.sections_autorisees.all()
        
        if user.role == 'PROFESSEUR':
            try:
                professeur = user.professeur
                context['professeur'] = professeur
                context['age'] = professeur.get_age()
                context['sections_enseignement'] = professeur.sections.all()
            except Professeur.DoesNotExist:
                context['professeur'] = None
        
        elif user.role == 'COMPTABLE':
            try:
                comptable = user.comptable
                context['comptable'] = comptable
                context['age'] = comptable.get_age()
                context['anciennete_jours'] = comptable.anciennete_jours
                context['anciennete_annees'] = round(comptable.anciennete_annees, 1)
                
                if hasattr(comptable, 'profile'):
                    context['profile'] = comptable.profile
            except Comptable.DoesNotExist:
                context['comptable'] = None
        
        context['derniere_connexion'] = user.last_login
        context['date_creation'] = user.created_at
        context['derniere_modification'] = user.updated_at
        
        context['peut_modifier'] = (
            self.request.user.role == 'ADMIN' or 
            self.request.user == user
        )
        context['peut_supprimer'] = self.request.user.role == 'ADMIN'
        
        return context


# @login_required
# @permission_required('utilisateurs.add_customuser', raise_exception=True)
# def create_user(request):
#     """Vue pour créer un utilisateur avec documents"""
    
#     if request.method == 'POST':
#         form = CustomUserCreationWithDocumentsForm(request.POST, request.FILES)
        
#         if form.is_valid():
#             try:
#                 with transaction.atomic():
#                     # Sauvegarder l'utilisateur
#                     user = form.save()
#                     role = form.cleaned_data['role']
                    
#                     logger.info(f"Utilisateur créé: {user.email} avec rôle {role}")
                    
#                     if role == 'PROFESSEUR':
#                         # Récupérer les sections d'enseignement
#                         sections_enseignement = form.cleaned_data.get('sections_enseignement')
                        
#                         # Vérification de sécurité
#                         if not sections_enseignement or not sections_enseignement.exists():
#                             raise ValidationError(
#                                 "Au moins une section d'enseignement est requise pour un professeur."
#                             )
                        
#                         # Convertir en liste pour manipulation
#                         sections_list = list(sections_enseignement)
                        
#                         # Déterminer la section active (première section par défaut)
#                         section_active = sections_list[0]
                        
#                         logger.info(
#                             f"Création professeur pour {user.email} avec "
#                             f"{len(sections_list)} sections, active: {section_active}"
#                         )
                        
#                         # Créer le professeur avec tous les champs
#                         professeur = Professeur.objects.create(
#                             user=user,
#                             date_naissance=form.cleaned_data.get('date_naissance_prof'),
#                             grade=form.cleaned_data.get('grade', ''),
#                             statut=form.cleaned_data.get('statut', ''),
#                             genre=form.cleaned_data.get('genre', ''),
#                             nationalite=form.cleaned_data.get('nationalite', ''),
#                             numero_cni=form.cleaned_data.get('numero_cni', ''),
#                             situation_matrimoniale=form.cleaned_data.get('situation_matrimoniale', ''),
#                             domicile=form.cleaned_data.get('domicile', ''),
#                             specialite=form.cleaned_data.get('specialite', ''),
#                             diplome=form.cleaned_data.get('diplome', ''),
#                             annee_experience=form.cleaned_data.get('annee_experience', 0),
#                             section_active=section_active,
#                             photo=form.cleaned_data.get('photo'),
#                             cni_document=form.cleaned_data.get('cni_document'),
#                             rib_document=form.cleaned_data.get('rib_document'),
#                             cv_document=form.cleaned_data.get('cv_document'),
#                             diplome_document=form.cleaned_data.get('diplome_document'),
#                         )
                        
#                         logger.info(f"Professeur créé avec matricule: {professeur.matricule}")
                        
#                         # Assigner les sections d'enseignement (relation ManyToMany)
#                         professeur.sections.set(sections_list)
                        
#                         logger.info(f"Sections assignées: {[s.nom for s in sections_list]}")
                        
#                         messages.success(
#                             request,
#                             f"✓ Le professeur {user.get_full_name()} a été créé avec succès. "
#                             f"Matricule: {professeur.matricule}"
#                         )
                    
#                     elif role == 'COMPTABLE':
#                         comptable = Comptable.objects.create(
#                             user=user,
#                             date_naissance=form.cleaned_data.get('date_naissance_compta')
#                         )
#                         logger.info(f"Comptable créé avec matricule: {comptable.matricule}")
                        
#                         messages.success(
#                             request,
#                             f"✓ Le comptable {user.get_full_name()} a été créé avec succès. "
#                             f"Matricule: {comptable.matricule}"
#                         )
                    
#                     else:
#                         # Autres rôles (ADMIN, RESP_PEDA, etc.)
#                         logger.info(f"Utilisateur {role} créé: {user.email}")
                        
#                         messages.success(
#                             request,
#                             f"✓ L'utilisateur {user.get_full_name()} ({user.get_role_display()}) "
#                             f"a été créé avec succès."
#                         )
                    
#                     return redirect('user_list')
                    
#             except ValidationError as ve:
#                 # Erreurs de validation
#                 logger.error(f"ValidationError lors de la création: {str(ve)}")
#                 messages.error(request, f"❌ Erreur de validation : {str(ve)}")
                
#             except Exception as e:
#                 # Autres erreurs avec plus de détails
#                 import traceback
#                 error_details = traceback.format_exc()
                
#                 logger.error(f"Erreur création utilisateur: {error_details}")
                
#                 messages.error(
#                     request,
#                     f"❌ Une erreur est survenue lors de la création : {str(e)}"
#                 )
#         else:
#             # Afficher les erreurs du formulaire
#             logger.warning(f"Formulaire invalide: {form.errors}")
            
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     if field == '__all__':
#                         messages.error(request, f"❌ {error}")
#                     else:
#                         field_label = form.fields.get(field).label if field in form.fields else field
#                         messages.error(request, f"❌ {field_label}: {error}")
#     else:
#         form = CustomUserCreationWithDocumentsForm()
    
#     context = {
#         'form': form,
#         'title': 'Créer un utilisateur',
#     }
    
#     return render(request, 'utilisateurs/creation.html', context)
@login_required
@permission_required('utilisateurs.add_customuser', raise_exception=True)
def create_user(request):
    """Vue pour créer un utilisateur avec documents"""
    
    if request.method == 'POST':
        form = CustomUserCreationWithDocumentsForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Sauvegarder l'utilisateur
                    user = form.save(commit=False)
                    
                    # Pour les nouveaux utilisateurs, définir un mot de passe par défaut
                    if not user.pk:
                        user.set_password('@elites@')  # Mot de passe par défaut
                    
                    user.save()
                    role = form.cleaned_data['role']
                    
                    logger.info(f"Utilisateur créé: {user.email} avec rôle {role}")
                    
                    if role == 'PROFESSEUR':
                        # Récupérer les sections d'enseignement
                        sections_enseignement = form.cleaned_data.get('sections_enseignement', [])
                        
                        # Vérification de sécurité
                        if not sections_enseignement:
                            raise ValidationError(
                                "Au moins une section d'enseignement est requise pour un professeur."
                            )
                        
                        # Convertir en liste pour manipulation
                        sections_list = list(sections_enseignement)
                        
                        # Déterminer la section active (première section par défaut)
                        section_active = sections_list[0]
                        
                        logger.info(
                            f"Création professeur pour {user.email} avec "
                            f"{len(sections_list)} sections, active: {section_active}"
                        )
                        
                        # Créer le professeur avec tous les champs
                        professeur = Professeur.objects.create(
                            user=user,
                            date_naissance=form.cleaned_data.get('date_naissance_prof'),
                            grade=form.cleaned_data.get('grade', ''),
                            statut=form.cleaned_data.get('statut', ''),
                            genre=form.cleaned_data.get('genre', ''),
                            nationalite=form.cleaned_data.get('nationalite', ''),
                            numero_cni=form.cleaned_data.get('numero_cni', ''),
                            situation_matrimoniale=form.cleaned_data.get('situation_matrimoniale', ''),
                            domicile=form.cleaned_data.get('domicile', ''),
                            specialite=form.cleaned_data.get('specialite', ''),
                            diplome=form.cleaned_data.get('diplome', ''),
                            annee_experience=form.cleaned_data.get('annee_experience', 0),
                            section_active=section_active,
                            photo=form.cleaned_data.get('photo'),
                            cni_document=form.cleaned_data.get('cni_document'),
                            rib_document=form.cleaned_data.get('rib_document'),
                            cv_document=form.cleaned_data.get('cv_document'),
                            diplome_document=form.cleaned_data.get('diplome_document'),
                        )
                        
                        logger.info(f"Professeur créé avec matricule: {professeur.matricule}")
                        
                        # Assigner les sections d'enseignement (relation ManyToMany)
                        professeur.sections.set(sections_list)
                        
                        logger.info(f"Sections assignées: {[s.nom for s in sections_list]}")
                        
                        messages.success(
                            request,
                            f"✓ Le professeur {user.get_full_name()} a été créé avec succès. "
                            f"Matricule: {professeur.matricule}"
                        )
                    
                    elif role == 'COMPTABLE':
                        comptable = Comptable.objects.create(
                            user=user,
                            date_naissance=form.cleaned_data.get('date_naissance_compta')
                        )
                        logger.info(f"Comptable créé avec matricule: {comptable.matricule}")
                        
                        messages.success(
                            request,
                            f"✓ Le comptable {user.get_full_name()} a été créé avec succès. "
                            f"Matricule: {comptable.matricule}"
                        )
                    
                    else:
                        # Autres rôles (ADMIN, RESP_PEDA, etc.)
                        logger.info(f"Utilisateur {role} créé: {user.email}")
                        
                        messages.success(
                            request,
                            f"✓ L'utilisateur {user.get_full_name()} ({user.get_role_display()}) "
                            f"a été créé avec succès."
                        )
                    
                    return redirect('user_list')
                    
            except ValidationError as ve:
                # Erreurs de validation
                logger.error(f"ValidationError lors de la création: {str(ve)}")
                messages.error(request, f"❌ Erreur de validation : {str(ve)}")
                
            except Exception as e:
                # Autres erreurs avec plus de détails
                import traceback
                error_details = traceback.format_exc()
                
                logger.error(f"Erreur création utilisateur: {error_details}")
                
                messages.error(
                    request,
                    f"❌ Une erreur est survenue lors de la création : {str(e)}"
                )
        else:
            # Afficher les erreurs du formulaire de manière plus détaillée
            logger.warning(f"Formulaire invalide: {form.errors}")
            
            # Afficher toutes les erreurs
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_label = form.fields[field].label if field in form.fields else field
                        messages.error(request, f"❌ {field_label}: {error}")
            
            # Debug: logger les données du formulaire
            logger.warning(f"Données POST: {request.POST}")
            logger.warning(f"Fichiers: {request.FILES}")
    else:
        form = CustomUserCreationWithDocumentsForm()
    
    context = {
        'form': form,
        'title': 'Créer un utilisateur',
    }
    
    return render(request, 'utilisateurs/creation.html', context)


class UserCompleteDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Vue de suppression d'un utilisateur avec vérifications"""
    model = CustomUser
    template_name = 'utilisateurs/suppression.html'
    success_url = reverse_lazy('user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        context['has_professeur'] = hasattr(user, 'professeur')
        context['has_comptable'] = hasattr(user, 'comptable')
        
        if context['has_professeur']:
            context['professeur_sections'] = user.professeur.sections.count()
        
        context['warning_message'] = (
            "La suppression de cet utilisateur est définitive et "
            "entraînera la suppression de toutes les données associées."
        )
        
        return context
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user_name = user.get_full_name()
        
        try:
            with transaction.atomic():
                response = super().delete(request, *args, **kwargs)
                messages.success(
                    request,
                    f'Utilisateur {user_name} supprimé avec succès.'
                )
                return response
        
        except Exception as e:
            messages.error(
                request,
                f'Erreur lors de la suppression: {str(e)}'
            )
            return redirect('user_detail', pk=user.pk)


@login_required
def user_toggle_active(request, pk):
    """Basculer le statut actif/inactif d'un utilisateur via AJAX"""
    if request.user.role != 'ADMIN':
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    user = get_object_or_404(CustomUser, pk=pk)
    user.is_active_user = not user.is_active_user
    user.save(update_fields=['is_active_user', 'updated_at'])
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active_user,
        'message': f"Utilisateur {'activé' if user.is_active_user else 'désactivé'} avec succès."
    })


@login_required
def user_change_password(request, pk):
    """Changer le mot de passe d'un utilisateur"""
    user = get_object_or_404(CustomUser, pk=pk)
    
    if request.user.role != 'ADMIN' and request.user != user:
        messages.error(request, "Vous n'avez pas la permission de modifier ce mot de passe.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user.set_password(new_password)
            user.save()
            
            messages.success(request, 'Mot de passe modifié avec succès.')
            return redirect('user_detail', pk=user.pk)
    else:
        form = UserPasswordChangeForm()
    
    context = {
        'form': form,
        'user_detail': user,
        'title': f'Changer le mot de passe de {user.get_full_name()}'
    }
    
    return render(request, 'utilisateurs/changement.html', context)


# ==========================================
# VUES PROFESSEURS
# ==========================================

class ProfesseurListView(LoginRequiredMixin, ListView):
    """Liste des professeurs"""
    model = Professeur
    template_name = 'professeurs/liste.html'
    context_object_name = 'professeurs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Professeur.objects.select_related('user').prefetch_related('sections')
        
        section_id = self.request.GET.get('section')
        if section_id:
            queryset = queryset.filter(sections__id=section_id)
        
        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade=grade)
        
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(matricule__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(specialite__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_professeurs'] = Professeur.objects.count()
        context['professeurs_actifs'] = Professeur.objects.filter(is_active=True).count()
        context['sections'] = Section.objects.filter(is_active=True)
        context['grades'] = Professeur._meta.get_field('grade').choices
        context['statuts'] = Professeur._meta.get_field('statut').choices
        return context


class ProfesseurDetailView(LoginRequiredMixin, DetailView):
    """Détail complet d'un professeur avec toutes ses informations"""
    model = Professeur
    template_name = 'professeurs/detail.html'
    context_object_name = 'professeur'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professeur = self.object
        
        # Informations de base
        context['age'] = professeur.get_age()
        context['sections'] = professeur.sections.all()
        
        # Calcul de la complétude des documents
        documents = {
            'photo': bool(professeur.photo),
            'cni': bool(professeur.cni_document),
            'rib': bool(professeur.rib_document),
            'cv': bool(professeur.cv_document),
            'diplome': bool(professeur.diplome_document),
        }
        
        total_docs = len(documents)
        docs_presents = sum(documents.values())
        context['completude_percentage'] = (docs_presents / total_docs) * 100 if total_docs > 0 else 0
        
        # Documents manquants
        context['missing_documents'] = professeur.get_missing_documents()
        
        # Permissions
        context['peut_modifier'] = (
            self.request.user.role in ['ADMIN', 'RESP_PEDA', 'RESP_RH'] or
            self.request.user == professeur.user
        )
        context['peut_supprimer'] = self.request.user.role == 'ADMIN'
        
        # Statistiques supplémentaires
        context['stats'] = {
            'total_sections': professeur.sections.count(),
            'documents_complets': professeur.has_complete_documents(),
            'anciennete_jours': (timezone.now().date() - professeur.created_at.date()).days if professeur.created_at else 0,
        }
        
        # Alertes et notifications
        context['alertes'] = []
        
        if not professeur.has_complete_documents():
            context['alertes'].append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'message': f'Dossier incomplet : {len(context["missing_documents"])} document(s) manquant(s)'
            })
        
        if not professeur.is_active:
            context['alertes'].append({
                'type': 'danger',
                'icon': 'fa-ban',
                'message': 'Ce professeur est actuellement désactivé'
            })
        
        if not professeur.user.is_active_user:
            context['alertes'].append({
                'type': 'warning',
                'icon': 'fa-user-slash',
                'message': 'Le compte utilisateur est désactivé'
            })
        
        if not professeur.user.last_login:
            context['alertes'].append({
                'type': 'info',
                'icon': 'fa-info-circle',
                'message': 'Ce professeur ne s\'est jamais connecté'
            })
        
        # Historique des modifications
        context['historique'] = {
            'creation': professeur.created_at,
            'derniere_modification': professeur.updated_at,
            'derniere_connexion': professeur.user.last_login,
            'date_embauche': professeur.date_embauche,
        }
        
        # Informations pour les graphiques (si nécessaire)
        if professeur.annee_experience:
            context['experience_data'] = {
                'annees': professeur.annee_experience,
                'pourcentage': min((professeur.annee_experience / 30) * 100, 100)  # Max 30 ans
            }
        
        return context



# Ajouter cette vue dans votre fichier views.py

@login_required
def professeur_print_view(request, pk):
    """Vue pour l'impression de la fiche professeur"""
    professeur = get_object_or_404(Professeur, pk=pk)
    
    # Vérifier les permissions
    if request.user.role not in ['ADMIN', 'RESP_PEDA', 'RESP_RH']:
        if request.user != professeur.user:
            messages.error(request, "Vous n'avez pas les permissions nécessaires.")
            return redirect('professeur_detail', pk=pk)
    
    # Calcul de la complétude des documents
    documents = {
        'photo': bool(professeur.photo),
        'cni': bool(professeur.cni_document),
        'rib': bool(professeur.rib_document),
        'cv': bool(professeur.cv_document),
        'diplome': bool(professeur.diplome_document),
    }
    
    total_docs = len(documents)
    docs_presents = sum(documents.values())
    completude_percentage = (docs_presents / total_docs) * 100 if total_docs > 0 else 0
    
    context = {
        'professeur': professeur,
        'age': professeur.get_age(),
        'sections': professeur.sections.all(),
        'completude_percentage': completude_percentage,
        'missing_documents': professeur.get_missing_documents(),
        'now': timezone.now(),
    }
    
    return render(request, 'professeurs/print.html', context)





class ProfesseurUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Modification d'un professeur"""
    model = Professeur
    form_class = ProfesseurForm
    template_name = 'professeurs/modification.html'
    allowed_roles = ['ADMIN', 'RESP_PEDA', 'RESP_RH']
    
    def get_success_url(self):
        return reverse_lazy('professeur_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Professeur modifié avec succès.')
        return super().form_valid(form)


class ProfesseurDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Suppression d'un professeur"""
    model = Professeur
    template_name = 'professeurs/suppression.html'
    success_url = reverse_lazy('professeur_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Professeur supprimé avec succès.')
        return super().delete(request, *args, **kwargs)


@login_required
def professeur_toggle_status(request, pk):
    """Basculer le statut actif/inactif d'un professeur"""
    if request.user.role not in ['ADMIN', 'RESP_PEDA', 'RESP_RH']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    professeur = get_object_or_404(Professeur, pk=pk)
    professeur.is_active = not professeur.is_active
    professeur.save()
    
    return JsonResponse({
        'success': True,
        'status': professeur.is_active,
        'message': f"Professeur {'activé' if professeur.is_active else 'désactivé'}"
    })


@login_required
@permission_required('utilisateurs.change_professeur', raise_exception=True)
def update_professeur_documents(request, professeur_id):
    """Vue pour mettre à jour les documents d'un professeur"""
    
    professeur = get_object_or_404(Professeur, id=professeur_id)
    
    if request.method == 'POST':
        photo = request.FILES.get('photo')
        cni = request.FILES.get('cni_document')
        rib = request.FILES.get('rib_document')
        cv = request.FILES.get('cv_document')
        diplome = request.FILES.get('diplome_document')
        
        try:
            with transaction.atomic():
                if photo:
                    if professeur.photo:
                        professeur.photo.delete(save=False)
                    professeur.photo = photo
                
                if cni:
                    if professeur.cni_document:
                        professeur.cni_document.delete(save=False)
                    professeur.cni_document = cni
                
                if rib:
                    if professeur.rib_document:
                        professeur.rib_document.delete(save=False)
                    professeur.rib_document = rib
                
                if cv:
                    if professeur.cv_document:
                        professeur.cv_document.delete(save=False)
                    professeur.cv_document = cv
                
                if diplome:
                    if professeur.diplome_document:
                        professeur.diplome_document.delete(save=False)
                    professeur.diplome_document = diplome
                
                professeur.save()
                
                messages.success(request, "Les documents ont été mis à jour avec succès.")
                return redirect('professeur_detail', pk=professeur.id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    context = {
        'professeur': professeur,
        'title': f'Documents de {professeur.user.get_full_name()}',
    }
    
    return render(request, 'utilisateurs/professeur_documents.html', context)


@login_required
def download_professeur_document(request, professeur_id, document_type):
    """Vue pour télécharger un document d'un professeur"""
    
    professeur = get_object_or_404(Professeur, id=professeur_id)
    
    document_map = {
        'photo': professeur.photo,
        'cni': professeur.cni_document,
        'rib': professeur.rib_document,
        'cv': professeur.cv_document,
        'diplome': professeur.diplome_document,
    }
    
    document = document_map.get(document_type)
    
    if not document or not document.name:
        raise Http404("Document non trouvé")
    
    try:
        return FileResponse(
            document.open('rb'),
            as_attachment=True,
            filename=document.name.split('/')[-1]
        )
    except Exception as e:
        messages.error(request, f"Erreur lors du téléchargement: {str(e)}")
        return redirect('professeur_detail', pk=professeur.id)


# ==========================================
# VUES COMPTABLES
# ==========================================

class ComptableListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Liste des comptables"""
    model = Comptable
    template_name = 'comptables/liste.html'
    context_object_name = 'comptables'
    paginate_by = 20
    allowed_roles = ['ADMIN', 'RESP_RH']
    
    def get_queryset(self):
        queryset = Comptable.objects.select_related('user')
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(matricule__icontains=search) |
                Q(code_unique__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statistiques'] = Comptable.statistiques()
        return context


class ComptableDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un comptable"""
    model = Comptable
    template_name = 'comptables/detail.html'
    context_object_name = 'comptable'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comptable = self.object
        
        context['age'] = comptable.get_age()
        context['profile'] = None  # ComptableProfile n'existe pas encore
        context['anciennete'] = {
            'jours': comptable.anciennete_jours,
            'annees': comptable.anciennete_annees
        }
        context['derniere_connexion'] = comptable.get_derniere_connexion()
        
        return context


class ComptableCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Création d'un comptable"""
    model = Comptable
    form_class = ComptableForm
    template_name = 'comptables/creation.html'
    success_url = reverse_lazy('comptable_list')
    
    def form_valid(self, form):
        with transaction.atomic():
            comptable = form.save()            
            messages.success(
                self.request,
                f'Comptable {comptable.get_nom_complet()} créé avec succès.'
            )
        return super().form_valid(form)


class ComptableUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Modification d'un comptable"""
    model = Comptable
    form_class = ComptableForm
    template_name = 'comptables/modification.html'
    allowed_roles = ['ADMIN', 'RESP_RH']
    
    def get_success_url(self):
        return reverse_lazy('comptable_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Comptable modifié avec succès.')
        return super().form_valid(form)


class ComptableDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Suppression d'un comptable"""
    model = Comptable
    template_name = 'comptables/suppression.html'
    success_url = reverse_lazy('comptable_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Comptable supprimé avec succès.')
        return super().delete(request, *args, **kwargs)


@login_required
def comptable_toggle_status(request, pk):
    """Basculer le statut actif/inactif d'un comptable"""
    if request.user.role not in ['ADMIN', 'RESP_RH']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    comptable = get_object_or_404(Comptable, pk=pk)
    comptable.toggle_activation()
    
    return JsonResponse({
        'success': True,
        'status': comptable.is_active,
        'message': f"Comptable {'activé' if comptable.is_active else 'désactivé'}"
    })


# ==========================================
# VUES UTILITAIRES
# ==========================================

@login_required
def recherche_globale(request):
    """Recherche globale dans toute l'application"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    results = []
    
    professeurs = Professeur.objects.filter(
        Q(matricule__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__email__icontains=query)
    )[:5]
    
    for prof in professeurs:
        results.append({
            'type': 'Professeur',
            'titre': prof.user.get_full_name(),
            'sous_titre': prof.matricule,
            'url': reverse('professeur_detail', kwargs={'pk': prof.pk})
        })
    
    comptables = Comptable.objects.filter(
        Q(matricule__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__email__icontains=query)
    )[:5]
    
    for comp in comptables:
        results.append({
            'type': 'Comptable',
            'titre': comp.get_nom_complet(),
            'sous_titre': comp.matricule,
            'url': reverse('comptable_detail', kwargs={'pk': comp.pk})
        })
    
    sections = Section.objects.filter(
        Q(nom__icontains=query) |
        Q(adresse__icontains=query)
    )[:5]
    
    for section in sections:
        results.append({
            'type': 'Section',
            'titre': section.get_nom_display(),
            'sous_titre': section.adresse[:50],
            'url': reverse('section_detail', kwargs={'pk': section.pk})
        })
    
    return JsonResponse({'results': results})


@login_required
def export_data(request):
    """Export des données en JSON"""
    if request.user.role not in ['ADMIN', 'SERVICE_DATA']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    data_type = request.GET.get('type', 'all')
    data = {}
    
    if data_type in ['all', 'professeurs']:
        professeurs = Professeur.objects.select_related('user').values(
            'matricule', 'user__first_name', 'user__last_name',
            'grade', 'statut', 'is_active'
        )
        data['professeurs'] = list(professeurs)
    
    if data_type in ['all', 'comptables']:
        comptables = Comptable.objects.select_related('user').values(
            'matricule', 'code_unique', 'user__first_name',
            'user__last_name', 'is_active'
        )
        data['comptables'] = list(comptables)
    
    if data_type in ['all', 'sections']:
        sections = Section.objects.values('nom', 'adresse', 'is_active')
        data['sections'] = list(sections)
    
    return JsonResponse(data, safe=False)


@login_required
def mon_profil(request):
    """Profil de l'utilisateur connecté"""
    user = request.user
    context = {
        'user': user,
        'sections': user.get_sections_disponibles()
    }
    
    if user.role == 'PROFESSEUR' and hasattr(user, 'professeur'):
        context['professeur'] = user.professeur
    
    elif user.role == 'COMPTABLE' and hasattr(user, 'comptable'):
        context['comptable'] = user.comptable
        context['profile'] = None  # ComptableProfile n'existe pas encore
    
    return render(request, 'users/mon_profil.html', context)


class StatistiquesView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Page de statistiques globales"""
    template_name = 'statistiques/dashboard.html'
    allowed_roles = ['ADMIN', 'RESP_PEDA', 'RESP_RH', 'SERVICE_DATA']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'sections': {
                'total': Section.objects.count(),
                'actives': Section.objects.filter(is_active=True).count()
            },
            'utilisateurs': {
                'total': CustomUser.objects.count(),
                'actifs': CustomUser.objects.filter(is_active=True, is_active_user=True).count(),
                'par_role': list(CustomUser.objects.values('role').annotate(count=Count('id')))
            },
            'professeurs': {
                'total': Professeur.objects.count(),
                'actifs': Professeur.objects.filter(is_active=True).count(),
                'par_grade': list(Professeur.objects.values('grade').annotate(count=Count('id'))),
                'par_statut': list(Professeur.objects.values('statut').annotate(count=Count('id')))
            },
            'comptables': Comptable.statistiques(),
        }
        
        date_limite = timezone.now() - timedelta(days=30)
        context['activites_recentes'] = {
            'nouveaux_professeurs': Professeur.objects.filter(created_at__gte=date_limite).count(),
            'nouveaux_utilisateurs': CustomUser.objects.filter(created_at__gte=date_limite).count(),
        }
        
        return context




#==============================================
# VUES POUR LES APIS
#==============================================
# ==========================================
# VUES CLASSES (API)
# ==========================================

# ==========================================
# VUES CLASSES (API)
# ==========================================

class ClasseListView(LoginRequiredMixin, ListView):
    """Liste des classes synchronisées depuis l'API"""
    model = Classe
    template_name = 'classes/liste.html'
    context_object_name = 'classes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Classe.objects.prefetch_related('maquettes')
        
        # Filtre par section
        section_id = self.request.GET.get('section')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        # Filtre par statut
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filtre par filière
        filiere = self.request.GET.get('filiere')
        if filiere:
            queryset = queryset.filter(filiere__icontains=filiere)
        
        # Filtre par niveau
        niveau = self.request.GET.get('niveau')
        if niveau:
            queryset = queryset.filter(niveau__icontains=niveau)
        
        # Recherche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) |
                Q(description__icontains=search) |
                Q(filiere__icontains=search) |
                Q(niveau__icontains=search)
            )
        
        return queryset.order_by('filiere', 'niveau')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total': Classe.objects.count(),
            'actives': Classe.objects.filter(is_active=True).count(),
            'inactives': Classe.objects.filter(is_active=False).count(),
        }
        
        context['sections'] = Section.objects.filter(is_active=True)
        
        # Liste des filières distinctes
        context['filieres'] = Classe.objects.filter(
            is_active=True
        ).values_list('filiere', flat=True).distinct().order_by('filiere')
        
        # Liste des niveaux distincts
        context['niveaux'] = Classe.objects.filter(
            is_active=True
        ).values_list('niveau', flat=True).distinct().order_by('niveau')
        
        # Classes nécessitant une synchronisation
        from datetime import timedelta
        time_threshold = timezone.now() - timedelta(hours=1)
        context['classes_needs_sync'] = Classe.objects.filter(
            last_synced__lt=time_threshold
        ).count()
        
        return context


# class ClasseDetailView(LoginRequiredMixin, DetailView):
#     """Détail d'une classe avec ses maquettes"""
#     model = Classe
#     template_name = 'classes/detail.html'
#     context_object_name = 'classe'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         classe = self.object
        
#         # Maquettes de la classe
#         context['maquettes'] = classe.maquettes.filter(is_active=True).order_by('niveau_libelle')
#         context['total_maquettes'] = context['maquettes'].count()
        
#         # Statistiques maquettes
#         maquettes = context['maquettes']
#         context['stats_maquettes'] = {
#             'total_ues': sum(m.get_total_ues() for m in maquettes),
#         }
        
#         # Vérifier si sync nécessaire
#         context['needs_sync'] = classe.needs_sync
        
#         # Permissions
#         context['peut_synchroniser'] = self.request.user.role in [
#             'ADMIN', 'RESP_PEDA', 'INFORMATICIEN'
#         ]
        
#         return context

"""
Vue ClasseDetailView modifiée pour afficher les matières des maquettes
À remplacer dans votre fichier views.py
"""

class ClasseDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une classe avec ses maquettes et matières"""
    model = Classe
    template_name = 'classes/detail.html'
    context_object_name = 'classe'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classe = self.object
        
        # Maquettes de la classe
        maquettes = classe.maquettes.filter(is_active=True).order_by('niveau_libelle')
        context['maquettes'] = maquettes
        context['total_maquettes'] = maquettes.count()
        
        # Récupération de TOUTES les matières de TOUTES les maquettes de la classe
        toutes_matieres = []
        total_ues = 0
        total_heures = 0
        total_cout_global = 0
        
        for maquette in maquettes:
            # Récupérer les UEs depuis le champ JSON
            unites_enseignement = maquette.unites_enseignement or []
            total_ues += len(unites_enseignement)
            
            for ue in unites_enseignement:
                ue_libelle = ue.get('libelle', 'UE sans nom')
                ue_code = ue.get('code', '')
                ue_semestre = ue.get('semestre')
                
                matieres = ue.get('matieres', [])
                
                for matiere in matieres:
                    # Récupération des données
                    nom = matiere.get('nom', 'Matière sans nom')
                    code = matiere.get('code', '')
                    
                    # Coefficient/Crédits
                    coefficient = matiere.get('coefficient', 0)
                    try:
                        coefficient = float(coefficient) if coefficient else 0
                    except (ValueError, TypeError):
                        coefficient = 0
                    
                    # Volumes horaires
                    volume_cm = matiere.get('volume_horaire_cm', 0) or 0
                    volume_td = matiere.get('volume_horaire_td', 0) or 0
                    
                    try:
                        volume_cm = float(volume_cm) if volume_cm else 0
                        volume_td = float(volume_td) if volume_td else 0
                    except (ValueError, TypeError):
                        volume_cm = 0
                        volume_td = 0
                    
                    volume_total = volume_cm + volume_td
                    total_heures += volume_total
                    
                    # Taux horaires
                    taux_cm = matiere.get('taux_horaire_cm', 0) or 0
                    taux_td = matiere.get('taux_horaire_td', 0) or 0
                    
                    try:
                        taux_cm = float(taux_cm) if taux_cm else 0
                        taux_td = float(taux_td) if taux_td else 0
                    except (ValueError, TypeError):
                        taux_cm = 0
                        taux_td = 0
                    
                    # Calculs des coûts
                    cout_cm = volume_cm * taux_cm
                    cout_td = volume_td * taux_td
                    montant_total = cout_cm + cout_td
                    total_cout_global += montant_total
                    
                    # Déterminer le semestre
                    semestre = matiere.get('semestre') or ue_semestre
                    
                    # Ajouter à la liste
                    toutes_matieres.append({
                        'id': matiere.get('id', ''),
                        'nom': nom,
                        'code': code,
                        'description': matiere.get('description', nom),
                        'ue_libelle': ue_libelle,
                        'ue_code': ue_code,
                        'maquette_nom': f"{maquette.filiere_sigle} - {maquette.niveau_libelle}",
                        'semestre': semestre,
                        'coefficient': coefficient,
                        'volume_cm': volume_cm,
                        'taux_cm': taux_cm,
                        'cout_cm': cout_cm,
                        'volume_td': volume_td,
                        'taux_td': taux_td,
                        'cout_td': cout_td,
                        'volume_total': volume_total,
                        'montant_total': montant_total,
                    })
        
        # Trier les matières par semestre puis par nom
        toutes_matieres.sort(key=lambda x: (x['semestre'] if x['semestre'] else 999, x['nom']))
        
        # Calculer les totaux pour le tableau
        total_volume_cm = sum(m['volume_cm'] for m in toutes_matieres)
        total_volume_td = sum(m['volume_td'] for m in toutes_matieres)
        total_cout_cm = sum(m['cout_cm'] for m in toutes_matieres)
        total_cout_td = sum(m['cout_td'] for m in toutes_matieres)
        total_coefficient = sum(m['coefficient'] for m in toutes_matieres)
        
        # Ajouter au contexte
        context['matieres'] = toutes_matieres
        context['total_matieres'] = len(toutes_matieres)
        
        # Statistiques maquettes
        context['stats_maquettes'] = {
            'total_ues': total_ues,
            'total_heures': int(total_heures),
            'total_matieres': len(toutes_matieres),
            'cout_total': total_cout_global,
            'total_volume_cm': total_volume_cm,
            'total_volume_td': total_volume_td,
            'total_cout_cm': total_cout_cm,
            'total_cout_td': total_cout_td,
            'total_coefficient': total_coefficient,
        }
        
        # Vérifier si sync nécessaire
        context['needs_sync'] = classe.needs_sync
        
        # Permissions
        context['peut_synchroniser'] = self.request.user.role in [
            'ADMIN', 'RESP_PEDA', 'INFORMATICIEN', 'SERVICE_DATA'
        ]
        
        return context


        
class ClasseCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Création manuelle d'une classe"""
    model = Classe
    template_name = 'classes/form.html'
    allowed_roles = ['ADMIN', 'RESP_PEDA']
    fields = [
        'external_id', 'nom', 'description', 'filiere', 'niveau',
        'departement', 'annee_academique', 'section'
    ]
    success_url = reverse_lazy('classe_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Classe "{form.instance.nom}" créée avec succès.')
        return super().form_valid(form)


class ClasseUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Modification d'une classe"""
    model = Classe
    template_name = 'classes/form.html'
    allowed_roles = ['ADMIN', 'RESP_PEDA']
    fields = [
        'nom', 'description', 'filiere', 'niveau', 'departement',
        'annee_academique', 'section', 'is_active'
    ]
    
    def get_success_url(self):
        return reverse_lazy('classe_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Classe modifiée avec succès.')
        return super().form_valid(form)


class ClasseDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Suppression d'une classe"""
    model = Classe
    template_name = 'classes/confirm_delete.html'
    success_url = reverse_lazy('classe_list')
    
    def delete(self, request, *args, **kwargs):
        classe = self.get_object()
        messages.success(request, f'Classe "{classe.nom}" supprimée avec succès.')
        return super().delete(request, *args, **kwargs)


@login_required
def classe_sync(request, pk):
    """Synchroniser une classe spécifique"""
    if request.user.role not in ['ADMIN', 'RESP_PEDA', 'INFORMATICIEN']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    classe = get_object_or_404(Classe, pk=pk)
    
    try:
        from .services import SyncService
        sync_service = SyncService()
        
        # Re-synchroniser toutes les données
        success, result = sync_service.full_sync(force=True)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Données synchronisées avec succès',
                'result': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Erreur inconnue')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Erreur sync classe {pk}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)



# ================================================
# SYNCHRO DES GROUPES
# ================================================

# Dans views.py - VERSION CORRIGÉE
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .services import GroupeSynchronizationService
from Gestion.models import Groupe, Classe
from django.db.models import Count, Sum
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
@login_required
def sync_groupes(request):
    """Vue pour synchroniser les groupes"""
    try:
        force = request.POST.get('force', 'false') == 'true'
        
        service = GroupeSynchronizationService()
        stats = service.sync_tous_les_groupes(force=force)
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'message': f"Synchronisation terminée: {stats.get('groupes_crees', 0)} créés, {stats.get('groupes_mis_a_jour', 0)} mis à jour"
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur sync groupes: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': "Erreur lors de la synchronisation"
        }, status=500)

@require_GET
@login_required
def get_statut_groupes(request):
    """Vue pour obtenir le statut des groupes"""
    try:
        service = GroupeSynchronizationService()
        statut = service.get_statut_synchronisation()
        
        # Ajouter des statistiques détaillées
        total_classes = Classe.objects.filter(is_active=True).count()
        classes_avec_groupes = Classe.objects.annotate(
            nb_groupes=Count('groupes')
        ).filter(nb_groupes__gt=0)
        
        statut['details'] = {
            'total_classes': total_classes,
            'classes_avec_groupes': classes_avec_groupes.count(),
            'groupes_par_classe': list(
                Groupe.objects.values('classe__nom', 'classe__filiere')
                .annotate(total=Count('id'), effectif=Sum('effectif'))
                .order_by('classe__nom')
            )
        }
        
        return JsonResponse({
            'success': True,
            'statut': statut
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur statut groupes: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def liste_groupes(request):
    """Vue pour lister tous les groupes"""
    groupes = Groupe.objects.select_related('classe').all()
    
    # Statistiques détaillées
    stats = {
        'total': groupes.count(),
        'actifs': groupes.filter(is_active=True).count(),
        'effectif_total': groupes.filter(is_active=True).aggregate(Sum('effectif'))['effectif__sum'] or 0,
        'par_classe': groupes.values('classe__nom', 'classe__filiere')
                      .annotate(total=Count('id'), effectif=Sum('effectif'))
                      .order_by('classe__nom')
    }
    
    context = {
        'groupes': groupes,
        'stats': stats,
        'title': 'Liste des Groupes'
    }
    
    return render(request, 'groupes/liste_groupes.html', context)


# @login_required
# def sync_groupes_only(request):
#     """Synchroniser uniquement les groupes (AJAX)"""
#     if request.user.role not in ['ADMIN', 'INFORMATICIEN']:
#         return JsonResponse({'error': 'Permission refusée'}, status=403)
    
#     try:
#         from .services import SyncService
#         sync_service = SyncService()
        
#         force = request.GET.get('force', 'false').lower() == 'true'
        
#         logger.info(f"🔄 Synchronisation groupes demandée: force={force}")
        
#         success, result = sync_service.sync_groupes(force=force)
        
#         if success:
#             return JsonResponse({
#                 'success': True,
#                 'message': f'Synchronisation des groupes effectuée: {result.get("created", 0)} créés, {result.get("updated", 0)} mis à jour',
#                 'result': result
#             })
#         else:
#             return JsonResponse({
#                 'success': False,
#                 'error': result.get('error', 'Erreur inconnue')
#             }, status=400)
            
#     except Exception as e:
#         logger.error(f"Erreur sync groupes: {e}", exc_info=True)
#         return JsonResponse({
#             'success': False,
#             'error': f"Erreur lors de la synchronisation des groupes: {str(e)}"
#         }, status=500)

@login_required
def sync_all_api_data(request):
    """Synchroniser toutes les données API (AJAX)"""
    if request.user.role not in ['ADMIN', 'INFORMATICIEN']:
        return JsonResponse({'error': 'Permission refusée'}, status=403)
    
    try:
        from .services import SyncService
        sync_service = SyncService()
        
        success, result = sync_service.full_sync(force=True)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Synchronisation complète effectuée avec succès',
                'result': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Erreur inconnue')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Erreur sync complète: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==========================================
# VUES MAQUETTES (API)
# ==========================================

class MaquetteListView(LoginRequiredMixin, ListView):
    """Liste des maquettes"""
    model = Maquette
    template_name = 'maquettes/liste.html'
    context_object_name = 'maquettes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Maquette.objects.select_related('classe')
        
        # Filtre par classe
        classe_id = self.request.GET.get('classe')
        if classe_id:
            queryset = queryset.filter(classe_id=classe_id)
        
        # Filtre par niveau
        niveau = self.request.GET.get('niveau')
        if niveau:
            queryset = queryset.filter(niveau_libelle__icontains=niveau)
        
        # Filtre par statut
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Recherche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(filiere_sigle__icontains=search) |
                Q(filiere_nom__icontains=search) |
                Q(niveau_libelle__icontains=search)
            )
        
        return queryset.order_by('filiere_nom', 'niveau_libelle')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['stats'] = {
            'total': Maquette.objects.count(),
            'actives': Maquette.objects.filter(is_active=True).count(),
        }
        
        context['classes'] = Classe.objects.filter(is_active=True).order_by('nom')
        
        # Niveaux disponibles
        context['niveaux'] = Maquette.objects.filter(
            is_active=True
        ).values_list('niveau_libelle', flat=True).distinct().order_by('niveau_libelle')
        
        return context


class MaquetteDetailView(LoginRequiredMixin, DetailView):
    """
    Vue de détail d'une maquette - VERSION CORRIGÉE pour format API réel
    """
    model = Maquette
    template_name = 'maquettes/detail.html'
    context_object_name = 'maquette'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        maquette = self.object
        
        try:
            # ========================================
            # INFORMATIONS DE BASE
            # ========================================
            
            context['classe'] = maquette.classe
            
            context['autres_maquettes'] = Maquette.objects.filter(
                filiere_nom=maquette.filiere_nom,
                is_active=True
            ).exclude(pk=maquette.pk).order_by('niveau_libelle')[:5]
            
            # Récupérer les UEs depuis le champ JSON
            unites_enseignement = maquette.unites_enseignement or []
            context['total_ues'] = len(unites_enseignement)
            context['unites_enseignement'] = unites_enseignement
            
            # ========================================
            # EXTRACTION DES UEs ET MATIÈRES
            # ========================================
            
            matieres_list = []
            ues_list = []
            semestres_set = set()
            
            # Statistiques globales
            total_coefficient = 0
            total_volume_horaire = 0
            total_volume_cm = 0
            total_volume_td = 0
            total_volume_tp = 0
            total_cout_global = 0
            
            # Parcourir chaque UE
            for ue in unites_enseignement:
                # ========================================
                # EXTRACTION INFOS UE (format API réel)
                # ========================================
                ue_id = ue.get('id', '')
                ue_libelle = ue.get('libelle', 'UE sans nom')
                ue_code = ue.get('code', '')
                
                # CORRECTION: Gérer semestre_id au lieu de semestre
                ue_semestre = ue.get('semestre')
                if not ue_semestre:
                    ue_semestre = ue.get('semestre_id')
                
                # Extraire le numéro du semestre_libelle si nécessaire
                if not ue_semestre and ue.get('semestre_libelle'):
                    semestre_libelle = ue.get('semestre_libelle', '')
                    # Extraire "1" de "SEMESTRE 1"
                    import re
                    match = re.search(r'\d+', semestre_libelle)
                    if match:
                        ue_semestre = int(match.group())
                
                # Crédits
                ue_credits = ue.get('credits', 0)
                try:
                    ue_credits = float(ue_credits) if ue_credits else 0
                except (ValueError, TypeError):
                    ue_credits = 0
                
                # Ajouter le semestre au set
                if ue_semestre:
                    semestres_set.add(ue_semestre)
                
                # ========================================
                # EXTRACTION DES MATIÈRES (si présentes)
                # ========================================
                matieres = ue.get('matieres', [])
                
                # Ajouter l'UE à la liste
                ues_list.append({
                    'id': ue_id,
                    'libelle': ue_libelle,
                    'code': ue_code,
                    'semestre': ue_semestre,
                    'semestre_libelle': ue.get('semestre_libelle', ''),
                    'credits': ue_credits,
                    'nombre_matieres': len(matieres),
                    'categorie': ue.get('categorie_nom', ''),
                })
                
                # Si pas de matières, continuer
                if not matieres:
                    continue
                
                # ========================================
                # TRAITEMENT DES MATIÈRES
                # ========================================
                for matiere in matieres:
                    # Données de base
                    nom = matiere.get('nom', 'Matière sans nom')
                    code = matiere.get('code', '')
                    description = matiere.get('description', '')
                    
                    # Coefficient
                    coefficient = matiere.get('coefficient', 0)
                    try:
                        coefficient = float(coefficient) if coefficient else 0
                    except (ValueError, TypeError):
                        coefficient = 0
                    total_coefficient += coefficient
                    
                    # Volumes horaires
                    volume_cm = matiere.get('volume_horaire_cm', 0) or 0
                    volume_td = matiere.get('volume_horaire_td', 0) or 0
                    volume_tp = matiere.get('volume_horaire_tp', 0) or 0
                    
                    try:
                        volume_cm = float(volume_cm) if volume_cm else 0
                        volume_td = float(volume_td) if volume_td else 0
                        volume_tp = float(volume_tp) if volume_tp else 0
                    except (ValueError, TypeError):
                        volume_cm = 0
                        volume_td = 0
                        volume_tp = 0
                    
                    volume_total = volume_cm + volume_td + volume_tp
                    total_volume_horaire += volume_total
                    total_volume_cm += volume_cm
                    total_volume_td += volume_td
                    total_volume_tp += volume_tp
                    
                    # Taux horaires
                    taux_cm = matiere.get('taux_horaire_cm', 0) or 0
                    taux_td = matiere.get('taux_horaire_td', 0) or 0
                    taux_tp = matiere.get('taux_horaire_tp', 0) or 0
                    
                    try:
                        taux_cm = float(taux_cm) if taux_cm else 0
                        taux_td = float(taux_td) if taux_td else 0
                        taux_tp = float(taux_tp) if taux_tp else 0
                    except (ValueError, TypeError):
                        taux_cm = 0
                        taux_td = 0
                        taux_tp = 0
                    
                    # Calculs des coûts
                    cout_cm = volume_cm * taux_cm
                    cout_td = volume_td * taux_td
                    cout_tp = volume_tp * taux_tp
                    cout_total = cout_cm + cout_td + cout_tp
                    total_cout_global += cout_total
                    
                    # Déterminer le semestre
                    semestre = matiere.get('semestre') or ue_semestre
                    
                    # Professeur
                    professeur = matiere.get('professeur', {})
                    professeur_nom = ''
                    if professeur:
                        if isinstance(professeur, dict):
                            professeur_nom = professeur.get('nom', '')
                        elif isinstance(professeur, str):
                            professeur_nom = professeur
                    
                    # Ajouter la matière
                    matieres_list.append({
                        'id': matiere.get('id', ''),
                        'nom': nom,
                        'code': code,
                        'description': description,
                        'coefficient': coefficient,
                        'ue_libelle': ue_libelle,
                        'ue_code': ue_code,
                        'ue_id': ue_id,
                        'ue_credits': ue_credits,
                        'semestre': semestre,
                        'volume_cm': volume_cm,
                        'taux_cm': taux_cm,
                        'cout_cm': cout_cm,
                        'volume_td': volume_td,
                        'taux_td': taux_td,
                        'cout_td': cout_td,
                        'volume_tp': volume_tp,
                        'taux_tp': taux_tp,
                        'cout_tp': cout_tp,
                        'volume_total': volume_total,
                        'cout_total': cout_total,
                        'professeur_nom': professeur_nom,
                    })
            
            # ========================================
            # TRI ET GROUPEMENT
            # ========================================
            
            # Trier les matières
            matieres_list.sort(key=lambda x: (x['semestre'] if x['semestre'] else 999, x['nom']))
            
            # Semestres uniques
            semestres_uniques = sorted(list(semestres_set))
            
            # Groupement des matières par semestre
            matieres_par_semestre = {}
            for semestre in semestres_uniques:
                matieres_par_semestre[semestre] = [
                    m for m in matieres_list if m['semestre'] == semestre
                ]
            
            # Groupement des UEs par semestre
            ues_par_semestre = {}
            for semestre in semestres_uniques:
                ues_par_semestre[semestre] = [
                    ue for ue in ues_list if ue['semestre'] == semestre
                ]
            
            # ========================================
            # STATISTIQUES PAR SEMESTRE
            # ========================================
            
            stats_par_semestre = []
            for sem in semestres_uniques:
                matieres_sem = matieres_par_semestre.get(sem, [])
                ues_sem = ues_par_semestre.get(sem, [])
                
                stats_par_semestre.append({
                    'semestre': sem,
                    'nombre_ues': len(ues_sem),
                    'nombre_matieres': len(matieres_sem),
                    'credits_total': sum(ue['credits'] for ue in ues_sem),
                    'coefficient_total': sum(m['coefficient'] for m in matieres_sem),
                    'volume_total': sum(m['volume_total'] for m in matieres_sem),
                    'volume_cm': sum(m['volume_cm'] for m in matieres_sem),
                    'volume_td': sum(m['volume_td'] for m in matieres_sem),
                    'volume_tp': sum(m.get('volume_tp', 0) for m in matieres_sem),
                    'cout_total': sum(m['cout_total'] for m in matieres_sem),
                })
            
            # ========================================
            # AJOUT AU CONTEXTE
            # ========================================
            
            context['matieres'] = matieres_list
            context['ues'] = ues_list
            context['matieres_par_semestre'] = matieres_par_semestre
            context['ues_par_semestre'] = ues_par_semestre
            context['total_matieres'] = len(matieres_list)
            
            # Statistiques globales
            context['total_coefficient'] = total_coefficient
            context['total_volume_horaire'] = int(total_volume_horaire)
            context['total_volume_cm'] = total_volume_cm
            context['total_volume_td'] = total_volume_td
            context['total_volume_tp'] = total_volume_tp
            context['total_cout'] = total_cout_global
            
            # Semestres
            context['semestres'] = semestres_uniques
            context['stats_par_semestre'] = stats_par_semestre
            
            # Flags
            context['has_matieres'] = len(matieres_list) > 0
            context['has_ues'] = len(ues_list) > 0
            
            # Log
            logger.info(
                f"Détail maquette {maquette.pk} chargé: "
                f"{len(matieres_list)} matières, "
                f"{len(ues_list)} UEs, "
                f"{len(semestres_uniques)} semestres"
            )
            
        except Exception as e:
            # Gestion des erreurs
            logger.error(f"Erreur chargement détail maquette {maquette.pk}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            messages.error(self.request, f"Erreur lors du chargement: {str(e)}")
            
            # Contexte par défaut
            context['error'] = str(e)
            context['matieres'] = []
            context['ues'] = []
            context['total_matieres'] = 0
            context['total_ues'] = 0
            context['has_matieres'] = False
            context['has_ues'] = False
            context['semestres'] = []
            context['stats_par_semestre'] = []
        
        return context

# ==========================================
# MATIÈRES D'UNE MAQUETTE
# ==========================================

@login_required
def maquette_matieres_view(request, pk):
    """
    Vue dédiée pour afficher toutes les matières d'une maquette
    avec statistiques détaillées et groupement par semestre
    """
    try:
        # Récupérer la maquette
        maquette = get_object_or_404(Maquette, pk=pk)
        
        # Récupérer les UEs depuis le champ JSON
        unites_enseignement = maquette.unites_enseignement or []
        
        # Construction de la liste des matières avec informations complètes
        matieres_list = []
        
        for ue in unites_enseignement:
            ue_libelle = ue.get('libelle', 'UE sans nom')
            ue_code = ue.get('code', '')
            ue_id = ue.get('id', '')
            ue_semestre = ue.get('semestre')
            
            matieres = ue.get('matieres', [])
            
            for matiere in matieres:
                # Récupération des données
                nom = matiere.get('nom', 'Matière sans nom')
                code = matiere.get('code', '')
                coefficient = matiere.get('coefficient', 0)
                
                # Volumes horaires
                volume_cm = matiere.get('volume_horaire_cm', 0) or 0
                volume_td = matiere.get('volume_horaire_td', 0) or 0
                
                # S'assurer que ce sont des nombres
                try:
                    volume_cm = float(volume_cm) if volume_cm else 0
                    volume_td = float(volume_td) if volume_td else 0
                    coefficient = float(coefficient) if coefficient else 0
                except (ValueError, TypeError):
                    volume_cm = 0
                    volume_td = 0
                    coefficient = 0
                
                volume_total = volume_cm + volume_td
                
                # Taux horaires
                taux_cm = matiere.get('taux_horaire_cm', 0) or 0
                taux_td = matiere.get('taux_horaire_td', 0) or 0
                
                try:
                    taux_cm = float(taux_cm) if taux_cm else 0
                    taux_td = float(taux_td) if taux_td else 0
                except (ValueError, TypeError):
                    taux_cm = 0
                    taux_td = 0
                
                # Calcul du coût total
                total_taux = (volume_cm * taux_cm) + (volume_td * taux_td)
                
                # Déterminer le semestre
                semestre = matiere.get('semestre') or ue_semestre
                
                matieres_list.append({
                    'id': matiere.get('id', ''),
                    'nom': nom,
                    'code': code,
                    'description': matiere.get('description', ''),
                    'coefficient': coefficient,
                    'ue_libelle': ue_libelle,
                    'ue_code': ue_code,
                    'ue_id': ue_id,
                    'semestre': semestre,
                    'volume_horaire_cm': volume_cm,
                    'taux_horaire_cm': taux_cm,
                    'volume_horaire_td': volume_td,
                    'taux_horaire_td': taux_td,
                    'volume_horaire_total': volume_total,
                    'total_taux_horaire': total_taux,
                })
        
        # Trier par semestre puis par nom de matière
        matieres_list.sort(key=lambda x: (x['semestre'] if x['semestre'] else 999, x['nom']))
        
        # Calcul des statistiques globales
        total_coefficient = sum(m['coefficient'] for m in matieres_list)
        total_volume_horaire = sum(m['volume_horaire_total'] for m in matieres_list)
        total_volume_cm = sum(m['volume_horaire_cm'] for m in matieres_list)
        total_volume_td = sum(m['volume_horaire_td'] for m in matieres_list)
        total_cout = sum(m['total_taux_horaire'] for m in matieres_list)
        
        # Récupération des semestres uniques
        semestres_uniques = sorted(list(set(
            m['semestre'] for m in matieres_list if m['semestre']
        )))
        
        # Groupement des matières par semestre
        matieres_par_semestre = {}
        for semestre in semestres_uniques:
            matieres_par_semestre[semestre] = [
                m for m in matieres_list if m['semestre'] == semestre
            ]
        
        # Statistiques par semestre
        stats_par_semestre = []
        for sem in semestres_uniques:
            matieres_sem = matieres_par_semestre[sem]
            stats_par_semestre.append({
                'semestre': sem,
                'nombre_matieres': len(matieres_sem),
                'coefficient_total': sum(m['coefficient'] for m in matieres_sem),
                'volume_total': sum(m['volume_horaire_total'] for m in matieres_sem),
                'volume_cm': sum(m['volume_horaire_cm'] for m in matieres_sem),
                'volume_td': sum(m['volume_horaire_td'] for m in matieres_sem),
                'cout_total': sum(m['total_taux_horaire'] for m in matieres_sem),
            })
        
        # Préparation du contexte
        context = {
            'maquette': maquette,
            'maquette_id': pk,
            'matieres': matieres_list,
            'matieres_par_semestre': matieres_par_semestre,
            'total_ues': len(unites_enseignement),
            'total_matieres': len(matieres_list),
            'total_coefficient': total_coefficient,
            'total_volume_horaire': total_volume_horaire,
            'total_volume_cm': total_volume_cm,
            'total_volume_td': total_volume_td,
            'total_cout': total_cout,
            'semestres': semestres_uniques,
            'stats_par_semestre': stats_par_semestre,
            'has_matieres': len(matieres_list) > 0,
        }
        
        logger.info(
            f"Matières chargées pour maquette {pk}: "
            f"{len(matieres_list)} matières, "
            f"{len(semestres_uniques)} semestres"
        )
        
        return render(request, 'maquettes/matieres.html', context)
        
    except Maquette.DoesNotExist:
        logger.error(f"Maquette {pk} introuvable")
        messages.error(request, f"La maquette avec l'ID {pk} n'existe pas.")
        return redirect('maquette_list')
        
    except Exception as e:
        logger.error(f"Erreur chargement matières: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('maquette_detail', pk=pk)


# ==========================================
# MODIFICATION D'UNE MAQUETTE
# ==========================================

class MaquetteUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Modification d'une maquette (réservé aux admins et resp pédagogiques)"""
    model = Maquette
    template_name = 'gestion/maquettes/form.html'
    allowed_roles = ['ADMIN', 'RESP_PEDA']
    fields = [
        'filiere_nom', 'filiere_sigle', 'niveau_libelle',
        'parcour', 'annee_academique', 'is_active'
    ]
    
    def get_success_url(self):
        return reverse_lazy('maquette_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Maquette modifiée avec succès.')
        return super().form_valid(form)


# ==========================================
# SYNCHRONISATION API
# ==========================================

@login_required
def sync_maquettes_view(request):
    """Vue pour déclencher la synchronisation des maquettes depuis l'API"""
    
    # Vérifier les permissions
    if request.user.role not in ['ADMIN', 'SERVICE_DATA']:
        messages.error(request, "Vous n'avez pas la permission de synchroniser.")
        return redirect('maquette_list')
    
    try:
        from Utilisateur.services import SyncService
        
        force = request.GET.get('force', 'false').lower() == 'true'
        
        sync_service = SyncService()
        success, result = sync_service.sync_maquettes(force=force)
        
        if success:
            messages.success(
                request,
                f"✅ Synchronisation réussie: "
                f"{result['created']} créées, "
                f"{result['updated']} mises à jour"
            )
        else:
            messages.error(
                request,
                f"❌ Erreur de synchronisation: {result.get('error', 'Erreur inconnue')}"
            )
    
    except Exception as e:
        logger.error(f"Erreur synchronisation: {str(e)}")
        messages.error(request, f"Erreur: {str(e)}")
    
    return redirect('maquette_list')







@login_required
def sync_single_maquette_view(request, maquette_id):
    """
    Synchronise une seule maquette par son external_id
    URL: /gestion/maquettes/sync/<int:maquette_id>/
    
    Args:
        maquette_id: external_id de la maquette dans l'API (pas le pk Django)
    """
    
    # Vérifier les permissions
    if request.user.role not in ['ADMIN', 'SERVICE_DATA', 'INFORMATICIEN']:
        messages.error(request, "Vous n'avez pas la permission de synchroniser.")
        return redirect('maquette_list')
    
    try:
        sync_service = SyncService()
        
        # Trouver la maquette par son external_id
        try:
            maquette = Maquette.objects.get(external_id=maquette_id)
        except Maquette.DoesNotExist:
            messages.error(request, f"Maquette avec l'ID externe {maquette_id} introuvable.")
            return redirect('maquette_list')
        
        # Synchroniser les UEs de cette maquette
        logger.info(f"Synchronisation de la maquette {maquette_id} (pk: {maquette.pk})")
        success = sync_service._sync_maquette_ues(maquette, force=True)
        
        if success:
            # Compter les UEs et matières
            ues_count = len(maquette.unites_enseignement or [])
            matieres_count = sum(
                len(ue.get('matieres', [])) 
                for ue in (maquette.unites_enseignement or [])
            )
            
            messages.success(
                request,
                f"✅ Maquette synchronisée avec succès: "
                f"{ues_count} UEs, {matieres_count} matières"
            )
            # Rediriger vers le détail de la maquette
            return redirect('maquette_detail', pk=maquette.pk)
        else:
            messages.error(request, "❌ Erreur lors de la synchronisation des UEs")
            return redirect('maquette_detail', pk=maquette.pk)
    
    except Exception as e:
        logger.error(f"Erreur synchronisation maquette {maquette_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('maquette_list')


# ==========================================
# VUE DASHBOARD SYNCHRONISATION
# ==========================================

class SyncDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Dashboard de synchronisation des données API"""
    template_name = 'sync/dashboard.html'
    allowed_roles = ['ADMIN', 'INFORMATICIEN', 'RESP_PEDA']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques globales
        context['stats'] = {
            'classes': {
                'total': Classe.objects.count(),
                'actives': Classe.objects.filter(is_active=True).count(),
                'needs_sync': Classe.objects.filter(
                    last_synced__lt=timezone.now() - timedelta(hours=1)
                ).count(),
            },
            'maquettes': {
                'total': Maquette.objects.count(),
                'actives': Maquette.objects.filter(is_active=True).count(),
            }
        }
        
        # Dernières synchronisations
        context['dernieres_syncs'] = {
            'classes': Classe.objects.order_by('-last_synced')[:5],
            'maquettes': Maquette.objects.order_by('-last_synced')[:5],
        }
        
        # Classes nécessitant une synchronisation
        context['classes_needs_sync'] = Classe.objects.filter(
            last_synced__lt=timezone.now() - timedelta(hours=1)
        ).order_by('last_synced')[:10]
        
        return context