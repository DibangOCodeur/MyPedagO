
"""
Signaux Django pour le système de gestion IIPEA
CORRECTION : Éviter les contraintes de clés étrangères et les boucles infinies
"""

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from .models import Professeur, CustomUser, Comptable
import logging

logger = logging.getLogger(__name__)


# ==========================================
# SIGNAUX PROFESSEUR - CRÉATION
# ==========================================

@receiver(post_save, sender=Professeur)
def professeur_created_notification(sender, instance, created, **kwargs):
    """
    Envoyer une notification quand un professeur est créé
    """
    if created:
        try:
            # Email de bienvenue au professeur
            send_welcome_email(instance)
            
            # Notification admin si documents manquants
            if not instance.has_complete_documents():
                notify_admin_missing_documents(instance)
        except Exception as e:
            logger.error(f"Erreur notifications professeur: {str(e)}")


def send_welcome_email(professeur):
    """Envoyer l'email de bienvenue au nouveau professeur"""
    try:
        subject = 'Bienvenue à l\'Institut IIPEA'
        
        plain_message = f"""
Bonjour {professeur.user.get_full_name()},

Bienvenue à l'Institut IIPEA !

Votre compte a été créé avec succès. Voici vos informations de connexion :

Email: {professeur.user.email}
Mot de passe temporaire: @elites@
Matricule: {professeur.matricule}

Nous vous recommandons de changer votre mot de passe dès votre première connexion.

N'oubliez pas de compléter votre dossier avec tous les documents requis.

Cordialement,
L'équipe IIPEA
        """
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [professeur.user.email],
            fail_silently=True,
        )
        
        logger.info(f"Email de bienvenue envoyé à {professeur.user.email}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de bienvenue: {str(e)}")


def notify_admin_missing_documents(professeur):
    """Notifier les administrateurs des documents manquants"""
    try:
        missing_docs = professeur.get_missing_documents()
        subject = f'Documents manquants - {professeur.user.get_full_name()}'
        
        message = f"""
Un nouveau professeur a été créé avec des documents manquants :

Nom complet: {professeur.user.get_full_name()}
Matricule: {professeur.matricule}
Email: {professeur.user.email}
Téléphone: {professeur.user.telephone}
Grade: {professeur.get_grade_display()}
Statut: {professeur.get_statut_display()}

Documents manquants ({len(missing_docs)}/{5}):
{chr(10).join([f'  • {doc}' for doc in missing_docs])}

Merci de faire le suivi auprès du professeur.

---
Cet email a été généré automatiquement.
        """
        
        # Récupérer les emails des administrateurs et RH
        admin_emails = CustomUser.objects.filter(
            role__in=['ADMIN', 'RESP_RH'],
            is_active=True,
            is_active_user=True
        ).values_list('email', flat=True)
        
        if admin_emails:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(admin_emails),
                fail_silently=True,
            )
            
            logger.info(
                f"Notification admin envoyée pour {professeur.matricule} "
                f"à {len(admin_emails)} destinataires"
            )
        
    except Exception as e:
        logger.error(f"Erreur notification admin: {str(e)}")


# ==========================================
# SIGNAUX PROFESSEUR - SUPPRESSION
# ==========================================

@receiver(pre_delete, sender=Professeur)
def delete_professeur_files(sender, instance, **kwargs):
    """
    Supprimer tous les fichiers associés quand un professeur est supprimé
    """
    try:
        files_deleted = []
        
        # Liste des champs de fichiers à supprimer
        file_fields = [
            ('photo', 'Photo'),
            ('cni_document', 'CNI'),
            ('rib_document', 'RIB'),
            ('cv_document', 'CV'),
            ('diplome_document', 'Diplôme')
        ]
        
        # Supprimer chaque fichier
        for field_name, doc_name in file_fields:
            field = getattr(instance, field_name)
            if field:
                try:
                    field.delete(save=False)
                    files_deleted.append(doc_name)
                except Exception as e:
                    logger.warning(f"Erreur suppression {doc_name}: {str(e)}")
        
        if files_deleted:
            logger.info(
                f"Documents supprimés pour {instance.matricule}: "
                f"{', '.join(files_deleted)}"
            )
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des fichiers: {str(e)}")


# ==========================================
# SIGNAUX UTILISATEUR - SYNCHRONISATION
# ==========================================

@receiver(post_save, sender=CustomUser)
def sync_user_with_profiles(sender, instance, created, update_fields=None, **kwargs):
    """
    Synchroniser l'état de l'utilisateur avec ses profils associés
    CORRECTION : Éviter les boucles infinies avec update_fields
    """
    # Ne rien faire pour les nouvelles créations
    if created:
        return
    
    # Ne rien faire si c'est déjà une mise à jour spécifique
    if update_fields:
        return
    
    try:
        # Synchroniser avec le profil Comptable
        if hasattr(instance, 'comptable'):
            comptable = instance.comptable
            
            # Si l'utilisateur est désactivé, désactiver aussi le comptable
            if not instance.is_active and comptable.is_active:
                # Utiliser update_fields pour éviter les boucles
                Comptable.objects.filter(pk=comptable.pk).update(
                    is_active=False
                )
                logger.info(
                    f"Comptable {comptable.matricule} désactivé "
                    f"suite à la désactivation de l'utilisateur"
                )
        
        # Synchroniser avec le profil Professeur
        if hasattr(instance, 'professeur'):
            professeur = instance.professeur
            
            # Si l'utilisateur est désactivé, désactiver aussi le professeur
            if not instance.is_active and professeur.is_active:
                # Utiliser update_fields pour éviter les boucles
                Professeur.objects.filter(pk=professeur.pk).update(
                    is_active=False
                )
                logger.info(
                    f"Professeur {professeur.matricule} désactivé "
                    f"suite à la désactivation de l'utilisateur"
                )
                
    except Exception as e:
        logger.error(f"Erreur synchronisation profils: {str(e)}")


# ==========================================
# SIGNAUX UTILISATEUR - PROTECTION
# ==========================================

@receiver(pre_delete, sender=CustomUser)
def prevent_active_user_deletion(sender, instance, **kwargs):
    """
    Empêcher la suppression d'utilisateurs actifs avec profils
    """
    try:
        # Vérifier si c'est un professeur actif
        if hasattr(instance, 'professeur') and instance.professeur.is_active:
            raise ValidationError(
                f"Impossible de supprimer l'utilisateur {instance.email} : "
                f"le professeur {instance.professeur.matricule} est actif. "
                f"Veuillez d'abord désactiver le professeur."
            )
        
        # Vérifier si c'est un comptable actif
        if hasattr(instance, 'comptable') and instance.comptable.is_active:
            raise ValidationError(
                f"Impossible de supprimer l'utilisateur {instance.email} : "
                f"le comptable {instance.comptable.matricule} est actif. "
                f"Veuillez d'abord désactiver le comptable."
            )
            
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erreur vérification suppression utilisateur: {str(e)}")


# ==========================================
# SIGNAUX COMPTABLE - CRÉATION
# ==========================================

@receiver(post_save, sender=Comptable)
def comptable_created_notification(sender, instance, created, **kwargs):
    """
    Envoyer une notification quand un comptable est créé
    """
    if created:
        try:
            subject = 'Bienvenue à l\'Institut IIPEA - Service Comptabilité'
            
            message = f"""
Bonjour {instance.user.get_full_name()},

Bienvenue à l'Institut IIPEA !

Votre compte comptable a été créé avec succès. Voici vos informations :

Email: {instance.user.email}
Mot de passe temporaire: @elites@
Matricule: {instance.matricule}
Code unique: {instance.code_unique}

Nous vous recommandons de :
1. Changer votre mot de passe dès votre première connexion
2. Compléter votre profil avec vos informations personnelles
3. Vous familiariser avec l'interface de gestion

Cordialement,
L'équipe IIPEA
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                fail_silently=True,
            )
            
            logger.info(f"Email de bienvenue comptable envoyé à {instance.user.email}")
            
        except Exception as e:
            logger.error(f"Erreur email bienvenue comptable: {str(e)}")


# ==========================================
# SIGNAUX COMPTABLE - SUPPRESSION
# ==========================================

@receiver(pre_delete, sender=Comptable)
def comptable_deletion_log(sender, instance, **kwargs):
    """
    Logger la suppression d'un comptable
    """
    try:
        logger.warning(
            f"Suppression du comptable: {instance.get_nom_complet()} "
            f"(Matricule: {instance.matricule}, Code: {instance.code_unique})"
        )
    except Exception as e:
        logger.error(f"Erreur log suppression comptable: {str(e)}")


# ==========================================
# VALIDATION PRÉ-SAUVEGARDE
# ==========================================

@receiver(pre_save, sender=Comptable)
def validate_comptable_user(sender, instance, **kwargs):
    """
    Valider l'utilisateur avant la sauvegarde du comptable
    """
    if instance.user_id:
        # Vérifier que l'utilisateur a le bon rôle
        if instance.user.role != 'COMPTABLE':
            raise ValidationError(
                f"L'utilisateur doit avoir le rôle COMPTABLE. "
                f"Rôle actuel : {instance.user.get_role_display()}"
            )
        
        # Vérifier qu'il n'y a pas de doublon
        existing = Comptable.objects.filter(
            user=instance.user
        ).exclude(pk=instance.pk)
        
        if existing.exists():
            raise ValidationError(
                f"L'utilisateur {instance.user.email} est déjà "
                f"associé à un autre comptable."
            )


@receiver(pre_save, sender=Professeur)
def validate_professeur_user(sender, instance, **kwargs):
    """
    Valider l'utilisateur avant la sauvegarde du professeur
    """
    if instance.user_id:
        # Vérifier que l'utilisateur a le bon rôle
        if instance.user.role != 'PROFESSEUR':
            logger.error(
                f"Tentative de création professeur avec mauvais rôle: "
                f"{instance.user.get_role_display()} pour {instance.user.email}"
            )
            raise ValidationError(
                f"L'utilisateur doit avoir le rôle PROFESSEUR. "
                f"Rôle actuel : {instance.user.get_role_display()}"
            )
        
        # Vérifier qu'il n'y a pas de doublon
        existing = Professeur.objects.filter(
            user=instance.user
        ).exclude(pk=instance.pk)
        
        if existing.exists():
            logger.error(f"Doublon professeur détecté pour {instance.user.email}")
            raise ValidationError(
                f"L'utilisateur {instance.user.email} est déjà "
                f"associé à un autre professeur."
            )
        
        logger.info(f"Validation professeur OK pour {instance.user.email}")

# ==========================================
# UTILITAIRES
# ==========================================

def send_bulk_notification(subject, message, recipient_roles=None, active_only=True):
    """
    Envoyer une notification à plusieurs utilisateurs selon leur rôle
    
    Args:
        subject (str): Sujet de l'email
        message (str): Corps du message
        recipient_roles (list): Liste des rôles destinataires (None = tous)
        active_only (bool): Envoyer uniquement aux utilisateurs actifs
    """
    try:
        queryset = CustomUser.objects.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True, is_active_user=True)
        
        if recipient_roles:
            queryset = queryset.filter(role__in=recipient_roles)
        
        recipient_emails = list(queryset.values_list('email', flat=True))
        
        if recipient_emails:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_emails,
                fail_silently=True,
            )
            
            logger.info(
                f"Notification envoyée à {len(recipient_emails)} utilisateurs "
                f"(Rôles: {recipient_roles or 'Tous'})"
            )
            return len(recipient_emails)
        else:
            logger.warning("Aucun destinataire trouvé pour la notification")
            return 0
            
    except Exception as e:
        logger.error(f"Erreur envoi notification groupée: {str(e)}")
        return 0