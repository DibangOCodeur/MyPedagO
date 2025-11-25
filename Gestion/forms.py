from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from django.db.models import Sum
from .models import Groupe

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
        fields = ['professeur', 'classe']
    
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
# Dans forms.py - Créez un nouveau formulaire

class PointageForm(forms.ModelForm):
    """
    Formulaire pour enregistrer les heures effectuées avec sélection des groupes
    """
    
    # ⭐ CORRECTION : Ce champ n'est pas dans le modèle, c'est un champ personnalisé
    groupes_selection = forms.ModelMultipleChoiceField(
        queryset=Groupe.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '5'
        }),
        label="Groupes concernés",
        help_text="Sélectionnez les groupes pour ce pointage"
    )
    
    class Meta:
        model = Pointage
        fields = [  # ⭐ CORRECTION : Ne pas inclure groupes_selection ici
            'date_seance',
            'heure_debut', 
            'heure_fin',
            'heures_cours',
            'heures_td',
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
                'max': '8',
                'placeholder': '0.0'
            }),
            'heures_td': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '8',
                'placeholder': '0.0'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.contrat = kwargs.pop('contrat', None)
        super().__init__(*args, **kwargs)
        
        if self.contrat:
            # Remplir le queryset avec les groupes du contrat
            groupes = self.contrat.get_all_groupes()
            self.fields['groupes_selection'].queryset = Groupe.objects.filter(
                id__in=[g.id for g in groupes]
            )
            
            # Sélectionner tous les groupes par défaut
            self.fields['groupes_selection'].initial = [g.id for g in groupes]

    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifications existantes...
        cours = cleaned_data.get('heures_cours', 0) or 0
        td = cleaned_data.get('heures_td', 0) or 0

        if cours + td == 0:
            raise ValidationError(
                'Vous devez renseigner au moins un type d\'heures (cours ou TD)'
            )
        
        # Vérifier qu'au moins un groupe est sélectionné
        groupes = cleaned_data.get('groupes_selection')
        if not groupes:
            raise ValidationError('Vous devez sélectionner au moins un groupe')
        
        return cleaned_data

    # ⭐ CORRECTION : Méthode save pour gérer la relation ManyToMany
    def save(self, commit=True):
        # Sauvegarder d'abord l'instance Pointage
        pointage = super().save(commit=False)
        
        if commit:
            pointage.save()
            # Sauvegarder la relation ManyToMany avec les groupes
            if hasattr(self, 'save_m2m'):
                self.save_m2m()
            else:
                # Si save_m2m n'existe pas, sauvegarder manuellement
                groupes_selectionnes = self.cleaned_data.get('groupes_selection', [])
                pointage.groupes.set(groupes_selectionnes)
        
        return pointage
#==============================================
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

from django import forms
from django.utils import timezone
from .models import Contrat, Classe, Groupe

class ContratStartForm(forms.Form):
    """
    Formulaire pour démarrer un contrat avec sélection des groupes
    """
    type_enseignement = forms.ChoiceField(
        choices=Contrat.TYPE_ENSEIGNEMENT_CHOICES,
        initial='NORMAL',
        label="Type d'enseignement",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_type_enseignement',
            'onchange': 'toggleGroupSelection()'  # JavaScript pour basculer l'affichage
        })
    )
    
    date_debut_prevue = forms.DateField(
        initial=timezone.now().date,
        label="Date de début prévue",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    # Groupes de la classe principale
    groupes_classe_principale = forms.ModelMultipleChoiceField(
        queryset=Groupe.objects.none(),
        required=False,
        label="Groupes de la classe principale",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_groupes_principale'
        }),
        help_text="Sélectionnez les groupes pour ce cours"
    )
    
    # Classes en tronc commun (EXISTANT)
    classes_tronc_commun = forms.ModelMultipleChoiceField(
        queryset=Classe.objects.none(),
        required=False,
        label="Classes en tronc commun",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_classes_tronc_commun'
        }),
        help_text="Sélectionnez les classes supplémentaires pour le tronc commun"
    )
    
    # Groupes des classes en tronc commun
    groupes_tronc_commun = forms.ModelMultipleChoiceField(
        queryset=Groupe.objects.none(),
        required=False,
        label="Groupes des classes en tronc commun",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_groupes_tronc_commun'
        }),
        help_text="Sélectionnez les groupes des classes en tronc commun"
    )
    
    def __init__(self, *args, **kwargs):
        self.contrat = kwargs.pop('contrat', None)
        super().__init__(*args, **kwargs)
        
        if self.contrat:
            # Groupes de la classe principale
            self.fields['groupes_classe_principale'].queryset = Groupe.objects.filter(
                classe=self.contrat.classe,
                is_active=True
            ).order_by('nom')
            
            # Classes en tronc commun (exclure la classe principale)
            self.fields['classes_tronc_commun'].queryset = Classe.objects.filter(
                is_active=True
            ).exclude(id=self.contrat.classe.id)
            
            # Initialiser les groupes des classes en tronc commun
            self.fields['groupes_tronc_commun'].queryset = Groupe.objects.filter(
                is_active=True
            )




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


#=====================================
# DOCUMENT CONTRAT
#=====================================
from django import forms
from .models import DocumentContrat
import os

class DocumentContratForm(forms.ModelForm):
    """Formulaire pour l'upload de documents de contrat"""
    
    class Meta:
        model = DocumentContrat
        fields = ['type_document', 'titre', 'fichier', 'description']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du document'
            }),
            'type_document': forms.Select(attrs={
                'class': 'form-control'
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du document (optionnel)'
            }),
        }
        labels = {
            'fichier': 'Fichier à uploader',
            'type_document': 'Type de document'
        }
    
    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            # Validation de la taille (20MB max)
            if fichier.size > 20 * 1024 * 1024:
                raise forms.ValidationError("Le fichier est trop volumineux (max 20MB)")
            
            # Validation de l'extension
            ext = os.path.splitext(fichier.name)[1].lower()
            extensions_valides = [
                '.pdf', '.doc', '.docx', '.ppt', '.pptx', 
                '.jpg', '.jpeg', '.png', '.xls', '.xlsx', '.txt'
            ]
            
            if ext not in extensions_valides:
                raise forms.ValidationError(
                    f"Type de fichier non supporté. Formats acceptés: {', '.join(extensions_valides)}"
                )
        
        return fichier
    
    def clean_titre(self):
        titre = self.cleaned_data.get('titre')
        if titre and len(titre) < 3:
            raise forms.ValidationError("Le titre doit contenir au moins 3 caractères")
        return titre