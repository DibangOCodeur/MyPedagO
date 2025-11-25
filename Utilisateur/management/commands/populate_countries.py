import requests
from django.core.management.base import BaseCommand
from Utilisateur.models import Pays

class Command(BaseCommand):
    def handle(self, *args, **options):
        response = requests.get('https://restcountries.com/v3.1/all')
        countries = response.json()
        
        for pays in countries:
            Pays.objects.get_or_create(
                nom=pays['name']['common'],
                code=pays['cca3'],
                defaults={'flag': pays.get('flags', {}).get('png', '')}
            )