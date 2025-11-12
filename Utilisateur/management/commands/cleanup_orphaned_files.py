"""
==============================================
COMMANDE 2: cleanup_orphaned_files.py
Emplacement: management/commands/cleanup_orphaned_files.py
==============================================
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Nettoyer les fichiers orphelins (non référencés en base de données)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher les fichiers à supprimer sans les supprimer',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Supprimer automatiquement sans confirmation',
        )

    def handle(self, *args, **options):
        from utilisateurs.models import Professeur, ComptableProfile
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('    NETTOYAGE DES FICHIERS ORPHELINS'))
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))
        
        media_root = Path(settings.MEDIA_ROOT)
        
        if not media_root.exists():
            self.stdout.write(
                self.style.WARNING('⚠️  Dossier MEDIA_ROOT introuvable')
            )
            return
        
        # Nettoyer les fichiers des professeurs
        orphaned_prof = self.cleanup_professeur_files(media_root, options)
        
        # Nettoyer les fichiers des comptables
        orphaned_compta = self.cleanup_comptable_files(media_root, options)
        
        # Résumé global
        total_orphaned = orphaned_prof + orphaned_compta
        
        if total_orphaned > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  Total de fichiers orphelins: {total_orphaned}'
                )
            )
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(
                        '\n💡 Mode --dry-run activé: aucun fichier n\'a été supprimé'
                    )
                )
                self.stdout.write(
                    '   Relancez la commande sans --dry-run pour supprimer les fichiers'
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Aucun fichier orphelin trouvé')
            )
        
        self.stdout.write('\n')
    
    def cleanup_professeur_files(self, media_root, options):
        """Nettoyer les fichiers des professeurs"""
        from utilisateurs.models import Professeur
        
        professeurs_path = media_root / 'professeurs'
        
        if not professeurs_path.exists():
            self.stdout.write('📁 Aucun dossier professeurs trouvé')
            return 0
        
        self.stdout.write(
            self.style.SUCCESS('\n🔍 Analyse des fichiers professeurs...')
        )
        
        # Récupérer tous les fichiers référencés
        referenced_files = set()
        for prof in Professeur.objects.all():
            if prof.photo and prof.photo.name:
                referenced_files.add(str(media_root / prof.photo.name))
            if prof.cni_document and prof.cni_document.name:
                referenced_files.add(str(media_root / prof.cni_document.name))
            if prof.rib_document and prof.rib_document.name:
                referenced_files.add(str(media_root / prof.rib_document.name))
            if prof.cv_document and prof.cv_document.name:
                referenced_files.add(str(media_root / prof.cv_document.name))
            if prof.diplome_document and prof.diplome_document.name:
                referenced_files.add(str(media_root / prof.diplome_document.name))
        
        # Trouver les fichiers orphelins
        orphaned_files = []
        total_size = 0
        
        for root, dirs, files in os.walk(professeurs_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in referenced_files:
                    size = os.path.getsize(file_path)
                    orphaned_files.append((file_path, size))
                    total_size += size
        
        if orphaned_files:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  {len(orphaned_files)} fichier(s) orphelin(s) trouvé(s) '
                    f'({total_size / (1024 * 1024):.2f} MB)'
                )
            )
            
            # Afficher les fichiers
            for file_path, size in orphaned_files[:10]:  # Afficher max 10
                self.stdout.write(
                    f'   🗑️  {os.path.basename(file_path)} ({size / 1024:.2f} KB)'
                )
            
            if len(orphaned_files) > 10:
                self.stdout.write(f'   ... et {len(orphaned_files) - 10} autres')
            
            # Supprimer si demandé
            if not options['dry_run']:
                if options['auto'] or self.confirm_deletion():
                    deleted_count = self.delete_files([f[0] for f in orphaned_files])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {deleted_count} fichier(s) supprimé(s)'
                        )
                    )
        
        return len(orphaned_files)
    
    def cleanup_comptable_files(self, media_root, options):
        """Nettoyer les fichiers des comptables"""
        from utilisateurs.models import ComptableProfile
        
        comptables_path = media_root / 'comptables'
        
        if not comptables_path.exists():
            return 0
        
        self.stdout.write(
            self.style.SUCCESS('\n🔍 Analyse des fichiers comptables...')
        )
        
        # Récupérer tous les fichiers référencés
        referenced_files = set()
        for profile in ComptableProfile.objects.all():
            if profile.photo and profile.photo.name:
                referenced_files.add(str(media_root / profile.photo.name))
        
        # Trouver les fichiers orphelins
        orphaned_files = []
        total_size = 0
        
        for root, dirs, files in os.walk(comptables_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in referenced_files:
                    size = os.path.getsize(file_path)
                    orphaned_files.append((file_path, size))
                    total_size += size
        
        if orphaned_files:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  {len(orphaned_files)} fichier(s) orphelin(s) trouvé(s) '
                    f'({total_size / (1024 * 1024):.2f} MB)'
                )
            )
            
            if not options['dry_run']:
                if options['auto'] or self.confirm_deletion():
                    deleted_count = self.delete_files([f[0] for f in orphaned_files])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ {deleted_count} fichier(s) supprimé(s)'
                        )
                    )
        
        return len(orphaned_files)
    
    def confirm_deletion(self):
        """Demander confirmation à l'utilisateur"""
        response = input('\n❓ Voulez-vous supprimer ces fichiers ? (oui/non): ')
        return response.lower() in ['oui', 'o', 'yes', 'y']
    
    def delete_files(self, file_paths):
        """Supprimer une liste de fichiers"""
        deleted = 0
        for file_path in file_paths:
            try:
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erreur: {file_path} - {str(e)}')
                )
        return deleted
