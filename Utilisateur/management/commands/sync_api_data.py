"""
Commande Django pour synchroniser les données API
Usage: python manage.py sync_api_data
"""

from django.core.management.base import BaseCommand
from Utilisateur.services import SyncService


class Command(BaseCommand):
    help = 'Synchronise les données depuis les APIs externes MyIIPEA'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la synchronisation (ignore le cache)',
        )
        parser.add_argument(
            '--classes-only',
            action='store_true',
            help='Synchronise uniquement les classes',
        )
        parser.add_argument(
            '--maquettes-only',
            action='store_true',
            help='Synchronise uniquement les maquettes',
        )
    
    def handle(self, *args, **options):
        sync_service = SyncService()
        force = options['force']
        
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.HTTP_INFO(" 🔄 SYNCHRONISATION DES DONNÉES API "))
        self.stdout.write("=" * 60)
        
        if options['classes_only']:
            self.stdout.write("\n📚 Synchronisation des classes...")
            success, result = sync_service.sync_classes(force=force)
            
        elif options['maquettes_only']:
            self.stdout.write("\n📋 Synchronisation des maquettes...")
            success, result = sync_service.sync_maquettes(force=force)
            
        else:
            self.stdout.write("\n🔄 Synchronisation complète...")
            success, result = sync_service.full_sync(force=force)
        
        self.stdout.write("\n" + "=" * 60)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Synchronisation réussie!\n')
            )
            
            if 'classes' in result:
                classes = result['classes']
                self.stdout.write(f"📚 Classes:")
                self.stdout.write(f"   - Créées: {classes.get('created', 0)}")
                self.stdout.write(f"   - Mises à jour: {classes.get('updated', 0)}")
                self.stdout.write(f"   - Désactivées: {classes.get('deactivated', 0)}")
            
            if 'maquettes' in result:
                maquettes = result['maquettes']
                self.stdout.write(f"\n📋 Maquettes:")
                self.stdout.write(f"   - Créées: {maquettes.get('total_created', 0)}")
                self.stdout.write(f"   - Mises à jour: {maquettes.get('total_updated', 0)}")
            
            if isinstance(result, dict) and 'created' in result:
                self.stdout.write(f"\n✅ Créées: {result['created']}")
                self.stdout.write(f"♻️  Mises à jour: {result['updated']}")
        else:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Échec de la synchronisation')
            )
            self.stdout.write(
                self.style.ERROR(f'Erreur: {result.get("error", "Inconnue")}')
            )
        
        self.stdout.write("\n" + "=" * 60)