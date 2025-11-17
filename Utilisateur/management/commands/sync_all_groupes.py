# management/commands/sync_all_groupes.py
from django.core.management.base import BaseCommand
from Gestion.models import Classe
from Utilisateur.services import GroupeSynchronizationService
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronise tous les groupes depuis l\'API MyIIPEA'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer la synchronisation (ignorer le cache)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 LANCEMENT DE LA SYNCHRONISATION COMPLÈTE DES GROUPES")
        self.stdout.write("=" * 60)
        
        force = options.get('force', False)
        
        service = GroupeSynchronizationService()
        
        # Récupérer toutes les classes actives
        classes = Classe.objects.filter(is_active=True)
        total_classes = classes.count()
        
        self.stdout.write(f"📚 {total_classes} classes actives trouvées")
        self.stdout.write(f"⚡ Mode: {'FORCE' if force else 'NORMAL'}")
        self.stdout.write("⏳ Démarrage de la synchronisation...\n")
        
        start_time = time.time()
        
        # Utiliser la méthode existante du service
        stats = service.sync_tous_les_groupes(force=force)
        
        duration = time.time() - start_time
        
        # Affichage des résultats
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 RÉSULTATS DE LA SYNCHRONISATION")
        self.stdout.write("=" * 50)
        self.stdout.write(f"✅ Stratégie utilisée: {stats.get('strategie_utilisee', 'N/A')}")
        self.stdout.write(f"✅ Groupes trouvés dans l'API: {stats.get('groupes_trouves', 0)}")
        self.stdout.write(f"✅ Groupes créés: {stats.get('groupes_crees', 0)}")
        self.stdout.write(f"✅ Groupes mis à jour: {stats.get('groupes_mis_a_jour', 0)}")
        self.stdout.write(f"✅ Groupes désactivés: {stats.get('groupes_desactives', 0)}")
        self.stdout.write(f"✅ Durée totale: {duration:.2f} secondes")
        
        # Gestion des erreurs
        errors = stats.get('errors', [])
        if errors:
            self.stdout.write(f"\n❌ ERREURS RENCONTRÉES: {len(errors)}")
            for i, error in enumerate(errors[:10], 1):  # Afficher les 10 premières
                self.stdout.write(f"   {i}. {error}")
            
            if len(errors) > 10:
                self.stdout.write(f"   ... et {len(errors) - 10} erreur(s) supplémentaire(s)")
        
        self.stdout.write("\n🎯 SYNCHRONISATION TERMINÉE!")
        
        # Vérification finale
        from Gestion.models import Groupe
        total_groupes_final = Groupe.objects.count()
        groupes_actifs = Groupe.objects.filter(is_active=True).count()
        self.stdout.write(f"\n📦 BILAN FINAL:")
        self.stdout.write(f"   • Groupes totaux en base: {total_groupes_final}")
        self.stdout.write(f"   • Groupes actifs: {groupes_actifs}")