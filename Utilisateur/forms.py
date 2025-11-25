
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date
from django_countries.widgets import CountrySelectWidget
from .models import (
    Section, CustomUser, Professeur,
    Comptable, GradesProfesseurs,
    StatusProfesseurs, SituationMatrimoniale, GenreProfesseurs
)

#=========================================
# LOGIN
#=========================================
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError


class LoginForm(forms.Form):
    """Formulaire de connexion"""
    
    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Entrez votre email',
            'autofocus': True,
            'required': True
        })
    )
    
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Entrez votre mot de passe',
            'required': True
        })
    )
    
    remember_me = forms.BooleanField(
        label='Se souvenir de moi',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_email(self):
        """Normaliser l'email"""
        email = self.cleaned_data.get('email')
        if email:
            return email.lower().strip()
        return email
    
    def clean(self):
        """Validation globale"""
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            # Vérifier que l'utilisateur existe (sans révéler trop d'informations)
            from .models import CustomUser
            try:
                user = CustomUser.objects.get(email=email)
                # Vérifier le mot de passe
                if not user.check_password(password):
                    raise ValidationError('Email ou mot de passe incorrect.')
            except CustomUser.DoesNotExist:
                raise ValidationError('Email ou mot de passe incorrect.')
        
        return cleaned_data


# ========================================
# WIDGETS PERSONNALISÉS
# ========================================

class DatePickerInput(forms.DateInput):
    """Widget de sélection de date avec calendrier"""
    input_type = 'date'
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({
            'class': 'form-control',
            'placeholder': 'jj/mm/aaaa'
        })
        super().__init__(*args, **kwargs)


class CustomFileInput(forms.FileInput):
    """Widget de sélection de fichier personnalisé"""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})
        kwargs['attrs'].update({
            'class': 'form-control-file',
            'accept': kwargs.pop('accept', None)
        })
        super().__init__(*args, **kwargs)


# ========================================
# FORMULAIRE SECTION
# ========================================

class SectionForm(forms.ModelForm):
    """Formulaire de création/modification de section"""
    
    class Meta:
        model = Section
        fields = [
            'nom', 'adresse', 'telephone', 'email',
            'responsable_nom', 'is_active'
        ]
        widgets = {
            'nom': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète de la section'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+225XXXXXXXXXX ou 10 chiffres',
                'pattern': r'^(\+225)?\d{10}$'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'responsable_nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du responsable de la section'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'nom': 'Nom de la section',
            'adresse': 'Adresse',
            'telephone': 'Téléphone',
            'email': 'Email de contact',
            'responsable_nom': 'Responsable',
            'is_active': 'Section active'
        }
    
    def clean_telephone(self):
        """Validation du numéro de téléphone"""
        telephone = self.cleaned_data.get('telephone')
        if telephone and len(telephone.replace('+225', '').replace(' ', '')) != 10:
            raise ValidationError("Le numéro de téléphone doit contenir 10 chiffres.")
        return telephone


class SectionSearchForm(forms.Form):
    """Formulaire de recherche de sections"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher une section...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('active', 'Actives'), ('inactive', 'Inactives')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ========================================
# FORMULAIRES UTILISATEUR
# ========================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import (
    CustomUser, Section, Professeur, 
    GradesProfesseurs, StatusProfesseurs, GenreProfesseurs,
    SituationMatrimoniale
)
from datetime import date
import logging
logger = logging.getLogger(__name__)


class CustomUserCreationWithDocumentsForm(UserCreationForm):
    """
    Formulaire de création d'utilisateur avec gestion des documents
    Version adaptée pour les responsables pédagogiques
    """
    
    # Champs de base utilisateur
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Prénom(s)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le prénom'})
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entrez le nom'})
    )
    
    email = forms.EmailField(
        required=True,
        label="Adresse email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'clovis.anoman@iipea.com'})
    )
    
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        label="Rôle",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_role'})
    )
    
    telephone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+225 0102030405'})
    )
    
    section_principale = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Section principale",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sections_autorisees = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Sections autorisées",
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'})
    )
    
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Laisser vide pour mot de passe par défaut'}),
        required=False,
        help_text="Laissez vide pour utiliser le mot de passe par défaut (@elites@)"
    )
    
    password2 = forms.CharField(
        label="Confirmation",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmez le mot de passe'}),
        required=False
    )
    

    # Champs spécifiques PROFESSEUR
    date_naissance_prof = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    statut = forms.ChoiceField(
        choices=StatusProfesseurs.choices,
        required=False,
        label="Statut",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    genre = forms.ChoiceField(
        choices=GenreProfesseurs.choices,
        required=False,
        label="Genre",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    grade = forms.ChoiceField(
        choices=[('', '---------')] + list(GradesProfesseurs.choices),
        required=False,
        label="Grade",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_grade'
        })
    )

    diplome = forms.CharField(
        max_length=100,
        required=False,
        label="Diplôme",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_diplome',
            'readonly': 'readonly'
        })
    )

    nationalite = forms.CharField(
        max_length=100,
        required=False,
        label="Nationalité",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_nationalite',
            'placeholder': 'Sélectionnez une nationalité'
        })
    )
        
    numero_cni = forms.CharField(
        max_length=20,
        required=False,
        label="Numéro CNI",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CI00000000'})
    )
    
    situation_matrimoniale = forms.ChoiceField(
        choices=SituationMatrimoniale.choices,
        required=False,
        label="Situation matrimoniale",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    domicile = forms.CharField(
        max_length=200,
        required=False,
        label="Adresse de domicile",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse complète'})
    )
    
    specialite = forms.CharField(
        max_length=100,
        required=False,
        label="Spécialité",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mathématiques'})
    )

    annee_experience = forms.IntegerField(
        initial=0,
        min_value=0,
        required=True,
        label="Années d'expérience",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'required': 'required'
        }),
        error_messages={
            'min_value': 'Les années d\'expérience doivent être positives.',
            'required': 'Ce champ est obligatoire pour les professeurs.'
        }
    )
    
    sections_enseignement = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Sections d'enseignement",
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'})
    )
    
    # Documents PROFESSEUR
    photo = forms.ImageField(
        required=False,
        label="Photo de profil",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/jpg,image/png'}),
        help_text="Format: JPG, PNG (max 10MB)"
    )
    
    cni_document = forms.FileField(
        required=False,
        label="Carte Nationale d'Identité (CNI)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'}),
        help_text="Format: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    
    rib_document = forms.FileField(
        required=False,
        label="Relevé d'Identité Bancaire (RIB)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'}),
        help_text="Format: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    
    cv_document = forms.FileField(
        required=False,
        label="Curriculum Vitae (CV)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        help_text="Format: PDF, DOC, DOCX (max 10MB)"
    )
    
    diplome_document = forms.FileField(
        required=False,
        label="Diplôme(s)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'}),
        help_text="Format: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    
    # Champs spécifiques COMPTABLE
    date_naissance_compta = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'role', 'telephone',
            'section_principale', 'sections_autorisees',
            'password1', 'password2'
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Récupérer l'utilisateur connecté
        super().__init__(*args, **kwargs)
        
        # Appliquer les restrictions selon le rôle
        if self.user:
            if self.user.role == 'RESP_PEDA':
                self._apply_resp_peda_restrictions()
            elif self.user.role == 'ADMIN':
                self._apply_admin_permissions()
        
        self.fields['password1'].required = False
        self.fields['password2'].required = False
    
    def _apply_resp_peda_restrictions(self):
        """Appliquer les restrictions pour les responsables pédagogiques"""
        logger.info("Application des restrictions RESP_PEDA")
        
        # Forcer le rôle à PROFESSEUR et désactiver le champ
        self.fields['role'].initial = 'PROFESSEUR'
        self.fields['role'].disabled = True
        self.fields['role'].help_text = "Les responsables pédagogiques ne peuvent créer que des professeurs"
        
        # Limiter les sections aux sections accessibles
        sections_accessibles = self.user.get_sections_disponibles()
        if sections_accessibles:
            self.fields['sections_enseignement'].queryset = sections_accessibles
            self.fields['section_principale'].queryset = sections_accessibles
            self.fields['sections_autorisees'].queryset = sections_accessibles
            
            # Définir la section principale par défaut si une seule section accessible
            if sections_accessibles.count() == 1:
                self.fields['section_principale'].initial = sections_accessibles.first()
        else:
            # Si aucune section accessible, désactiver les champs de sections
            self.fields['sections_enseignement'].disabled = True
            self.fields['section_principale'].disabled = True
            self.fields['sections_autorisees'].disabled = True
            self.fields['sections_enseignement'].help_text = "Aucune section accessible"
        
        # Masquer les champs spécifiques aux comptables
        comptable_fields = ['date_naissance_compta']
        for field in comptable_fields:
            if field in self.fields:
                del self.fields[field]
        
        # Ajuster les labels et help_texts
        self.fields['sections_enseignement'].help_text = "Sélectionnez les sections où ce professeur interviendra"
        self.fields['sections_enseignement'].required = True
        
    def _apply_admin_permissions(self):
        """Permissions complètes pour l'admin"""
        # L'admin a accès à tout, pas de restrictions
        pass
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError("Cet email est déjà utilisé.")
        return email
    
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 10 * 1024 * 1024:
                raise ValidationError("La taille de la photo ne doit pas dépasser 10MB.")
            ext = photo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                raise ValidationError("Format non supporté. Utilisez JPG, JPEG ou PNG.")
        return photo
    
    def _validate_document(self, document, nom_document, extensions=None):
        if document:
            if document.size > 10 * 1024 * 1024:
                raise ValidationError(f"La taille du {nom_document} ne doit pas dépasser 10MB.")
            ext = document.name.split('.')[-1].lower()
            if extensions is None:
                extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
            if ext not in extensions:
                raise ValidationError(f"Format non supporté pour {nom_document}.")
        return document
    
    def clean_cni_document(self):
        return self._validate_document(self.cleaned_data.get('cni_document'), 'CNI')
    
    def clean_rib_document(self):
        return self._validate_document(self.cleaned_data.get('rib_document'), 'RIB')
    
    def clean_cv_document(self):
        return self._validate_document(self.cleaned_data.get('cv_document'), 'CV', ['pdf', 'doc', 'docx'])
    
    def clean_diplome_document(self):
        return self._validate_document(self.cleaned_data.get('diplome_document'), 'Diplôme')

    def clean_annee_experience(self):
        annee_experience = self.cleaned_data.get('annee_experience')
        if annee_experience is not None and annee_experience < 0:
            raise ValidationError("Les années d'expérience doivent être positives.")
        return annee_experience
    
    def clean_date_naissance_prof(self):
        date_naissance = self.cleaned_data.get('date_naissance_prof')
        if date_naissance:
            if date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            age = (date.today() - date_naissance).days // 365
            if age < 18 or age > 100:
                raise ValidationError("L'âge doit être compris entre 18 et 100 ans.")
        return date_naissance
    
    def clean_date_naissance_compta(self):
        date_naissance = self.cleaned_data.get('date_naissance_compta')
        if date_naissance:
            if date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            age = (date.today() - date_naissance).days // 365
            if age < 16 or age > 100:
                raise ValidationError("L'âge doit être compris entre 16 et 100 ans.")
        return date_naissance
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        # Validation spécifique pour RESP_PEDA
        if self.user and self.user.role == 'RESP_PEDA':
            # Forcer le rôle à PROFESSEUR
            if role != 'PROFESSEUR':
                raise ValidationError("Les responsables pédagogiques ne peuvent créer que des professeurs.")
            
            # Vérifier les sections d'enseignement
            sections_enseignement = cleaned_data.get('sections_enseignement', [])
            sections_accessibles = self.user.get_sections_disponibles()
            
            if not sections_enseignement:
                raise ValidationError({
                    'sections_enseignement': "Au moins une section d'enseignement est requise."
                })
            
            # Vérifier que toutes les sections sélectionnées sont accessibles
            for section in sections_enseignement:
                if section not in sections_accessibles:
                    raise ValidationError({
                        'sections_enseignement': f"Vous n'avez pas accès à la section '{section.nom}'."
                    })
        
        # Validation du mot de passe
        if password1 or password2:
            if password1 != password2:
                raise ValidationError({'password2': "Les mots de passe ne correspondent pas."})
        
        # Validation selon le rôle
        if role == 'PROFESSEUR':
            date_naissance = cleaned_data.get('date_naissance_prof')
            if not date_naissance:
                raise ValidationError({
                    'date_naissance_prof': "La date de naissance est obligatoire pour un professeur."
                })
            
            sections_enseignement = cleaned_data.get('sections_enseignement')
            if not sections_enseignement:
                raise ValidationError({
                    'sections_enseignement': "Au moins une section d'enseignement est requise."
                })
        
        if role == 'COMPTABLE':
            date_naissance = cleaned_data.get('date_naissance_compta')
            if not date_naissance:
                raise ValidationError({
                    'date_naissance_compta': "La date de naissance est obligatoire pour un comptable."
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_password('@elites@')
        
        if commit:
            user.save()
            self.save_m2m()
        
        return user



class UserSearchForm(forms.Form):
    """Formulaire de recherche d'utilisateurs"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, email...'
        })
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les rôles')] + list(CustomUser.ROLE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('active', 'Actifs'), ('inactive', 'Inactifs')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class UserPasswordChangeForm(PasswordChangeForm):
    """Formulaire de changement de mot de passe utilisateur"""
    
    old_password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe actuel'
        })
    )
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        })
    )
    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )


# ========================================
# FORMULAIRES PROFESSEUR
# ========================================

class ProfesseurForm(forms.ModelForm):
    """Formulaire de création/modification de professeur"""
    
    # Champs supplémentaires pour l'utilisateur
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    first_name = forms.CharField(
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom'
        })
    )
    telephone_user = forms.CharField(
        label="Téléphone",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225XXXXXXXXXX'
        })
    )
    
    class Meta:
        model = Professeur
        fields = [
            'grade', 'statut', 'genre', 'nationalite', 'numero_cni',
            'situation_matrimoniale', 'domicile', 'date_naissance',
            'specialite', 'diplome', 'annee_experience', 'sections',
            'section_active', 'is_active'
        ]
        widgets = {
            'grade': forms.Select(attrs={
                'class': 'form-control'
            }),
            'statut': forms.Select(attrs={
                'class': 'form-control'
            }),
            'genre': forms.Select(attrs={
                'class': 'form-control'
            }),
            'nationalite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ivoirienne'
            }),
            'numero_cni': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro CNI'
            }),
            'situation_matrimoniale': forms.Select(attrs={
                'class': 'form-control'
            }),
            'domicile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse de domicile'
            }),
            'date_naissance': DatePickerInput(),
            'specialite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Domaine de spécialité'
            }),
            'diplome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dernier diplôme obtenu'
            }),
            'annee_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Années d\'expérience'
            }),
            'sections': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),
            'section_active': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les sections actives
        self.fields['sections'].queryset = Section.objects.filter(is_active=True)
        self.fields['section_active'].queryset = Section.objects.filter(is_active=True)
        
        # Si modification, pré-remplir les champs utilisateur
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['telephone_user'].initial = self.instance.user.telephone
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # Pour la création uniquement
            if not self.instance.pk:
                if CustomUser.objects.filter(email=email).exists():
                    raise ValidationError("Cette adresse email est déjà utilisée.")
        return email
    
    def clean_date_naissance(self):
        """Validation de la date de naissance"""
        date_naissance = self.cleaned_data.get('date_naissance')
        if date_naissance:
            if date_naissance > timezone.now().date():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            
            # Vérifier l'âge (au moins 18 ans)
            age = (timezone.now().date() - date_naissance).days / 365.25
            if age < 18:
                raise ValidationError("Le professeur doit avoir au moins 18 ans.")
            if age > 100:
                raise ValidationError("Veuillez vérifier la date de naissance.")
        return date_naissance
    
    def save(self, commit=True):
        """Sauvegarde avec création/mise à jour de l'utilisateur"""
        professeur = super().save(commit=False)
        
        # Créer ou mettre à jour l'utilisateur
        if not professeur.pk:  # Création
            user = CustomUser.objects.create_user(
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role='PROFESSEUR',
                telephone=self.cleaned_data.get('telephone_user', ''),
                password='@elites@'
            )
            professeur.user = user
        else:  # Mise à jour
            user = professeur.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.telephone = self.cleaned_data.get('telephone_user', '')
            user.save()
        
        if commit:
            professeur.save()
            self.save_m2m()
        
        return professeur


class ProfesseurSearchForm(forms.Form):
    """Formulaire de recherche de professeurs"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, matricule, spécialité...'
        })
    )
    section = forms.ModelChoiceField(
        required=False,
        queryset=Section.objects.filter(is_active=True),
        empty_label="Toutes les sections",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    grade = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les grades')] + list(GradesProfesseurs.choices),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    statut = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous les statuts')] + list(StatusProfesseurs.choices),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('active', 'Actifs'), ('inactive', 'Inactifs')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ========================================
# FORMULAIRES DOSSIER PROFESSEUR
# ========================================
class ProfesseurDocumentsForm(forms.ModelForm):
    """
    Formulaire pour gérer UNIQUEMENT les documents d'un professeur existant
    Utilisé pour la mise à jour des documents
    """
    
    class Meta:
        model = Professeur
        fields = ['photo', 'cni_document', 'rib_document', 'cv_document', 'diplome_document']
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png'
            }),
            'cni_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'
            }),
            'rib_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'
            }),
            'cv_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'diplome_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,image/jpeg,image/jpg,image/png'
            }),
        }
        labels = {
            'photo': 'Photo de profil (JPG, PNG - max 10MB)',
            'cni_document': 'Carte Nationale d\'Identité (PDF, DOC, DOCX, JPG, PNG - max 10MB)',
            'rib_document': 'Relevé d\'Identité Bancaire (PDF, DOC, DOCX, JPG, PNG - max 10MB)',
            'cv_document': 'Curriculum Vitae (PDF, DOC, DOCX - max 10MB)',
            'diplome_document': 'Diplôme(s) (PDF, DOC, DOCX, JPG, PNG - max 10MB)',
        }
    
    def clean_photo(self):
        """Validation de la photo"""
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError("La taille de la photo ne doit pas dépasser 10MB.")
            
            ext = photo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                raise ValidationError("Format non supporté. Utilisez JPG, JPEG ou PNG.")
        return photo
    
    def clean_cni_document(self):
        """Validation du document CNI"""
        return self._validate_document(self.cleaned_data.get('cni_document'), 'CNI')
    
    def clean_rib_document(self):
        """Validation du document RIB"""
        return self._validate_document(self.cleaned_data.get('rib_document'), 'RIB')
    
    def clean_cv_document(self):
        """Validation du CV"""
        return self._validate_document(self.cleaned_data.get('cv_document'), 'CV', ['pdf', 'doc', 'docx'])
    
    def clean_diplome_document(self):
        """Validation du diplôme"""
        return self._validate_document(self.cleaned_data.get('diplome_document'), 'Diplôme')
    
    def _validate_document(self, document, nom_document, extensions=None):
        """Validation générique des documents"""
        if document:
            if document.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError(f"La taille du {nom_document} ne doit pas dépasser 10MB.")
            
            ext = document.name.split('.')[-1].lower()
            if extensions is None:
                extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
            
            if ext not in extensions:
                raise ValidationError(
                    f"Format non supporté pour {nom_document}. "
                    f"Utilisez: {', '.join([e.upper() for e in extensions])}"
                )
        return document



# ========================================
# FORMULAIRES COMPTABLE
# ========================================

class ComptableForm(forms.ModelForm):
    """Formulaire de création/modification de comptable"""
    
    # Champs supplémentaires pour l'utilisateur
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    first_name = forms.CharField(
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom'
        })
    )
    telephone_user = forms.CharField(
        label="Téléphone",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225XXXXXXXXXX'
        })
    )
    
    class Meta:
        model = Comptable
        fields = ['date_naissance', 'is_active']
        widgets = {
            'date_naissance': DatePickerInput(),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si modification, pré-remplir les champs utilisateur
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['telephone_user'].initial = self.instance.user.telephone
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # Pour la création uniquement
            if not self.instance.pk:
                if CustomUser.objects.filter(email=email).exists():
                    raise ValidationError("Cette adresse email est déjà utilisée.")
        return email
    
    def clean_date_naissance(self):
        """Validation de la date de naissance"""
        date_naissance = self.cleaned_data.get('date_naissance')
        if date_naissance:
            if date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            
            # Vérifier l'âge
            age = (date.today() - date_naissance).days / 365.25
            if age < 16:
                raise ValidationError("Le comptable doit avoir au moins 16 ans.")
            if age > 100:
                raise ValidationError("Veuillez vérifier la date de naissance.")
        return date_naissance
    
    def save(self, commit=True):
        """Sauvegarde avec création/mise à jour de l'utilisateur"""
        comptable = super().save(commit=False)
        
        # Créer ou mettre à jour l'utilisateur
        if not comptable.pk:  # Création
            user = CustomUser.objects.create_user(
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role='COMPTABLE',
                telephone=self.cleaned_data.get('telephone_user', ''),
                password='@elites@'
            )
            comptable.user = user
        else:  # Mise à jour
            user = comptable.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.telephone = self.cleaned_data.get('telephone_user', '')
            user.save()
        
        if commit:
            comptable.save()
        
        return comptable


class ComptableSearchForm(forms.Form):
    """Formulaire de recherche de comptables"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, matricule, email...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('active', 'Actifs'), ('inactive', 'Inactifs')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ========================================
# FORMULAIRES DE FILTRAGE
# ========================================

class GlobalSearchForm(forms.Form):
    """Formulaire de recherche globale"""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Rechercher dans toute l\'application...',
            'autocomplete': 'off'
        })
    )


class DateRangeForm(forms.Form):
    """Formulaire de sélection de plage de dates"""
    
    date_debut = forms.DateField(
        required=False,
        label="Date de début",
        widget=DatePickerInput()
    )
    date_fin = forms.DateField(
        required=False,
        label="Date de fin",
        widget=DatePickerInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin and date_debut > date_fin:
            raise ValidationError("La date de début doit être antérieure à la date de fin.")
        
        return cleaned_data


class ExportForm(forms.Form):
    """Formulaire d'export de données"""
    
    TYPE_CHOICES = [
        ('all', 'Toutes les données'),
        ('professeurs', 'Professeurs uniquement'),
        ('comptables', 'Comptables uniquement'),
        ('sections', 'Sections uniquement'),
        ('utilisateurs', 'Utilisateurs uniquement')
    ]
    
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('excel', 'Excel')
    ]
    
    type_export = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    format_export = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_debut = forms.DateField(
        required=False,
        widget=DatePickerInput()
    )
    date_fin = forms.DateField(
        required=False,
        widget=DatePickerInput()
    )


# ========================================
# FORMULAIRE DE VALIDATION EN MASSE
# ========================================

class BulkActionForm(forms.Form):
    """Formulaire pour les actions en masse"""
    
    ACTION_CHOICES = [
        ('', '--- Choisir une action ---'),
        ('activate', 'Activer'),
        ('deactivate', 'Désactiver'),
        ('delete', 'Supprimer'),
        ('export', 'Exporter')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )
    selected_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean_selected_ids(self):
        """Convertir la liste d'IDs en liste Python"""
        ids_str = self.cleaned_data.get('selected_ids', '')
        if ids_str:
            try:
                return [int(id_) for id_ in ids_str.split(',') if id_.strip()]
            except ValueError:
                raise ValidationError("IDs invalides")
        return []





# ========================================
# FORMULAIRE DE VALIDATION EN MASSE
# ========================================
# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import (
    CustomUser, Section, Professeur, Comptable, 
    GradesProfesseurs, StatusProfesseurs, GenreProfesseurs,
    SituationMatrimoniale
)
from datetime import date

class CustomUserCreationForm(UserCreationForm):
    """Formulaire de création d'utilisateur avec gestion des rôles"""
    
    # Champs de base
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le nom'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label="Adresse email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'exemple@iipea.edu.ci'
        })
    )
    
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        label="Rôle",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_role'
        })
    )
    
    telephone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225XXXXXXXXXX'
        })
    )
    
    section_principale = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Section principale",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    sections_autorisees = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Sections autorisées",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '5'
        })
    )
    
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le mot de passe'
        }),
        required=False,
        help_text="Laissez vide pour utiliser le mot de passe par défaut (@elites@)"
    )
    
    password2 = forms.CharField(
        label="Confirmation",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmez le mot de passe'
        }),
        required=False
    )
    
    # is_active_user = forms.BooleanField(
    #     required=False,
    #     initial=True,
    #     label="Utilisateur actif",
    #     widget=forms.CheckboxInput(attrs={
    #         'class': 'form-check-input'
    #     })
    # )
    
    # Champs spécifiques pour PROFESSEUR
    date_naissance_prof = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    grade = forms.ChoiceField(
        choices=GradesProfesseurs.choices,
        required=False,
        label="Grade",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    statut = forms.ChoiceField(
        choices=StatusProfesseurs.choices,
        required=False,
        label="Statut",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    genre = forms.ChoiceField(
        choices=GenreProfesseurs.choices,
        required=False,
        label="Genre",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    nationalite = forms.CharField(
        max_length=100,
        required=False,
        label="Nationalité",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ivoirienne'
        })
    )
    
    numero_cni = forms.CharField(
        max_length=20,
        required=False,
        label="Numéro CNI",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'CI00000000'
        })
    )
    
    situation_matrimoniale = forms.ChoiceField(
        choices=SituationMatrimoniale.choices,
        required=False,
        label="Situation matrimoniale",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    domicile = forms.CharField(
        max_length=200,
        required=False,
        label="Adresse de domicile",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adresse complète'
        })
    )
    
    specialite = forms.CharField(
        max_length=100,
        required=False,
        label="Spécialité",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Mathématiques'
        })
    )
    
    diplome = forms.CharField(
        max_length=100,
        required=False,
        label="Diplôme",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Master en Mathématiques'
        })
    )
    
    annee_experience = forms.IntegerField(
        required=False,
        initial=0,
        label="Années d'expérience",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '50'
        })
    )
    
    sections_enseignement = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Sections d'enseignement",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '5'
        })
    )
    
    # Champs spécifiques pour COMPTABLE
    date_naissance_compta = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'role', 'telephone',
            'section_principale', 'sections_autorisees',
            'password1', 'password2'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les mots de passe optionnels pour la création
        self.fields['password1'].required = False
        self.fields['password2'].required = False
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # Vérifier l'unicité
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError("Cet email est déjà utilisé.")
        return email
    
    def clean_date_naissance_prof(self):
        """Validation de la date de naissance pour professeur"""
        date_naissance = self.cleaned_data.get('date_naissance_prof')
        if date_naissance:
            if date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            
            age = (date.today() - date_naissance).days // 365
            if age < 18 or age > 100:
                raise ValidationError("L'âge doit être compris entre 18 et 100 ans.")
        
        return date_naissance
    
    def clean_date_naissance_compta(self):
        """Validation de la date de naissance pour comptable"""
        date_naissance = self.cleaned_data.get('date_naissance_compta')
        if date_naissance:
            if date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur.")
            
            age = (date.today() - date_naissance).days // 365
            if age < 16 or age > 100:
                raise ValidationError("L'âge doit être compris entre 16 et 100 ans.")
        
        return date_naissance
    
    def clean(self):
        """Validation globale du formulaire"""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        # Validation des mots de passe si fournis
        if password1 or password2:
            if password1 != password2:
                raise ValidationError({
                    'password2': "Les mots de passe ne correspondent pas."
                })
        
        # Validation spécifique pour PROFESSEUR
        if role == 'PROFESSEUR':
            date_naissance = cleaned_data.get('date_naissance_prof')
            if not date_naissance:
                raise ValidationError({
                    'date_naissance_prof': "La date de naissance est obligatoire pour un professeur."
                })
            
            sections_enseignement = cleaned_data.get('sections_enseignement')
            if not sections_enseignement:
                raise ValidationError({
                    'sections_enseignement': "Au moins une section d'enseignement est requise."
                })
        
        # Validation spécifique pour COMPTABLE
        if role == 'COMPTABLE':
            date_naissance = cleaned_data.get('date_naissance_compta')
            if not date_naissance:
                raise ValidationError({
                    'date_naissance_compta': "La date de naissance est obligatoire pour un comptable."
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Sauvegarde avec gestion du mot de passe"""
        user = super().save(commit=False)
        
        # Définir le mot de passe
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_password('@elites@')  # Mot de passe par défaut
        
        if commit:
            user.save()
            # Sauvegarder les relations many-to-many
            self.save_m2m()
        
        return user


class CustomUserUpdateForm(forms.ModelForm):
    """Formulaire de modification d'utilisateur"""
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le nom'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label="Adresse email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'  # Email non modifiable
        })
    )
    
    telephone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225XXXXXXXXXX'
        })
    )
    
    section_principale = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Section principale",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    sections_autorisees = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        required=False,
        label="Sections autorisées",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '5'
        })
    )
    
    is_active_user = forms.BooleanField(
        required=False,
        label="Utilisateur actif",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_staff = forms.BooleanField(
        required=False,
        label="Accès admin",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'telephone',
            'section_principale', 'sections_autorisees',
            'is_active_user', 'is_staff'
        ]
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        return email


class ProfesseurUpdateForm(forms.ModelForm):
    """Formulaire de modification des informations du professeur"""
    
    date_naissance = forms.DateField(
        label="Date de naissance",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    sections = forms.ModelMultipleChoiceField(
        queryset=Section.objects.filter(is_active=True),
        label="Sections d'enseignement",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'size': '5'
        })
    )
    
    class Meta:
        model = Professeur
        fields = [
            'grade', 'statut', 'genre', 'nationalite', 'numero_cni',
            'situation_matrimoniale', 'domicile', 'date_naissance',
            'specialite', 'diplome', 'annee_experience', 'sections',
            'section_active', 'is_active'
        ]
        widgets = {
            'grade': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'nationalite': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control'}),
            'situation_matrimoniale': forms.Select(attrs={'class': 'form-control'}),
            'domicile': forms.TextInput(attrs={'class': 'form-control'}),
            'specialite': forms.TextInput(attrs={'class': 'form-control'}),
            'diplome': forms.TextInput(attrs={'class': 'form-control'}),
            'annee_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '50'
            }),
            'section_active': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ComptableUpdateForm(forms.ModelForm):
    """Formulaire de modification des informations du comptable"""
    
    date_naissance = forms.DateField(
        label="Date de naissance",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = Comptable
        fields = ['date_naissance', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserPasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe"""
    
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entrez le nouveau mot de passe'
        }),
        help_text="Minimum 8 caractères"
    )
    
    new_password2 = forms.CharField(
        label="Confirmation",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmez le nouveau mot de passe'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Les mots de passe ne correspondent pas.")
            
            if len(password1) < 8:
                raise ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        
        return cleaned_data