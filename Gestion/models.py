from django.db import models
from Utilisateur.models import Section
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
#============================================
# MODELS POUR LES APIS
#============================================

class Classe(models.Model):
    """Modèle pour les classes provenant de l'API MyIIPEA"""
    
    # ID de l'API externe
    external_id = models.IntegerField(
        unique=True, 
        db_index=True,
        verbose_name="ID API"
    )
    
    # Informations de base
    nom = models.CharField(
        max_length=300,
        verbose_name="Nom de la classe"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Informations académiques
    annee_academique = models.CharField(
        max_length=50,
        verbose_name="Année académique"
    )
    annee_etat = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="État de l'année"
    )
    filiere = models.CharField(
        max_length=200,
        verbose_name="Filière"
    )
    niveau = models.CharField(
        max_length=100,
        verbose_name="Niveau"
    )
    departement = models.CharField(
        max_length=100,
        verbose_name="Département"
    )
    
    # Statistiques
    nombre_groupes = models.IntegerField(
        default=0,
        verbose_name="Nombre de groupes"
    )
    effectif_total = models.IntegerField(
        default=0,
        verbose_name="Effectif total"
    )
    
    # Association avec section locale (optionnel)
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes',
        verbose_name="Section IIPEA"
    )
    
    # Données brutes de l'API
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données brutes API"
    )
    
    # Métadonnées de synchronisation
    last_synced = models.DateTimeField(
        default=timezone.now,
        verbose_name="Dernière synchronisation"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Classe active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )
    
    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        ordering = ['filiere', 'niveau']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['filiere']),
            models.Index(fields=['niveau']),
            models.Index(fields=['departement']),
            models.Index(fields=['last_synced']),
        ]
    
    def __str__(self):
        return f"{self.nom}"
    
    @property
    def needs_sync(self):
        """Vérifie si les données doivent être resynchronisées"""
        from django.conf import settings
        delta = timezone.now() - self.last_synced
        max_age = getattr(settings, 'API_DATA_MAX_AGE', 3600)  # 1 heure
        return delta.total_seconds() > max_age
    
    def get_code_filiere(self):
        """Extrait le code de la filière depuis le nom"""
        # Ex: "FINANCE COMPTABILITE... FCGE BTS 1" -> "FCGE"
        parts = self.nom.split()
        for i, part in enumerate(parts):
            if part.isupper() and len(part) <= 10 and i > 0:
                return part
        return ""
    
    def get_maquettes_count(self):
        """Retourne le nombre de maquettes associées"""
        return self.maquettes.filter(is_active=True).count()


class Maquette(models.Model):
    """Modèle pour les maquettes pédagogiques"""
    
    # ID de l'API externe
    external_id = models.IntegerField(
        unique=True,
        db_index=True,
        verbose_name="ID API"
    )
    
    # Relations
    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name='maquettes',
        null=True,
        blank=True,
        verbose_name="Classe"
    )
    
    # Informations de base (de l'API)
    filiere_id = models.IntegerField(
        verbose_name="ID Filière"
    )
    niveau_id = models.IntegerField(
        verbose_name="ID Niveau"
    )
    anneeacademique_id = models.IntegerField(
        verbose_name="ID Année académique"
    )
    
    # Informations détaillées
    filiere_nom = models.CharField(
        max_length=200,
        verbose_name="Nom de la filière"
    )
    filiere_sigle = models.CharField(
        max_length=20,
        verbose_name="Sigle de la filière"
    )
    niveau_libelle = models.CharField(
        max_length=100,
        verbose_name="Libellé du niveau"
    )
    annee_academique = models.CharField(
        max_length=50,
        verbose_name="Année académique"
    )
    parcour = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Parcours"
    )
    
    # Date de création API
    date_creation_api = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date création (API)"
    )
    
    # Données supplémentaires (UEs, etc.)
    unites_enseignement = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Unités d'enseignement"
    )
    
    # Données brutes
    raw_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données brutes API"
    )
    
    # Métadonnées
    last_synced = models.DateTimeField(
        default=timezone.now,
        verbose_name="Dernière synchronisation"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Maquette active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )
    
    class Meta:
        verbose_name = "Maquette"
        verbose_name_plural = "Maquettes"
        ordering = ['filiere_nom', 'niveau_libelle']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['filiere_id']),
            models.Index(fields=['niveau_id']),
            models.Index(fields=['anneeacademique_id']),
        ]
    
    def __str__(self):
        return f"{self.filiere_sigle} {self.niveau_libelle} - {self.annee_academique}"
    
    def get_total_ues(self):
        """Retourne le nombre d'unités d'enseignement"""
        return len(self.unites_enseignement) if self.unites_enseignement else 0



#=================================================
# MODELE POUR LES CONTRATS
#=================================================
# ============================================
# MODELS POUR LES PRÉCONTRATS
# ============================================
"""
Modèles pour la gestion des précontrats et contrats
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import uuid

from Utilisateur.models import CustomUser
from Gestion.models import Classe, Maquette


# ==========================================
# MODÈLE PRÉCONTRAT
# ==========================================

class PreContrat(models.Model):
    """
    Modèle pour la création d'un précontrat avant validation RH.
    Un précontrat lie un professeur à une classe avec une liste de modules.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('SUBMITTED', 'Soumis pour validation'),
        ('UNDER_REVIEW', 'En cours de révision'),
        ('VALIDATED', 'Validé'),
        ('REJECTED', 'Rejeté'),
        ('CANCELLED', 'Annulé'),
    ]
    
    # Identifiant unique
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID Unique"
    )
    
    # Référence du précontrat (généré automatiquement)
    reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="Référence",
        help_text="Référence unique du précontrat (ex: PC-2024-001)"
    )
    
    # Relations principales
    professeur = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        limit_choices_to={'role': 'PROFESSEUR', 'is_active': True},
        related_name='precontrats',
        verbose_name="Professeur"
    )
    
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name='precontrats',
        verbose_name="Classe",
        help_text="Classe pour laquelle le précontrat est créé"
    )
    
    # Informations automatiques de la classe (dénormalisées pour historique)
    classe_nom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom de la classe"
    )
    classe_niveau = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Niveau de la classe"
    )
    classe_filiere = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Filière de la classe"
    )
    
    # Statut et workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name="Statut"
    )
    
    # Notes et commentaires
    
    raison_rejet = models.TextField(
        blank=True,
        verbose_name="Raison du rejet",
        help_text="Raison du rejet si le précontrat est rejeté"
    )
    
    # Traçabilité
    cree_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='precontrats_crees',
        verbose_name="Créé par"
    )
    
    valide_par = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='precontrats_valides',
        verbose_name="Validé par"
    )
    
    # Dates
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    date_soumission = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de soumission"
    )
    
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )
    
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )
    
    # Année académique
    annee_academique = models.CharField(
        max_length=9,
        blank=True,
        verbose_name="Année académique",
        help_text="Ex: 2024-2025"
    )
    
    class Meta:
        verbose_name = "Précontrat"
        verbose_name_plural = "Précontrats"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['status', 'date_creation']),
            models.Index(fields=['professeur', 'classe']),
            models.Index(fields=['reference']),
        ]
    
    def __str__(self):
        return f"{self.reference or 'PC-DRAFT'} - {self.professeur.get_full_name()} - {self.classe_nom or self.classe.nom}"
    
    def clean(self):
        """Validation personnalisée du modèle"""
        super().clean()
        
        # Vérifier que le professeur est bien actif
        if self.professeur and not self.professeur.is_active:
            raise ValidationError({
                'professeur': 'Ce professeur n\'est pas actif.'
            })
        
        # Vérifier que la classe est active
        if self.classe and not self.classe.is_active:
            raise ValidationError({
                'classe': 'Cette classe n\'est pas active.'
            })
    
    def save(self, *args, **kwargs):
        """Sauvegarde avec génération automatique de la référence"""
        
        # Remplir les infos de la classe (dénormalisation)
        if self.classe:
            self.classe_nom = self.classe.nom
            self.classe_niveau = self.classe.niveau
            self.classe_filiere = self.classe.filiere
        
        # Générer l'année académique si vide
        if not self.annee_academique:
            now = timezone.now()
            year = now.year
            # Si on est entre janvier et août, l'année académique a commencé l'année précédente
            if now.month < 9:
                self.annee_academique = f"{year-1}-{year}"
            else:
                self.annee_academique = f"{year}-{year+1}"
        
        # Valider le modèle
        self.full_clean()
        
        # Première sauvegarde pour obtenir un ID
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Générer la référence si c'est un nouveau précontrat
        if is_new and not self.reference:
            year = timezone.now().year
            # Compter les précontrats de l'année
            count = PreContrat.objects.filter(
                date_creation__year=year
            ).count()
            self.reference = f"PC-{year}-{str(count).zfill(4)}"
            self.save(update_fields=['reference'])
    
    def get_absolute_url(self):
        """URL de détail du précontrat"""
        return reverse('precontrat_detail', kwargs={'pk': self.pk})
    
    # ==========================================
    # PROPRIÉTÉS CALCULÉES
    # ==========================================
    
    @property
    def progression_pourcentage(self):
        """Calcule le pourcentage de progression de la validation"""
        total = self.nombre_modules
        if total == 0:
            return 0
        return (self.modules_valides_count / total) * 100

    @property
    def nombre_modules(self):
        """Retourne le nombre de modules proposés"""
        return self.modules_proposes.count()
    
    @property
    def modules_valides_count(self):
        """Retourne le nombre de modules validés"""
        return self.modules_proposes.filter(est_valide=True).count()
    
    @property
    def est_complet(self):
        """Vérifie si le précontrat a au moins un module"""
        return self.nombre_modules > 0
    
    @property
    def peut_etre_soumis(self):
        """Vérifie si le précontrat peut être soumis"""
        return self.status == 'DRAFT' and self.est_complet
    
    @property
    def peut_etre_valide(self):
        """Vérifie si le précontrat peut être validé"""
        return self.status in ['SUBMITTED', 'UNDER_REVIEW']
    
    def get_volume_total(self):
        """Calcule le volume horaire total de tous les modules"""
        total = self.modules_proposes.aggregate(
            total_cm=models.Sum('volume_heure_cours'),
            total_td=models.Sum('volume_heure_td'),
        )
        
        cm = total.get('total_cm') or Decimal('0')
        td = total.get('total_td') or Decimal('0')
        
        return {
            'cours': cm,
            'td': td,
            'total': cm + td
        }
    
    def get_montant_total(self):
        """Calcule le montant total estimé de tous les modules"""
        total = Decimal('0')
        for module in self.modules_proposes.all():
            total += module.get_montant_total()
        return total
    
    def get_statut_display_classe(self):
        """Retourne la classe CSS pour le badge de statut"""
        status_classes = {
            'DRAFT': 'secondary',
            'SUBMITTED': 'info',
            'UNDER_REVIEW': 'warning',
            'VALIDATED': 'success',
            'REJECTED': 'danger',
            'CANCELLED': 'dark',
        }
        return status_classes.get(self.status, 'secondary')
    
    # ==========================================
    # MÉTHODES D'ACTION
    # ==========================================
    
    def soumettre(self, user=None):
        """Soumet le précontrat pour validation"""
        if not self.peut_etre_soumis:
            raise ValidationError("Ce précontrat ne peut pas être soumis.")
        
        self.status = 'SUBMITTED'
        self.date_soumission = timezone.now()
        self.save(update_fields=['status', 'date_soumission'])
        
        # Log l'action
        self.log_action(user, 'SOUMISSION', "Précontrat soumis pour validation")
    
    def mettre_en_revision(self, user=None):
        """Met le précontrat en révision"""
        if self.status != 'SUBMITTED':
            raise ValidationError("Seuls les précontrats soumis peuvent être mis en révision.")
        
        self.status = 'UNDER_REVIEW'
        self.save(update_fields=['status'])
        
        # Log l'action
        self.log_action(user, 'REVISION', "Précontrat mis en révision")
    
    def valider(self, user=None, notes=""):
        """Valide le précontrat"""
        if not self.peut_etre_valide:
            raise ValidationError("Ce précontrat ne peut pas être validé.")
        
        self.status = 'VALIDATED'
        self.date_validation = timezone.now()
        self.valide_par = user
        self.save(update_fields=['status', 'date_validation', 'valide_par'])
        
        # Log l'action
        self.log_action(user, 'VALIDATION', "Précontrat validé")
    
    def rejeter(self, user=None, raison=""):
        """Rejette le précontrat"""
        if not self.peut_etre_valide:
            raise ValidationError("Ce précontrat ne peut pas être rejeté.")
        
        if not raison:
            raise ValidationError("Une raison de rejet est requise.")
        
        self.status = 'REJECTED'
        self.raison_rejet = raison
        self.save(update_fields=['status', 'raison_rejet'])
        
        # Log l'action
        self.log_action(user, 'REJET', f"Précontrat rejeté: {raison}")
    
    def annuler(self, user=None, raison=""):
        """Annule le précontrat"""
        self.status = 'CANCELLED'
        self.save(update_fields=['status'])
        
        # Log l'action
        self.log_action(user, 'ANNULATION', f"Précontrat annulé: {raison}")
    
    def log_action(self, user, action_type, description):
        """Enregistre une action dans les logs"""
        try:
            from .models import ActionLog
            ActionLog.objects.create(
                precontrat=self,
                user=user,
                action_type=action_type,
                description=description
            )
        except Exception as e:
            # Si ActionLog n'existe pas encore, on ignore
            pass


# ==========================================
# MODÈLE MODULE PROPOSÉ
# ==========================================

class ModulePropose(models.Model):
    """
    Modèle pour un module proposé dans un précontrat.
    Contient les informations sur le volume horaire et les taux.
    """
    
    # Relation avec le précontrat
    pre_contrat = models.ForeignKey(
        PreContrat,
        on_delete=models.CASCADE,
        related_name='modules_proposes',
        verbose_name="Précontrat"
    )
    
    # Informations du module (depuis la maquette)
    code_module = models.CharField(
        max_length=20,
        verbose_name="Code du module"
    )
    
    nom_module = models.CharField(
        max_length=200,
        verbose_name="Nom du module"
    )
    
    ue_nom = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Unité d'Enseignement",
        help_text="Nom de l'UE à laquelle appartient ce module"
    )
    
    # Volumes horaires (CM, TD)
    volume_heure_cours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Volume Heures CM"
    )
    
    volume_heure_td = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Volume Heures TD"
    )
    
    # Taux horaires (en FCFA)
    taux_horaire_cours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Taux Horaire CM (FCFA)"
    )
    
    taux_horaire_td = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Taux Horaire TD (FCFA)"
    )
    
    # Validation RH
    est_valide = models.BooleanField(
        default=False,
        verbose_name="Validé par RH",
        help_text="Indique si le module a été validé par le responsable RH"
    )
    
    # Dates
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )
    
    class Meta:
        verbose_name = "Module Proposé"
        verbose_name_plural = "Modules Proposés"
        ordering = ['code_module']
        unique_together = ['pre_contrat', 'code_module']
        indexes = [
            models.Index(fields=['pre_contrat', 'est_valide']),
        ]
    
    def __str__(self):
        return f"{self.code_module} - {self.nom_module}"
    
    def clean(self):
        """Validation personnalisée"""
        super().clean()
        
        # Au moins un volume doit être > 0
        if (self.volume_heure_cours == 0 and 
            self.volume_heure_td == 0):
            raise ValidationError(
                "Au moins un type de volume horaire doit être supérieur à 0."
            )
        
        # Si un volume > 0, son taux doit être > 0
        if self.volume_heure_cours > 0 and self.taux_horaire_cours == 0:
            raise ValidationError({
                'taux_horaire_cours': 'Le taux horaire CM doit être supérieur à 0 si le volume CM est défini.'
            })
        
        if self.volume_heure_td > 0 and self.taux_horaire_td == 0:
            raise ValidationError({
                'taux_horaire_td': 'Le taux horaire TD doit être supérieur à 0 si le volume TD est défini.'
            })
    
    def save(self, *args, **kwargs):
        """Sauvegarde avec validation"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    
    @property
    def volume_total(self):
        """Retourne le volume horaire total du module"""
        return self.volume_heure_cours + self.volume_heure_td
    
    def get_montant_cours(self):
        """Calcule le montant pour les heures CM"""
        return self.volume_heure_cours * self.taux_horaire_cours
    
    def get_montant_td(self):
        """Calcule le montant pour les heures TD"""
        return self.volume_heure_td * self.taux_horaire_td
    
    def get_montant_total(self):
        """Calcule le montant total du module"""
        return self.get_montant_cours() + self.get_montant_td()
    
    def get_details_volumes(self):
        """Retourne un dictionnaire avec les détails des volumes"""
        return {
            'cm': {
                'volume': float(self.volume_heure_cours),
                'taux': float(self.taux_horaire_cours),
                'montant': float(self.get_montant_cours())
            },
            'td': {
                'volume': float(self.volume_heure_td),
                'taux': float(self.taux_horaire_td),
                'montant': float(self.get_montant_td())
            },
            'total': {
                'volume': float(self.volume_total),
                'montant': float(self.get_montant_total())
            }
        }
    
    
    def valider(self, user=None, notes=""):
        """Valide le module"""
        self.est_valide = True
        self.date_validation = timezone.now()
        self.save(update_fields=['est_valide', 'date_validation'])
    
    def invalider(self):
        """Invalide le module"""
        self.est_valide = False
        self.date_validation = None
        self.save(update_fields=['est_valide', 'date_validation'])



# ==========================================
# MODÈLE CONTRAT
# ==========================================

class Contrat(models.Model):
    """
    Contrat validé pour un module spécifique
    Un contrat est créé automatiquement lors de la validation d'un ModulePropose
    """
    
    STATUS_CHOICES = [
        ('VALIDATED', 'Validé'),
        ('READY_TO_START', 'Prêt à démarrer'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('PENDING_DOCUMENTS', 'En attente documents'),
        ('READY_FOR_PAYMENT', 'Prêt pour paiement'),
        ('PAID', 'Payé'),
        ('CANCELLED', 'Annulé'),
    ]
    
    TYPE_ENSEIGNEMENT_CHOICES = [
        ('NORMAL', 'Cours normal'),
        ('TRONC_COMMUN', 'Tronc commun'),
    ]
    
    # Relation avec le module proposé validé
    module_propose = models.OneToOneField(
        ModulePropose,
        on_delete=models.CASCADE,
        related_name='contrat',
        verbose_name="Module proposé"
    )
    
    # Relations principales (dupliquées pour faciliter les requêtes)
    professeur = models.ForeignKey(
        'Utilisateur.Professeur',
        on_delete=models.CASCADE,
        related_name='contrats',
        verbose_name="Professeur"
    )
    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name='contrats',
        verbose_name="Classe principale"
    )
    maquette = models.ForeignKey(
        Maquette,
        on_delete=models.CASCADE,
        related_name='contrats',
        verbose_name="Module"
    )
    
    # Volumes horaires contractuels
    volume_heure_cours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Volume heures cours contractuel"
    )
    volume_heure_td = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Volume heures TD contractuel"
    )
    
    # Taux horaires
    taux_horaire_cours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Taux horaire cours (FCFA)"
    )
    taux_horaire_td = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Taux horaire TD (FCFA)"
    )
    
    # Type d'enseignement
    type_enseignement = models.CharField(
        max_length=20,
        choices=TYPE_ENSEIGNEMENT_CHOICES,
        default='NORMAL',
        verbose_name="Type d'enseignement"
    )
    
    # Classes supplémentaires (pour tronc commun)
    classes_tronc_commun = models.ManyToManyField(
        Classe,
        blank=True,
        related_name='contrats_tronc_commun',
        verbose_name="Classes en tronc commun"
    )
    
    # Dates importantes
    date_debut_prevue = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de début prévue"
    )
    date_debut_reelle = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de début réelle"
    )
    date_fin_prevue = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin prévue"
    )
    date_fin_reelle = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin réelle"
    )
    
    # Statut
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='VALIDATED',
        verbose_name="Statut"
    )
    
    # Validation
    valide_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contrats_valides',
        verbose_name="Validé par"
    )
    date_validation = models.DateTimeField(
        verbose_name="Date de validation"
    )
    
    # Gestion pédagogique
    demarre_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contrats_demarres',
        verbose_name="Démarré par"
    )
    date_demarrage = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de démarrage"
    )
    
    # Documents obligatoires
    support_cours_uploaded = models.BooleanField(
        default=False,
        verbose_name="Support de cours chargé"
    )
    syllabus_uploaded = models.BooleanField(
        default=False,
        verbose_name="Syllabus chargé"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"
        ordering = ['-date_validation']
        indexes = [
            models.Index(fields=['professeur', 'status']),
            models.Index(fields=['classe', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['-date_validation']),
        ]
    
    def __str__(self):
        return f"Contrat #{self.id} - {self.professeur} - {self.maquette}"
    
    @property
    def volume_total_contractuel(self):
        """Volume horaire total contractuel"""
        return self.volume_heure_cours + self.volume_heure_td
    
    @property
    def montant_total_contractuel(self):
        """Montant total du contrat"""
        montant = Decimal('0.00')
        montant += self.volume_heure_cours * self.taux_horaire_cours
        montant += self.volume_heure_td * self.taux_horaire_td
        return montant
    
    def get_heures_effectuees(self):
        """Retourne les heures effectivement réalisées"""
        pointages = self.pointages.aggregate(
            cours=models.Sum('heures_cours'),
            td=models.Sum('heures_td'),
        )
        return {
            'cours': pointages['cours'] or Decimal('0.00'),
            'td': pointages['td'] or Decimal('0.00'),
        }
    
    @property
    def volume_total_effectue(self):
        """Volume horaire total effectué"""
        effectues = self.get_heures_effectuees()
        return effectues['cours'] + effectues['td']
    
    @property
    def taux_realisation(self):
        """Taux de réalisation en pourcentage"""
        if self.volume_total_contractuel == 0:
            return 0
        return (self.volume_total_effectue / self.volume_total_contractuel) * 100
    
    def calculate_montant_a_payer(self):
        """Calcule le montant à payer basé sur les heures effectuées"""
        effectues = self.get_heures_effectuees()
        montant = Decimal('0.00')
        
        montant += effectues['cours'] * self.taux_horaire_cours
        montant += effectues['td'] * self.taux_horaire_td
        
        return montant
    
    def demarrer_cours(self, user, type_enseignement='NORMAL', classes_tronc_commun=None):
        """
        Démarre le cours
        """
        if self.status not in ['VALIDATED', 'READY_TO_START']:
            raise ValidationError("Le contrat ne peut pas être démarré")
        
        self.type_enseignement = type_enseignement
        self.demarre_par = user
        self.date_demarrage = timezone.now()
        self.date_debut_reelle = timezone.now().date()
        self.status = 'IN_PROGRESS'
        self.save()
        
        # Ajouter les classes en tronc commun si applicable
        if type_enseignement == 'TRONC_COMMUN' and classes_tronc_commun:
            self.classes_tronc_commun.set(classes_tronc_commun)
        
        # Log l'action
        ActionLog.objects.create(
            contrat=self,
            action='STARTED',
            user=user,
            details=f"Cours démarré en mode {type_enseignement}"
        )
    
    def terminer_cours(self, user):
        """
        Termine le cours et vérifie les documents obligatoires
        """
        if self.status != 'IN_PROGRESS':
            raise ValidationError("Le contrat n'est pas en cours")
        
        self.date_fin_reelle = timezone.now().date()
        
        # Vérifier les documents obligatoires
        if self.support_cours_uploaded and self.syllabus_uploaded:
            self.status = 'READY_FOR_PAYMENT'
        else:
            self.status = 'PENDING_DOCUMENTS'
        
        self.save()
        
        # Log l'action
        ActionLog.objects.create(
            contrat=self,
            action='COMPLETED',
            user=user,
            details=f"Cours terminé - Documents: {'OK' if self.status == 'READY_FOR_PAYMENT' else 'Manquants'}"
        )
    
    def check_documents_and_update_status(self):
        """
        Vérifie si tous les documents sont chargés et met à jour le statut
        """
        if self.status == 'PENDING_DOCUMENTS':
            if self.support_cours_uploaded and self.syllabus_uploaded:
                self.status = 'READY_FOR_PAYMENT'
                self.save()
                
                # Log l'action
                ActionLog.objects.create(
                    contrat=self,
                    action='READY_FOR_PAYMENT',
                    details="Tous les documents ont été chargés"
                )
    
    def can_start(self):
        """Vérifie si le contrat peut être démarré"""
        return self.status in ['VALIDATED', 'READY_TO_START']
    
    def can_be_paid(self):
        """Vérifie si le contrat peut être payé"""
        return (
            self.status == 'READY_FOR_PAYMENT' and
            self.support_cours_uploaded and
            self.syllabus_uploaded and
            self.volume_total_effectue > 0
        )


class Pointage(models.Model):
    """
    Pointage des heures effectuées pour un contrat
    Créé régulièrement par le responsable pédagogique
    """
    
    # Relations
    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.CASCADE,
        related_name='pointages',
        verbose_name="Contrat"
    )
    
    # Date et heures
    date_seance = models.DateField(
        verbose_name="Date de la séance"
    )
    heure_debut = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure de début"
    )
    heure_fin = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure de fin"
    )
    
    # Volumes horaires de la séance
    heures_cours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Heures de cours"
    )
    heures_td = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Heures de TD"
    )   
    # Validation
    est_valide = models.BooleanField(
        default=True,
        verbose_name="Est validé"
    )
    
    # Enregistré par
    enregistre_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pointages_enregistres',
        verbose_name="Enregistré par"
    )
    date_enregistrement = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'enregistrement"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Pointage"
        verbose_name_plural = "Pointages"
        ordering = ['-date_seance']
        indexes = [
            models.Index(fields=['contrat', '-date_seance']),
            models.Index(fields=['-date_seance']),
        ]
    
    def __str__(self):
        return f"Pointage {self.date_seance} - {self.contrat}"
    
    @property
    def total_heures(self):
        """Total des heures de la séance"""
        return self.heures_cours + self.heures_td
    
    def clean(self):
        """Validation personnalisée"""
        super().clean()
        
        # Vérifier qu'au moins un type d'heure est renseigné
        if self.total_heures == 0:
            raise ValidationError("Au moins un type d'heure doit être renseigné")
        
        # ⭐ CORRECTION : Vérifier si le contrat existe sans déclencher d'erreur RelatedObjectDoesNotExist
        if not hasattr(self, 'contrat') or not self.contrat:
            # Si le contrat n'est pas défini, on ne peut pas faire les vérifications de volume
            return
        
        # Vérifier que les heures ne dépassent pas les volumes contractuels
        effectues = self.contrat.get_heures_effectuees()
        
        # Exclure ce pointage s'il existe déjà
        if self.pk:
            effectues['cours'] -= self.heures_cours
            effectues['td'] -= self.heures_td
        
        if effectues['cours'] + self.heures_cours > self.contrat.volume_heure_cours:
            raise ValidationError(
                f"Les heures de cours dépassent le volume contractuel "
                f"({effectues['cours'] + self.heures_cours} > {self.contrat.volume_heure_cours})"
            )
        
        if effectues['td'] + self.heures_td > self.contrat.volume_heure_td:
            raise ValidationError(
                f"Les heures de TD dépassent le volume contractuel "
                f"({effectues['td'] + self.heures_td} > {self.contrat.volume_heure_td})"
            )


class DocumentContrat(models.Model):
    """
    Documents associés à un contrat (support de cours, syllabus, etc.)
    """
    
    TYPE_DOCUMENT_CHOICES = [
        ('SUPPORT_COURS', 'Support de cours'),
        ('SYLLABUS', 'Syllabus'),
        ('FICHE_CONTRAT', 'Fiche de contrat'),
        ('AUTRE', 'Autre'),
    ]
    
    # Relations
    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Contrat"
    )
    
    # Informations du document
    type_document = models.CharField(
        max_length=20,
        choices=TYPE_DOCUMENT_CHOICES,
        verbose_name="Type de document"
    )
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    fichier = models.FileField(
        upload_to='contrats/documents/%Y/%m/',
        verbose_name="Fichier"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Métadonnées
    charge_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='documents_charges',
        verbose_name="Chargé par"
    )
    date_upload = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'upload"
    )
    
    # Validation
    est_valide = models.BooleanField(
        default=False,
        verbose_name="Est validé"
    )
    valide_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_valides',
        verbose_name="Validé par"
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Document de contrat"
        verbose_name_plural = "Documents de contrat"
        ordering = ['-date_upload']
        indexes = [
            models.Index(fields=['contrat', 'type_document']),
        ]
    
    def __str__(self):
        return f"{self.get_type_document_display()} - {self.contrat}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Mettre à jour les champs du contrat
        if self.type_document == 'SUPPORT_COURS' and self.est_valide:
            self.contrat.support_cours_uploaded = True
            self.contrat.save()
            self.contrat.check_documents_and_update_status()
        
        elif self.type_document == 'SYLLABUS' and self.est_valide:
            self.contrat.syllabus_uploaded = True
            self.contrat.save()
            self.contrat.check_documents_and_update_status()


class PaiementContrat(models.Model):
    """
    Paiement d'un contrat
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé'),
        ('PROCESSING', 'En cours de traitement'),
        ('PAID', 'Payé'),
        ('REJECTED', 'Rejeté'),
        ('CANCELLED', 'Annulé'),
    ]
    
    MODE_PAIEMENT_CHOICES = [
        ('VIREMENT', 'Virement bancaire'),
        ('CHEQUE', 'Chèque'),
        ('ESPECES', 'Espèces'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    # Relations
    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name="Contrat"
    )
    professeur = models.ForeignKey(
        'Utilisateur.Professeur',
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name="Professeur"
    )
    
    # Montants
    montant_brut = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant brut (FCFA)"
    )
    montant_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name="Déductions (FCFA)",
        help_text="Impôts, cotisations, etc."
    )
    montant_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Montant net (FCFA)"
    )
    
    # Détails du paiement
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Mode de paiement"
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence de paiement",
        help_text="Numéro de chèque, référence virement, etc."
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )
    
    # Dates
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    date_approbation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'approbation"
    )
    date_paiement = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    
    # Acteurs
    cree_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='paiements_crees',
        verbose_name="Créé par"
    )
    approuve_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_approuves',
        verbose_name="Approuvé par"
    )
    paye_par = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_effectues',
        verbose_name="Payé par"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    raison_rejet = models.TextField(
        blank=True,
        verbose_name="Raison du rejet"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paiement de contrat"
        verbose_name_plural = "Paiements de contrats"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['professeur', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['-date_creation']),
        ]
    
    def __str__(self):
        return f"Paiement #{self.id} - {self.professeur} - {self.montant_net} FCFA"
    
    def save(self, *args, **kwargs):
        # Calculer le montant net si pas déjà fait
        if not self.montant_net:
            self.montant_net = self.montant_brut - self.montant_deductions
        
        super().save(*args, **kwargs)
    
    def approuver(self, user):
        """Approuve le paiement"""
        if self.status != 'PENDING':
            raise ValidationError("Seuls les paiements en attente peuvent être approuvés")
        
        self.status = 'APPROVED'
        self.approuve_par = user
        self.date_approbation = timezone.now()
        self.save()
        
        ActionLog.objects.create(
            contrat=self.contrat,
            paiement=self,
            action='PAYMENT_APPROVED',
            user=user,
            details=f"Paiement approuvé - Montant: {self.montant_net} FCFA"
        )
    
    def effectuer_paiement(self, user, mode_paiement, reference=''):
        """Effectue le paiement"""
        if self.status != 'APPROVED':
            raise ValidationError("Seuls les paiements approuvés peuvent être payés")
        
        self.status = 'PAID'
        self.mode_paiement = mode_paiement
        self.reference_paiement = reference
        self.paye_par = user
        self.date_paiement = timezone.now()
        self.save()
        
        # Mettre à jour le statut du contrat
        self.contrat.status = 'PAID'
        self.contrat.save()
        
        ActionLog.objects.create(
            contrat=self.contrat,
            paiement=self,
            action='PAID',
            user=user,
            details=f"Paiement effectué - Mode: {mode_paiement} - Montant: {self.montant_net} FCFA"
        )
    
    def rejeter(self, user, raison):
        """Rejette le paiement"""
        if self.status not in ['PENDING', 'APPROVED']:
            raise ValidationError("Ce paiement ne peut plus être rejeté")
        
        self.status = 'REJECTED'
        self.raison_rejet = raison
        self.save()
        
        ActionLog.objects.create(
            contrat=self.contrat,
            paiement=self,
            action='PAYMENT_REJECTED',
            user=user,
            details=f"Paiement rejeté - Raison: {raison}"
        )


class ActionLog(models.Model):
    """
    Journal des actions effectuées sur les contrats
    """
    
    ACTION_CHOICES = [
        ('CREATED', 'Créé'),
        ('SUBMITTED', 'Soumis'),
        ('VALIDATED', 'Validé'),
        ('STARTED', 'Démarré'),
        ('COMPLETED', 'Terminé'),
        ('READY_FOR_PAYMENT', 'Prêt pour paiement'),
        ('PAYMENT_CREATED', 'Paiement créé'),
        ('PAYMENT_APPROVED', 'Paiement approuvé'),
        ('PAID', 'Payé'),
        ('PAYMENT_REJECTED', 'Paiement rejeté'),
        ('CANCELLED', 'Annulé'),
        ('DOCUMENT_UPLOADED', 'Document chargé'),
        ('OTHER', 'Autre'),
    ]
    
    # Relations (tous optionnels car l'action peut concerner différents objets)
    pre_contrat = models.ForeignKey(
        PreContrat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Pré-contrat"
    )
    module_propose = models.ForeignKey(
        ModulePropose,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Module proposé"
    )
    contrat = models.ForeignKey(
        Contrat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Contrat"
    )
    paiement = models.ForeignKey(
        PaiementContrat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Paiement"
    )
    
    # Action
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    details = models.TextField(
        blank=True,
        verbose_name="Détails"
    )
    
    # Acteur
    user = models.ForeignKey(
        'Utilisateur.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='action_logs',
        verbose_name="Utilisateur"
    )
    
    # Date
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date/Heure"
    )
    
    class Meta:
        verbose_name = "Journal d'action"
        verbose_name_plural = "Journal des actions"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['contrat', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp}"