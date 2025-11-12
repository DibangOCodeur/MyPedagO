from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from Utilisateur.models import Professeur
import csv


class Command(BaseCommand):
    help = 'Vérifier les documents manquants des professeurs et envoyer des notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Envoyer des emails aux professeurs avec documents manquants',
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Exporter la liste dans un fichier CSV (ex: --export rapport.csv)',
        )
        parser.add_argument(
            '--section',
            type=str,
            help='Filtrer par section spécifique',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Inclure aussi les professeurs inactifs',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('    VÉRIFICATION DES DOCUMENTS PROFESSEURS'))
        self.stdout.write(self.style.SUCCESS('=' * 70 + '\n'))
        
        # Construire la requête
        queryset = Professeur.objects.all()
        
        if not options['all']:
            queryset = queryset.filter(is_active=True)
            self.stdout.write('📋 Analyse des professeurs actifs uniquement\n')
        else:
            self.stdout.write('📋 Analyse de tous les professeurs (actifs et inactifs)\n')
        
        if options['section']:
            queryset = queryset.filter(sections__nom__icontains=options['section'])
            self.stdout.write(f'📍 Filtré par section: {options["section"]}\n')
        
        professeurs = queryset.select_related('user')
        professeurs_incomplets = []
        
        # Analyser chaque professeur
        for prof in professeurs:
            if not prof.has_complete_documents():
                professeurs_incomplets.append(prof)
                missing = prof.get_missing_documents()
                
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️  {prof.user.get_full_name()} ({prof.matricule})'
                    )
                )
                self.stdout.write(f'   Email: {prof.user.email}')
                self.stdout.write(f'   Grade: {prof.get_grade_display()}')
                self.stdout.write(f'   Statut: {prof.get_statut_display()}')
                
                if not prof.is_active:
                    self.stdout.write(self.style.ERROR('   ⚠️  INACTIF'))
                
                self.stdout.write(
                    self.style.ERROR(
                        f'   Documents manquants ({len(missing)}/5): {", ".join(missing)}'
                    )
                )
                
                # Envoyer un email si demandé
                if options['send_email'] and prof.is_active:
                    self.send_notification_email(prof, missing)
        
        # Afficher le résumé
        self.display_summary(professeurs.count(), len(professeurs_incomplets))
        
        # Exporter si demandé
        if options['export']:
            self.export_to_csv(professeurs_incomplets, options['export'])
        
        self.stdout.write(self.style.SUCCESS('\n✅ Vérification terminée\n'))
    
    def send_notification_email(self, professeur, missing_docs):
        """Envoyer un email de notification au professeur"""
        subject = 'Documents manquants - Action requise'
        
        message = f"""
Bonjour {professeur.user.get_full_name()},

Nous avons constaté que certains documents de votre dossier administratif 
sont manquants ou incomplets.

Documents manquants ({len(missing_docs)}/5):
{chr(10).join([f'  • {doc}' for doc in missing_docs])}

Merci de les fournir dans les meilleurs délais en vous connectant à votre 
espace personnel ou en contactant le service des ressources humaines.

Informations de connexion:
Email: {professeur.user.email}

Pour toute question, n'hésitez pas à nous contacter.

Cordialement,
Le service des Ressources Humaines
Institut IIPEA
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [professeur.user.email],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Email envoyé à {professeur.user.email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Erreur email: {str(e)}')
            )
    
    def display_summary(self, total, incomplets):
        """Afficher le résumé des statistiques"""
        complets = total - incomplets
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('    RÉSUMÉ'))
        self.stdout.write('=' * 70)
        
        self.stdout.write(f'\n📊 Total de professeurs analysés: {total}')
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Dossiers complets: {complets} ({complets/total*100:.1f}%)'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'⚠️  Dossiers incomplets: {incomplets} ({incomplets/total*100:.1f}%)'
            )
        )
        
        if incomplets > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n💡 {incomplets} professeur(s) doivent compléter leur dossier'
                )
            )
    
    def export_to_csv(self, professeurs, filename):
        """Exporter la liste vers un fichier CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # En-têtes
                writer.writerow([
                    'Matricule',
                    'Nom',
                    'Prénom',
                    'Email',
                    'Téléphone',
                    'Grade',
                    'Statut',
                    'Actif',
                    'Nb Documents Manquants',
                    'Documents Manquants',
                    'Date Création'
                ])
                
                # Données
                for prof in professeurs:
                    missing = prof.get_missing_documents()
                    writer.writerow([
                        prof.matricule,
                        prof.user.last_name,
                        prof.user.first_name,
                        prof.user.email,
                        prof.user.telephone or '',
                        prof.get_grade_display(),
                        prof.get_statut_display(),
                        'Oui' if prof.is_active else 'Non',
                        len(missing),
                        ', '.join(missing),
                        prof.created_at.strftime('%d/%m/%Y %H:%M')
                    ])
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Rapport exporté vers: {filename}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Erreur export CSV: {str(e)}')
            )