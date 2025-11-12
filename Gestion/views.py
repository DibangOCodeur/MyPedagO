from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from decimal import Decimal
import json
import logging
from .forms import PreContratCreateForm

from .models import (
    PreContrat, ModulePropose, Contrat, Pointage,
    PaiementContrat, ActionLog, Classe, Maquette
)
from .permissions import (
    role_required,
)
from .utils import generate_recu_paiement_pdf
from django.db import transaction
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)                                                    

# ==========================================
# VUES POUR LES PRÉCONTRATS
# ==========================================


# ==========================================
# FONCTION UTILITAIRE POUR EXTRAIRE LES MODULES
# ==========================================

def find_module_in_maquettes(maquettes, module_id):
    """
    Trouve un module dans les données des maquettes
    
    Args:
        maquettes: QuerySet de Maquette
        module_id: ID du module à rechercher
        
    Returns:
        dict: Données du module ou None si non trouvé
    """
    for maquette in maquettes:
        # Les UE sont stockées dans le champ JSON unites_enseignement
        ues = maquette.unites_enseignement or []
        
        for ue in ues:
            # Parcourir les matières de chaque UE
            matieres = ue.get('matieres', [])
            
            for matiere in matieres:
                # Vérifier si c'est le bon module
                if str(matiere.get('id')) == str(module_id):
                    # Retourner les données du module
                    return {
                        'id': matiere.get('id'),
                        'code': matiere.get('code', ''),
                        'nom': matiere.get('nom', ''),
                        'ue_nom': ue.get('libelle', ''),
                        'volume_cm': float(matiere.get('volume_horaire_cm', 0)),
                        'volume_td': float(matiere.get('volume_horaire_td', 0)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 0)),
                        'taux_td': float(matiere.get('taux_horaire_td', 0)),
                    }
    
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
                        'volume_cm': float(matiere.get('volume_horaire_cm', 0)),
                        'volume_td': float(matiere.get('volume_horaire_td', 0)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 0)),
                        'taux_td': float(matiere.get('taux_horaire_td', 0)),
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
                notes_proposition = form.cleaned_data.get('notes_proposition', '')
                
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
                        notes_proposition=notes_proposition
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
                    
                    for module_id in selected_modules_ids:
                        try:
                            module_data = find_module_in_maquettes(maquettes, module_id)
                            
                            if module_data:
                                # Conversion sécurisée des Decimal
                                def safe_decimal(value, default=0):
                                    try:
                                        return Decimal(str(value)) if value is not None else Decimal(default)
                                    except (TypeError, ValueError):
                                        return Decimal(default)
                                
                                ModulePropose.objects.create(
                                    pre_contrat=precontrat,
                                    code_module=module_data.get('id', f'MOD_{module_id}'),
                                    nom_module=module_data.get('nom', 'Module sans nom'),
                                    ue_nom=module_data.get('ue_nom', 'UE non spécifiée'),
                                    volume_heure_cours=safe_decimal(module_data.get('volume_horaire_cm')),
                                    volume_heure_td=safe_decimal(module_data.get('volume_horaire_td')),
                                    taux_horaire_cours=safe_decimal(module_data.get('taux_horaire_cm')),
                                    taux_horaire_td=safe_decimal(module_data.get('taux_horaire_td')),
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
                    return redirect('gestion:precontrat_detail', pk=precontrat.pk)
                    
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


# Vue auxiliaire pour récupérer les modules d'une classe

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
                        'volume_cm': float(matiere.get('volume_horaire_cm', 0)),
                        'volume_td': float(matiere.get('volume_horaire_td', 0)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 0)),
                        'taux_td': float(matiere.get('taux_horaire_td', 0)),
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


def find_module_in_maquettes(maquettes, module_id):
    """
    Fonction utilitaire pour trouver un module dans les maquettes
    Utilise le champ JSON unites_enseignement
    """
    for maquette in maquettes:
        # Accès au champ JSON
        ues = maquette.unites_enseignement or []
        
        for ue in ues:
            matieres = ue.get('matieres', [])
            
            for matiere in matieres:
                if str(matiere.get('id')) == str(module_id):
                    return {
                        'code': matiere.get('code', ''),
                        'nom': matiere.get('nom', ''),
                        'ue_nom': ue.get('libelle', ''),
                        'volume_cm': float(matiere.get('volume_horaire_cm', 0)),
                        'volume_td': float(matiere.get('volume_horaire_td', 0)),
                        'taux_cm': float(matiere.get('taux_horaire_cm', 0)),
                        'taux_td': float(matiere.get('taux_horaire_td', 0)),
                    }
    return None

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
# VUE DE RÉCAPITULATIF AVANT VALIDATION
# ==========================================

@login_required
@require_http_methods(["GET", "POST"])
def precontrat_recapitulatif(request, pk):
    """
    Vue pour afficher un récapitulatif complet avant la soumission du précontrat.
    Permet à l'utilisateur de vérifier toutes les informations avant validation.
    """
    precontrat = get_object_or_404(
        PreContrat.objects.select_related('professeur', 'classe'),
        pk=pk
    )
    
    # Vérifier que l'utilisateur a le droit de soumettre
    if request.user != precontrat.cree_par and request.user.role not in ['RESP_RH', 'ADMIN']:
        messages.error(request, "❌ Vous n'avez pas la permission de soumettre ce précontrat.")
        return redirect('gestion:precontrat_detail', pk=pk)
    
    # Vérifier que le précontrat peut être soumis
    if not precontrat.peut_etre_soumis:
        messages.error(request, "❌ Ce précontrat ne peut pas être soumis dans son état actuel.")
        return redirect('gestion:precontrat_detail', pk=pk)
    
    if request.method == 'POST':
        # Soumettre le précontrat
        action = request.POST.get('action')
        
        if action == 'submit':
            try:
                precontrat.soumettre(user=request.user)
                messages.success(
                    request,
                    f"✅ Le précontrat {precontrat.reference} a été soumis avec succès pour validation !"
                )
                return redirect('gestion:precontrat_detail', pk=pk)
            except ValidationError as e:
                messages.error(request, f"❌ Erreur : {str(e)}")
        
        elif action == 'back':
            return redirect('gestion:precontrat_detail', pk=pk)
    
    # Récupérer les modules
    modules = precontrat.modules_proposes.all()
    
    # Calculer les totaux
    volumes = precontrat.get_volume_total()
    montant_total = precontrat.get_montant_total()
    
    # Détails par module
    modules_details = []
    for module in modules:
        modules_details.append({
                'module': module,
            'details': module.get_details_volumes()
        })
    
    context = {
        'precontrat': precontrat,
        'modules': modules,
        'modules_details': modules_details,
        'volumes': volumes,
        'montant_total': montant_total,
        'title': f'Récapitulatif - {precontrat.reference}',
    }
    
    return render(request, 'contrats/precontrats/recapitulatif.html', context)


# ==========================================
# ACTIONS SUR LES PRÉCONTRATS
# ==========================================

@login_required
@require_http_methods(["POST"])
def precontrat_soumettre(request, pk):
    """Soumet un précontrat pour validation"""
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions
    if request.user != precontrat.cree_par and request.user.role not in ['RESP_RH', 'ADMIN']:
        return JsonResponse({
            'success': False,
            'error': 'Permission refusée'
        }, status=403)
    
    try:
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
    """Valide un précontrat (RH uniquement)"""
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    # Vérifier les permissions
    if request.user.role not in ['RESP_RH', 'ADMIN']:
        return JsonResponse({
            'success': False,
            'error': 'Seuls les responsables RH peuvent valider les précontrats'
        }, status=403)
    
    try:
        notes = request.POST.get('notes', '')
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
            return redirect('contrats:precontrat_detail', pk=module.pre_contrat.pk)
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

@login_required
@role_required(['RESP_RH', 'ADMIN'])
def precontrat_submit(request, pk):
    """
    Soumettre un précontrat pour validation.
    """
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    if request.method == 'POST':
        try:
            precontrat.submit(request.user)
            messages.success(request, "📨 Précontrat soumis pour validation")
        except Exception as e:
            messages.error(request, f"❌ Erreur : {str(e)}")
        
        return redirect('contrats:precontrat_detail', pk=pk)
    
    return redirect('contrats:precontrat_detail', pk=pk)


# ============================================================================
# VUE DE SUPPRESSION D'UN PRÉCONTRAT
# ============================================================================

@login_required
@role_required(['RESP_RH', 'ADMIN'])
def precontrat_delete(request, pk):
    """
    Supprimer un précontrat (seulement si DRAFT).
    """
    precontrat = get_object_or_404(PreContrat, pk=pk)
    
    if precontrat.status != 'DRAFT':
        messages.error(request, "❌ Seuls les précontrats en brouillon peuvent être supprimés")
        return redirect('contrats:precontrat_detail', pk=pk)
    
    if request.method == 'POST':
        precontrat.delete()
        messages.success(request, "🗑️ Précontrat supprimé")
        return redirect('contrats:precontrat_list')
    
    return render(request, 'contrats/precontrat_confirm_delete.html', {
        'precontrat': precontrat
    })



# ==========================================
# VUES POUR LES CONTRATS
# ==========================================

@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def contrat_start(request, pk):
    """
    Démarrage d'un cours
    """
    contrat = get_object_or_404(Contrat, pk=pk)
    
    if request.method == 'POST':
        form = ContratStartForm(request.POST)
        
        if form.is_valid():
            try:
                type_enseignement = form.cleaned_data['type_enseignement']
                classes_tronc_commun = form.cleaned_data.get('classes_tronc_commun', [])
                
                contrat.demarrer_cours(
                    user=request.user,
                    type_enseignement=type_enseignement,
                    classes_tronc_commun=classes_tronc_commun if type_enseignement == 'TRONC_COMMUN' else None
                )
                
                messages.success(request, f"Cours démarré en mode {type_enseignement}")
                return redirect('contrat_detail', pk=contrat.pk)
                
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = ContratStartForm(initial={
            'date_debut_prevue': timezone.now().date(),
            'classe_principale': contrat.classe,
        })
    
    context = {
        'contrat': contrat,
        'form': form,
    }
    return render(request, 'contrats/contrat_start.html', context)


@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
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
        'labels': ['Cours', 'TD', 'TP'],
        'contractuel': [
            float(contrat.volume_heure_cours),
            float(contrat.volume_heure_td),
            float(contrat.volume_heure_tp),
        ],
        'effectue': [
            float(heures_effectuees['cours']),
            float(heures_effectuees['td']),
            float(heures_effectuees['tp']),
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
    Création d'un pointage pour un contrat
    """
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    
    if contrat.status != 'IN_PROGRESS':
        messages.error(request, "Ce contrat n'est pas en cours")
        return redirect('contrat_detail', pk=contrat.pk)
    
    if request.method == 'POST':
        form = PointageForm(request.POST)
        
        if form.is_valid():
            try:
                pointage = form.save(commit=False)
                pointage.contrat = contrat
                pointage.enregistre_par = request.user
                pointage.save()
                
                messages.success(
                    request,
                    f"Pointage enregistré: {pointage.total_heures}h le {pointage.date_seance}"
                )
                return redirect('contrat_detail', pk=contrat.pk)
                
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        # Pré-remplir avec la date du jour
        form = PointageForm(initial={
            'date_seance': timezone.now().date(),
        })
    
    # Calculer les heures restantes
    heures_effectuees = contrat.get_heures_effectuees()
    heures_restantes = {
        'cours': contrat.volume_heure_cours - heures_effectuees['cours'],
        'td': contrat.volume_heure_td - heures_effectuees['td'],
        'tp': contrat.volume_heure_tp - heures_effectuees['tp'],
    }
    
    context = {
        'contrat': contrat,
        'form': form,
        'heures_restantes': heures_restantes,
    }
    return render(request, 'contrats/pointage_form.html', context)


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


@login_required
@role_required(['RESP_PEDA', 'ADMIN'])
def document_upload(request, contrat_id):
    """
    Upload d'un document pour un contrat
    """
    contrat = get_object_or_404(Contrat, pk=contrat_id)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
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
    else:
        form = DocumentForm()
    
    context = {
        'contrat': contrat,
        'form': form,
    }
    return render(request, 'contrats/document_upload.html', context)


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
                'tp': float(contrat.volume_heure_tp),
                'total': float(contrat.volume_total_contractuel),
            },
            'effectue': {
                'cours': float(heures_effectuees['cours']),
                'td': float(heures_effectuees['td']),
                'tp': float(heures_effectuees['tp']),
                'total': float(contrat.volume_total_effectue),
            },
            'restant': {
                'cours': float(contrat.volume_heure_cours - heures_effectuees['cours']),
                'td': float(contrat.volume_heure_td - heures_effectuees['td']),
                'tp': float(contrat.volume_heure_tp - heures_effectuees['tp']),
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
            'taux_tp': grille.taux_tp,
        }
    except GrilleTauxHoraire.DoesNotExist:
        return None