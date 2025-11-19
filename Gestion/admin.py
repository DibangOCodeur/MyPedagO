from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (
    Classe, Maquette, PreContrat, ModulePropose, Contrat,
    Pointage, DocumentContrat, PaiementContrat, ActionLog, Groupe
)
from Utilisateur.models import CustomUser

from decimal import Decimal
from django.urls import reverse

# ==========================================
# ADMIN CLASSE
# ==========================================

@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'nom', 'filiere', 'niveau', 'departement', 
        'effectif_total', 'nombre_groupes', 'is_active'
    ]
    list_filter = ['is_active', 'departement', 'annee_academique', 'niveau']
    search_fields = ['nom', 'filiere', 'niveau', 'departement']
    readonly_fields = ['external_id', 'raw_data', 'last_synced', 'created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('external_id', 'nom', 'description')
        }),
        ('Informations académiques', {
            'fields': (
                'filiere', 'niveau', 'departement', 
                'annee_academique', 'annee_etat'
            )
        }),
        ('Statistiques', {
            'fields': ('nombre_groupes', 'effectif_total')
        }),
        ('Association', {
            'fields': ('section',)
        }),
        ('Données techniques', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Statut et dates', {
            'fields': ('is_active', 'last_synced', 'created_at', 'updated_at')
        }),
    )


# ==========================================
# GROUPE ADMIN
# ==========================================
# Dans Gestion/admin.py - VERSION SIMPLIFIÉE
from django.contrib import admin
from .models import Groupe

@admin.register(Groupe)
class GroupeAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 
        'classe', 
        'code', 
        'effectif', 
        'capacite_max',
        'is_active',
        'last_synced'
    ]
    
    list_filter = [
        'is_active',
        'classe',
        'last_synced'
    ]
    
    search_fields = [
        'nom',
        'code',
        'classe__nom'
    ]
    
    readonly_fields = [
        'external_id',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Informations principales', {
            'fields': (
                'external_id',
                'classe',
                'nom',
                'code'
            )
        }),
        ('Effectifs', {
            'fields': (
                'effectif',
                'capacite_max',
                'taux_remplissage'
            )
        }),
        ('Statut', {
            'fields': (
                'is_active',
                'last_synced'
            )
        })
    )
# ==========================================
# ADMIN MAQUETTE
# ==========================================

@admin.register(Maquette)
class MaquetteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'filiere_sigle', 'niveau_libelle', 'annee_academique',
        'parcour', 'classe', 'is_active'
    ]
    list_filter = ['is_active', 'parcour', 'annee_academique', 'filiere_nom']
    search_fields = ['filiere_nom', 'filiere_sigle', 'niveau_libelle']
    readonly_fields = [
        'external_id', 'filiere_id', 'niveau_id', 'anneeacademique_id',
        'date_creation_api', 'raw_data', 'last_synced', 'created_at', 'updated_at'
    ]
    list_per_page = 25
    
    fieldsets = (
        ('Informations principales', {
            'fields': (
                'external_id', 'filiere_nom', 'filiere_sigle',
                'niveau_libelle', 'annee_academique', 'parcour'
            )
        }),
        ('IDs de référence', {
            'fields': ('filiere_id', 'niveau_id', 'anneeacademique_id')
        }),
        ('Association', {
            'fields': ('classe',)
        }),
        ('Unités d\'enseignement', {
            'fields': ('unites_enseignement',),
            'classes': ('collapse',)
        }),
        ('Données techniques', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'date_creation_api', 'is_active', 
                'last_synced', 'created_at', 'updated_at'
            )
        }),
    )


# ==========================================
# INLINES
# ==========================================

class ModuleProposeInline(admin.TabularInline):
    model = ModulePropose
    extra = 0
    fields = [
        'code_module', 'nom_module', 'ue_nom',
        'volume_heure_cours', 'volume_heure_td',
        'taux_horaire_cours', 'taux_horaire_td',
        'est_valide'
    ]
    readonly_fields = ['date_creation', 'date_validation']
    
    def has_delete_permission(self, request, obj=None):

        if obj is None:
            return True
        
        return obj.status == 'DRAFT'

class PointageInline(admin.TabularInline):
    model = Pointage
    extra = 0
    fields = [
        'date_seance', 'heures_cours', 'heures_td',
        'est_valide'
    ]
    readonly_fields = ['enregistre_par', 'date_enregistrement']


class DocumentContratInline(admin.TabularInline):
    model = DocumentContrat
    extra = 0
    fields = [
        'type_document', 'titre', 'fichier',
        'est_valide', 'date_upload'
    ]
    readonly_fields = ['charge_par', 'date_upload']


class PaiementContratInline(admin.TabularInline):
    model = PaiementContrat
    extra = 0
    fields = [
        'montant_brut', 'montant_deductions', 'montant_net',
        'status', 'mode_paiement', 'date_creation'
    ]
    readonly_fields = ['date_creation', 'cree_par']
    
    def has_add_permission(self, request, obj=None):
        return False


# ==========================================
# ADMIN PRÉCONTRAT
# ==========================================

@admin.register(PreContrat)
class PreContratAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'professeur', 'classe_display', 'status_badge',
        'modules_count', 'modules_valides_count',
        'date_creation', 'cree_par'
    ]
    list_filter = [
        'status', 'date_creation', 'date_soumission'
    ]
    search_fields = [
        'reference',
        'professeur__first_name', 'professeur__last_name',
        'professeur__email',
        'classe__nom', 'classe_nom'
    ]
    readonly_fields = [
        'id', 'reference',
        'classe_nom', 'classe_niveau', 'classe_filiere',
        'date_creation', 'date_soumission', 'date_validation', 'date_modification',
        'modules_count', 'modules_valides_count', 'progression_bar',
        'volume_total_display', 'montant_total_display'
    ]
    inlines = [ModuleProposeInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': (
                'id', 'reference', 'status', 'annee_academique'
            )
        }),
        ('Professeur et Classe', {
            'fields': (
                'professeur', 'classe',
                ('classe_nom', 'classe_niveau', 'classe_filiere')
            )
        }),
        ('Résumé', {
            'fields': (
                'modules_count', 'modules_valides_count',
                'progression_bar',
                'volume_total_display',
                'montant_total_display'
            )
        }),
        ('Traçabilité', {
            'fields': (
                'cree_par', 'valide_par',
                'date_creation', 'date_soumission', 
                'date_validation', 'date_modification'
            )
        }),
    )
    
    actions = ['soumettre_precontrats', 'valider_precontrats']
    
    def classe_display(self, obj):
        """Affiche les informations de la classe"""
        return format_html(
            '<strong>{}</strong><br><small>{} - {}</small>',
            obj.classe_nom or obj.classe.nom,
            obj.classe_niveau or '',
            obj.classe_filiere or ''
        )
    classe_display.short_description = 'Classe'
    
    def status_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'DRAFT': '#6c757d',
            'SUBMITTED': '#0dcaf0',
            'UNDER_REVIEW': '#ffc107',
            'VALIDATED': '#198754',
            'REJECTED': '#dc3545',
            'CANCELLED': '#343a40',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def modules_count(self, obj):
        """Nombre total de modules"""
        return obj.nombre_modules
    modules_count.short_description = 'Modules'
    
    def modules_valides_count(self, obj):
        """Nombre de modules validés"""
        count = obj.modules_valides_count
        total = obj.nombre_modules
        if count == total and total > 0:
            return format_html('<span style="color: green;">✓ {}/{}</span>', count, total)
        return f'{count}/{total}'
    modules_valides_count.short_description = 'Validés'
    
    def progression_bar(self, obj):
        """Barre de progression"""
        total = obj.nombre_modules
        if total == 0:
            return "Aucun module"
        
        valides = obj.modules_valides_count
        percentage = (valides / total) * 100
        
        color = '#198754' if percentage == 100 else '#ffc107' if percentage > 0 else '#dc3545'
        
        return format_html(
            '<div style="width: 200px; background: #e9ecef; border-radius: 10px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 10px; '
            'text-align: center; color: white; line-height: 20px;">'
            '{}%'
            '</div>'
            '</div>',
            percentage, color, int(percentage)
        )
    progression_bar.short_description = 'Progression'
    
    def volume_total_display(self, obj):
        """Affiche le volume horaire total"""
        volumes = obj.get_volume_total()
        return format_html(
            '<strong>Total: {}h</strong><br>'
            '<small>CM: {}h | TD: {}h</small>',
            volumes['total'],
            volumes['cours'],
            volumes['td'],
        )
    volume_total_display.short_description = 'Volumes'
    
    def montant_total_display(self, obj):
        """Affiche le montant total"""
        montant = obj.get_montant_total()
        return format_html(
            '<strong style="color: #198754; font-size: 14px;">{:,.0f} FCFA</strong>',
            montant
        )
    montant_total_display.short_description = 'Montant'
    
    def soumettre_precontrats(self, request, queryset):
        """Action pour soumettre plusieurs précontrats"""
        count = 0
        for precontrat in queryset:
            if precontrat.peut_etre_soumis:
                try:
                    precontrat.soumettre(user=request.user)
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Erreur: {str(e)}', level='error')
        
        if count > 0:
            self.message_user(request, f'{count} précontrat(s) soumis.')
    soumettre_precontrats.short_description = 'Soumettre les précontrats sélectionnés'
    
    def valider_precontrats(self, request, queryset):
        """Action pour valider plusieurs précontrats"""
        if not request.user.role in ['RESP_RH', 'ADMIN']:
            self.message_user(request, "Permission refusée", level='error')
            return
        
        count = 0
        for precontrat in queryset:
            if precontrat.peut_etre_valide:
                try:
                    precontrat.valider(user=request.user)
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Erreur: {str(e)}', level='error')
        
        if count > 0:
            self.message_user(request, f'{count} précontrat(s) validé(s).')
    valider_precontrats.short_description = 'Valider les précontrats sélectionnés'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('professeur', 'classe', 'cree_par', 'valide_par')\
                .prefetch_related('modules_proposes')  # ⭐ AJOUT pour optimiser les requêtes


# ==========================================
# ADMIN MODULE PROPOSÉ
# ==========================================
@admin.register(ModulePropose)
class ModuleProposeAdmin(admin.ModelAdmin):
    list_display = [
        'code_module', 'nom_module', 'pre_contrat_ref',
        'ue_nom', 'volume_total_display', 'montant_display',
        'est_valide_badge','date_creation'
    ]
    list_filter = [
        'est_valide', 'date_creation'
    ]
    search_fields = [
        'code_module', 'nom_module', 'ue_nom',
        'pre_contrat__reference'
    ]
    readonly_fields = [
        'date_creation', 'date_validation',
        'volume_total_display', 'montant_display'
    ]
    
    fieldsets = (
        ('Module', {
            'fields': (
                'pre_contrat', 'code_module', 'nom_module', 'ue_nom'
            )
        }),
        ('Volumes', {
            'fields': (
                ('volume_heure_cours', 'taux_horaire_cours'),
                ('volume_heure_td', 'taux_horaire_td'),
                'volume_total_display'
            )
        }),
        ('Montant', {
            'fields': ('montant_display',)
        }),
        ('Validation', {
            'fields': (
                'est_valide',
                'date_validation'
            )
        }),
        ('Dates', {
            'fields': ('date_creation',)
        }),
    )
    
    def pre_contrat_ref(self, obj):
        """Lien vers le précontrat"""
        if obj.pre_contrat:
            url = reverse('admin:Gestion_precontrat_change', args=[obj.pre_contrat.pk])
            return format_html('<a href="{}">{}</a>', url, obj.pre_contrat.reference)
        return "-"
    pre_contrat_ref.short_description = "Précontrat"
    
    def volume_total_display(self, obj):
        """Volume total"""
        return format_html(
            '<strong>{}h</strong><br><small>CM:{}h | TD:{}h</small>',
            obj.volume_total,
            obj.volume_heure_cours,
            obj.volume_heure_td,
        )
    volume_total_display.short_description = "Volumes"
    
    def montant_display(self, obj):
        """Montant - VERSION CORRIGÉE ET SÉCURISÉE"""
        try:
            montant = obj.get_montant_total()
            if montant is None:
                montant = Decimal('0')
            
            montant_formate = "{:,.0f}".format(float(montant))
            
            return format_html(
                '<strong style="color: #198754;">{} FCFA</strong>',
                montant_formate
            )
        except (AttributeError, ValueError, TypeError):
            return format_html('<span style="color: #dc3545;">N/A</span>')
    montant_display.short_description = "Montant"
    
    def est_valide_badge(self, obj):
        """Badge de validation"""
        if obj.est_valide:
            return format_html(
                '<span style="background: #198754; color: white; padding: 3px 10px; '
                'border-radius: 10px; font-size: 11px;">✓ Validé</span>'
            )
        return format_html(
            '<span style="background: #ffc107; color: black; padding: 3px 10px; '
            'border-radius: 10px; font-size: 11px;">⏱ En attente</span>'
        )
    est_valide_badge.short_description = "Validation"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('pre_contrat')


# ==========================================
# ADMIN CONTRAT
# ==========================================

@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'professeur', 'classe', 'maquette',
        'status_badge', 'type_enseignement',
        'volumes_display', 'date_validation'
    ]
    list_filter = [
        'status', 'type_enseignement', 
        'date_debut_prevue', 'date_fin_prevue'
    ]
    search_fields = [
        'professeur__user__first_name',
        'professeur__user__last_name',
        'classe__nom',
        'notes'
    ]
    readonly_fields = [
        'module_propose', 'date_validation', 'valide_par',
        'date_demarrage', 'demarre_par',
        'created_at', 'updated_at',
        'volumes_display', 'montant_contractuel_display'
    ]
    inlines = [PointageInline, DocumentContratInline, PaiementContratInline]
    
    fieldsets = (
        ('Informations principales', {
            'fields': (
                'module_propose', 'professeur', 'classe', 
                'maquette', 'status'
            )
        }),
        ('Type d\'enseignement', {
            'fields': (
                'type_enseignement', 'classes_tronc_commun'
            )
        }),
        ('Volumes contractuels', {
            'fields': (
                ('volume_heure_cours', 'taux_horaire_cours'),
                ('volume_heure_td', 'taux_horaire_td'),
                'volumes_display',
                'montant_contractuel_display'
            )
        }),
        ('Dates', {
            'fields': (
                ('date_debut_prevue', 'date_debut_reelle'),
                ('date_fin_prevue', 'date_fin_reelle')
            )
        }),
        ('Validation', {
            'fields': ('valide_par', 'date_validation')
        }),
        ('Démarrage', {
            'fields': ('demarre_par', 'date_demarrage')
        }),
        ('Documents', {
            'fields': ('support_cours_uploaded', 'syllabus_uploaded')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Badge de statut"""
        colors = {
            'VALIDATED': '#0dcaf0',
            'READY_TO_START': '#6610f2',
            'IN_PROGRESS': '#0d6efd',
            'COMPLETED': '#198754',
            'PENDING_DOCUMENTS': '#ffc107',
            'READY_FOR_PAYMENT': '#20c997',
            'PAID': '#198754',
            'CANCELLED': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def volumes_display(self, obj):
        """Affiche les volumes"""
        total = obj.volume_heure_cours + obj.volume_heure_td
        return format_html(
            '<strong>Total: {}h</strong><br>'
            '<small>CM: {}h | TD: {}h</small>',
            total,
            obj.volume_heure_cours,
            obj.volume_heure_td,
        )
    volumes_display.short_description = 'Volumes'
    
    def montant_contractuel_display(self, obj):
        """Affiche le montant contractuel"""
        try:
            montant_cours = (obj.volume_heure_cours or Decimal('0')) * (obj.taux_horaire_cours or Decimal('0'))
            montant_td = (obj.volume_heure_td or Decimal('0')) * (obj.taux_horaire_td or Decimal('0'))
            montant_total = montant_cours + montant_td
            
            return format_html(
                '<strong style="color: #198754; font-size: 14px;">{:,.0f} FCFA</strong>',
                float(montant_total)
            )
        except (TypeError, ValueError):
            return format_html('<span style="color: #dc3545;">Erreur de calcul</span>')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'professeur', 'professeur__user', 'classe', 
            'maquette', 'valide_par', 'demarre_par'
        )

    def groupes_count(self, obj):
        """Affiche le nombre de groupes sélectionnés"""
        count = obj.groupes_selectionnes.count()
        return format_html(
            '<span class="badge bg-primary">{}</span>',
            count
        )
    groupes_count.short_description = 'Groupes'
    
    # Ajouter le filtre par groupes
    list_filter = [
        'status', 'type_enseignement', 
        'date_debut_prevue', 'date_fin_prevue',
        'groupes_selectionnes'  # ⭐ NOUVEAU
    ]


# ==========================================
# ADMIN POINTAGE
# ==========================================

@admin.register(Pointage)
class PointageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'contrat', 'date_seance',
        'heures_display', 'est_valide',
        'date_enregistrement'
    ]
    list_filter = [
        'est_valide', 'date_seance', 'date_enregistrement'
       
    ]
    search_fields = [
        'contrat__professeur__user__first_name',
        'contrat__professeur__user__last_name',
    ]
    readonly_fields = [
        'enregistre_par', 'date_enregistrement',
        'created_at', 'updated_at'
    ]
    
    def groupes_count(self, obj):
        """Affiche le nombre de groupes pour ce pointage"""
        count = obj.groupes.count()
        return format_html(
            '<span class="badge bg-info">{}</span>',
            count
        )
    groupes_count.short_description = 'Groupes'

    
    fieldsets = (
        ('Contrat', {
            'fields': ('contrat',)
        }),
        ('Séance', {
            'fields': (
                'date_seance', 'heure_debut', 'heure_fin',
            )
        }),
        ('Heures effectuées', {
            'fields': (
                'heures_cours', 'heures_td'
            )
        }),
        ('Groupes', {
            'fields': ('groupes',)
        }),
        ('Enregistrement', {
            'fields': ('enregistre_par', 'date_enregistrement')
        }),
        ('Validation', {
            'fields': ('est_valide',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def heures_display(self, obj):
        """Affiche les heures"""
        total = (obj.heures_cours or 0) + (obj.heures_td or 0)
        return format_html(
            '<strong>{}h</strong><br><small>CM:{}h TD:{}h</small>',
            total,
            obj.heures_cours or 0,
            obj.heures_td or 0
        )
    heures_display.short_description = 'Heures'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.enregistre_par = request.user
        
        super().save_model(request, obj, form, change)


# ==========================================
# ADMIN DOCUMENT CONTRAT
# ==========================================

@admin.register(DocumentContrat)
class DocumentContratAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'contrat', 'type_document', 'titre',
        'fichier_link', 'est_valide', 'date_upload'
    ]
    list_filter = [
        'type_document', 'est_valide',
        'date_upload', 'date_validation'
    ]
    search_fields = [
        'contrat__professeur__user__first_name',
        'contrat__professeur__user__last_name',
        'titre', 'description'
    ]
    readonly_fields = [
        'charge_par', 'date_upload', 'valide_par',
        'date_validation', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Contrat', {
            'fields': ('contrat',)
        }),
        ('Document', {
            'fields': (
                'type_document', 'titre', 'fichier', 'description'
            )
        }),
        ('Upload', {
            'fields': ('charge_par', 'date_upload')
        }),
        ('Validation', {
            'fields': (
                'est_valide', 'valide_par', 'date_validation'
            )
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def fichier_link(self, obj):
        """Lien vers le fichier"""
        if obj.fichier:
            return format_html(
                '<a href="{}" target="_blank">📄 Télécharger</a>',
                obj.fichier.url
            )
        return '-'
    fichier_link.short_description = 'Fichier'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.charge_par = request.user
        
        if change and 'est_valide' in form.changed_data and obj.est_valide:
            obj.valide_par = request.user
            obj.date_validation = timezone.now()
        
        super().save_model(request, obj, form, change)


# ==========================================
# ADMIN PAIEMENT
# ==========================================

@admin.register(PaiementContrat)
class PaiementContratAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'professeur', 'contrat_display',
        'montant_net_display', 'status_badge',
        'mode_paiement', 'date_creation', 'date_paiement'
    ]
    list_filter = [
        'status', 'mode_paiement', 'date_creation',
        'date_paiement', 'date_approbation'
    ]
    search_fields = [
        'professeur__user__first_name',
        'professeur__user__last_name',
        'reference_paiement', 'notes'
    ]
    readonly_fields = [
        'cree_par', 'date_creation', 'approuve_par',
        'date_approbation', 'paye_par', 'date_paiement',
        'created_at', 'updated_at', 'montant_net_calcule'
    ]
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('contrat', 'professeur', 'status')
        }),
        ('Montants', {
            'fields': (
                'montant_brut', 'montant_deductions',
                'montant_net', 'montant_net_calcule'
            )
        }),
        ('Paiement', {
            'fields': (
                'mode_paiement', 'reference_paiement'
            )
        }),
        ('Création', {
            'fields': ('cree_par', 'date_creation')
        }),
        ('Approbation', {
            'fields': ('approuve_par', 'date_approbation')
        }),
        ('Exécution', {
            'fields': ('paye_par', 'date_paiement')
        }),
        ('Notes', {
            'fields': ('notes', 'raison_rejet'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approuver_paiements']
    
    def contrat_display(self, obj):
        """Lien vers le contrat"""
        url = reverse('admin:Gestion_contrat_change', args=[obj.contrat.id])
        return format_html('<a href="{}">Contrat #{}</a>', url, obj.contrat.id)
    contrat_display.short_description = 'Contrat'
    
    def montant_net_display(self, obj):
        """Montant net"""
        return format_html(
            '<strong style="font-size: 14px; color: #198754;">{:,.0f} FCFA</strong>',
            obj.montant_net
        )
    montant_net_display.short_description = 'Montant net'
    
    def montant_net_calcule(self, obj):
        """Montant net calculé"""
        montant = obj.montant_brut - obj.montant_deductions
        return format_html('{:,.0f} FCFA', montant)
    montant_net_calcule.short_description = 'Montant net (calculé)'
    
    def status_badge(self, obj):
        """Badge de statut"""
        colors = {
            'PENDING': '#f59e0b',
            'APPROVED': '#3b82f6',
            'PROCESSING': '#8b5cf6',
            'PAID': '#22c55e',
            'REJECTED': '#ef4444',
            'CANCELLED': '#6b7280',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def approuver_paiements(self, request, queryset):
        """Approuve les paiements sélectionnés"""
        count = 0
        for paiement in queryset:
            if paiement.status == 'PENDING':
                try:
                    paiement.approuver(request.user)
                    count += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f'Erreur pour le paiement #{paiement.id}: {str(e)}',
                        level='error'
                    )
        
        if count > 0:
            self.message_user(
                request,
                f'{count} paiement(s) approuvé(s) avec succès.'
            )
    approuver_paiements.short_description = 'Approuver les paiements sélectionnés'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# ADMIN ACTION LOG
# ==========================================

@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'action_display', 'user', 'timestamp',
        'pre_contrat', 'contrat', 'paiement',
        'details_short'
    ]
    list_filter = [
        'action', 'timestamp'
    ]
    search_fields = [
        'user__first_name', 'user__last_name',
        'details'
    ]
    readonly_fields = [
        'pre_contrat', 'module_propose', 'contrat',
        'paiement', 'action', 'user', 'timestamp', 'details'
    ]
    
    fieldsets = (
        ('Action', {
            'fields': ('action', 'user', 'timestamp')
        }),
        ('Objets concernés', {
            'fields': (
                'pre_contrat', 'module_propose',
                'contrat', 'paiement'
            )
        }),
        ('Détails', {
            'fields': ('details',)
        }),
    )
    
    def action_display(self, obj):
        """Affiche l'action avec badge"""
        return format_html(
            '<span style="background: #0d6efd; color: white; padding: 3px 8px; '
            'border-radius: 8px; font-size: 11px;">{}</span>',
            obj.get_action_display()
        )
    action_display.short_description = 'Action'
    
    def details_short(self, obj):
        """Détails tronqués"""
        if obj.details:
            return obj.details[:50] + '...' if len(obj.details) > 50 else obj.details
        return '-'
    details_short.short_description = 'Détails'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False