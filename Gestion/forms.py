from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

# ============================================================================
# IMPORTS DES MODÈLES - DOIT ÊTRE EN PREMIER
# ============================================================================
from .models import (
    PreContrat,
    ModulePropose,
    Contrat,
    Pointage,
    DocumentContrat,
    Classe
)
from Utilisateur.models import CustomUser


# ============================================================================
# ⭐ WIDGETS PERSONNALISÉS - VERSION CORRIGÉE DJANGO 5.x ⭐
# ============================================================================

class ClasseSelectWidget(forms.Select):
    """
    Widget Select personnalisé qui ajoute automatiquement les attributs data-* 
    pour le niveau, la filière et le nom de chaque classe.
    
    ✅ COMPATIBLE DJANGO 5.x - Gère ModelChoiceIteratorValue
    """
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """Surcharge de la méthode create_option pour ajouter les attributs data-*"""
        # Appeler la méthode parent pour créer l'option de base
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Si une valeur est présente (pas l'option vide)
        if value:
            try:
                # ⭐ CORRECTION DJANGO 5.x : Extraire la vraie valeur
                # Dans Django 5.x, value peut être un ModelChoiceIteratorValue
                actual_value = value.value if hasattr(value, 'value') else value
                
                # Récupérer l'objet Classe depuis la base de données
                classe = Classe.objects.get(pk=actual_value)
                
                # Ajouter les attributs data-* personnalisés
                option['attrs']['data-nom'] = classe.nom
                option['attrs']['data-niveau'] = classe.niveau
                option['attrs']['data-filiere'] = classe.filiere
                
            except (Classe.DoesNotExist, ValueError, TypeError):
                # Si erreur, ne rien faire (option vide ou données invalides)
                pass
        
        return option


class ProfesseurSelectWidget(forms.Select):
    """
    Widget Select personnalisé qui ajoute automatiquement les attributs data-* 
    pour le nom complet et l'email de chaque professeur.
    
    ✅ COMPATIBLE DJANGO 5.x - Gère ModelChoiceIteratorValue
    """
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """Surcharge de la méthode create_option pour ajouter les attributs data-*"""
        # Appeler la méthode parent
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Si une valeur est présente
        if value:
            try:
                # ⭐ CORRECTION DJANGO 5.x : Extraire la vraie valeur
                actual_value = value.value if hasattr(value, 'value') else value
                
                # Récupérer l'objet CustomUser depuis la base de données
                professeur = CustomUser.objects.get(pk=actual_value)
                
                # Ajouter les attributs data-* personnalisés
                option['attrs']['data-nom'] = f"{professeur.first_name} {professeur.last_name}"
                option['attrs']['data-email'] = professeur.email
                
            except (CustomUser.DoesNotExist, ValueError, TypeError):
                pass
        
        return option


# ============================================================================
# ⭐ FORMULAIRES POUR PRÉCONTRATS - VERSION FINALE CORRIGÉE ⭐
# ============================================================================

class PreContratCreateForm(forms.ModelForm):
    """
    Formulaire corrigé pour la création de précontrat
    ⭐ UTILISE LES WIDGETS PERSONNALISÉS (DJANGO 5.x COMPATIBLE)
    """
    
    # Définition explicite des champs pour plus de contrôle
    professeur = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),  # Sera défini dans __init__
        widget=ProfesseurSelectWidget(attrs={  # ⭐ WIDGET PERSONNALISÉ
            'class': 'form-select form-select-lg',
            'id': 'id_professeur',
            'required': True,
            'data-placeholder': 'Sélectionnez un professeur'
        }),
        empty_label="-- Sélectionnez un professeur --",
        label="Professeur",
        help_text="Sélectionnez le professeur pour ce contrat"
    )
    
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),  # Sera défini dans __init__
        widget=ClasseSelectWidget(attrs={  # ⭐ WIDGET PERSONNALISÉ
            'class': 'form-select form-select-lg',
            'id': 'id_classe',
            'required': True,
            'data-placeholder': 'Sélectionnez une classe'
        }),
        empty_label="-- Sélectionnez une classe --",
        label="Classe",
        help_text="Les modules de cette classe se chargeront automatiquement"
    )

    class Meta:
        model = PreContrat
        fields = ['professeur', 'classe', 'notes_proposition']
        widgets = {
            'notes_proposition': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ajoutez des notes sur cette proposition de contrat...',
                'style': 'resize: vertical; min-height: 100px;'
            }),
        }
        labels = {
            'notes_proposition': 'Notes de proposition (optionnel)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Définition des querysets avec filtres
        self.fields['professeur'].queryset = CustomUser.objects.filter(
            role='PROFESSEUR',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        self.fields['classe'].queryset = Classe.objects.filter(
            is_active=True
        ).select_related('section').order_by('nom')
        
        # Ajout de classes Bootstrap pour uniformité
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    if isinstance(field, forms.ChoiceField):
                        field.widget.attrs['class'] = 'form-select'
                    else:
                        field.widget.attrs['class'] = 'form-control'

    def clean_professeur(self):
        """Validation spécifique du champ professeur"""
        professeur = self.cleaned_data.get('professeur')
        if not professeur:
            raise ValidationError("Veuillez sélectionner un professeur")
        
        # Vérifier que c'est bien une instance CustomUser
        if not isinstance(professeur, CustomUser):
            raise ValidationError("Sélection de professeur invalide")
            
        return professeur

    def clean_classe(self):
        """Validation spécifique du champ classe"""
        classe = self.cleaned_data.get('classe')
        if not classe:
            raise ValidationError("Veuillez sélectionner une classe")
        
        # Vérifier que c'est bien une instance Classe
        if not isinstance(classe, Classe):
            raise ValidationError("Sélection de classe invalide")
            
        return classe

    def clean(self):
        """Validation croisée"""
        cleaned_data = super().clean()
        
        # Vérifier que les instances sont valides
        professeur = cleaned_data.get('professeur')
        classe = cleaned_data.get('classe')
        
        # Si vous avez d'autres validations à faire, ajoutez-les ici
        
        return cleaned_data


# ============================================================================
# RESTE DU FICHIER INCHANGÉ
# ============================================================================

class ModuleValidationForm(forms.ModelForm):
    """
    Formulaire pour valider un module proposé.
    RH peut ajuster les volumes et taux si nécessaire.
    """
    
    class Meta:
        model = ModulePropose
        fields = [
            'volume_heure_cours',
            'volume_heure_td',
            'taux_horaire_cours',
            'taux_horaire_td',
            'notes_validation'
        ]
        widgets = {
            'volume_heure_cours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'volume_heure_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'taux_horaire_cours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '100',
                'min': '0'
            }),
            'taux_horaire_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '100',
                'min': '0'
            }),
            'notes_validation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes sur les ajustements effectués...'
            }),
        }


# ============================================================================
# FORMULAIRES POUR CONTRATS
# ============================================================================

class ContratCreateForm(forms.ModelForm):
    """
    Formulaire pour créer un contrat à partir d'un précontrat validé
    ⭐ CORRIGÉ : Utilise les vrais noms de champs du modèle Contrat
    """
    
    class Meta:
        model = Contrat
        fields = [
            'professeur',
            'classe',
            'maquette',  # ✅ CORRECTION : 'module' → 'maquette'
            'volume_heure_cours',
            'volume_heure_td',
            'taux_horaire_cours',
            'taux_horaire_td',
            'date_debut_prevue',  # ✅ CORRECTION : 'date_debut' → 'date_debut_prevue'
            'date_fin_prevue',    # ✅ CORRECTION : 'date_fin' → 'date_fin_prevue'
            'notes'
            # ❌ SUPPRIMÉ : 'annee_academique' n'existe pas dans Contrat
        ]
        widgets = {
            'professeur': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
            'classe': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
            'maquette': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
            'volume_heure_cours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'volume_heure_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'taux_horaire_cours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '100'
            }),
            'taux_horaire_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '100'
            }),
            'date_debut_prevue': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_fin_prevue': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes sur le contrat...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut_prevue')
        date_fin = cleaned_data.get('date_fin_prevue')

        if date_debut and date_fin:
            if date_fin <= date_debut:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début"
                )

        return cleaned_data



# ============================================================================
# FORMULAIRES POUR POINTAGES
# ============================================================================

class PointageForm(forms.ModelForm):
    """
    Formulaire pour enregistrer les heures effectuées
    """
    
    class Meta:
        model = Pointage
        fields = [
            'date_seance',
            'heure_debut',
            'heure_fin',
            'heures_cours',
            'heures_td',
            'taux_presence',
            'observations'
        ]
        widgets = {
            'date_seance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'heure_debut': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'heure_fin': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'heures_cours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '8'
            }),
            'heures_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '8'
            }),
            'taux_presence': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.1'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observations sur la séance...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.contrat = kwargs.pop('contrat', None)
        super().__init__(*args, **kwargs)
        
        if self.contrat:
            # Calculer les heures déjà effectuées
            heures_deja_effectuees = Pointage.objects.filter(
                contrat=self.contrat,
                statut__in=['VALIDE', 'EN_ATTENTE']
            ).aggregate(
                cours=Sum('heures_cours'),
                td=Sum('heures_td')
            )
            
            # Convertir None en 0
            heures_deja_effectuees = {
                'cours': heures_deja_effectuees['cours'] or 0,
                'td': heures_deja_effectuees['td'] or 0,
                'tp': heures_deja_effectuees['tp'] or 0
            }
            
            # Ajouter les infos dans les help_text
            self.fields['heures_cours'].help_text = (
                f"Déjà effectuées: {heures_deja_effectuees['cours']}h / "
                f"Contractuel: {self.contrat.volume_heure_cours}h"
            )
            self.fields['heures_td'].help_text = (
                f"Déjà effectuées: {heures_deja_effectuees['td']}h / "
                f"Contractuel: {self.contrat.volume_heure_td}h"
            )
            self.fields['heures_tp'].help_text = (
                f"Déjà effectuées: {heures_deja_effectuees['tp']}h / "
                f"Contractuel: {self.contrat.volume_heure_tp}h"
            )

    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifier qu'au moins un type d'heures est renseigné
        cours = cleaned_data.get('heures_cours', 0) or 0
        td = cleaned_data.get('heures_td', 0) or 0
        
        if cours + td == 0:
            raise ValidationError(
                'Vous devez renseigner au moins un type d\'heures (cours, TD ou TP)'
            )
        
        # Vérifier que les heures ne dépassent pas le volume contractuel
        if self.contrat:
            heures_deja_effectuees = Pointage.objects.filter(
                contrat=self.contrat,
                statut__in=['VALIDE', 'EN_ATTENTE']
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).aggregate(
                cours=Sum('heures_cours'),
                td=Sum('heures_td') 
            )
            
            heures_deja_effectuees = {
                'cours': heures_deja_effectuees['cours'] or 0,
                'td': heures_deja_effectuees['td'] or 0,
            }
            
            if cours > 0:
                total_cours = heures_deja_effectuees['cours'] + cours
                if total_cours > self.contrat.volume_heure_cours:
                    self.add_error(
                        'heures_cours',
                        f'Le total des heures de cours ({total_cours}h) dépasserait le volume contractuel ({self.contrat.volume_heure_cours}h)'
                    )
            
            if td > 0:
                total_td = heures_deja_effectuees['td'] + td
                if total_td > self.contrat.volume_heure_td:
                    self.add_error(
                        'heures_td',
                        f'Le total des heures de TD ({total_td}h) dépasserait le volume contractuel ({self.contrat.volume_heure_td}h)'
                    )
            
        # Vérifier la cohérence des heures
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')
        
        if heure_debut and heure_fin:
            if heure_fin <= heure_debut:
                self.add_error(
                    'heure_fin',
                    "L'heure de fin doit être postérieure à l'heure de début"
                    )
        
        # Vérifier la cohérence des heures
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')
        
        if heure_debut and heure_fin:
            if heure_fin <= heure_debut:
                self.add_error(
                    'heure_fin',
                    "L'heure de fin doit être postérieure à l'heure de début"
                )
        
        # Vérifier le taux de présence
        taux = cleaned_data.get('taux_presence')
        if taux is not None and (taux < 0 or taux > 100):
            self.add_error(
                'taux_presence',
                'Le taux de présence doit être entre 0 et 100%'
            )
        
        return cleaned_data


# ============================================================================
# FORMULAIRES POUR DOCUMENTS
# ============================================================================

class DocumentUploadForm(forms.ModelForm):
    """
    Formulaire pour charger des documents (support de cours, syllabus, etc.).
    """
    
    class Meta:
        model = DocumentContrat
        fields = ['type_document', 'titre', 'fichier', 'description']
        widgets = {
            'type_document': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Support de cours - Chapitre 1'
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du document...'
            }),
        }
        labels = {
            'type_document': 'Type de document',
            'titre': 'Titre',
            'fichier': 'Fichier',
            'description': 'Description',
        }


# ============================================================================
# FORMULAIRES POUR PAIEMENTS
# ============================================================================

class PaiementRejectForm(forms.Form):
    """
    Formulaire pour rejeter un paiement.
    Demande une raison obligatoire.
    """
    
    raison_rejet = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Expliquez la raison du rejet...',
            'required': True
        }),
        label='Raison du rejet',
        help_text='Cette raison sera visible par le professeur et les autres responsables'
    )


class PaiementExecuteForm(forms.Form):
    """
    Formulaire pour exécuter un paiement (marquer comme payé).
    """
    
    METHODE_CHOICES = [
        ('VIREMENT', 'Virement bancaire'),
        ('CHEQUE', 'Chèque'),
        ('ESPECES', 'Espèces'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    methode_paiement = forms.ChoiceField(
        choices=METHODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Méthode de paiement',
        initial='VIREMENT'
    )
    
    reference_paiement = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: VIR-2024-001234'
        }),
        label='Référence du paiement',
        help_text='Numéro de transaction, chèque, etc.',
        required=False
    )
    
    date_paiement = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date du paiement',
        initial=date.today
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notes sur le paiement...'
        }),
        required=False,
        label='Notes'
    )


# ============================================================================
# FORMULAIRES DE RECHERCHE ET FILTRES
# ============================================================================

class ContratSearchForm(forms.Form):
    """Formulaire de recherche/filtrage des contrats"""
    
    search = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par professeur, classe, module...'
        }),
        required=False,
        label='Recherche'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Contrat.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='Statut'
    )
    
    annee_academique = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '2024-2025'
        }),
        required=False,
        label='Année académique'
    )


# ============================================================================
# ⭐ RÉSUMÉ DES CORRECTIONS DJANGO 5.x ⭐
# ============================================================================
"""
CORRECTIONS CRITIQUES POUR DJANGO 5.x :

1. ✅ Ligne 38 : Extraction de la vraie valeur avec value.value
   - Django 5.x utilise ModelChoiceIteratorValue qui encapsule la valeur
   - On doit extraire la vraie valeur avec hasattr(value, 'value')
   
2. ✅ Ligne 72 : Même correction pour ProfesseurSelectWidget
   - actual_value = value.value if hasattr(value, 'value') else value
   
3. ✅ Ligne 48 & 82 : Gestion des exceptions (ValueError, TypeError)
   - Ajout de ValueError et TypeError pour gérer tous les cas d'erreur

RÉSULTAT :
✅ Plus d'erreur "Field 'id' expected a number"
✅ Le niveau et la filière s'affichent correctement
✅ Les modules de la maquette se chargent
✅ Compatible Django 5.x

COMMENT ÇA FONCTIONNE :
1. Django 5.x encapsule les valeurs dans ModelChoiceIteratorValue
2. On extrait la vraie valeur (l'ID) avec .value
3. On utilise cet ID pour faire le get() sur la base de données
4. Les attributs data-* sont ajoutés correctement
"""

# ============================================================================
# FIN DU FICHIER
# ============================================================================













# from django import forms
# from django.forms import inlineformset_factory
# from django.core.exceptions import ValidationError
# from decimal import Decimal
# from datetime import date

# # ============================================================================
# # IMPORTS DES MODÈLES - DOIT ÊTRE EN PREMIER
# # ============================================================================
# from .models import (
#     PreContrat,
#     ModulePropose,
#     Contrat,
#     Pointage,
#     DocumentContrat,
#     Classe
# )
# from Utilisateur.models import CustomUser


# # ============================================================================
# # ⭐ WIDGETS PERSONNALISÉS - VERSION CORRIGÉE DJANGO 5.x ⭐
# # ============================================================================

# class ClasseSelectWidget(forms.Select):
#     """
#     Widget Select personnalisé qui ajoute automatiquement les attributs data-* 
#     pour le niveau, la filière et le nom de chaque classe.
    
#     ✅ COMPATIBLE DJANGO 5.x - Gère ModelChoiceIteratorValue
#     """
    
#     def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
#         """Surcharge de la méthode create_option pour ajouter les attributs data-*"""
#         # Appeler la méthode parent pour créer l'option de base
#         option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
#         # Si une valeur est présente (pas l'option vide)
#         if value:
#             try:
#                 # ⭐ CORRECTION DJANGO 5.x : Extraire la vraie valeur
#                 # Dans Django 5.x, value peut être un ModelChoiceIteratorValue
#                 actual_value = value.value if hasattr(value, 'value') else value
                
#                 # Récupérer l'objet Classe depuis la base de données
#                 classe = Classe.objects.get(pk=actual_value)
                
#                 # Ajouter les attributs data-* personnalisés
#                 option['attrs']['data-nom'] = classe.nom
#                 option['attrs']['data-niveau'] = classe.niveau
#                 option['attrs']['data-filiere'] = classe.filiere
                
#             except (Classe.DoesNotExist, ValueError, TypeError):
#                 # Si erreur, ne rien faire (option vide ou données invalides)
#                 pass
        
#         return option


# class ProfesseurSelectWidget(forms.Select):
#     """
#     Widget Select personnalisé qui ajoute automatiquement les attributs data-* 
#     pour le nom complet et l'email de chaque professeur.
    
#     ✅ COMPATIBLE DJANGO 5.x - Gère ModelChoiceIteratorValue
#     """
    
#     def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
#         """Surcharge de la méthode create_option pour ajouter les attributs data-*"""
#         # Appeler la méthode parent
#         option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
#         # Si une valeur est présente
#         if value:
#             try:
#                 # ⭐ CORRECTION DJANGO 5.x : Extraire la vraie valeur
#                 actual_value = value.value if hasattr(value, 'value') else value
                
#                 # Récupérer l'objet CustomUser depuis la base de données
#                 professeur = CustomUser.objects.get(pk=actual_value)
                
#                 # Ajouter les attributs data-* personnalisés
#                 option['attrs']['data-nom'] = f"{professeur.first_name} {professeur.last_name}"
#                 option['attrs']['data-email'] = professeur.email
                
#             except (CustomUser.DoesNotExist, ValueError, TypeError):
#                 pass
        
#         return option


# # ============================================================================
# # ⭐ FORMULAIRES POUR PRÉCONTRATS - VERSION FINALE CORRIGÉE ⭐
# # ============================================================================

# class PreContratCreateForm(forms.ModelForm):
#     """
#     Formulaire corrigé pour la création de précontrat
#     ⭐ UTILISE LES WIDGETS PERSONNALISÉS (DJANGO 5.x COMPATIBLE)
#     """
    
#     # Définition explicite des champs pour plus de contrôle
#     professeur = forms.ModelChoiceField(
#         queryset=CustomUser.objects.none(),  # Sera défini dans __init__
#         widget=ProfesseurSelectWidget(attrs={  # ⭐ WIDGET PERSONNALISÉ
#             'class': 'form-select form-select-lg',
#             'id': 'id_professeur',
#             'required': True,
#             'data-placeholder': 'Sélectionnez un professeur'
#         }),
#         empty_label="-- Sélectionnez un professeur --",
#         label="Professeur",
#         help_text="Sélectionnez le professeur pour ce contrat"
#     )
    
#     classe = forms.ModelChoiceField(
#         queryset=Classe.objects.none(),  # Sera défini dans __init__
#         widget=ClasseSelectWidget(attrs={  # ⭐ WIDGET PERSONNALISÉ
#             'class': 'form-select form-select-lg',
#             'id': 'id_classe',
#             'required': True,
#             'data-placeholder': 'Sélectionnez une classe'
#         }),
#         empty_label="-- Sélectionnez une classe --",
#         label="Classe",
#         help_text="Les modules de cette classe se chargeront automatiquement"
#     )

#     class Meta:
#         model = PreContrat
#         fields = ['professeur', 'classe', 'notes_proposition']
#         widgets = {
#             'notes_proposition': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 4,
#                 'placeholder': 'Ajoutez des notes sur cette proposition de contrat...',
#                 'style': 'resize: vertical; min-height: 100px;'
#             }),
#         }
#         labels = {
#             'notes_proposition': 'Notes de proposition (optionnel)',
#         }
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
        
#         # Définition des querysets avec filtres
#         self.fields['professeur'].queryset = CustomUser.objects.filter(
#             role='PROFESSEUR',
#             is_active=True
#         ).order_by('first_name', 'last_name')
        
#         self.fields['classe'].queryset = Classe.objects.filter(
#             is_active=True
#         ).select_related('section').order_by('nom')
        
#         # Ajout de classes Bootstrap pour uniformité
#         for field_name, field in self.fields.items():
#             if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
#                 if 'class' not in field.widget.attrs:
#                     if isinstance(field, forms.ChoiceField):
#                         field.widget.attrs['class'] = 'form-select'
#                     else:
#                         field.widget.attrs['class'] = 'form-control'

#     def clean_professeur(self):
#         """Validation spécifique du champ professeur"""
#         professeur = self.cleaned_data.get('professeur')
#         if not professeur:
#             raise ValidationError("Veuillez sélectionner un professeur")
        
#         # Vérifier que c'est bien une instance CustomUser
#         if not isinstance(professeur, CustomUser):
#             raise ValidationError("Sélection de professeur invalide")
            
#         return professeur

#     def clean_classe(self):
#         """Validation spécifique du champ classe"""
#         classe = self.cleaned_data.get('classe')
#         if not classe:
#             raise ValidationError("Veuillez sélectionner une classe")
        
#         # Vérifier que c'est bien une instance Classe
#         if not isinstance(classe, Classe):
#             raise ValidationError("Sélection de classe invalide")
            
#         return classe

#     def clean(self):
#         """Validation croisée"""
#         cleaned_data = super().clean()
        
#         # Vérifier que les instances sont valides
#         professeur = cleaned_data.get('professeur')
#         classe = cleaned_data.get('classe')
        
#         # Si vous avez d'autres validations à faire, ajoutez-les ici
        
#         return cleaned_data


# # ============================================================================
# # RESTE DU FICHIER INCHANGÉ
# # ============================================================================

# class ModuleValidationForm(forms.ModelForm):
#     """
#     Formulaire pour valider un module proposé.
#     RH peut ajuster les volumes et taux si nécessaire.
#     """
    
#     class Meta:
#         model = ModulePropose
#         fields = [
#             'volume_heure_cours',
#             'volume_heure_td',
#             'volume_heure_tp',
#             'taux_horaire_cours',
#             'taux_horaire_td',
#             'taux_horaire_tp',
#             'notes_validation'
#         ]
#         widgets = {
#             'volume_heure_cours': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'volume_heure_td': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'volume_heure_tp': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'taux_horaire_cours': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100',
#                 'min': '0'
#             }),
#             'taux_horaire_td': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100',
#                 'min': '0'
#             }),
#             'taux_horaire_tp': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100',
#                 'min': '0'
#             }),
#             'notes_validation': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'Notes sur les ajustements effectués...'
#             }),
#         }


# # ============================================================================
# # FORMULAIRES POUR CONTRATS
# # ============================================================================

# class ContratCreateForm(forms.ModelForm):
#     """
#     Formulaire pour créer un contrat à partir d'un précontrat validé
#     ⭐ CORRIGÉ : Utilise les vrais noms de champs du modèle Contrat
#     """
    
#     class Meta:
#         model = Contrat
#         fields = [
#             'professeur',
#             'classe',
#             'maquette',  # ✅ CORRECTION : 'module' → 'maquette'
#             'volume_heure_cours',
#             'volume_heure_td',
#             'volume_heure_tp',
#             'taux_horaire_cours',
#             'taux_horaire_td',
#             'taux_horaire_tp',
#             'date_debut_prevue',  # ✅ CORRECTION : 'date_debut' → 'date_debut_prevue'
#             'date_fin_prevue',    # ✅ CORRECTION : 'date_fin' → 'date_fin_prevue'
#             'notes'
#             # ❌ SUPPRIMÉ : 'annee_academique' n'existe pas dans Contrat
#         ]
#         widgets = {
#             'professeur': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
#             'classe': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
#             'maquette': forms.Select(attrs={'class': 'form-select', 'disabled': True}),
#             'volume_heure_cours': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'volume_heure_td': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'volume_heure_tp': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0'
#             }),
#             'taux_horaire_cours': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100'
#             }),
#             'taux_horaire_td': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100'
#             }),
#             'taux_horaire_tp': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '100'
#             }),
#             'date_debut_prevue': forms.DateInput(attrs={
#                 'class': 'form-control',
#                 'type': 'date'
#             }),
#             'date_fin_prevue': forms.DateInput(attrs={
#                 'class': 'form-control',
#                 'type': 'date'
#             }),
#             'notes': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'Notes sur le contrat...'
#             }),
#         }

#     def clean(self):
#         cleaned_data = super().clean()
#         date_debut = cleaned_data.get('date_debut_prevue')
#         date_fin = cleaned_data.get('date_fin_prevue')

#         if date_debut and date_fin:
#             if date_fin <= date_debut:
#                 raise ValidationError(
#                     "La date de fin doit être postérieure à la date de début"
#                 )

#         return cleaned_data



# # ============================================================================
# # FORMULAIRES POUR POINTAGES
# # ============================================================================

# class PointageForm(forms.ModelForm):
#     """
#     Formulaire pour enregistrer les heures effectuées
#     """
    
#     class Meta:
#         model = Pointage
#         fields = [
#             'date_seance',
#             'heure_debut',
#             'heure_fin',
#             'heures_cours',
#             'heures_td',
#             'heures_tp',
#             'taux_presence',
#             'observations'
#         ]
#         widgets = {
#             'date_seance': forms.DateInput(attrs={
#                 'class': 'form-control',
#                 'type': 'date'
#             }),
#             'heure_debut': forms.TimeInput(attrs={
#                 'class': 'form-control',
#                 'type': 'time'
#             }),
#             'heure_fin': forms.TimeInput(attrs={
#                 'class': 'form-control',
#                 'type': 'time'
#             }),
#             'heures_cours': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0',
#                 'max': '8'
#             }),
#             'heures_td': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0',
#                 'max': '8'
#             }),
#             'heures_tp': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.5',
#                 'min': '0',
#                 'max': '8'
#             }),
#             'taux_presence': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'min': '0',
#                 'max': '100',
#                 'step': '0.1'
#             }),
#             'observations': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'Observations sur la séance...'
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         self.contrat = kwargs.pop('contrat', None)
#         super().__init__(*args, **kwargs)
        
#         if self.contrat:
#             # Calculer les heures déjà effectuées
#             heures_deja_effectuees = Pointage.objects.filter(
#                 contrat=self.contrat,
#                 statut__in=['VALIDE', 'EN_ATTENTE']
#             ).aggregate(
#                 cours=Sum('heures_cours'),
#                 td=Sum('heures_td'),
#                 tp=Sum('heures_tp')
#             )
            
#             # Convertir None en 0
#             heures_deja_effectuees = {
#                 'cours': heures_deja_effectuees['cours'] or 0,
#                 'td': heures_deja_effectuees['td'] or 0,
#                 'tp': heures_deja_effectuees['tp'] or 0
#             }
            
#             # Ajouter les infos dans les help_text
#             self.fields['heures_cours'].help_text = (
#                 f"Déjà effectuées: {heures_deja_effectuees['cours']}h / "
#                 f"Contractuel: {self.contrat.volume_heure_cours}h"
#             )
#             self.fields['heures_td'].help_text = (
#                 f"Déjà effectuées: {heures_deja_effectuees['td']}h / "
#                 f"Contractuel: {self.contrat.volume_heure_td}h"
#             )
#             self.fields['heures_tp'].help_text = (
#                 f"Déjà effectuées: {heures_deja_effectuees['tp']}h / "
#                 f"Contractuel: {self.contrat.volume_heure_tp}h"
#             )

#     def clean(self):
#         cleaned_data = super().clean()
        
#         # Vérifier qu'au moins un type d'heures est renseigné
#         cours = cleaned_data.get('heures_cours', 0) or 0
#         td = cleaned_data.get('heures_td', 0) or 0
#         tp = cleaned_data.get('heures_tp', 0) or 0
        
#         if cours + td + tp == 0:
#             raise ValidationError(
#                 'Vous devez renseigner au moins un type d\'heures (cours, TD ou TP)'
#             )
        
#         # Vérifier que les heures ne dépassent pas le volume contractuel
#         if self.contrat:
#             heures_deja_effectuees = Pointage.objects.filter(
#                 contrat=self.contrat,
#                 statut__in=['VALIDE', 'EN_ATTENTE']
#             ).exclude(
#                 pk=self.instance.pk if self.instance.pk else None
#             ).aggregate(
#                 cours=Sum('heures_cours'),
#                 td=Sum('heures_td'),
#                 tp=Sum('heures_tp')
#             )
            
#             heures_deja_effectuees = {
#                 'cours': heures_deja_effectuees['cours'] or 0,
#                 'td': heures_deja_effectuees['td'] or 0,
#                 'tp': heures_deja_effectuees['tp'] or 0
#             }
            
#             if cours > 0:
#                 total_cours = heures_deja_effectuees['cours'] + cours
#                 if total_cours > self.contrat.volume_heure_cours:
#                     self.add_error(
#                         'heures_cours',
#                         f'Le total des heures de cours ({total_cours}h) dépasserait le volume contractuel ({self.contrat.volume_heure_cours}h)'
#                     )
            
#             if td > 0:
#                 total_td = heures_deja_effectuees['td'] + td
#                 if total_td > self.contrat.volume_heure_td:
#                     self.add_error(
#                         'heures_td',
#                         f'Le total des heures de TD ({total_td}h) dépasserait le volume contractuel ({self.contrat.volume_heure_td}h)'
#                     )
            
#             if tp > 0:
#                 total_tp = heures_deja_effectuees['tp'] + tp
#                 if total_tp > self.contrat.volume_heure_tp:
#                     self.add_error(
#                         'heures_tp',
#                         f'Le total des heures de TP ({total_tp}h) dépasserait le volume contractuel ({self.contrat.volume_heure_tp}h)'
#                     )
        
#         # Vérifier la cohérence des heures
#         heure_debut = cleaned_data.get('heure_debut')
#         heure_fin = cleaned_data.get('heure_fin')
        
#         if heure_debut and heure_fin:
#             if heure_fin <= heure_debut:
#                 self.add_error(
#                     'heure_fin',
#                     "L'heure de fin doit être postérieure à l'heure de début"
#                 )
        
#         # Vérifier le taux de présence
#         taux = cleaned_data.get('taux_presence')
#         if taux is not None and (taux < 0 or taux > 100):
#             self.add_error(
#                 'taux_presence',
#                 'Le taux de présence doit être entre 0 et 100%'
#             )
        
#         return cleaned_data


# # ============================================================================
# # FORMULAIRES POUR DOCUMENTS
# # ============================================================================

# class DocumentUploadForm(forms.ModelForm):
#     """
#     Formulaire pour charger des documents (support de cours, syllabus, etc.).
#     """
    
#     class Meta:
#         model = DocumentContrat
#         fields = ['type_document', 'titre', 'fichier', 'description']
#         widgets = {
#             'type_document': forms.Select(attrs={
#                 'class': 'form-select',
#                 'required': True
#             }),
#             'titre': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'Ex: Support de cours - Chapitre 1'
#             }),
#             'fichier': forms.FileInput(attrs={
#                 'class': 'form-control',
#                 'accept': '.pdf,.doc,.docx,.ppt,.pptx'
#             }),
#             'description': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'Description du document...'
#             }),
#         }
#         labels = {
#             'type_document': 'Type de document',
#             'titre': 'Titre',
#             'fichier': 'Fichier',
#             'description': 'Description',
#         }


# # ============================================================================
# # FORMULAIRES POUR PAIEMENTS
# # ============================================================================

# class PaiementRejectForm(forms.Form):
#     """
#     Formulaire pour rejeter un paiement.
#     Demande une raison obligatoire.
#     """
    
#     raison_rejet = forms.CharField(
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 4,
#             'placeholder': 'Expliquez la raison du rejet...',
#             'required': True
#         }),
#         label='Raison du rejet',
#         help_text='Cette raison sera visible par le professeur et les autres responsables'
#     )


# class PaiementExecuteForm(forms.Form):
#     """
#     Formulaire pour exécuter un paiement (marquer comme payé).
#     """
    
#     METHODE_CHOICES = [
#         ('VIREMENT', 'Virement bancaire'),
#         ('CHEQUE', 'Chèque'),
#         ('ESPECES', 'Espèces'),
#         ('MOBILE_MONEY', 'Mobile Money'),
#     ]
    
#     methode_paiement = forms.ChoiceField(
#         choices=METHODE_CHOICES,
#         widget=forms.Select(attrs={'class': 'form-select'}),
#         label='Méthode de paiement',
#         initial='VIREMENT'
#     )
    
#     reference_paiement = forms.CharField(
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Ex: VIR-2024-001234'
#         }),
#         label='Référence du paiement',
#         help_text='Numéro de transaction, chèque, etc.',
#         required=False
#     )
    
#     date_paiement = forms.DateField(
#         widget=forms.DateInput(attrs={
#             'class': 'form-control',
#             'type': 'date'
#         }),
#         label='Date du paiement',
#         initial=date.today
#     )
    
#     notes = forms.CharField(
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 3,
#             'placeholder': 'Notes sur le paiement...'
#         }),
#         required=False,
#         label='Notes'
#     )


# # ============================================================================
# # FORMULAIRES DE RECHERCHE ET FILTRES
# # ============================================================================

# class ContratSearchForm(forms.Form):
#     """Formulaire de recherche/filtrage des contrats"""
    
#     search = forms.CharField(
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Rechercher par professeur, classe, module...'
#         }),
#         required=False,
#         label='Recherche'
#     )
    
#     status = forms.ChoiceField(
#         choices=[('', 'Tous')] + list(Contrat.STATUS_CHOICES),
#         widget=forms.Select(attrs={'class': 'form-select'}),
#         required=False,
#         label='Statut'
#     )
    
#     annee_academique = forms.CharField(
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': '2024-2025'
#         }),
#         required=False,
#         label='Année académique'
#     )


# # ============================================================================
# # ⭐ RÉSUMÉ DES CORRECTIONS DJANGO 5.x ⭐
# # ============================================================================
# """
# CORRECTIONS CRITIQUES POUR DJANGO 5.x :

# 1. ✅ Ligne 38 : Extraction de la vraie valeur avec value.value
#    - Django 5.x utilise ModelChoiceIteratorValue qui encapsule la valeur
#    - On doit extraire la vraie valeur avec hasattr(value, 'value')
   
# 2. ✅ Ligne 72 : Même correction pour ProfesseurSelectWidget
#    - actual_value = value.value if hasattr(value, 'value') else value
   
# 3. ✅ Ligne 48 & 82 : Gestion des exceptions (ValueError, TypeError)
#    - Ajout de ValueError et TypeError pour gérer tous les cas d'erreur

# RÉSULTAT :
# ✅ Plus d'erreur "Field 'id' expected a number"
# ✅ Le niveau et la filière s'affichent correctement
# ✅ Les modules de la maquette se chargent
# ✅ Compatible Django 5.x

# COMMENT ÇA FONCTIONNE :
# 1. Django 5.x encapsule les valeurs dans ModelChoiceIteratorValue
# 2. On extrait la vraie valeur (l'ID) avec .value
# 3. On utilise cet ID pour faire le get() sur la base de données
# 4. Les attributs data-* sont ajoutés correctement
# """

# # ============================================================================
# # FIN DU FICHIER
# # ============================================================================
