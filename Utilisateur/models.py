from django.utils.text import slugify
from django.core.validators import MinValueValidator
import requests  # Ajoutez cette ligne en haut avec les autres imports

from django.db import models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from datetime import date
from django_countries.fields import CountryField
import re
import uuid
import os
import logging

logger = logging.getLogger(__name__)

# ==========================================
# VALIDATEURS PERSONNALISÉS
# ==========================================

def validate_phone_number(value):
    """Validateur pour les numéros de téléphone ivoiriens"""
    pattern = r'^(?:\+225)?\d{10}$'
    if value and not re.match(pattern, value):
        raise ValidationError(
            "Format de téléphone invalide. Utilisez un numéro à 10 chiffres "
            "ou le format international (+225XXXXXXXXXX)."
        )


def validate_file_size(file):
    """Valider la taille du fichier (max 10MB)"""
    max_size = 10 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(
            f"La taille du fichier ne doit pas dépasser 10MB. "
            f"Taille actuelle: {file.size / (1024 * 1024):.2f}MB"
        )


def validate_email_domain(value):
    """Validateur pour s'assurer que l'email a un domaine valide"""
    if value:
        allowed_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'iipea.edu.ci']
        domain = value.split('@')[-1].lower()
        # Pour l'instant, on accepte tous les domaines
        pass


# ==========================================
# APIS POUR LES PAYS
# ==========================================
# Ajoutez cette classe dans models.py
class CountryService:
    @staticmethod
    def get_countries():
        """Récupère la liste des pays depuis l'API"""
        try:
            response = requests.get('https://restcountries.com/v3.1/all?fields=name,translations')
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []
    
    @staticmethod
    def search_countries(query):
        """Recherche des pays par nom"""
        countries = CountryService.get_countries()
        if not query:
            return []
        
        search_term = query.lower()
        return [country for country in countries 
                if search_term in country['name']['common'].lower() 
                or (country.get('translations', {}).get('fra', {}).get('common', '').lower().find(search_term) != -1)]

# ==========================================
# MODÈLE SECTION
# ==========================================

class Section(models.Model):
    """Sections géographiques de l'institution"""
    
    SECTIONS_CHOICES = [
        ('IIPEA YAKRO', 'IIPEA YAKRO'),
        ('IIPEA ABOBO', 'IIPEA ABOBO'),
        ('IIPEA RIVIERA 2', 'IIPEA RIVIERA 2'),
    ]
    
    nom = models.CharField(
        max_length=20,
        choices=SECTIONS_CHOICES,
        unique=True,
        verbose_name="Nom de la section"
    )
    adresse = models.TextField(blank=True, verbose_name="Adresse")
    telephone = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone_number],
        verbose_name="Téléphone"
    )
    email = models.EmailField(blank=True, verbose_name="Email de contact")
    responsable_nom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom du responsable"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    is_active = models.BooleanField(default=True, verbose_name="Section active")

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ['nom']

    def __str__(self):
        return self.get_nom_display()
    
    def get_professeurs_count(self):
        """Retourne le nombre de professeurs dans cette section"""
        try:
            return self.professeurs.count()
        except Exception:
            return 0
    
    def get_classes_count(self):
        """Retourne le nombre de classes dans cette section"""
        try:
            return getattr(self, 'classes', self.__class__.objects.none()).count()
        except Exception:
            return 0



class Pays(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)
    flag = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return self.nom

# ==========================================
# GESTIONNAIRE UTILISATEURS PERSONNALISÉ
# ==========================================

class CustomUserManager(BaseUserManager):
    """Gestionnaire personnalisé pour CustomUser avec authentification par email"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Crée et retourne un utilisateur avec un email et mot de passe"""
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        
        email = self.normalize_email(email)
        
        try:
            validate_email_domain(email)
        except ValidationError as e:
            raise ValueError(f'Email invalide: {e}')
        
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            user.set_password('@elites@')
            
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Crée et retourne un superutilisateur"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_active_user', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        if not password:
            raise ValueError('Le superutilisateur doit avoir un mot de passe.')
            
        return self.create_user(email, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        """Permet la recherche par email (case insensitive)"""
        return self.get(email__iexact=username)


# ==========================================
# MODÈLE UTILISATEUR PERSONNALISÉ
# ==========================================

class CustomUser(AbstractUser):
    """Utilisateur personnalisé avec authentification par email"""
    
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('RESP_PEDA', 'Responsable Pédagogique'),
        ('RESP_RH', 'Responsable Ressources Humaines'),
        ('PROFESSEUR', 'Professeur'),
        ('INFORMATICIEN', 'Service Informatique'),
        ('COMPTABLE', 'Comptable'),
        ('SERVICE_DATA', 'Service Data'),
    ]

    username = None
    email = models.EmailField(
        'Adresse email',
        unique=True,
        validators=[EmailValidator()],
        help_text="Adresse email utilisée pour la connexion"
    )
    
    role = models.CharField(
        max_length=15,
        choices=ROLE_CHOICES,
        verbose_name="Rôle"
    )
    section_principale = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_principaux",
        verbose_name="Section principale"
    )
    sections_autorisees = models.ManyToManyField(
        Section,
        related_name='utilisateurs_autorises',
        blank=True,
        verbose_name="Sections autorisées"
    )
    sections = models.ManyToManyField(
        Section,
        blank=True,
        related_name='utilisateurs_sections',
        verbose_name="Sections associées"
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone_number],
        verbose_name="Téléphone"
    )
    is_active_user = models.BooleanField(
        default=True,
        verbose_name="Utilisateur actif",
        help_text="Décochez pour suspendre temporairement l'accès de l'utilisateur"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    last_section_access = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernier accès section"
    )

    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['email']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'is_active_user']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})" if self.get_full_name() else self.email

    def clean(self):
        """Validation personnalisée"""
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()
    
    def save(self, *args, **kwargs):
        """Sauvegarde avec nettoyage automatique de l'email"""
        if self.email:
            self.email = self.email.lower().strip()
        
        if not self.password and not self.pk:
            self.set_password('@elites@')
            
        super().save(*args, **kwargs)

    def peut_acceder_section(self, section):
        """Vérifie si l'utilisateur peut accéder à une section"""
        if not self.is_active or not self.is_active_user:
            return False
            
        if self.role == 'ADMIN':
            return True
        if self.role == 'PROFESSEUR':
            return section in self.sections_autorisees.all()
        return self.section_principale == section

    def get_sections_disponibles(self):
        """Retourne les sections auxquelles l'utilisateur peut accéder"""
        if self.role == 'ADMIN':
            return Section.objects.filter(is_active=True)
        elif self.role == 'PROFESSEUR':
            return self.sections_autorisees.filter(is_active=True)
        elif self.section_principale:
            return Section.objects.filter(id=self.section_principale.id, is_active=True)
        return Section.objects.none()

    def update_last_section_access(self):
        """Met à jour le timestamp du dernier accès à une section"""
        self.last_section_access = timezone.now()
        self.save(update_fields=['last_section_access'])

    def get_role_display_badge(self):
        """Retourne le rôle avec un badge CSS"""
        role_badges = {
            'ADMIN': 'badge-danger',
            'RESP_PEDA': 'badge-primary',
            'PROFESSEUR': 'badge-success',
            'INFORMATICIEN': 'badge-info',
            'COMPTABLE': 'badge-warning',
            'SERVICE_DATA': 'badge-secondary',
        }
        return role_badges.get(self.role, 'badge-light')


# ==========================================
# ÉNUMÉRATIONS PROFESSEURS
# ==========================================

class GradesProfesseurs(models.TextChoices):
    PROFESSEUR = "Professeur", _("Professeur")
    DOCTORANT = "Doctorant", _("Doctorant")
    DOCTEUR = "Docteur", _("Docteur")


class StatusProfesseurs(models.TextChoices):
    VACATAIRE = "Vacataire", _("Vacataire")
    TITULAIRE = "Titulaire", _("Titulaire")


class SituationMatrimoniale(models.TextChoices):
    MARIE = "Marié", _("Marié")
    CELEBATAIRE = "Célibataire", _("Célibataire")
    DIVORCE = "Divorcé", _("Divorcé")
    VEUF = "Veuf", _("Veuf")


class GenreProfesseurs(models.TextChoices):
    MASCULIN = "Masculin", _("Masculin")
    FEMININ = "Feminin", _("Feminin")


# ==========================================
# FONCTIONS UPLOAD PROFESSEURS
# ==========================================

def professeur_photo_path(instance, filename):
    """Chemin pour les photos des professeurs (avec leur nom au lieu de l'ID)"""
    ext = filename.split('.')[-1]

    # Récupère le nom complet du prof
    full_name = f"{instance.user.last_name}_{instance.user.first_name}"
    # Nettoie le nom (ex: "Jean Dupont" -> "jean-dupont")
    safe_name = slugify(full_name)

    filename = f"photo_{safe_name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    return os.path.join('professeurs', safe_name, 'photo', filename)



def professeur_document_path(instance, filename):
    """Chemin pour les documents des professeurs"""
    doc_type = filename.split('_')[0] if '_' in filename else 'document'
    return os.path.join('professeurs', str(instance.user.id), 'documents', doc_type, filename)


# ==========================================
# MODÈLE PROFESSEUR
# ==========================================

class Professeur(models.Model):
    """Modèle pour gérer les professeurs"""
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="professeur",
        limit_choices_to={'role': 'PROFESSEUR'}
    )
    
    # Informations personnelles
    grade = models.CharField(
        max_length=50,
        choices=GradesProfesseurs.choices,
        default=GradesProfesseurs.PROFESSEUR,
        verbose_name="Grade"
    )
    statut = models.CharField(
        max_length=50,
        choices=StatusProfesseurs.choices,
        default=StatusProfesseurs.VACATAIRE,
        verbose_name="Statut"
    )
    genre = models.CharField(
        max_length=50,
        choices=GenreProfesseurs.choices,
        default=GenreProfesseurs.MASCULIN,
        verbose_name="Genre"
    )
    nationalite = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nationalité",
        help_text="Nationalité du professeur"
    )
    numero_cni = models.CharField(max_length=20, blank=True, verbose_name="Numéro CNI")
    situation_matrimoniale = models.CharField(
        max_length=100,
        choices=SituationMatrimoniale.choices,
        default=SituationMatrimoniale.CELEBATAIRE,
        verbose_name="Situation matrimoniale"
    )
    domicile = models.CharField(max_length=200, blank=True, verbose_name="Adresse de domicile")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    matricule = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Matricule"
    )
    
    # Informations professionnelles
    specialite = models.CharField(max_length=100, blank=True, verbose_name="Spécialité")
    diplome = models.CharField(max_length=100, blank=True, verbose_name="Diplôme")
    annee_experience = models.IntegerField(
        default=0,
        verbose_name="Année d'expérience",
        validators=[MinValueValidator(0, message="Les années d'expérience ne peuvent pas être négatives.")]
    )
    sections = models.ManyToManyField(
        Section,
        related_name="professeurs",
        verbose_name="Sections d'enseignement"
    )
    section_active = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professeurs_actifs",
        verbose_name="Section active"
    )
    
    # Documents
    photo = models.ImageField(
        upload_to=professeur_photo_path,
        blank=True,
        null=True,
        validators=[
            validate_file_size,
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])
        ],
        verbose_name="Photo de profil",
        help_text="Format accepté: JPG, PNG (max 10MB)"
    )
    cni_document = models.FileField(
        upload_to=professeur_document_path,
        blank=True,
        null=True,
        validators=[
            validate_file_size,
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])
        ],
        verbose_name="CNI",
        help_text="Format accepté: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    rib_document = models.FileField(
        upload_to=professeur_document_path,
        blank=True,
        null=True,
        validators=[
            validate_file_size,
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])
        ],
        verbose_name="RIB",
        help_text="Format accepté: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    cv_document = models.FileField(
        upload_to=professeur_document_path,
        blank=True,
        null=True,
        validators=[
            validate_file_size,
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])
        ],
        verbose_name="CV",
        help_text="Format accepté: PDF, DOC, DOCX (max 10MB)"
    )
    diplome_document = models.FileField(
        upload_to=professeur_document_path,
        blank=True,
        null=True,
        validators=[
            validate_file_size,
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])
        ],
        verbose_name="Diplôme",
        help_text="Format accepté: PDF, DOC, DOCX, JPG, PNG (max 10MB)"
    )
    
    # Dates upload documents
    photo_uploaded_at = models.DateTimeField(null=True, blank=True)
    cni_uploaded_at = models.DateTimeField(null=True, blank=True)
    rib_uploaded_at = models.DateTimeField(null=True, blank=True)
    cv_uploaded_at = models.DateTimeField(null=True, blank=True)
    diplome_uploaded_at = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    date_embauche = models.DateField(
        editable=False,
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="Date d'embauche"
    )
    is_active = models.BooleanField(default=True, verbose_name="Professeur actif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Professeur"
        verbose_name_plural = "Professeurs"
        ordering = ['user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['matricule']),
            models.Index(fields=['is_active']),
        ]

    def save(self, *args, **kwargs):
        """Génération automatique du matricule et mise à jour des dates d'upload"""
        # Mettre à jour les dates d'upload
        if self.pk:
            try:
                old_instance = Professeur.objects.get(pk=self.pk)
                if self.photo and (not old_instance.photo or self.photo != old_instance.photo):
                    self.photo_uploaded_at = timezone.now()
                if self.cni_document and (not old_instance.cni_document or self.cni_document != old_instance.cni_document):
                    self.cni_uploaded_at = timezone.now()
                if self.rib_document and (not old_instance.rib_document or self.rib_document != old_instance.rib_document):
                    self.rib_uploaded_at = timezone.now()
                if self.cv_document and (not old_instance.cv_document or self.cv_document != old_instance.cv_document):
                    self.cv_uploaded_at = timezone.now()
                if self.diplome_document and (not old_instance.diplome_document or self.diplome_document != old_instance.diplome_document):
                    self.diplome_uploaded_at = timezone.now()
            except Professeur.DoesNotExist:
                pass
        else:
            if self.photo:
                self.photo_uploaded_at = timezone.now()
            if self.cni_document:
                self.cni_uploaded_at = timezone.now()
            if self.rib_document:
                self.rib_uploaded_at = timezone.now()
            if self.cv_document:
                self.cv_uploaded_at = timezone.now()
            if self.diplome_document:
                self.diplome_uploaded_at = timezone.now()
        
        # Génération du matricule
        if not self.matricule and self.date_naissance:
            with transaction.atomic():
                annee = str(self.date_naissance.year)[::-1]
                jour_mois = f"{self.date_naissance.day:02d}{self.date_naissance.month:02d}"[::-1]
                
                same_birth_count = Professeur.objects.select_for_update().filter(
                    date_naissance=self.date_naissance
                ).exclude(pk=self.pk).count() + 1
                
                compteur = f"{same_birth_count:03d}"
                self.matricule = f"MAT/IIPEA-{annee}-{jour_mois}-{compteur}"
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validation personnalisée"""
        super().clean()
        if self.date_naissance and self.date_naissance > timezone.now().date():
            raise ValidationError("La date de naissance ne peut pas être dans le futur.")
        
        if self.date_embauche and self.date_embauche > timezone.now().date():
            raise ValidationError("La date d'embauche ne peut pas être dans le futur.")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.matricule}"

    def get_age(self):
        """Calcule l'âge du professeur"""
        if self.date_naissance:
            today = timezone.now().date()
            return today.year - self.date_naissance.year - (
                (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
            )
        return None
    
    def has_complete_documents(self):
        """Vérifie si tous les documents sont présents"""
        return all([
            self.photo,
            self.cni_document,
            self.rib_document,
            self.cv_document,
            self.diplome_document
        ])
    
    def get_missing_documents(self):
        """Retourne la liste des documents manquants"""
        missing = []
        if not self.photo:
            missing.append('Photo de profil')
        if not self.cni_document:
            missing.append('CNI')
        if not self.rib_document:
            missing.append('RIB')
        if not self.cv_document:
            missing.append('CV')
        if not self.diplome_document:
            missing.append('Diplôme')
        return missing
    
    def delete_document(self, document_type):
        """Supprimer un document spécifique"""
        if document_type == 'photo' and self.photo:
            self.photo.delete(save=True)
            self.photo_uploaded_at = None
        elif document_type == 'cni' and self.cni_document:
            self.cni_document.delete(save=True)
            self.cni_uploaded_at = None
        elif document_type == 'rib' and self.rib_document:
            self.rib_document.delete(save=True)
            self.rib_uploaded_at = None
        elif document_type == 'cv' and self.cv_document:
            self.cv_document.delete(save=True)
            self.cv_uploaded_at = None
        elif document_type == 'diplome' and self.diplome_document:
            self.diplome_document.delete(save=True)
            self.diplome_uploaded_at = None
        self.save()


# ==========================================
# FONCTIONS UTILITAIRES COMPTABLE
# ==========================================

def generate_unique_code():
    """Génère un code unique pour le comptable"""
    return f"UNI/{uuid.uuid4().hex[:8].upper()}"


# ==========================================
# MANAGER COMPTABLE
# ==========================================

class ComptableManager(models.Manager):
    """Manager personnalisé pour les comptables"""
    
    def actifs(self):
        return self.filter(is_active=True)
    
    def inactifs(self):
        return self.filter(is_active=False)
    
    def avec_utilisateurs_actifs(self):
        return self.filter(is_active=True, user__is_active=True)
    
    def par_age(self, min_age=None, max_age=None):
        """Filtre les comptables par tranche d'âge"""
        queryset = self.all()
        today = date.today()
        
        if max_age:
            min_birth_date = today.replace(year=today.year - max_age)
            queryset = queryset.filter(date_naissance__gte=min_birth_date)
        
        if min_age:
            max_birth_date = today.replace(year=today.year - min_age)
            queryset = queryset.filter(date_naissance__lte=max_birth_date)
        
        return queryset


# ==========================================
# MODÈLE COMPTABLE
# ==========================================

class Comptable(models.Model):
    """Modèle représentant un comptable de l'établissement"""
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='comptable',
        verbose_name="Utilisateur",
        help_text="Utilisateur Django associé à ce comptable"
    )
    
    date_naissance = models.DateField(
        verbose_name="Date de naissance",
        help_text="Date de naissance du comptable",
        null=True,
        blank=True
    )
    
    matricule = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Matricule",
        help_text="Matricule unique du comptable (généré automatiquement si vide)",
        blank=True
    )
    code_unique = models.CharField(
        max_length=20,
        unique=True,
        default=generate_unique_code,
        verbose_name="Code unique",
        help_text="Code d'identification unique généré automatiquement"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Indique si le comptable est actuellement actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    
    objects = ComptableManager()
    
    class Meta:
        verbose_name = "Comptable"
        verbose_name_plural = "Comptables"
        ordering = ['user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['matricule']),
            models.Index(fields=['code_unique']),
        ]
    
    def __str__(self):
        return self.get_nom_complet() or f"Comptable #{self.pk}"
    
    def clean(self):
        """Validation personnalisée du modèle"""
        super().clean()
        
        if self.user_id:
            existing = Comptable.objects.filter(user=self.user).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'user': 'Cet utilisateur est déjà associé à un autre comptable.'
                })
        
        if self.date_naissance:
            if self.date_naissance > date.today():
                raise ValidationError({
                    'date_naissance': 'La date de naissance ne peut pas être dans le futur.'
                })
            
            age = self.get_age()
            if age and (age < 16 or age > 100):
                raise ValidationError({
                    'date_naissance': 'L\'âge doit être compris entre 16 et 100 ans.'
                })
    
    def save(self, *args, **kwargs):
        """Sauvegarde avec génération automatique du matricule"""
        if not self.matricule:
            temp_id = str(self.pk or '').zfill(3)
            date_part = timezone.now().strftime('%Y%m')
            self.matricule = f"COMP{temp_id}{date_part}"
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        if not args and not kwargs.get('update_fields'):
            new_matricule = f"MAT/COMP/{str(self.pk).zfill(3)}-{timezone.now().strftime('%Y%m')}"
            if self.matricule != new_matricule:
                self.matricule = new_matricule
                self.save(update_fields=['matricule'])
    
    def get_nom_complet(self):
        """Retourne le nom complet du comptable"""
        if self.user:
            nom_complet = self.user.get_full_name()
            return nom_complet.strip() if nom_complet else self.user.email
        return None
    
    def get_prenom(self):
        return self.user.first_name if self.user else None
    
    def get_nom(self):
        return self.user.last_name if self.user else None
    
    def get_email(self):
        return self.user.email if self.user else None
    
    def get_age(self):
        """Calcule et retourne l'âge du comptable en années"""
        if not self.date_naissance:
            return None
        
        today = date.today()
        age = today.year - self.date_naissance.year
        
        if (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day):
            age -= 1
        
        return age
    
    def get_age_display(self):
        age = self.get_age()
        return f"{age} ans" if age else "Non renseigné"
    
    def get_statut_display(self):
        if self.is_active:
            if self.user and self.user.is_active:
                return "Actif"
            else:
                return "Comptable actif, Utilisateur inactif"
        return "Inactif"
    
    def get_statut_color(self):
        if self.is_active:
            if self.user and self.user.is_active:
                return "success"
            else:
                return "warning"
        return "danger"
    
    def activer(self):
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
    
    def desactiver(self):
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def toggle_activation(self):
        self.is_active = not self.is_active
        self.save(update_fields=['is_active', 'updated_at'])
    
    def is_user_active(self):
        return self.user.is_active if self.user else False
    
    def is_fully_active(self):
        return self.is_active and self.is_user_active()
    
    def get_permissions(self):
        if self.user:
            return self.user.get_all_permissions()
        return set()
    
    def get_groups(self):
        if self.user:
            return self.user.groups.all()
        return []
    
    def get_absolute_url(self):
        return reverse('comptable_detail', kwargs={'pk': self.pk})
    
    @property
    def anciennete_jours(self):
        return (timezone.now().date() - self.created_at.date()).days
    
    @property
    def anciennete_annees(self):
        return self.anciennete_jours / 365.25
    
    def get_derniere_connexion(self):
        return self.user.last_login if self.user else None
    
    def est_connecte_recemment(self, jours=7):
        if not self.user or not self.user.last_login:
            return False
        
        delta = timezone.now() - self.user.last_login
        return delta.days <= jours
    
    @classmethod
    def statistiques(cls):
        """Retourne des statistiques sur les comptables"""
        queryset = cls.objects.all()
        
        return {
            'total': queryset.count(),
            'actifs': queryset.filter(is_active=True).count(),
            'inactifs': queryset.filter(is_active=False).count(),
            'pleinement_actifs': queryset.filter(is_active=True, user__is_active=True).count(),
            'avec_email': queryset.exclude(user__email='').count(),
            'connectes_recemment': queryset.filter(
                user__last_login__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
        }

# ==========================================
# SIGNAUX
# ==========================================

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver


@receiver(post_save, sender=CustomUser)
def sync_user_changes(sender, instance, **kwargs):
    """Synchronise les changements de l'utilisateur avec le comptable"""
    try:
        comptable = instance.comptable
        if not instance.is_active and comptable.is_active:
            comptable.is_active = False
            comptable.save(update_fields=['is_active', 'updated_at'])
    except Comptable.DoesNotExist:
        pass


@receiver(pre_delete, sender=CustomUser)
def prevent_user_deletion_if_comptable(sender, instance, **kwargs):
    """Empêche la suppression d'un utilisateur qui est un comptable actif"""
    try:
        comptable = instance.comptable
        if comptable.is_active:
            raise ValidationError(
                f"Impossible de supprimer l'utilisateur {instance.email} : "
                f"il est associé au comptable actif {comptable.get_nom_complet()}"
            )
    except Comptable.DoesNotExist:
        pass



