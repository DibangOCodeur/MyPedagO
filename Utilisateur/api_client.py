"""
Client pour interagir avec les APIs MyIIPEA
VERSION MODIFIÉE - Avec récupération des matières
"""

import requests
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MyIIPEAAPIClient:
    """Client pour les APIs MyIIPEA"""
    
    def __init__(self):
        self.base_url = 'https://myiipea.ci/api'
        self.maquettes_base_url = 'https://myiipea.ci/api/maquettes'
        self.timeout = 30
        self.cache_timeout = 300  # 5 minutes
        
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _make_request(self, url, method='GET', params=None, data=None):
        """
        Méthode générique pour les appels API
        
        Args:
            url: URL complète
            method: Méthode HTTP (GET, POST, etc.)
            params: Paramètres query string
            data: Données pour POST/PUT
            
        Returns:
            tuple: (data, error)
        """
        try:
            logger.info(f"🌐 Appel API: {method} {url}")
            
            if method == 'GET':
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout,
                    verify=True  # Vérification SSL
                )
            elif method == 'POST':
                response = requests.post(
                    url,
                    headers=self.headers,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                    verify=True
                )
            else:
                return None, f"Méthode HTTP non supportée: {method}"
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Succès: {len(data) if isinstance(data, list) else 'OK'}")
            
            return data, None
            
        except requests.Timeout:
            error = f"Timeout lors de l'appel à {url}"
            logger.error(f"❌ {error}")
            return None, error
            
        except requests.RequestException as e:
            error = f"Erreur API: {str(e)}"
            logger.error(f"❌ {error}")
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Détails: {error_detail}")
                except:
                    logger.error(f"Status code: {e.response.status_code}")
            
            return None, error
        
        except Exception as e:
            error = f"Erreur inattendue: {str(e)}"
            logger.error(f"❌ {error}")
            return None, error
    
    # ==========================================
    # MÉTHODES POUR LES CLASSES
    # ==========================================
    
    def get_classes_liste(self, departement_id=None, annee_id=None, use_cache=True):
        """
        Récupère la liste des classes
        
        URL: https://myiipea.ci/api/public/public/classes/liste?departement_id=1&annee_id=1
        
        Args:
            departement_id: ID du département (optionnel)
            annee_id: ID de l'année académique (optionnel)
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_classes_{departement_id}_{annee_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info("📦 Classes depuis cache")
                return cached, None
        
        url = f'{self.base_url}/public/public/classes/liste'
        params = {}
        
        if departement_id:
            params['departement_id'] = departement_id
        if annee_id:
            params['annee_id'] = annee_id
        
        data, error = self._make_request(url, params=params)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
            logger.info(f"💾 {len(data) if isinstance(data, list) else 1} classes en cache")
        
        return data, error
    
    def get_classe_detail(self, classe_id, use_cache=True):
        """
        Récupère le détail d'une classe
        
        URL: https://myiipea.ci/api/public/public/classe/62
        
        Args:
            classe_id: ID de la classe
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_classe_{classe_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"📦 Classe {classe_id} depuis cache")
                return cached, None
        
        url = f'{self.base_url}/public/public/classe/{classe_id}'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    def get_groupe_detail(self, groupe_id, use_cache=True):
        """
        Récupère le détail d'un groupe
        
        URL: https://myiipea.ci/api/public/public/groupe/89
        
        Args:
            groupe_id: ID du groupe
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_groupe_{groupe_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"📦 Groupe {groupe_id} depuis cache")
                return cached, None
        
        url = f'{self.base_url}/public/public/groupe/{groupe_id}'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    # ==========================================
    # MÉTHODES POUR LES MAQUETTES
    # ==========================================
    
    def get_all_maquettes(self, use_cache=True):
        """
        Récupère toutes les maquettes
        
        URL: https://myiipea.ci/api/maquettes/
        
        Returns:
            tuple: (data, error)
        """
        cache_key = 'myiipea_all_maquettes'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info("📦 Toutes les maquettes depuis cache")
                return cached, None
        
        url = f'{self.maquettes_base_url}/'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    def get_annees_academiques(self, use_cache=True):
        """
        Récupère les années académiques
        
        URL: https://myiipea.ci/api/maquettes/annees-accademique
        
        Returns:
            tuple: (data, error)
        """
        cache_key = 'myiipea_annees_academiques'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info("📦 Années académiques depuis cache")
                return cached, None
        
        url = f'{self.maquettes_base_url}/annees-accademique'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    def get_maquette_detail(self, maquette_id, use_cache=True):
        """
        Récupère le détail d'une maquette
        
        URL: https://myiipea.ci/api/maquettes/maquettes/3
        
        Args:
            maquette_id: ID de la maquette
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_maquette_{maquette_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"📦 Maquette {maquette_id} depuis cache")
                return cached, None
        
        url = f'{self.maquettes_base_url}/maquettes/{maquette_id}'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    def get_maquette_ues(self, maquette_id, use_cache=True):
        """
        Récupère les UEs d'une maquette
        
        URL: https://myiipea.ci/api/maquettes/maquettes/3/ues
        
        Args:
            maquette_id: ID de la maquette
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_maquette_ues_{maquette_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"📦 UEs maquette {maquette_id} depuis cache")
                return cached, None
        
        url = f'{self.maquettes_base_url}/maquettes/{maquette_id}/ues'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
        
        return data, error
    
    def get_maquette_matieres(self, maquette_id, use_cache=True):
        """
        ⭐ NOUVELLE MÉTHODE - CRITIQUE ⭐
        Récupère TOUTES les matières d'une maquette
        
        URL: https://myiipea.ci/api/maquettes/maquettes/{id}/matieres
        (Basé sur le code qui fonctionne dans l'autre projet)
        
        Args:
            maquette_id: ID de la maquette
            use_cache: Utiliser le cache
            
        Returns:
            tuple: (data, error)
        """
        cache_key = f'myiipea_maquette_matieres_{maquette_id}'
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(f"📦 Matières maquette {maquette_id} depuis cache")
                return cached, None
        
        url = f'{self.maquettes_base_url}/maquettes/{maquette_id}/matieres'
        data, error = self._make_request(url)
        
        if data and not error:
            cache.set(cache_key, data, self.cache_timeout)
            
            if isinstance(data, list):
                logger.info(f"📚 {len(data)} matière(s) récupérée(s) pour maquette {maquette_id}")
        
        return data, error
    
    def clear_cache(self):
        """Vide tous les caches API"""
        cache_keys = [
            'myiipea_all_maquettes',
            'myiipea_annees_academiques',
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        logger.info("🗑️ Cache API vidé")


# ==========================================
# FONCTIONS DE TEST
# ==========================================

def test_api_connection():
    """
    Teste la connexion aux APIs MyIIPEA
    
    Usage:
        from Utilisateur.api_client import test_api_connection
        test_api_connection()
    """
    client = MyIIPEAAPIClient()
    
    print("=" * 60)
    print("🧪 TEST DE CONNEXION AUX APIs MyIIPEA")
    print("=" * 60)
    
    # Test 1: Classes
    print("\n1️⃣ Test récupération des classes...")
    classes, error = client.get_classes_liste(departement_id=1, annee_id=1)
    if error:
        print(f"   ❌ Erreur: {error}")
    else:
        print(f"   ✅ {len(classes) if isinstance(classes, list) else 1} classe(s) trouvée(s)")
        if classes and isinstance(classes, list) and len(classes) > 0:
            print(f"   Exemple: {classes[0]}")
    
    # Test 2: Maquettes
    print("\n2️⃣ Test récupération des maquettes...")
    maquettes, error = client.get_all_maquettes()
    if error:
        print(f"   ❌ Erreur: {error}")
    else:
        print(f"   ✅ {len(maquettes) if isinstance(maquettes, list) else 1} maquette(s) trouvée(s)")
        if maquettes and isinstance(maquettes, list) and len(maquettes) > 0:
            print(f"   Exemple: {maquettes[0]}")
    
    # Test 3: Années académiques
    print("\n3️⃣ Test récupération des années académiques...")
    annees, error = client.get_annees_academiques()
    if error:
        print(f"   ❌ Erreur: {error}")
    else:
        print(f"   ✅ {len(annees) if isinstance(annees, list) else 1} année(s) trouvée(s)")
        if annees and isinstance(annees, list) and len(annees) > 0:
            print(f"   Exemple: {annees[0]}")
    
    print("\n" + "=" * 60)
    print("✅ Tests terminés")
    print("=" * 60)


def test_maquette_matieres(maquette_id=2):
    """
    ⭐ NOUVEAU TEST - Teste la récupération des matières
    
    Usage:
        from Utilisateur.api_client import test_maquette_matieres
        test_maquette_matieres(2)
    """
    client = MyIIPEAAPIClient()
    
    print("=" * 70)
    print(f"🧪 TEST RÉCUPÉRATION MATIÈRES - MAQUETTE {maquette_id}")
    print("=" * 70)
    
    # Test matières
    print("\n📚 Récupération des matières...")
    matieres, error = client.get_maquette_matieres(maquette_id)
    
    if error:
        print(f"❌ ERREUR: {error}")
        return False
    
    if not matieres:
        print(f"⚠️ Aucune matière trouvée")
        return False
    
    if isinstance(matieres, list):
        print(f"✅ SUCCÈS: {len(matieres)} matière(s) trouvée(s)")
        
        if len(matieres) > 0:
            print(f"\n📋 Exemples de matières:")
            for i, matiere in enumerate(matieres[:3], 1):
                print(f"\n  {i}. {matiere.get('nom', 'Sans nom')}")
                print(f"     Code: {matiere.get('code', 'N/A')}")
                print(f"     Coefficient: {matiere.get('coefficient', 'N/A')}")
                print(f"     UE ID: {matiere.get('ue_id') or matiere.get('unite_enseignement_id', 'N/A')}")
                print(f"     Volume CM: {matiere.get('volume_horaire_cm', 0)}h")
        
        print("\n" + "=" * 70)
        print("✅ TEST RÉUSSI")
        print("=" * 70)
        return True
    
    print(f"⚠️ Format inattendu: {type(matieres)}")
    return False