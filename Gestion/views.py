from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from decimal import Decimal
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage  # ⭐ AJOUTEZ CETTE LIGNE
# Ajoutez cette ligne dans vos imports
from .forms import PreContratCreateForm, ContratStartForm, PointageForm
import json
import logging

from .models import (
    PreContrat, ModulePropose, Contrat, Pointage,
    PaiementContrat, ActionLog, Classe, Maquette, Groupe  
)
from .permissions import (
    role_required,
)
from .utils import generate_recu_paiement_pdf
from django.db import transaction
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)                                                    

# ==========================================
# FONCTION UTILITAIRE POUR EXTRAIRE LES MODULES
# ==========================================

# ==========================================
# FONCTION UNIFIÉE POUR EXTRAIRE LES MODULES
# ==========================================

def find_module_in_maquettes(maquettes, module_id):
    """
    ⭐ FONCTION UNIFIÉE ET CORRIGÉE ⭐
    Trouve un module dans les données des maquettes avec gestion robuste des données
    
    Args:
        maquettes: QuerySet de Maquette
        module_id: ID du module à rechercher (string ou int)
        
    Returns:
        dict: Données du module ou None si non trouvé
    """
    logger.debug(f"🔍 Recherche du module {module_id} dans {maquettes.count()} maquette(s)")
    
    for maquette in maquettes:
        # Les UE sont stockées dans le champ JSON unites_enseignement
        ues = maquette.unites_enseignement or []
        
        for ue in ues:
            # Parcourir les matières de chaque UE
            matieres = ue.get('matieres', [])
            
            for matiere in matieres:
                # ⭐ CORRECTION : Comparaison robuste des IDs (string vs int)
                matiere_id = str(matiere.get('id', ''))
                module_id_str = str(module_id)
                
                if matiere_id == module_id_str:
                    logger.info(f"✅ Module trouvé: {matiere.get('nom', 'Sans nom')}")
                    
                    # ⭐ GESTION ROBUSTE DES VOLUMES HORAIRES
                    def safe_float(value, default=0.0):
                        """Convertit en float de manière sécurisée"""
                        try:
                            if value is None or value == '':
                                return default
                            return float(value)
                        except (TypeError, ValueError):
                            return default
                    
                    # Récupération des volumes avec valeurs par défaut intelligentes
                    volume_cm = safe_float(matiere.get('volume_horaire_cm'), 20.0)
                    volume_td = safe_float(matiere.get('volume_horaire_td'), 20.0)
                    
                    # ⭐ CORRECTION CRITIQUE : Si tous les volumes sont à 0, on met des valeurs par défaut
                    if volume_cm <= 0 and volume_td <= 0:
                        logger.warning(f"⚠️ Module {module_id} a tous les volumes à 0, utilisation de valeurs par défaut")
                        volume_cm = 20.0
                        volume_td = 20.0
                    
                    # ⭐ GESTION ROBUSTE DES TAUX HORAIRES
                    taux_cm = safe_float(matiere.get('taux_horaire_cm'), 5000.0)
                    taux_td = safe_float(matiere.get('taux_horaire_td'), 5000.0)
                    
                    # ⭐ VÉRIFICATION : Si volume > 0 mais taux = 0, on corrige
                    if volume_cm > 0 and taux_cm <= 0:
                        logger.warning(f"⚠️ Module {module_id}: Volume CM > 0 mais taux CM = 0, correction à 5000")
                        taux_cm = 5000.0
                    
                    if volume_td > 0 and taux_td <= 0:
                        logger.warning(f"⚠️ Module {module_id}: Volume TD > 0 mais taux TD = 0, correction à 5000")
                        taux_td = 5000.0
                    
                    # Données du module trouvé
                    module_data = {
                        'id': matiere.get('id'),
                        'code': matiere.get('code', f'MOD_{module_id}'),
                        'nom': matiere.get('nom', 'Module sans nom'),
                        'ue_nom': ue.get('libelle', 'UE non spécifiée'),
                        'volume_horaire_cm': volume_cm,
                        'volume_horaire_td': volume_td,
                        'taux_horaire_cm': taux_cm,
                        'taux_horaire_td': taux_td,
                    }
                    
                    logger.debug(f"📊 Données module: {module_data}")
                    return module_data
    
    logger.warning(f"❌ Module {module_id} non trouvé dans les maquettes")
    return None

# ==========================================
# NOUVEL ENDPOINT API - RÉCUPÉRATION DES MODULES
# ==========================================

@login_required
@require_http_methods(["GET"])
def api_get_classe_modules(request, classe_id):
    """
    ⭐ NOUVEAU ENDPOINT ⭐
    Récupère les modules disponibles pour une classe donnée
    
    URL: /api/classes/<id>/modules/
    
    Returns:
        JSON avec la liste des modules de la maquette
    """
    try:
        # Récupérer la classe
        classe = get_object_or_404(Classe, pk=classe_id)
        
        # Récupérer les maquettes actives de cette classe
        maquettes = Maquette.objects.filter(
            classe=classe,
            is_active=True
        )
        
        if not maquettes.exists():
            return JsonResponse({
                'success': False,
                'error': 'Aucune maquette trouvée pour cette classe',
                'modules': []
            })
        
        # Extraire tous les modules de toutes les UEs
        modules = []
        
        for maquette in maquettes:
            # Les UE sont stockées dans le champ JSON unites_enseignement
            ues = maquette.unites_enseignement or []
            
            for ue in ues:
                # Parcourir les matières de chaque UE
                matieres = ue.get('matieres', [])
                
                for matiere in matieres:
                    module = {
                        'id': matiere.get('id'),
                        'code': matiere.get('code', ''),
                        'nom': matiere.get('libelle', ''),
                        'ue_nom': ue.get('nom', ''),
                        'volume_cm': float(matiere.get('volume_horaire_cm', 5)),
                        'volume_td': float(matiere.get('volume_horaire_td', 5)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 5000)),
                        'taux_td': float(matiere.get('taux_horaire_td', 5000)),
                    }
                    modules.append(module)
        
        return JsonResponse({
            'success': True,
            'modules': modules,
            'count': len(modules)
        })
        
    except Classe.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Classe non trouvée',
            'modules': []
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'modules': []
        }, status=500)


# ==========================================
# VUE DE CRÉATION D'UN PRÉCONTRAT (CORRIGÉE)
# ==========================================

@login_required
@require_http_methods(["GET", "POST"])
def precontrat_create(request):
    """
    Vue corrigée pour la création de précontrat
    """
    context = {
        'title': 'Créer un précontrat',
        'active_page': 'precontrats'
    }
    
    if request.method == 'POST':
        form = PreContratCreateForm(request.POST)
        
        # Debug logging
        logger.info("🔄 Tentative de création de précontrat")
        logger.debug(f"Données POST: {dict(request.POST)}")
        logger.debug(f"Utilisateur: {request.user}")
        
        if form.is_valid():
            logger.info("✅ Formulaire valide, traitement des données...")
            
            try:
                # Récupérer les données nettoyées
                professeur = form.cleaned_data['professeur']
                classe = form.cleaned_data['classe']

                # Log des instances récupérées
                logger.info(f"📋 Professeur: {professeur} (ID: {professeur.id})")
                logger.info(f"📋 Classe: {classe} (ID: {classe.id})")
                
                # Récupérer les modules sélectionnés
                selected_modules_json = request.POST.get('selected_modules', '[]')
                try:
                    selected_modules_ids = json.loads(selected_modules_json)
                    logger.info(f"📦 Modules sélectionnés: {len(selected_modules_ids)}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Erreur décodage JSON: {e}")
                    messages.error(request, "Erreur dans la sélection des modules")
                    context['form'] = form
                    return render(request, 'contrats/precontrats/creation.html', context)
                
                # Validation des modules
                if not selected_modules_ids:
                    messages.error(request, "❌ Veuillez sélectionner au moins un module")
                    context['form'] = form
                    return render(request, 'contrats/precontrats/creation.html', context)
                
                # CRÉATION EN TRANSACTION
                with transaction.atomic():
                    # Création du précontrat
                    precontrat = PreContrat(
                        professeur=professeur,
                        classe=classe,
                        cree_par=request.user,
                        status='DRAFT',
                    )
                    
                    # Validation et sauvegarde
                    precontrat.full_clean()
                    precontrat.save()
                    logger.info(f"✅ Précontrat créé: {precontrat.id}")
                    
                    # Récupération des maquettes
                    maquettes = Maquette.objects.filter(
                        classe=classe,
                        is_active=True
                    )
                    
                    logger.info(f"🔍 Maquettes trouvées: {maquettes.count()}")
                    
                    # Création des modules proposés
                    modules_crees = 0
                    modules_errors = []
                    
                    # Dans la boucle de création des modules
                    # Dans la boucle de création des modules
                    for module_id in selected_modules_ids:
                        try:
                            module_data = find_module_in_maquettes(maquettes, module_id)
                            
                            if module_data:
                                # ⭐ LOGS DÉTAILLÉS POUR LES VOLUMES ET TAUX
                                logger.info(f"📊 Module {module_id}:")
                                logger.info(f"   Volumes: CM={module_data.get('volume_horaire_cm')}, TD={module_data.get('volume_horaire_td')}")
                                logger.info(f"   Taux: CM={module_data.get('taux_horaire_cm')}, TD={module_data.get('taux_horaire_td')}")
                                
                                # Conversion sécurisée des Decimal
                                def safe_decimal(value, default=0):
                                    try:
                                        return Decimal(str(value)) if value is not None else Decimal(default)
                                    except (TypeError, ValueError):
                                        return Decimal(default)
                                
                                # Récupérer les valeurs
                                volume_cm = safe_decimal(module_data.get('volume_horaire_cm'))
                                volume_td = safe_decimal(module_data.get('volume_horaire_td'))
                                taux_cm = safe_decimal(module_data.get('taux_horaire_cm'))
                                taux_td = safe_decimal(module_data.get('taux_horaire_td'))
                                
                                # ⭐ VÉRIFICATION FINALE DES TAUX
                                if volume_td > 0 and taux_td <= 0:
                                    logger.warning(f"⚠️ Module {module_id}: Volume TD > 0 mais taux TD = 0, correction automatique")
                                    taux_td = Decimal('5000')
                                
                                if volume_cm > 0 and taux_cm <= 0:
                                    logger.warning(f"⚠️ Module {module_id}: Volume CM > 0 mais taux CM = 0, correction automatique")
                                    taux_cm = Decimal('5000')
                                
                                # Vérification finale des volumes
                                if volume_cm <= 0 and volume_td <= 0:
                                    logger.warning(f"⚠️ Module {module_id} a tous les volumes à 0, utilisation de valeurs par défaut")
                                    volume_cm = Decimal('20')
                                    volume_td = Decimal('20')
                                
                                # Création du module
                                ModulePropose.objects.create(
                                    pre_contrat=precontrat,
                                    code_module=module_data.get('id', f'MOD_{module_id}'),
                                    nom_module=module_data.get('nom', 'Module sans nom'),
                                    ue_nom=module_data.get('ue_nom', 'UE non spécifiée'),
                                    volume_heure_cours=volume_cm,
                                    volume_heure_td=volume_td,
                                    taux_horaire_cours=taux_cm,
                                    taux_horaire_td=taux_td,
                                    est_valide=False,
                                )
                                modules_crees += 1
                                logger.info(f"✅ Module créé: {module_data.get('nom')}")
                            else:
                                error_msg = f"Module ID {module_id} non trouvé"
                                modules_errors.append(error_msg)
                                logger.warning(f"⚠️ {error_msg}")
                                
                        except Exception as e:
                            error_msg = f"Erreur module {module_id}: {str(e)}"
                            modules_errors.append(error_msg)
                            logger.error(f"❌ {error_msg}")
                    
                    # Vérification finale
                    if modules_crees == 0:
                        error_msg = "Aucun module n'a pu être créé"
                        logger.error(f"❌ {error_msg}")
                        raise Exception(f"{error_msg}. Erreurs: {', '.join(modules_errors)}")
                    
                    # Message de succès
                    success_msg = f"✅ Précontrat créé avec succès ! {modules_crees} module(s) ajouté(s)."
                    if modules_errors:
                        success_msg += f" ⚠️ {len(modules_errors)} erreur(s) mineure(s)."
                    
                    messages.success(request, success_msg)
                    logger.info(f"🎉 Précontrat {precontrat.id} finalisé avec {modules_crees} modules")
                    
                    # Redirection
                    return redirect('precontrat_detail', pk=precontrat.pk)
                    # return redirect('/admin/Gestion/precontrat/')
                    
            except Exception as e:
                logger.error(f"❌ Erreur lors de la création: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors de la création : {str(e)}")
                context['form'] = form
                return render(request, 'contrats/precontrats/creation.html', context)
                
        else:
            # Formulaire invalide
            logger.warning("❌ Formulaire invalide")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
                    logger.debug(f"Erreur champ {field}: {error}")
            
            context['form'] = form
            return render(request, 'contrats/precontrats/creation.html', context)
    
    else:
        # GET request
        form = PreContratCreateForm()
        context['form'] = form
    
    return render(request, 'contrats/precontrats/creation.html', context)

@login_required
@require_http_methods(["GET"])
def get_modules_par_classe(request, classe_id):
    """
    API pour récupérer les modules d'une classe (AJAX)
    Utilise les données JSON du champ unites_enseignement
    """
    try:
        # Récupérer la classe
        classe = get_object_or_404(Classe, id=classe_id, is_active=True)
        
        # Récupérer les maquettes (SANS select_related)
        maquettes = Maquette.objects.filter(
            classe=classe,
            is_active=True
        )
        
        if not maquettes.exists():
            return JsonResponse({
                'success': False,
                'error': 'Aucune maquette trouvée pour cette classe',
                'modules': []
            })
        
        # Extraire les modules du champ JSON
        modules_data = []
        
        for maquette in maquettes:
            # Accès au champ JSON unites_enseignement
            ues = maquette.unites_enseignement or []
            
            for ue in ues:
                matieres = ue.get('matieres', [])
                
                for matiere in matieres:
                    modules_data.append({
                        'id': matiere.get('id'),
                        'code': matiere.get('code', ''),
                        'nom': matiere.get('nom', ''),
                        'ue_nom': ue.get('libelle', ''),
                        'volume_cm': float(matiere.get('volume_horaire_cm', 5)),
                        'volume_td': float(matiere.get('volume_horaire_td', 5)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 5000)),
                        'taux_td': float(matiere.get('taux_horaire_td', 5000)),
                    })
        
        return JsonResponse({
            'success': True,
            'classe': classe.nom,
            'modules': modules_data,
            'count': len(modules_data)
        })
        
    except Classe.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Classe non trouvée',
            'modules': []
        }, status=404)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur récupération modules: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==========================================
# VUE DE DÉTAIL D'UN PRÉCONTRAT
# ==========================================

@login_required
def precontrat_detail(request, pk):
    """
    Vue pour afficher le détail d'un précontrat avec tous ses modules
    """
    precontrat = get_object_or_404(
        PreContrat.objects.select_related('professeur', 'classe', 'cree_par', 'valide_par'),
        pk=pk
    )
    
    # Récupérer tous les modules avec prefetch
    modules = precontrat.modules_proposes.all()
    
    # Calculer les statistiques
    volumes = precontrat.get_volume_total()
    montant_total = precontrat.get_montant_total()
    
    # Vérifier les permissions
    can_edit = (
        request.user == precontrat.cree_par or 
        request.user.role in ['RESP_RH', 'ADMIN']
    ) and precontrat.status == 'DRAFT'
    
    can_submit = (
        request.user == precontrat.cree_par and 
        precontrat.peut_etre_soumis
    )
    
    can_validate = (
        request.user.role in ['RESP_RH', 'ADMIN'] and 
        precontrat.peut_etre_valide
    )
    
    context = {
        'precontrat': precontrat,
        'modules': modules,
        'volumes': volumes,
        'montant_total': montant_total,
        'can_edit': can_edit,
        'can_submit': can_submit,
        'can_validate': can_validate,
        'title': f'Précontrat {precontrat.reference}',
    }
    
    return render(request, 'contrats/precontrats/detail.html', context)

# ==========================================
# VUE DE RÉCAPITULATIF AVANT VALIDATION (MODIFIÉE)
# ==========================================
@login_required
@require_http_methods(["GET", "POST"])
def precontrat_recapitulatif(request, pk):
    """
    ⭐ VERSION AVEC LOGGING DÉTAILLÉ ⭐
    """
    precontrat = get_object_or_404(
        PreContrat.objects.select_related('professeur', 'classe'),
        pk=pk
    )
    
    logger.info(f"🔍 Accès récapitulatif précontrat {precontrat.reference} par {request.user}")
    
    # Vérifier les permissions
    if request.user != precontrat.cree_par and request.user.role not in ['RESP_RH', 'ADMIN']:
        messages.error(request, "❌ Vous n'avez pas la permission d'accéder à cette page.")
        return redirect('precontrat_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        logger.info(f"🔄 Action reçue: {action} pour le précontrat {precontrat.reference} par {request.user}")
        
        if action == 'validate_module':
            # Validation individuelle d'un module
            module_id = request.POST.get('module_id')
            logger.info(f"🔄 Validation module individuel: {module_id}")
            
            try:
                module = ModulePropose.objects.get(pk=module_id, pre_contrat=precontrat)
                
                # Valider le module
                module.est_valide = True
                module.valide_par = request.user
                module.date_validation = timezone.now()
                module.save()
                
                logger.info(f"✅ Module {module.nom_module} validé, création contrat...")
                
                # Créer automatiquement le contrat
                from .utils import create_contrat_from_module
                create_contrat_from_module(module, request.user)
                
                # Mettre à jour le statut du précontrat
                precontrat.update_status()
                
                messages.success(request, f"✅ Module {module.nom_module} validé et contrat créé avec succès !")
                
            except ModulePropose.DoesNotExist:
                logger.error(f"❌ Module {module_id} non trouvé")
                messages.error(request, "❌ Module non trouvé.")
            except Exception as e:
                logger.error(f"❌ Erreur validation module: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors de la validation du module: {str(e)}")
        
        elif action == 'validate_all_modules':
            # Valider tous les modules en une fois
            logger.info("🔄 Validation de tous les modules")
            try:
                modules_valides = 0
                for module in precontrat.modules_proposes.all():
                    if not module.est_valide:
                        module.est_valide = True
                        module.valide_par = request.user
                        module.date_validation = timezone.now()
                        module.save()
                        
                        logger.info(f"🔄 Création contrat pour module: {module.nom_module}")
                        
                        # Créer le contrat
                        from .utils import create_contrat_from_module
                        create_contrat_from_module(module, request.user)
                        
                        modules_valides += 1
                
                # Mettre à jour le statut du précontrat
                precontrat.update_status()
                
                if modules_valides > 0:
                    messages.success(request, f"✅ {modules_valides} module(s) validé(s) et contrat(s) créé(s) avec succès !")
                else:
                    messages.info(request, "ℹ️ Tous les modules étaient déjà validés.")
                    
            except Exception as e:
                logger.error(f"❌ Erreur validation globale: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors de la validation: {str(e)}")
        
        elif action == 'submit_precontrat':
            # Soumettre ou valider le précontrat complet
            logger.info("🔄 Soumission/Validation du précontrat complet")
            try:
                if request.user.role in ['RESP_RH', 'ADMIN']:
                    # Si c'est un RH, valider directement
                    notes = request.POST.get('notes', '')
                    logger.info(f"🔄 Validation RH du précontrat {precontrat.reference}")
                    precontrat.valider(user=request.user, notes=notes)
                    messages.success(request, f"✅ Le précontrat {precontrat.reference} a été validé avec succès ! Les contrats ont été créés automatiquement.")
                else:
                    # Si c'est le créateur, soumettre pour validation
                    logger.info(f"🔄 Soumission du précontrat {precontrat.reference} pour validation RH")
                    precontrat.soumettre(user=request.user)
                    messages.success(request, f"✅ Le précontrat {precontrat.reference} a été soumis pour validation RH !")
                
                return redirect('precontrat_detail', pk=pk)
                
            except ValidationError as e:
                logger.error(f"❌ Erreur validation précontrat: {str(e)}")
                messages.error(request, f"❌ Erreur de validation : {str(e)}")
            except Exception as e:
                logger.error(f"❌ Erreur inattendue: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur inattendue : {str(e)}")
        
        elif action == 'back':
            return redirect('precontrat_detail', pk=pk)
        
        # Recharger la page pour afficher les changements
        return redirect('precontrat_recapitulatif', pk=pk)
    
    # Récupérer les modules
    modules = precontrat.modules_proposes.all()
    
    # Calculer les totaux
    volumes = precontrat.get_volume_total()
    montant_total = precontrat.get_montant_total()
    
    # Détails par module avec statut des contrats
    modules_details = []
    for module in modules:
        contrat_existe = hasattr(module, 'contrat')
        modules_details.append({
            'module': module,
            'details': module.get_details_volumes(),
            'contrat_existe': contrat_existe,
            'contrat': module.contrat if contrat_existe else None
        })
    
    context = {
        'precontrat': precontrat,
        'modules': modules,
        'modules_details': modules_details,
        'volumes': volumes,
        'montant_total': montant_total,
        'title': f'Récapitulatif - {precontrat.reference}',
        'can_validate_modules': request.user.role in ['RESP_RH', 'ADMIN'],
        'can_submit_precontrat': request.user == precontrat.cree_par,
        'is_rh': request.user.role in ['RESP_RH', 'ADMIN'],
    }
    
    return render(request, 'contrats/precontrats/recapitulatif.html', context)


# ==========================================
# FONCTION POUR CRÉER UN CONTRAT À PARTIR D'UN MODULE
# ==========================================

def create_contrat_from_module(module, user):
    """
    ⭐ VERSION CORRIGÉE ⭐
    Crée automatiquement un contrat à partir d'un module validé
    """
    with transaction.atomic():
        # Vérifier si un contrat existe déjà pour ce module
        if hasattr(module, 'contrat'):
            logger.info(f"✅ Contrat existe déjà pour le module {module.id}")
            return module.contrat
        
        # Vérifier que le module est bien validé
        if not module.est_valide:
            raise ValidationError(f"Le module {module.nom_module} doit être validé avant de créer un contrat")
        
        try:
            # Récupérer la maquette associée
            maquette = Maquette.objects.filter(
                classe=module.pre_contrat.classe,
                is_active=True
            ).first()
            
            if not maquette:
                raise ValidationError("Aucune maquette active trouvée pour cette classe")
            
            # ⭐ GESTION SÉCURISÉE DE LA RELATION PROFESSEUR
            from Utilisateur.models import Professeur
            
            # Vérifier si l'utilisateur a déjà un profil professeur
            try:
                professeur_instance = module.pre_contrat.professeur.professeur
                logger.info(f"✅ Profil professeur trouvé: {professeur_instance}")
            except Professeur.DoesNotExist:
                # Créer un profil professeur si inexistant
                logger.warning(f"⚠️ Création du profil professeur pour {module.pre_contrat.professeur}")
                professeur_instance = Professeur.objects.create(
                    user=module.pre_contrat.professeur,
                    grade='AUTRE',  # Valeur par défaut
                    specialite='Non spécifiée',
                    est_actif=True
                )
                logger.info(f"✅ Profil professeur créé: {professeur_instance}")
            
            # ⭐ CRÉATION DU CONTRAT
            contrat = Contrat.objects.create(
                module_propose=module,
                professeur=professeur_instance,
                classe=module.pre_contrat.classe,
                maquette=maquette,
                volume_heure_cours=module.volume_heure_cours,
                volume_heure_td=module.volume_heure_td,
                taux_horaire_cours=module.taux_horaire_cours,
                taux_horaire_td=module.taux_horaire_td,
                valide_par=user,
                date_validation=timezone.now(),
                status='VALIDATED'
            )
            
            logger.info(f"✅ Contrat #{contrat.id} créé avec succès pour le module {module.nom_module}")
            
            # Log de l'action
            ActionLog.objects.create(
                contrat=contrat,
                action='CREATED',
                user=user,
                details=f"Contrat créé automatiquement depuis le module {module.code_module}"
            )
            
            return contrat
            
        except Exception as e:
            logger.error(f"❌ Erreur création contrat: {str(e)}", exc_info=True)
            raise ValidationError(f"Erreur lors de la création du contrat: {str(e)}")
            
# ==========================================
# ACTIONS SUR LES PRÉCONTRATS
# ==========================================

# ==========================================
# VUES CORRIGÉES - VERSION FONCTIONNELLE
# ==========================================

@login_required
@require_http_methods(["POST"])
def precontrat_soumettre(request, pk):
    """Soumet un précontrat pour validation - VERSION CORRIGÉE"""
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions
    if request.user != precontrat.cree_par and request.user.role not in ['RESP_RH', 'ADMIN']:
        return JsonResponse({
            'success': False,
            'error': 'Permission refusée'
        }, status=403)
    
    try:
        # ✅ CORRECTION : Utiliser la bonne méthode
        precontrat.soumettre(user=request.user)
        return JsonResponse({
            'success': True,
            'message': 'Précontrat soumis avec succès',
            'status': precontrat.get_status_display()
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@require_http_methods(["POST"])
def precontrat_valider(request, pk):
    """Valide un précontrat (RH uniquement) - VERSION CORRIGÉE"""
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions
    if request.user.role not in ['RESP_RH', 'ADMIN']:
        return JsonResponse({
            'success': False,
            'error': 'Seuls les responsables RH peuvent valider les précontrats'
        }, status=403)
    
    try:
        notes = request.POST.get('notes', '')
        # ✅ CORRECTION : Utiliser la bonne méthode
        precontrat.valider(user=request.user, notes=notes)
        
        return JsonResponse({
            'success': True,
            'message': 'Précontrat validé avec succès',
            'status': precontrat.get_status_display()
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def precontrat_rejeter(request, pk):
    """Rejette un précontrat (RH uniquement)"""
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions
    if request.user.role not in ['RESP_RH', 'ADMIN']:
        return JsonResponse({
            'success': False,
            'error': 'Seuls les responsables RH peuvent rejeter les précontrats'
        }, status=403)
    
    raison = request.POST.get('raison', '').strip()
    if not raison:
        return JsonResponse({
            'success': False,
            'error': 'Une raison de rejet est requise'
        }, status=400)
    
    try:
        precontrat.rejeter(user=request.user, raison=raison)
        
        return JsonResponse({
            'success': True,
            'message': 'Précontrat rejeté',
            'status': precontrat.get_status_display()
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ==========================================
# VUE POUR LA LISTE DES PRÉCONTRATS
# ==========================================
@login_required
def precontrat_list(request):
    """
    Vue pour afficher la liste des précontrats avec filtres et pagination
    """
    # Récupérer les paramètres de filtrage
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    annee_filter = request.GET.get('annee', '')
    
    # Base queryset avec prefetch_related pour optimiser les requêtes
    precontrats = PreContrat.objects.select_related(
        'professeur', 'classe', 'cree_par'
    ).prefetch_related(
        'modules_proposes'
    ).order_by('-date_creation')
    
    # Appliquer les filtres
    if search_query:
        precontrats = precontrats.filter(
            Q(reference__icontains=search_query) |
            Q(professeur__first_name__icontains=search_query) |
            Q(professeur__last_name__icontains=search_query) |
            Q(professeur__email__icontains=search_query) |
            Q(classe__nom__icontains=search_query) |
            Q(classe_nom__icontains=search_query)
        )
    
    if status_filter:
        precontrats = precontrats.filter(status=status_filter)
    
    if annee_filter:
        precontrats = precontrats.filter(annee_academique=annee_filter)
    
    # Pagination directement sur le queryset
    page = request.GET.get('page', 1)
    paginator = Paginator(precontrats, 20)
    
    try:
        precontrats_page = paginator.page(page)
    except PageNotAnInteger:
        precontrats_page = paginator.page(1)
    except EmptyPage:
        precontrats_page = paginator.page(paginator.num_pages)
    
    # Calculer les statistiques
    stats = {
        'total': PreContrat.objects.count(),
        'draft': PreContrat.objects.filter(status='DRAFT').count(),
        'submitted': PreContrat.objects.filter(status='SUBMITTED').count(),
        'under_review': PreContrat.objects.filter(status='UNDER_REVIEW').count(),
        'validated': PreContrat.objects.filter(status='VALIDATED').count(),
        'rejected': PreContrat.objects.filter(status='REJECTED').count(),
    }
    
    # Récupérer les années académiques distinctes pour le filtre
    years = PreContrat.objects.values_list('annee_academique', flat=True).distinct().order_by('-annee_academique')
    
    context = {
        'title': 'Liste des Précontrats',
        'active_page': 'precontrats',
        'precontrats': precontrats_page,
        'stats': stats,
        'years': years,
        'search_query': search_query,
        'status_filter': status_filter,
        'annee_filter': annee_filter,
        'filters_applied': any([search_query, status_filter, annee_filter]),
    }
    
    return render(request, 'contrats/precontrats/liste.html', context)
# ==========================================
# VUE POUR L'ÉDITION D'UN PRÉCONTRAT
# ==========================================

@login_required
@require_http_methods(["GET", "POST"])
def precontrat_edit(request, pk):
    """
    Vue pour modifier un précontrat existant
    """
    precontrat = get_object_or_404(
        PreContrat.objects.select_related('professeur', 'classe'),
        pk=pk
    )
    
    # Vérifier les permissions
    if not (request.user == precontrat.cree_par or request.user.role in ['RESP_RH', 'ADMIN']):
        messages.error(request, "❌ Vous n'avez pas la permission de modifier ce précontrat.")
        return redirect('precontrat_detail', pk=pk)
    
    # Vérifier que le précontrat peut être modifié
    if precontrat.status != 'DRAFT':
        messages.error(request, "❌ Seuls les précontrats en brouillon peuvent être modifiés.")
        return redirect('precontrat_detail', pk=pk)
    
    if request.method == 'POST':
        form = PreContratCreateForm(request.POST, instance=precontrat)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Sauvegarder les modifications de base
                    precontrat = form.save(commit=False)
                    precontrat.save()
                    
                    # Gérer les modules (logique similaire à la création)
                    selected_modules_json = request.POST.get('selected_modules', '[]')
                    try:
                        selected_modules_ids = json.loads(selected_modules_json)
                    except json.JSONDecodeError:
                        messages.error(request, "❌ Erreur dans la sélection des modules")
                        context = {'form': form, 'precontrat': precontrat}
                        return render(request, 'contrats/precontrats/edit.html', context)
                    
                    # Supprimer les modules existants et recréer
                    precontrat.modules_proposes.all().delete()
                    
                    # Recréer les modules sélectionnés
                    maquettes = Maquette.objects.filter(
                        classe=precontrat.classe,
                        is_active=True
                    )
                    
                    modules_crees = 0
                    for module_id in selected_modules_ids:
                        module_data = find_module_in_maquettes(maquettes, module_id)
                        if module_data:
                            ModulePropose.objects.create(
                                pre_contrat=precontrat,
                                code_module=module_data.get('id', f'MOD_{module_id}'),
                                nom_module=module_data.get('nom', 'Module sans nom'),
                                ue_nom=module_data.get('ue_nom', 'UE non spécifiée'),
                                volume_heure_cours=Decimal(str(module_data.get('volume_horaire_cm', 0))),
                                volume_heure_td=Decimal(str(module_data.get('volume_horaire_td', 0))),
                                taux_horaire_cours=Decimal(str(module_data.get('taux_horaire_cm', 5000))),
                                taux_horaire_td=Decimal(str(module_data.get('taux_horaire_td', 5000))),
                                est_valide=False,
                            )
                            modules_crees += 1
                    
                    messages.success(request, f"✅ Précontrat modifié avec succès ! {modules_crees} module(s) mis à jour.")
                    return redirect('precontrat_detail', pk=precontrat.pk)
                    
            except Exception as e:
                logger.error(f"❌ Erreur lors de la modification: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors de la modification : {str(e)}")
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    
    else:
        form = PreContratCreateForm(instance=precontrat)
    
    # Préparer les données des modules existants pour le template
    modules_existants = precontrat.modules_proposes.all()
    modules_data = []
    
    for module in modules_existants:
        modules_data.append({
            'id': module.code_module,  # Utiliser code_module comme ID
            'code': module.code_module,
            'nom': module.nom_module,
            'ue_nom': module.ue_nom,
            'volume_cm': float(module.volume_heure_cours),
            'volume_td': float(module.volume_heure_td),
            'taux_cm': float(module.taux_horaire_cours),
            'taux_td': float(module.taux_horaire_td),
        })
    
    context = {
        'title': f'Modifier le précontrat {precontrat.reference}',
        'form': form,
        'precontrat': precontrat,
        'modules_existants': modules_data,
        'classe_id': precontrat.classe.id,
    }
    
    return render(request, 'contrats/precontrats/edit.html', context)


# ==========================================
# VUE POUR L'EXPORT PDF D'UN PRÉCONTRAT
# ==========================================

@login_required
def precontrat_export_pdf(request, pk):
    """
    Vue pour exporter un précontrat en PDF
    """
    precontrat = get_object_or_404(
        PreContrat.objects.select_related('professeur', 'classe', 'cree_par'),
        pk=pk
    )
    
    modules = precontrat.modules_proposes.all()
    volumes = precontrat.get_volume_total()
    montant_total = precontrat.get_montant_total()
    
    # Créer le PDF (vous devrez implémenter cette fonction)
    try:
        pdf = generate_precontrat_pdf(precontrat, modules, volumes, montant_total)
        
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"PRECONTRAT_{precontrat.reference}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf".upper()
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erreur génération PDF: {str(e)}", exc_info=True)
        messages.error(request, "❌ Erreur lors de la génération du PDF")
        return redirect('precontrat_detail', pk=pk)


# ==========================================
# FONCTION UTILITAIRE POUR GÉNÉRER LE PDF
# ==========================================

def generate_precontrat_pdf(precontrat, modules, volumes, montant_total):
    """
    Génère un PDF pour un précontrat
    À implémenter avec ReportLab ou WeasyPrint
    """
    # TODO: Implémenter la génération PDF
    # Pour l'instant, retourner un PDF vide
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from io import BytesIO
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # En-tête
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"PRÉCONTRAT {precontrat.reference}")
    
    # Informations générales
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Professeur: {precontrat.professeur.get_full_name()}")
    p.drawString(100, 750, f"Classe: {precontrat.classe_nom}")
    p.drawString(100, 730, f"Année académique: {precontrat.annee_academique}")
    p.drawString(100, 710, f"Statut: {precontrat.get_status_display()}")
    
    # Modules
    y_position = 680
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y_position, "Modules proposés:")
    
    y_position -= 30
    for module in modules:
        if y_position < 100:  # Nouvelle page si nécessaire
            p.showPage()
            y_position = 750
        
        p.setFont("Helvetica", 10)
        p.drawString(120, y_position, f"- {module.code_module}: {module.nom_module}")
        y_position -= 20
        p.drawString(140, y_position, f"UE: {module.ue_nom} | CM: {module.volume_heure_cours}h | TD: {module.volume_heure_td}h")
        y_position -= 20
    
    # Totaux
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y_position, f"Volume total: {volumes['total']}h")
    y_position -= 20
    p.drawString(100, y_position, f"Montant total: {montant_total:,.0f} FCFA")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ============================================================================
# VUE DE VALIDATION D'UN MODULE
# ============================================================================

@login_required
@role_required(['RESP_RH', 'ADMIN'])
def module_validate(request, pk):
    """
    Valider un module proposé.
    RH peut ajuster les volumes et taux si nécessaire.
    """
    module = get_object_or_404(ModulePropose, pk=pk)
    
    if request.method == 'POST':
        form = ModuleValidationForm(request.POST, instance=module)
        
        if form.is_valid():
            module = form.save(commit=False)
            
            # Si validé, enregistrer l'utilisateur et la date
            if module.est_valide and not module.valide_par:
                module.valide_par = request.user
                module.date_validation = timezone.now()
            
            module.save()
            
            # Mettre à jour le statut du précontrat
            module.pre_contrat.update_status()
            
            # Log
            ActionLog.objects.create(
                pre_contrat=module.pre_contrat,
                module_propose=module,
                action='VALIDATED' if module.est_valide else 'OTHER',
                user=request.user,
                details=f"Module {module.module_code} {'validé' if module.est_valide else 'modifié'}"
            )
            
            messages.success(request, "✅ Module mis à jour avec succès")
            return redirect('precontrat_detail', pk=module.pre_contrat.pk)
    else:
        form = ModuleValidationForm(instance=module)
    
    context = {
        'form': form,
        'module': module,
        'precontrat': module.pre_contrat,
    }
    return render(request, 'contrats/module_validate.html', context)


# ============================================================================
# VUE DE SOUMISSION D'UN PRÉCONTRAT
# ============================================================================

# Dans views.py - CORRIGEZ cette vue
@login_required
@role_required(['RESP_RH', 'ADMIN'])
def precontrat_submit(request, pk):
    """
    ✅ VERSION CORRIGÉE - Utilise la bonne méthode
    """
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    if request.method == 'POST':
        try:
            # ✅ CORRECTION : Utiliser soumettre() au lieu de submit()
            precontrat.soumettre(user=request.user)
            messages.success(request, "📨 Précontrat soumis pour validation")
        except ValidationError as e:
            messages.error(request, f"❌ Erreur : {str(e)}")
        except Exception as e:
            messages.error(request, f"❌ Erreur inattendue : {str(e)}")
    
    return redirect('precontrat_detail', pk=pk)

# ==========================================
# VUE POUR LA SUPPRESSION D'UN PRÉCONTRAT (CORRIGÉE)
# ==========================================

@login_required
@require_http_methods(["POST"])
@role_required(['RESP_RH', 'ADMIN'])  # ⭐ AJOUT DU DÉCORATEUR ROLE_REQUIRED
def precontrat_delete(request, pk):
    """
    Vue pour supprimer un précontrat
    """
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions (déjà fait par le décorateur, mais double sécurité)
    if not (request.user == precontrat.cree_par or request.user.role in ['RESP_RH', 'ADMIN']):
        messages.error(request, "❌ Vous n'avez pas la permission de supprimer ce précontrat.")
        return redirect('precontrat_list')
    
    # Vérifier que le précontrat peut être supprimé
    if precontrat.status != 'DRAFT':
        messages.error(request, "❌ Seuls les précontrats en brouillon peuvent être supprimés.")
        return redirect('precontrat_list')
    
    try:
        reference = precontrat.reference
        precontrat.delete()
        messages.success(request, f"✅ Précontrat {reference} supprimé avec succès.")
        
    except Exception as e:
        logger.error(f"❌ Erreur suppression précontrat: {str(e)}", exc_info=True)
        messages.error(request, "❌ Erreur lors de la suppression du précontrat.")
    
    return redirect('precontrat_list')


# ==========================================
# VUES POUR LES CONTRATS
# ==========================================
# ==========================================
# VUE POUR L'AFFICHAGE IMPRIMABLE D'UN CONTRAT
# ==========================================

@login_required
def contrat_imprimable(request, pk):
    """
    Vue pour afficher un contrat dans un format optimisé pour l'impression
    """
    contrat = get_object_or_404(
        Contrat.objects.select_related(
            'professeur',
            'professeur__user',
            'classe',
            'maquette',
            'valide_par',
            'demarre_par'
        ).prefetch_related(
            'groupes_selectionnes',
            'classes_tronc_commun',
            'pointages'
        ),
        pk=pk
    )
    
    # Récupérer les données calculées
    heures_effectuees = contrat.get_heures_effectuees()
    montant_total_contractuel = contrat.montant_total_contractuel
    montant_a_payer = contrat.calculate_montant_a_payer()
    
    # Récupérer les groupes et classes
    groupes = contrat.groupes_selectionnes.all()
    classes_tronc_commun = contrat.classes_tronc_commun.all()
    
    # Récupérer les pointages triés par date
    pointages = contrat.pointages.all().order_by('date_seance')
    
    # Calculer les statistiques de pointage
    total_pointages = pointages.count()
    total_heures_pointages = sum([p.total_heures for p in pointages])
    
    # Informations de l'établissement (à adapter selon votre configuration)
    infos_etablissement = {
        'nom': "Institut International Polytechnique des Élites d'Abidjan (IIPEA)",
        'adresse': "Cocody Riviera 2, Route d'Attoban / Riviera Triangle / Yamoussoukro",
        'telephone': "+225 05 44 02 60 60 / +225 07 08 08 87 87",
        'email': "secretariat@iipea.com",
        'site_web': "www.iipea.com",
    }
    
    context = {
        'contrat': contrat,
        'heures_effectuees': heures_effectuees,
        'montant_total_contractuel': montant_total_contractuel,
        'montant_a_payer': montant_a_payer,
        'groupes': groupes,
        'classes_tronc_commun': classes_tronc_commun,
        'pointages': pointages,
        'total_pointages': total_pointages,
        'total_heures_pointages': total_heures_pointages,
        'infos_etablissement': infos_etablissement,
        'today': timezone.now().date(),
        'title': f'CONTRAT #{contrat.id} - {contrat.professeur.user.get_full_name().upper()}',  # ⭐ MAJUSCULES
    }
    
    return render(request, 'contrats/contrat_imprimable.html', context)

# ==========================================
# VUE POUR LA LISTE DES CONTRATS
# ==========================================

@login_required
def contrat_list(request):
    """
    Vue pour afficher la liste des contrats créés
    """
    # Récupérer les paramètres de filtrage
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    
    # Base queryset avec prefetch_related pour optimiser les requêtes
    contrats = Contrat.objects.select_related(
        'professeur', 'classe', 'maquette', 'valide_par'
    ).order_by('-date_validation')
    
    # Appliquer les filtres
    if search_query:
        contrats = contrats.filter(
            Q(professeur__user__first_name__icontains=search_query) |
            Q(professeur__user__last_name__icontains=search_query) |
            Q(classe__nom__icontains=search_query) |
            Q(maquette__filiere_nom__icontains=search_query)
        )
    
    if status_filter:
        contrats = contrats.filter(status=status_filter)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(contrats, 20)
    
    try:
        contrats_page = paginator.page(page)
    except PageNotAnInteger:
        contrats_page = paginator.page(1)
    except EmptyPage:
        contrats_page = paginator.page(paginator.num_pages)
    
    context = {
        'title': 'Liste des Contrats',
        'active_page': 'contrats',
        'contrats': contrats_page,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'contrats/liste.html', context)


@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def contrat_start(request, pk):
    """
    Démarrer un contrat avec sélection des groupes
    """
    contrat = get_object_or_404(Contrat, pk=pk)
    
    if not contrat.can_start():
        messages.error(request, "Ce contrat ne peut pas être démarré.")
        return redirect('contrat_detail', pk=contrat.pk)
    
    if request.method == 'POST':
        form = ContratStartForm(request.POST, contrat=contrat)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Récupérer les données du formulaire
                    type_enseignement = form.cleaned_data['type_enseignement']
                    date_debut_prevue = form.cleaned_data['date_debut_prevue']
                    groupes_principale = form.cleaned_data['groupes_classe_principale']
                    classes_tronc_commun = form.cleaned_data['classes_tronc_commun']
                    groupes_tronc_commun = form.cleaned_data['groupes_tronc_commun']
                    
                    # Démarrer le contrat
                    contrat.demarrer_cours(
                        user=request.user,
                        type_enseignement=type_enseignement,
                        classes_tronc_commun=classes_tronc_commun,
                        date_debut_prevue=date_debut_prevue
                    )
                    
                    # Associer les groupes sélectionnés
                    tous_les_groupes = list(groupes_principale) + list(groupes_tronc_commun)
                    contrat.groupes_selectionnes.set(tous_les_groupes)
                    
                    messages.success(
                        request,
                        f"✅ Cours démarré avec succès! {len(tous_les_groupes)} groupe(s) sélectionné(s)."
                    )
                
                return redirect('contrat_detail', pk=contrat.pk)
                
            except Exception as e:
                logger.error(f"Erreur démarrage contrat: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors du démarrage: {str(e)}")
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs du formulaire.")
    else:
        form = ContratStartForm(contrat=contrat)
    
    context = {
        'contrat': contrat,
        'form': form,
        'title': f'Démarrer le cours - {contrat.maquette}'
    }
    return render(request, 'contrats/contrat_start.html', context)


@login_required
@role_required(['RESP_PEDA','RESP_RH', 'ADMIN'])
def contrat_detail(request, pk):
    """
    Détail d'un contrat avec suivi de progression
    """
    contrat = get_object_or_404(Contrat, pk=pk)
    pointages = contrat.pointages.all().order_by('-date_seance')
    documents = contrat.documents.all()
    
    # Calcul de la progression
    heures_effectuees = contrat.get_heures_effectuees()
    taux_realisation = contrat.taux_realisation
    
    # Graphique de progression (données pour Chart.js)
    progression_data = {
        'labels': ['Cours', 'TD'],
        'contractuel': [
            float(contrat.volume_heure_cours),
            float(contrat.volume_heure_td),
        ],
        'effectue': [
            float(heures_effectuees['cours']),
            float(heures_effectuees['td']),
        ],
    }
    
    context = {
        'contrat': contrat,
        'pointages': pointages,
        'documents': documents,
        'heures_effectuees': heures_effectuees,
        'taux_realisation': taux_realisation,
        'progression_data': progression_data,
        'can_start': contrat.can_start(),
        'can_add_pointage': contrat.status == 'IN_PROGRESS',
        'can_complete': contrat.status == 'IN_PROGRESS',
        'can_upload_documents': contrat.status in ['IN_PROGRESS', 'PENDING_DOCUMENTS'],
    }
    return render(request, 'contrats/contrat_detail.html', context)



@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def pointage_create(request, contrat_id):
    """
    Création d'un pointage pour un contrat avec gestion des groupes
    """
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    
    if contrat.status != 'IN_PROGRESS':
        messages.error(request, "❌ Ce contrat n'est pas en cours. Impossible d'ajouter un pointage.")
        return redirect('contrat_detail', pk=contrat.pk)
    
    # Vérifier qu'il y a des groupes sélectionnés
    if not contrat.groupes_selectionnes.exists():
        messages.error(request, "❌ Aucun groupe sélectionné pour ce contrat. Veuillez d'abord sélectionner des groupes.")
        return redirect('contrat_detail', pk=contrat.pk)
    
    if request.method == 'POST':
        print("📨 POST request reçu")  # Debug
        form = PointageForm(request.POST, contrat=contrat)
        
        print(f"✅ Formulaire valide: {form.is_valid()}")  # Debug
        
        if not form.is_valid():
            print(f"❌ ERREURS DU FORMULAIRE:")
            for field, errors in form.errors.items():
                print(f"   - {field}: {errors}")
        
        if form.is_valid():
            print("🎯 Formulaire valide, traitement...")  # Debug
            try:
                with transaction.atomic():
                    pointage = form.save(commit=False)
                    pointage.contrat = contrat
                    pointage.enregistre_par = request.user
                    pointage.est_valide = True
                    
                    # Sauvegarder d'abord le pointage
                    pointage.save()
                    
                    # ⭐ CORRECTION : Lier les groupes sélectionnés via la relation ManyToMany
                    groupes_selectionnes = form.cleaned_data['groupes_selection']
                    pointage.groupes.set(groupes_selectionnes)
                    
                    print(f"✅ Pointage sauvegardé avec ID: {pointage.id} pour {len(groupes_selectionnes)} groupes")  # Debug
                
                messages.success(
                    request,
                    f"✅ Pointage enregistré: {pointage.total_heures}h le {pointage.date_seance.strftime('%d/%m/%Y')} pour {len(groupes_selectionnes)} groupe(s)"
                )
                
                return redirect('contrat_detail', pk=contrat.pk)
                
            except Exception as e:
                print(f"❌ Erreur lors de la sauvegarde: {e}")  # Debug
                logger.error(f"Erreur création pointage: {str(e)}", exc_info=True)
                messages.error(request, f"❌ Erreur lors de l'enregistrement du pointage: {str(e)}")
        else:
            # Afficher les erreurs dans les messages
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_name = form.fields[field].label or field
                        messages.error(request, f"❌ {field_name}: {error}")
    else:
        form = PointageForm(contrat=contrat, initial={
            'date_seance': timezone.now().date(),
        })
    
    heures_effectuees = contrat.get_heures_effectuees()
    heures_restantes = {
        'cours': max(contrat.volume_heure_cours - heures_effectuees['cours'], Decimal('0.00')),
        'td': max(contrat.volume_heure_td - heures_effectuees['td'], Decimal('0.00')),
    }
    
    # Récupérer les groupes disponibles
    groupes_disponibles = contrat.get_all_groupes()
    
    context = {
        'contrat': contrat,
        'form': form,
        'heures_restantes': heures_restantes,
        'heures_effectuees': heures_effectuees,
        'groupes_disponibles': groupes_disponibles,
        'title': f'Ajouter un pointage - Contrat #{contrat.id}'
    }
    return render(request, 'contrats/pointage_form.html', context)


# ==========================================
# VUES POUR LES CONTRATS
# ==========================================

@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def contrat_complete(request, pk):
    """
    Marquer un contrat comme terminé
    """
    contrat = get_object_or_404(Contrat, pk=pk)
    
    if request.method == 'POST':
        try:
            contrat.terminer_cours(request.user)
            
            if contrat.status == 'READY_FOR_PAYMENT':
                messages.success(
                    request,
                    "Cours terminé ! Le contrat est prêt pour paiement."
                )
            else:
                messages.warning(
                    request,
                    "Cours terminé. Veuillez charger les documents obligatoires (support + syllabus)."
                )
            
            return redirect('contrat_detail', pk=contrat.pk)
            
        except ValidationError as e:
            messages.error(request, str(e))
    
    context = {'contrat': contrat}
    return render(request, 'contrats/contrat_complete.html', context)



from .forms import DocumentContratForm  # ✅ Correction ici

@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def document_upload(request, contrat_id):
    """
    Upload d'un document pour un contrat
    """
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    
    if request.method == 'POST':
        form = DocumentContratForm(request.POST, request.FILES)  # ✅ Correction ici
        
        if form.is_valid():
            try:
                document = form.save(commit=False)
                document.contrat = contrat
                document.charge_par = request.user
                
                # Auto-valider si l'utilisateur a les permissions
                if request.user.role in ['ADMIN', 'RESP_PEDA']:
                    document.est_valide = True
                    document.valide_par = request.user
                    document.date_validation = timezone.now()
                
                document.save()
                
                messages.success(request, f"{document.get_type_document_display()} chargé avec succès")
                return redirect('contrat_detail', pk=contrat.pk)
                
            except Exception as e:
                messages.error(request, f"Erreur lors de l'upload: {str(e)}")
    else:
        form = DocumentContratForm()  # ✅ Correction ici
    
    context = {
        'contrat': contrat,
        'form': form,
        'title': f'Upload Document - {contrat.reference}'
    }
    return render(request, 'documents/document_upload.html', context)


# ==========================================
# VUES POUR LES PAIEMENTS
# ==========================================

@login_required
@role_required(['COMPTABLE', 'ADMIN'])
def paiement_list(request):
    """
    Liste des paiements en attente d'approbation
    """
    status_filter = request.GET.get('status', 'PENDING')
    
    paiements = PaiementContrat.objects.filter(
        status=status_filter
    ).select_related('contrat', 'professeur').order_by('-date_creation')
    
    context = {
        'paiements': paiements,
        'status_filter': status_filter,
        'total_montant': paiements.aggregate(total=Sum('montant_net'))['total'] or 0,
    }
    return render(request, 'paiements/paiement_list.html', context)


@login_required
@role_required(['COMPTABLE', 'ADMIN'])
def paiement_approve(request, pk):
    """
    Approbation d'un paiement
    """
    paiement = get_object_or_404(PaiementContrat, pk=pk)
    
    if request.method == 'POST':
        try:
            paiement.approuver(request.user)
            messages.success(request, f"Paiement #{paiement.id} approuvé - {paiement.montant_net} FCFA")
            return redirect('paiement_list')
        except ValidationError as e:
            messages.error(request, str(e))
    
    context = {
        'paiement': paiement,
        'contrat': paiement.contrat,
        'heures_effectuees': paiement.contrat.get_heures_effectuees(),
    }
    return render(request, 'paiements/paiement_approve.html', context)


@login_required
@role_required(['COMPTABLE', 'ADMIN'])
def paiement_execute(request, pk):
    """
    Exécution d'un paiement (par le comptable)
    """
    paiement = get_object_or_404(PaiementContrat, pk=pk)
    
    if paiement.status != 'APPROVED':
        messages.error(request, "Ce paiement n'est pas approuvé")
        return redirect('paiement_list')
    
    if request.method == 'POST':
        mode_paiement = request.POST.get('mode_paiement')
        reference = request.POST.get('reference_paiement', '')
        
        if not mode_paiement:
            messages.error(request, "Veuillez sélectionner un mode de paiement")
        else:
            try:
                paiement.effectuer_paiement(
                    user=request.user,
                    mode_paiement=mode_paiement,
                    reference=reference
                )
                
                messages.success(
                    request,
                    f"Paiement effectué avec succès - {paiement.montant_net} FCFA"
                )
                
                # Générer le reçu si demandé
                if 'generate_recu' in request.POST:
                    pdf = generate_recu_paiement_pdf(paiement)
                    response = HttpResponse(pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="recu_{paiement.id}.pdf"'
                    return response
                
                return redirect('paiement_list')
                
            except ValidationError as e:
                messages.error(request, str(e))
    
    context = {'paiement': paiement}
    return render(request, 'paiements/paiement_execute.html', context)


# ==========================================
# VUES POUR LE DASHBOARD
# ==========================================

@login_required
def dashboard(request):
    """
    Dashboard principal selon le rôle de l'utilisateur
    """
    user = request.user
    context = {'user': user}
    
    if user.role == 'RESP_RH':
        # Stats pour RH
        context.update({
            'precontrats_pending': PreContrat.objects.filter(
                status__in=['SUBMITTED', 'UNDER_REVIEW']
            ).count(),
            'contrats_actifs': Contrat.objects.filter(
                status__in=['VALIDATED', 'IN_PROGRESS']
            ).count(),
            'modules_a_valider': ModulePropose.objects.filter(
                est_valide=False,
                pre_contrat__status__in=['SUBMITTED', 'UNDER_REVIEW']
            ).count(),
        })
        template = 'dashboard/rh_dashboard.html'
    
    elif user.role == 'RESP_PEDA':
        # Stats pour responsable pédagogique
        context.update({
            'contrats_a_demarrer': Contrat.objects.filter(
                status__in=['VALIDATED', 'READY_TO_START']
            ).count(),
            'contrats_en_cours': Contrat.objects.filter(
                status='IN_PROGRESS'
            ).count(),
            'contrats_sans_documents': Contrat.objects.filter(
                status='PENDING_DOCUMENTS'
            ).count(),
            'pointages_today': Pointage.objects.filter(
                date_seance=timezone.now().date()
            ).count(),
        })
        template = 'dashboard/pedagogique_dashboard.html'
    
    elif user.role in ['COMPTABLE', 'COMPTABLE']:
        # Stats financières
        context.update({
            'paiements_pending': PaiementContrat.objects.filter(
                status='PENDING'
            ).count(),
            'paiements_approved': PaiementContrat.objects.filter(
                status='APPROVED'
            ).count(),
            'montant_a_payer': PaiementContrat.objects.filter(
                status__in=['PENDING', 'APPROVED']
            ).aggregate(total=Sum('montant_net'))['total'] or 0,
        })
        template = 'dashboard/financier_dashboard.html'
    
    elif user.role == 'PROFESSEUR':
        # Dashboard professeur
        professeur = user.professeur  # Supposant une relation OneToOne
        context.update({
            'mes_contrats': Contrat.objects.filter(
                professeur=professeur
            ).order_by('-date_validation')[:10],
            'contrats_en_cours': Contrat.objects.filter(
                professeur=professeur,
                status='IN_PROGRESS'
            ).count(),
            'paiements_recents': PaiementContrat.objects.filter(
                professeur=professeur
            ).order_by('-date_creation')[:5],
        })
        template = 'dashboard/professeur_dashboard.html'
    
    else:
        template = 'dashboard/default_dashboard.html'
    
    return render(request, template, context)


# ==========================================
# API ENDPOINTS (pour AJAX)
# ==========================================

@login_required
def api_get_maquettes(request):
    """
    API pour récupérer les maquettes d'une classe
    Utilisé pour charger dynamiquement les modules disponibles
    """
    classe_id = request.GET.get('classe_id')
    
    if not classe_id:
        return JsonResponse({'error': 'classe_id required'}, status=400)
    
    from apps.gestion.models import Maquette
    
    maquettes = Maquette.objects.filter(
        classe_id=classe_id,
        is_active=True
    ).values('id', 'filiere_sigle', 'niveau_libelle', 'filiere_nom')
    
    return JsonResponse({
        'maquettes': list(maquettes)
    })


@login_required
def api_contrat_progression(request, contrat_id):
    """
    API pour obtenir la progression d'un contrat
    """
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    
    heures_effectuees = contrat.get_heures_effectuees()
    
    data = {
        'contrat_id': contrat.id,
        'status': contrat.status,
        'taux_realisation': float(contrat.taux_realisation),
        'volumes': {
            'contractuel': {
                'cours': float(contrat.volume_heure_cours),
                'td': float(contrat.volume_heure_td),
                'total': float(contrat.volume_total_contractuel),
            },
            'effectue': {
                'cours': float(heures_effectuees['cours']),
                'td': float(heures_effectuees['td']),
                'total': float(contrat.volume_total_effectue),
            },
            'restant': {
                'cours': float(contrat.volume_heure_cours - heures_effectuees['cours']),
                'td': float(contrat.volume_heure_td - heures_effectuees['td']),
            },
        },
        'montant': {
            'contractuel': float(contrat.montant_total_contractuel),
            'a_payer': float(contrat.calculate_montant_a_payer()),
        },
        'documents': {
            'support_cours': contrat.support_cours_uploaded,
            'syllabus': contrat.syllabus_uploaded,
        },
    }
    
    return JsonResponse(data)


# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def get_taux_from_grille(professeur, classe):
    """
    Récupère les taux depuis la grille de référence
    """
    from .models import GrilleTauxHoraire
    
    try:
        grille = GrilleTauxHoraire.objects.get(
            grade_professeur=professeur.grade,
            niveau_classe=classe.niveau,
            is_active=True,
            date_debut__lte=timezone.now().date(),
        )
        return {
            'taux_cours': grille.taux_cours,
            'taux_td': grille.taux_td,
        }
    except GrilleTauxHoraire.DoesNotExist:
        return None


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

@require_GET
def api_groupes_by_classes(request):
    """API pour récupérer les groupes par classes"""
    classes_ids = request.GET.get('classes', '').split(',')
    classes_ids = [cid for cid in classes_ids if cid]
    
    groupes = Groupe.objects.filter(
        classe_id__in=classes_ids,
        is_active=True
    ).select_related('classe').order_by('classe__nom', 'nom')
    
    data = [
        {
            'id': groupe.id,
            'nom': groupe.nom,
            'classe_nom': groupe.classe.nom,
            'code': groupe.code,
            'effectif': groupe.effectif
        }
        for groupe in groupes
    ]
    
    return JsonResponse(data, safe=False)



# ============================================
# VUES DE SUIVI DES CLASSES
# ============================================
# ==========================================
# VUE POUR LE SUIVI DES CLASSES ET MODULES
# ==========================================

from django.db.models import Count, Q, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import datetime
# ==========================================
# VUES CORRIGÉES POUR LE SUIVI DES CLASSES
# ==========================================

@login_required
def classe_suivi_annuel(request):
    """
    Vue principale pour le suivi annuel des classes et modules - CORRIGÉE
    """
    # Récupérer l'année académique (paramètre ou année courante)
    annee_academique = request.GET.get('annee', timezone.now().year)
    
    # Récupérer toutes les classes actives avec statistiques
    classes = Classe.objects.filter(
        is_active=True
    ).prefetch_related(
        'maquettes',
        'contrats'
    ).annotate(
        # Nombre total de modules dans les maquettes actives
        total_modules=Count(
            'maquettes__unites_enseignement',
            filter=Q(maquettes__is_active=True)
        ),
        # Modules avec contrats démarrés
        modules_demarres=Count(
            'contrats',
            filter=Q(
                contrats__status__in=['IN_PROGRESS', 'COMPLETED', 'READY_FOR_PAYMENT'],
                contrats__date_validation__year=annee_academique
            ),
            distinct=True
        ),
        # Contrats en cours
        contrats_en_cours=Count(
            'contrats',
            filter=Q(
                contrats__status='IN_PROGRESS',
                contrats__date_validation__year=annee_academique
            )
        ),
        # Contrats terminés
        contrats_termines=Count(
            'contrats',
            filter=Q(
                contrats__status__in=['COMPLETED', 'READY_FOR_PAYMENT'],
                contrats__date_validation__year=annee_academique
            )
        )
    ).order_by('niveau', 'nom')

    # Calculer le pourcentage de progression et modules restants pour chaque classe
    for classe in classes:
        total_mods = classe.total_modules or 0
        modules_dems = classe.modules_demarres or 0
        
        # Calculer les modules restants
        classe.modules_restants = max(total_mods - modules_dems, 0)
        
        if total_mods > 0:
            classe.progression_pourcentage = round((modules_dems / total_mods) * 100, 1)
        else:
            classe.progression_pourcentage = 0

    # Statistiques globales
    stats_globales = {
        'total_classes': classes.count(),
        'total_modules_demarres': sum((c.modules_demarres or 0) for c in classes),
        'total_modules_planifies': sum((c.total_modules or 0) for c in classes),
        'contrats_en_cours': sum((c.contrats_en_cours or 0) for c in classes),
        'contrats_termines': sum((c.contrats_termines or 0) for c in classes),
    }

    if stats_globales['total_modules_planifies'] > 0:
        stats_globales['progression_globale'] = round(
            (stats_globales['total_modules_demarres'] / stats_globales['total_modules_planifies']) * 100, 1
        )
    else:
        stats_globales['progression_globale'] = 0

    # Récupérer les années académiques disponibles pour le filtre
    annees_disponibles = Contrat.objects.exclude(
        date_validation__isnull=True
    ).dates('date_validation', 'year').order_by('-date_validation')

    context = {
        'title': 'Suivi Annuel des Classes et Modules',
        'active_page': 'suivi_classes',
        'classes': classes,
        'stats_globales': stats_globales,
        'annee_academique': annee_academique,
        'annees_disponibles': [date.year for date in annees_disponibles],
    }

    return render(request, 'contrats/suivi/classe_suivi_annuel.html', context)


@login_required
def classe_detail_suivi(request, classe_id):
    """
    Vue détaillée du suivi pour une classe spécifique - CORRIGÉE
    """
    classe = get_object_or_404(Classe, pk=classe_id, is_active=True)
    annee_academique = request.GET.get('annee', timezone.now().year)

    # Récupérer la maquette active de la classe
    maquette = Maquette.objects.filter(
        classe=classe,
        is_active=True
    ).first()

    if not maquette:
        messages.error(request, f"Aucune maquette active trouvée pour la classe {classe.nom}")
        return redirect('classe_suivi_annuel')

    # Extraire tous les modules de la maquette
    tous_les_modules = []
    ues = maquette.unites_enseignement or []
    
    for ue in ues:
        for matiere in ue.get('matieres', []):
            module_data = {
                'id': matiere.get('id'),
                'code': matiere.get('code', ''),
                'nom': matiere.get('nom', 'Module sans nom'),
                'ue_nom': ue.get('libelle', 'UE non spécifiée'),
                'volume_cm': float(matiere.get('volume_horaire_cm', 0)),
                'volume_td': float(matiere.get('volume_horaire_td', 0)),
                'taux_cm': float(matiere.get('taux_horaire_cm', 5000)),
                'taux_td': float(matiere.get('taux_horaire_td', 5000)),
                'est_demarre': False,
                'contrat': None,
                'statut_contrat': None,
                'progression': 0,
            }
            tous_les_modules.append(module_data)

    # Récupérer les contrats existants pour cette classe - CORRECTION: utilisation de date_validation
    contrats = Contrat.objects.filter(
        classe=classe,
        date_validation__year=annee_academique
    ).select_related('professeur', 'professeur__user', 'valide_par', 'module_propose')

    # Marquer les modules démarrés
    modules_demarres = []
    modules_ids_demarres = set()
    
    for contrat in contrats:
        module_propose = contrat.module_propose
        if module_propose:
            # Trouver le module correspondant dans la liste
            for module in tous_les_modules:
                if str(module['id']) == str(module_propose.code_module):
                    module['est_demarre'] = True
                    module['contrat'] = contrat
                    module['statut_contrat'] = contrat.get_status_display()
                    module['professeur'] = contrat.professeur.user.get_full_name()
                    
                    # Calculer la progression du module
                    heures_effectuees = contrat.get_heures_effectuees()
                    volume_total = contrat.volume_total_contractuel
                    
                    if volume_total > 0:
                        module['progression'] = round(
                            (contrat.volume_total_effectue / volume_total) * 100, 1
                        )
                    else:
                        module['progression'] = 0
                    
                    modules_demarres.append(module)
                    modules_ids_demarres.add(module['id'])
                    break

    # Séparer les modules démarrés et non démarrés
    modules_non_demarres = [m for m in tous_les_modules if m['id'] not in modules_ids_demarres]

    # Statistiques de la classe
    stats_classe = {
        'total_modules': len(tous_les_modules),
        'modules_demarres': len(modules_demarres),
        'modules_non_demarres': len(modules_non_demarres),
        'contrats_total': contrats.count(),
        'contrats_en_cours': contrats.filter(status='IN_PROGRESS').count(),
        'contrats_termines': contrats.filter(status__in=['COMPLETED', 'READY_FOR_PAYMENT']).count(),
        'volume_total_prevue': sum(m['volume_cm'] + m['volume_td'] for m in tous_les_modules),
        'volume_total_effectue': sum(float(c.volume_total_effectue) for c in contrats),
    }

    if stats_classe['total_modules'] > 0:
        stats_classe['progression_globale'] = round(
            (stats_classe['modules_demarres'] / stats_classe['total_modules']) * 100, 1
        )
    else:
        stats_classe['progression_globale'] = 0

    # Progression par UE
    progression_par_ue = {}
    for module in tous_les_modules:
        ue_nom = module['ue_nom']
        if ue_nom not in progression_par_ue:
            progression_par_ue[ue_nom] = {
                'total_modules': 0,
                'modules_demarres': 0,
                'progression': 0
            }
        
        progression_par_ue[ue_nom]['total_modules'] += 1
        if module['est_demarre']:
            progression_par_ue[ue_nom]['modules_demarres'] += 1
    
    # Calculer le pourcentage par UE
    for ue_nom, data in progression_par_ue.items():
        if data['total_modules'] > 0:
            data['progression'] = round((data['modules_demarres'] / data['total_modules']) * 100, 1)

    context = {
        'title': f'Suivi détaillé - {classe.nom}',
        'active_page': 'suivi_classes',
        'classe': classe,
        'maquette': maquette,
        'modules_demarres': modules_demarres,
        'modules_non_demarres': modules_non_demarres,
        'stats_classe': stats_classe,
        'progression_par_ue': progression_par_ue,
        'contrats': contrats,
        'annee_academique': annee_academique,
    }

    return render(request, 'contrats/suivi/classe_detail_suivi.html', context)


@login_required
def progression_annuelle(request):
    """
    Vue globale de la progression annuelle avec graphiques - CORRIGÉE
    """
    annee_academique = request.GET.get('annee', timezone.now().year)
    
    # Récupérer toutes les classes avec leurs statistiques
    classes = Classe.objects.filter(is_active=True).order_by('niveau', 'nom')
    
    donnees_progression = []
    donnees_graphique = {
        'labels': [],
        'modules_demarres': [],
        'modules_restants': [],
        'progression_pourcent': []
    }
    
    for classe in classes:
        # Calculer les statistiques pour chaque classe
        total_modules = 0
        # Compter les modules via les maquettes actives
        maquettes_actives = Maquette.objects.filter(classe=classe, is_active=True)
        for maquette in maquettes_actives:
            ues = maquette.unites_enseignement or []
            for ue in ues:
                total_modules += len(ue.get('matieres', []))
        
        # Modules démarrés via les contrats
        modules_demarres = Contrat.objects.filter(
            classe=classe,
            date_validation__year=annee_academique,
            status__in=['IN_PROGRESS', 'COMPLETED', 'READY_FOR_PAYMENT']
        ).count()
        
        modules_restants = max(total_modules - modules_demarres, 0)
        
        if total_modules > 0:
            progression_pourcent = round((modules_demarres / total_modules) * 100, 1)
        else:
            progression_pourcent = 0
        
        # Données pour le graphique
        donnees_graphique['labels'].append(classe.nom)
        donnees_graphique['modules_demarres'].append(modules_demarres)
        donnees_graphique['modules_restants'].append(modules_restants)
        donnees_graphique['progression_pourcent'].append(progression_pourcent)
        
        # Données détaillées
        donnees_progression.append({
            'classe': classe,
            'total_modules': total_modules,
            'modules_demarres': modules_demarres,
            'modules_restants': modules_restants,
            'progression_pourcent': progression_pourcent,
            'contrats_en_cours': Contrat.objects.filter(
                classe=classe,
                date_validation__year=annee_academique,
                status='IN_PROGRESS'
            ).count(),
            'contrats_termines': Contrat.objects.filter(
                classe=classe,
                date_validation__year=annee_academique,
                status__in=['COMPLETED', 'READY_FOR_PAYMENT']
            ).count(),
        })
    
    # Statistiques globales
    total_modules_global = sum(item['total_modules'] for item in donnees_progression)
    total_demarres_global = sum(item['modules_demarres'] for item in donnees_progression)
    
    if total_modules_global > 0:
        progression_globale = round((total_demarres_global / total_modules_global) * 100, 1)
    else:
        progression_globale = 0
    
    # Utilisation de date_validation pour les statistiques globales
    contrats_globaux = Contrat.objects.filter(date_validation__year=annee_academique)
    
    stats_globales = {
        'total_classes': len(classes),
        'total_modules': total_modules_global,
        'modules_demarres': total_demarres_global,
        'modules_restants': total_modules_global - total_demarres_global,
        'progression_globale': progression_globale,
        'contrats_total': contrats_globaux.count(),
        'contrats_en_cours': contrats_globaux.filter(status='IN_PROGRESS').count(),
        'contrats_termines': contrats_globaux.filter(status__in=['COMPLETED', 'READY_FOR_PAYMENT']).count(),
    }
    
    # Récupérer les années académiques disponibles
    annees_disponibles = Contrat.objects.exclude(
        date_validation__isnull=True
    ).dates('date_validation', 'year').order_by('-date_validation')
    
    # CORRECTION : Utiliser des clés sans espaces pour le dictionnaire
    statuts_contrats = {
        'en_cours': stats_globales['contrats_en_cours'],
        'termines': stats_globales['contrats_termines'],
        'en_attente': stats_globales['contrats_total'] - 
                     stats_globales['contrats_en_cours'] - 
                     stats_globales['contrats_termines']
    }
    
    context = {
        'title': 'Progression Annuelle Globale',
        'active_page': 'progression_annuelle',
        'donnees_progression': donnees_progression,
        'stats_globales': stats_globales,
        'donnees_graphique': donnees_graphique,
        'statuts_contrats': statuts_contrats,
        'annee_academique': annee_academique,
        'annees_disponibles': [date.year for date in annees_disponibles],
    }
    
    return render(request, 'contrats/suivi/progression_annuelle.html', context)

@login_required
@require_http_methods(["GET"])
def api_progression_classes(request):
    """
    API pour récupérer les données de progression des classes (AJAX) - CORRIGÉE
    """
    annee_academique = request.GET.get('annee', timezone.now().year)
    
    classes = Classe.objects.filter(is_active=True).order_by('niveau', 'nom')
    
    data = []
    for classe in classes:
        # CORRECTION: Calcul correct des modules
        total_modules = 0
        maquettes_actives = Maquette.objects.filter(classe=classe, is_active=True)
        for maquette in maquettes_actives:
            ues = maquette.unites_enseignement or []
            for ue in ues:
                total_modules += len(ue.get('matieres', []))
        
        modules_demarres = Contrat.objects.filter(
            classe=classe,
            date_validation__year=annee_academique,
            status__in=['IN_PROGRESS', 'COMPLETED', 'READY_FOR_PAYMENT']
        ).count()
        
        data.append({
            'id': classe.id,
            'nom': classe.nom,
            'niveau': classe.niveau,
            'total_modules': total_modules,
            'modules_demarres': modules_demarres,
            'modules_restants': max(total_modules - modules_demarres, 0),
            'progression_pourcent': round((modules_demarres / total_modules * 100), 1) if total_modules > 0 else 0,
        })
    
    return JsonResponse({
        'success': True,
        'annee_academique': annee_academique,
        'classes': data,
    })