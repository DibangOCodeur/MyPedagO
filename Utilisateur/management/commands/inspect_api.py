"""
Commande pour inspecter la structure des données de l'API
Usage: python manage.py inspect_api
"""

from django.core.management.base import BaseCommand
from Utilisateur.api_client import MyIIPEAAPIClient
import json


class Command(BaseCommand):
    help = 'Inspecte la structure des données retournées par l\'API MyIIPEA'
    
    def handle(self, *args, **options):
        client = MyIIPEAAPIClient()
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.HTTP_INFO(" 🔍 INSPECTION DES APIs MyIIPEA "))
        self.stdout.write("=" * 80)
        
        # Inspecter les classes
        self.stdout.write("\n" + "─" * 80)
        self.stdout.write(self.style.SUCCESS("\n📚 CLASSES"))
        self.stdout.write("─" * 80)
        
        classes, error = client.get_classes_liste(departement_id=1, annee_id=1)
        
        if error:
            self.stdout.write(self.style.ERROR(f"❌ Erreur: {error}"))
        elif classes:
            if isinstance(classes, list):
                self.stdout.write(f"✅ {len(classes)} classe(s) trouvée(s)\n")
                
                if len(classes) > 0:
                    self.stdout.write("Structure de la première classe:")
                    self.stdout.write(json.dumps(classes[0], indent=2, ensure_ascii=False))
            else:
                self.stdout.write("Structure des données:")
                self.stdout.write(json.dumps(classes, indent=2, ensure_ascii=False))
        
        # Inspecter les maquettes
        self.stdout.write("\n" + "─" * 80)
        self.stdout.write(self.style.SUCCESS("\n📋 MAQUETTES"))
        self.stdout.write("─" * 80)
        
        maquettes, error = client.get_all_maquettes()
        
        if error:
            self.stdout.write(self.style.ERROR(f"❌ Erreur: {error}"))
        elif maquettes:
            if isinstance(maquettes, list):
                self.stdout.write(f"✅ {len(maquettes)} maquette(s) trouvée(s)\n")
                
                if len(maquettes) > 0:
                    self.stdout.write("Structure de la première maquette:")
                    self.stdout.write(json.dumps(maquettes[0], indent=2, ensure_ascii=False))
            else:
                self.stdout.write("Structure des données:")
                self.stdout.write(json.dumps(maquettes, indent=2, ensure_ascii=False))
        
        # Inspecter les années académiques
        self.stdout.write("\n" + "─" * 80)
        self.stdout.write(self.style.SUCCESS("\n📅 ANNÉES ACADÉMIQUES"))
        self.stdout.write("─" * 80)
        
        annees, error = client.get_annees_academiques()
        
        if error:
            self.stdout.write(self.style.ERROR(f"❌ Erreur: {error}"))
        elif annees:
            if isinstance(annees, list):
                self.stdout.write(f"✅ {len(annees)} année(s) trouvée(s)\n")
                
                if len(annees) > 0:
                    self.stdout.write("Structure:")
                    self.stdout.write(json.dumps(annees, indent=2, ensure_ascii=False))
            else:
                self.stdout.write("Structure des données:")
                self.stdout.write(json.dumps(annees, indent=2, ensure_ascii=False))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("\n✅ Inspection terminée"))
        self.stdout.write("=" * 80 + "\n")