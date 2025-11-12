"""
==============================================
COMMANDE 4: import_professeurs.py (BONUS)
Emplacement: management/commands/import_professeurs.py
==============================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from utilisateurs.models import Professeur, CustomUser, Section
import csv


class Command(BaseCommand):
    help = 'Importer des professeurs depuis un fichier CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Chemin vers le fichier CSV',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tester l\'import sans créer les données',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n📥 Import de professeurs...\n'))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Mode --dry-run: aucune donnée ne sera créée\n')
            )
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                success_count = 0
                error_count = 0
                
                for row in reader:
                    try:
                        if not dry_run:
                            self.create_professeur(row)
                        else:
                            self.validate_row(row)
                        
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ {row.get("nom")} {row.get("prenom")}'
                            )
                        )
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'❌ Erreur ligne {success_count + error_count}: {str(e)}'
                            )
                        )
                
                self.stdout.write(f'\n📊 Résumé:')
                self.stdout.write(f'  ✅ Succès: {success_count}')
                self.stdout.write(f'  ❌ Erreurs: {error_count}')
                
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'❌ Fichier non trouvé: {csv_file}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur: {str(e)}')
            )
    
    def create_professeur(self, row):
        """Créer un professeur depuis une ligne CSV"""
        with transaction.atomic():
            # Créer l'utilisateur
            user = CustomUser.objects.create_user(
                email=row['email'],
                first_name=row['prenom'],
                last_name=row['nom'],
                role='PROFESSEUR',
                telephone=row.get('telephone', ''),
            )
            
            # Créer le professeur
            from datetime import datetime
            date_naissance = datetime.strptime(row['date_naissance'], '%d/%m/%Y').date()
            
            professeur = Professeur.objects.create(
                user=user,
                date_naissance=date_naissance,
                grade=row.get('grade', 'Professeur'),
                statut=row.get('statut', 'Vacataire'),
                genre=row.get('genre', 'Masculin'),
                specialite=row.get('specialite', ''),
                diplome=row.get('diplome', ''),
            )
            
            return professeur
    
    def validate_row(self, row):
        """Valider une ligne CSV"""
        required_fields = ['email', 'nom', 'prenom', 'date_naissance']
        for field in required_fields:
            if not row.get(field):
                raise ValueError(f'Champ requis manquant: {field}')