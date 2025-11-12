from django.apps import AppConfig


class UtilisateurConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Utilisateur'
    verbose_name = 'Gestion des Utilisateurs'

    def ready(self):
        import Utilisateur.signals  # Importer les signaux