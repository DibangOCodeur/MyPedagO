"""
Service de synchronisation des données API MyIIPEA
VERSION MODIFIÉE - Avec récupération des matières
"""

from django.db import transaction
from django.utils import timezone
from dateutil import parser as date_parser
from .models import Section
from Gestion.models import Classe, Maquette
from .api_client import MyIIPEAAPIClient
import logging

logger = logging.getLogger(__name__)


class SyncService:
    """Service pour synchroniser les données API vers la base de données"""
    
    def __init__(self):
        self.client = MyIIPEAAPIClient()
    
    @transaction.atomic
    def sync_classes(self, departement_id=1, annee_id=1, force=False):
        """
        Synchronise les classes depuis l'API
        
        Args:
            departement_id: ID du département (défaut: 1 pour IIPEA COCODY)
            annee_id: ID de l'année académique
            force: Ignore le cache
            
        Returns:
            tuple: (success, result_dict)
        """
        logger.info("🔄 Début synchronisation des classes")
        
        # Récupérer les données de l'API
        response, error = self.client.get_classes_liste(
            departement_id=departement_id,
            annee_id=annee_id,
            use_cache=not force
        )
        
        if error:
            logger.error(f"❌ Échec sync classes: {error}")
            return False, {'error': error}
        
        # Vérifier le format de la réponse
        if not response or not response.get('success'):
            logger.error("❌ Réponse API invalide")
            return False, {'error': 'Réponse API invalide'}
        
        data = response.get('data', [])
        
        if not data:
            logger.warning("⚠️ Aucune classe reçue de l'API")
            return False, {'error': 'Aucune donnée'}
        
        created_count = 0
        updated_count = 0
        errors = []
        
        # IDs des classes actuelles dans l'API
        api_external_ids = set()
        
        for classe_data in data:
            try:
                external_id = classe_data.get('id')
                if not external_id:
                    logger.warning(f"⚠️ Classe sans ID: {classe_data}")
                    continue
                
                api_external_ids.add(external_id)
                
                # Mapper le département à une section locale (optionnel)
                section = None
                departement_nom = classe_data.get('departement', '')
                if 'COCODY' in departement_nom or 'RIVIERA' in departement_nom:
                    try:
                        section = Section.objects.filter(
                            nom__icontains='RIVIERA'
                        ).first()
                    except Section.DoesNotExist:
                        pass
                elif 'ABOBO' in departement_nom:
                    try:
                        section = Section.objects.filter(
                            nom__icontains='ABOBO'
                        ).first()
                    except Section.DoesNotExist:
                        pass
                elif 'YAKRO' in departement_nom or 'YOPOUGON' in departement_nom:
                    try:
                        section = Section.objects.filter(
                            nom__icontains='YAKRO'
                        ).first()
                    except Section.DoesNotExist:
                        pass
                
                # Préparer les données
                defaults = {
                    'nom': classe_data.get('nom', ''),
                    'description': classe_data.get('description', ''),
                    'annee_academique': classe_data.get('annee_academique', ''),
                    'annee_etat': classe_data.get('annee_etat', ''),
                    'filiere': classe_data.get('filiere', ''),
                    'niveau': classe_data.get('niveau', ''),
                    'departement': classe_data.get('departement', ''),
                    'nombre_groupes': int(classe_data.get('nombre_groupes', 0)),
                    'effectif_total': int(classe_data.get('effectif_total', 0)),
                    'section': section,
                    'raw_data': classe_data,
                    'last_synced': timezone.now(),
                    'is_active': True
                }
                
                # Créer ou mettre à jour
                classe, created = Classe.objects.update_or_create(
                    external_id=external_id,
                    defaults=defaults
                )
                
                if created:
                    created_count += 1
                    logger.info(f"✅ Classe créée: {classe.nom}")
                else:
                    updated_count += 1
                    logger.debug(f"♻️ Classe mise à jour: {classe.nom}")
                
            except Exception as e:
                error_msg = f"Erreur classe {classe_data.get('id')}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        # Désactiver les classes qui ne sont plus dans l'API
        deactivated = Classe.objects.exclude(
            external_id__in=api_external_ids
        ).update(is_active=False)
        
        result = {
            'created': created_count,
            'updated': updated_count,
            'deactivated': deactivated,
            'errors': errors
        }
        
        logger.info(
            f"✅ Sync classes terminée: "
            f"{created_count} créées, {updated_count} mises à jour, "
            f"{deactivated} désactivées"
        )
        
        return True, result
    
    @transaction.atomic
    def sync_maquettes(self, force=False, sync_matieres=True):
        """
        ⭐ MÉTHODE MODIFIÉE ⭐
        Synchronise les maquettes depuis l'API (AVEC ou SANS matières)
        
        Args:
            force: Ignore le cache
            sync_matieres: Synchroniser aussi les matières (par défaut: True)
            
        Returns:
            tuple: (success, result_dict)
        """
        logger.info("🔄 Début synchronisation des maquettes")
        
        # Récupérer toutes les maquettes
        maquettes_data, error = self.client.get_all_maquettes(use_cache=not force)
        
        if error:
            logger.error(f"❌ Échec sync maquettes: {error}")
            return False, {'error': error}
        
        # Vérifier si c'est une liste ou un objet
        if isinstance(maquettes_data, dict):
            # Si c'est un dict, chercher la clé 'data' ou autre
            if 'data' in maquettes_data:
                maquettes_data = maquettes_data['data']
            elif 'maquettes' in maquettes_data:
                maquettes_data = maquettes_data['maquettes']
            else:
                # Sinon c'est peut-être une seule maquette
                maquettes_data = [maquettes_data] if maquettes_data else []
        
        if not maquettes_data:
            logger.warning("⚠️ Aucune maquette reçue de l'API")
            return False, {'error': 'Aucune donnée'}
        
        created_count = 0
        updated_count = 0
        errors = []
        api_external_ids = set()
        total_matieres = 0  # ⭐ NOUVEAU
        
        logger.info(f"📦 {len(maquettes_data)} maquette(s) à traiter")
        
        for maquette_data in maquettes_data:
            try:
                external_id = maquette_data.get('id')
                if not external_id:
                    logger.warning(f"⚠️ Maquette sans ID: {maquette_data}")
                    continue
                
                api_external_ids.add(external_id)
                
                # Parser la date de création si présente
                date_creation_api = None
                if maquette_data.get('date_creation'):
                    try:
                        date_creation_api = date_parser.parse(
                            maquette_data['date_creation']
                        )
                    except Exception as e:
                        logger.debug(f"Erreur parsing date: {e}")
                
                # Essayer de lier à une classe existante
                classe = None
                filiere_nom = maquette_data.get('filiere_nom', '')
                niveau_libelle = maquette_data.get('niveau_libelle', '')
                annee_academique = maquette_data.get('annee_academique', '')
                
                if filiere_nom and niveau_libelle and annee_academique:
                    # Chercher une classe correspondante
                    # Essayer d'abord une correspondance exacte
                    classe = Classe.objects.filter(
                        filiere__iexact=filiere_nom,
                        niveau__iexact=niveau_libelle,
                        annee_academique=annee_academique,
                        is_active=True
                    ).first()
                    
                    # Si pas trouvé, essayer une correspondance partielle
                    if not classe:
                        classe = Classe.objects.filter(
                            filiere__icontains=filiere_nom[:20],  # Les 20 premiers caractères
                            niveau__icontains=niveau_libelle,
                            annee_academique=annee_academique,
                            is_active=True
                        ).first()
                    
                    if classe:
                        logger.debug(f"✅ Maquette {external_id} liée à classe {classe.id}")
                    else:
                        logger.warning(
                            f"⚠️ Pas de classe trouvée pour maquette {external_id}: "
                            f"{filiere_nom} - {niveau_libelle}"
                        )
                
                defaults = {
                    'classe': classe,
                    'filiere_id': maquette_data.get('filiere_id', 0),
                    'niveau_id': maquette_data.get('niveau_id', 0),
                    'anneeacademique_id': maquette_data.get('anneeacademique_id', 0),
                    'filiere_nom': filiere_nom,
                    'filiere_sigle': maquette_data.get('filiere_sigle', ''),
                    'niveau_libelle': niveau_libelle,
                    'annee_academique': annee_academique,
                    'parcour': maquette_data.get('parcour', ''),
                    'date_creation_api': date_creation_api,
                    'raw_data': maquette_data,
                    'last_synced': timezone.now(),
                    'is_active': True
                }
                
                maquette, created = Maquette.objects.update_or_create(
                    external_id=external_id,
                    defaults=defaults
                )
                
                if created:
                    created_count += 1
                    logger.info(f"✅ Maquette créée: {maquette}")
                else:
                    updated_count += 1
                    logger.debug(f"♻️ Maquette mise à jour: {maquette}")
                
                # ⭐ SYNCHRONISER LES UES + MATIÈRES ⭐
                if sync_matieres:
                    nb_matieres = self._sync_maquette_ues_avec_matieres(maquette, force=force)
                    total_matieres += nb_matieres
                else:
                    self._sync_maquette_ues(maquette, force=force)
                
            except Exception as e:
                error_msg = f"Erreur maquette {external_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
                errors.append(error_msg)
        
        # Désactiver les maquettes qui n'existent plus
        deactivated = Maquette.objects.exclude(
            external_id__in=api_external_ids
        ).update(is_active=False)
        
        result = {
            'created': created_count,
            'updated': updated_count,
            'deactivated': deactivated,
            'total_matieres': total_matieres,  # ⭐ NOUVEAU
            'errors': errors
        }
        
        logger.info(
            f"✅ Sync maquettes terminée: "
            f"{created_count} créées, {updated_count} mises à jour, "
            f"{total_matieres} matières synchronisées"  # ⭐ NOUVEAU
        )
        
        return True, result
    
    def _sync_maquette_ues(self, maquette, force=False):
        """
        Synchronise les unités d'enseignement d'une maquette (SANS matières)
        
        Args:
            maquette: Instance de Maquette
            force: Ignore le cache
        """
        try:
            ues_data, error = self.client.get_maquette_ues(
                maquette.external_id,
                use_cache=not force
            )
            
            if error or not ues_data:
                return
            
            # Initialiser les matières à vide
            for ue in ues_data:
                ue['matieres'] = []
            
            # Sauvegarder les UEs dans le champ JSON
            maquette.unites_enseignement = ues_data
            maquette.save(update_fields=['unites_enseignement'])
            
            logger.debug(f"✅ UEs synchronisées pour maquette {maquette.external_id}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sync UEs maquette {maquette.external_id}: {e}")
    
    def _sync_maquette_ues_avec_matieres(self, maquette, force=False):
        """
        ⭐ NOUVELLE MÉTHODE - CRITIQUE ⭐
        Synchronise les unités d'enseignement AVEC les matières
        
        Utilise l'endpoint qui fonctionne:
        GET /api/maquettes/maquettes/{id}/matieres
        
        Args:
            maquette: Instance de Maquette
            force: Ignore le cache
            
        Returns:
            int: Nombre de matières synchronisées
        """
        try:
            logger.info(f"📚 Sync UEs + matières pour maquette {maquette.external_id}")
            
            # 1. Récupérer les UEs
            ues_data, error = self.client.get_maquette_ues(
                maquette.external_id,
                use_cache=not force
            )
            
            if error or not ues_data:
                logger.warning(f"⚠️ Pas d'UEs pour maquette {maquette.external_id}")
                return 0
            
            # 2. Récupérer TOUTES les matières de la maquette
            #    (endpoint qui fonctionne dans l'autre projet)
            matieres_data, error = self.client.get_maquette_matieres(
                maquette.external_id,
                use_cache=not force
            )
            
            if error:
                logger.warning(f"⚠️ Erreur récupération matières: {error}")
                # Sauvegarder les UEs sans matières
                for ue in ues_data:
                    ue['matieres'] = []
                maquette.unites_enseignement = ues_data
                maquette.save(update_fields=['unites_enseignement'])
                return 0
            
            if not matieres_data or not isinstance(matieres_data, list):
                logger.info(f"ℹ️ Aucune matière pour maquette {maquette.external_id}")
                # Sauvegarder les UEs sans matières
                for ue in ues_data:
                    ue['matieres'] = []
                maquette.unites_enseignement = ues_data
                maquette.save(update_fields=['unites_enseignement'])
                return 0
            
            # 3. Associer les matières aux UEs
            # Créer un mapping: UE_ID -> [matières]
            matieres_par_ue = {}
            for matiere in matieres_data:
                # Récupérer l'ID de l'UE (plusieurs noms possibles)
                ue_id = (
                    matiere.get('ue_id') or 
                    matiere.get('unite_enseignement_id') or
                    matiere.get('uniteenseignement_id')
                )
                
                if ue_id:
                    if ue_id not in matieres_par_ue:
                        matieres_par_ue[ue_id] = []
                    matieres_par_ue[ue_id].append(matiere)
            
            # 4. Enrichir les UEs avec leurs matières
            ues_enrichies = []
            total_matieres = 0
            
            for ue in ues_data:
                ue_id = ue.get('id')
                
                # Ajouter les matières correspondantes
                ue['matieres'] = matieres_par_ue.get(ue_id, [])
                total_matieres += len(ue['matieres'])
                
                ues_enrichies.append(ue)
            
            # 5. Sauvegarder
            maquette.unites_enseignement = ues_enrichies
            maquette.save(update_fields=['unites_enseignement'])
            
            logger.info(
                f"✅ Maquette {maquette.external_id}: "
                f"{len(ues_enrichies)} UE(s), {total_matieres} matière(s)"
            )
            
            return total_matieres
            
        except Exception as e:
            logger.error(f"❌ Erreur sync UEs+matières maquette {maquette.external_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    def full_sync(self, force=False, departement_id=1, annee_id=1, sync_matieres=True):
        """
        ⭐ MÉTHODE MODIFIÉE ⭐
        Synchronisation complète: classes + maquettes + matières
        
        Args:
            force: Ignore le cache
            departement_id: ID du département
            annee_id: ID de l'année académique
            sync_matieres: Synchroniser aussi les matières (par défaut: True)
            
        Returns:
            tuple: (success, result_dict)
        """
        logger.info("🔄🔄 SYNCHRONISATION COMPLÈTE")
        
        # 1. Sync classes
        success, classes_result = self.sync_classes(
            departement_id=departement_id,
            annee_id=annee_id,
            force=force
        )
        if not success:
            return False, {'error': f"Échec sync classes: {classes_result}"}
        
        # 2. Sync maquettes (AVEC matières par défaut)
        success, maquettes_result = self.sync_maquettes(
            force=force,
            sync_matieres=sync_matieres  # ⭐ NOUVEAU
        )
        
        result = {
            'classes': classes_result,
            'maquettes': maquettes_result
        }
        
        logger.info("✅✅ SYNCHRONISATION COMPLÈTE TERMINÉE")
        logger.info(f"📊 {maquettes_result.get('total_matieres', 0)} matières synchronisées")  # ⭐ NOUVEAU
        
        return True, result

        

# """
# Service de synchronisation des données API MyIIPEA
# """

# from django.db import transaction
# from django.utils import timezone
# from dateutil import parser as date_parser
# from .models import Section
# from Gestion.models import Classe, Maquette
# from .api_client import MyIIPEAAPIClient
# import logging

# logger = logging.getLogger(__name__)


# class SyncService:
#     """Service pour synchroniser les données API vers la base de données"""
    
#     def __init__(self):
#         self.client = MyIIPEAAPIClient()
    
#     @transaction.atomic
#     def sync_classes(self, departement_id=1, annee_id=1, force=False):
#         """
#         Synchronise les classes depuis l'API
        
#         Args:
#             departement_id: ID du département (défaut: 1 pour IIPEA COCODY)
#             annee_id: ID de l'année académique
#             force: Ignore le cache
            
#         Returns:
#             tuple: (success, result_dict)
#         """
#         logger.info("🔄 Début synchronisation des classes")
        
#         # Récupérer les données de l'API
#         response, error = self.client.get_classes_liste(
#             departement_id=departement_id,
#             annee_id=annee_id,
#             use_cache=not force
#         )
        
#         if error:
#             logger.error(f"❌ Échec sync classes: {error}")
#             return False, {'error': error}
        
#         # Vérifier le format de la réponse
#         if not response or not response.get('success'):
#             logger.error("❌ Réponse API invalide")
#             return False, {'error': 'Réponse API invalide'}
        
#         data = response.get('data', [])
        
#         if not data:
#             logger.warning("⚠️ Aucune classe reçue de l'API")
#             return False, {'error': 'Aucune donnée'}
        
#         created_count = 0
#         updated_count = 0
#         errors = []
        
#         # IDs des classes actuelles dans l'API
#         api_external_ids = set()
        
#         for classe_data in data:
#             try:
#                 external_id = classe_data.get('id')
#                 if not external_id:
#                     logger.warning(f"⚠️ Classe sans ID: {classe_data}")
#                     continue
                
#                 api_external_ids.add(external_id)
                
#                 # Mapper le département à une section locale (optionnel)
#                 section = None
#                 departement_nom = classe_data.get('departement', '')
#                 if 'COCODY' in departement_nom or 'RIVIERA' in departement_nom:
#                     try:
#                         section = Section.objects.filter(
#                             nom__icontains='RIVIERA'
#                         ).first()
#                     except Section.DoesNotExist:
#                         pass
#                 elif 'ABOBO' in departement_nom:
#                     try:
#                         section = Section.objects.filter(
#                             nom__icontains='ABOBO'
#                         ).first()
#                     except Section.DoesNotExist:
#                         pass
#                 elif 'YAKRO' in departement_nom or 'YOPOUGON' in departement_nom:
#                     try:
#                         section = Section.objects.filter(
#                             nom__icontains='YAKRO'
#                         ).first()
#                     except Section.DoesNotExist:
#                         pass
                
#                 # Préparer les données
#                 defaults = {
#                     'nom': classe_data.get('nom', ''),
#                     'description': classe_data.get('description', ''),
#                     'annee_academique': classe_data.get('annee_academique', ''),
#                     'annee_etat': classe_data.get('annee_etat', ''),
#                     'filiere': classe_data.get('filiere', ''),
#                     'niveau': classe_data.get('niveau', ''),
#                     'departement': classe_data.get('departement', ''),
#                     'nombre_groupes': int(classe_data.get('nombre_groupes', 0)),
#                     'effectif_total': int(classe_data.get('effectif_total', 0)),
#                     'section': section,
#                     'raw_data': classe_data,
#                     'last_synced': timezone.now(),
#                     'is_active': True
#                 }
                
#                 # Créer ou mettre à jour
#                 classe, created = Classe.objects.update_or_create(
#                     external_id=external_id,
#                     defaults=defaults
#                 )
                
#                 if created:
#                     created_count += 1
#                     logger.info(f"✅ Classe créée: {classe.nom}")
#                 else:
#                     updated_count += 1
#                     logger.debug(f"♻️ Classe mise à jour: {classe.nom}")
                
#             except Exception as e:
#                 error_msg = f"Erreur classe {classe_data.get('id')}: {str(e)}"
#                 logger.error(f"❌ {error_msg}")
#                 errors.append(error_msg)
        
#         # Désactiver les classes qui ne sont plus dans l'API
#         deactivated = Classe.objects.exclude(
#             external_id__in=api_external_ids
#         ).update(is_active=False)
        
#         result = {
#             'created': created_count,
#             'updated': updated_count,
#             'deactivated': deactivated,
#             'errors': errors
#         }
        
#         logger.info(
#             f"✅ Sync classes terminée: "
#             f"{created_count} créées, {updated_count} mises à jour, "
#             f"{deactivated} désactivées"
#         )
        
#         return True, result
    
#     @transaction.atomic
#     def sync_maquettes(self, force=False):
#         """
#         Synchronise les maquettes depuis l'API
        
#         Args:
#             force: Ignore le cache
            
#         Returns:
#             tuple: (success, result_dict)
#         """
#         logger.info("🔄 Début synchronisation des maquettes")
        
#         # Récupérer toutes les maquettes
#         maquettes_data, error = self.client.get_all_maquettes(use_cache=not force)
        
#         if error:
#             logger.error(f"❌ Échec sync maquettes: {error}")
#             return False, {'error': error}
        
#         # Vérifier si c'est une liste ou un objet
#         if isinstance(maquettes_data, dict):
#             # Si c'est un dict, chercher la clé 'data' ou autre
#             if 'data' in maquettes_data:
#                 maquettes_data = maquettes_data['data']
#             elif 'maquettes' in maquettes_data:
#                 maquettes_data = maquettes_data['maquettes']
#             else:
#                 # Sinon c'est peut-être une seule maquette
#                 maquettes_data = [maquettes_data] if maquettes_data else []
        
#         if not maquettes_data:
#             logger.warning("⚠️ Aucune maquette reçue de l'API")
#             return False, {'error': 'Aucune donnée'}
        
#         created_count = 0
#         updated_count = 0
#         errors = []
#         api_external_ids = set()
        
#         logger.info(f"📦 {len(maquettes_data)} maquette(s) à traiter")
        
#         for maquette_data in maquettes_data:
#             try:
#                 external_id = maquette_data.get('id')
#                 if not external_id:
#                     logger.warning(f"⚠️ Maquette sans ID: {maquette_data}")
#                     continue
                
#                 api_external_ids.add(external_id)
                
#                 # Parser la date de création si présente
#                 date_creation_api = None
#                 if maquette_data.get('date_creation'):
#                     try:
#                         date_creation_api = date_parser.parse(
#                             maquette_data['date_creation']
#                         )
#                     except Exception as e:
#                         logger.debug(f"Erreur parsing date: {e}")
                
#                 # Essayer de lier à une classe existante
#                 classe = None
#                 filiere_nom = maquette_data.get('filiere_nom', '')
#                 niveau_libelle = maquette_data.get('niveau_libelle', '')
#                 annee_academique = maquette_data.get('annee_academique', '')
                
#                 if filiere_nom and niveau_libelle and annee_academique:
#                     # Chercher une classe correspondante
#                     # Essayer d'abord une correspondance exacte
#                     classe = Classe.objects.filter(
#                         filiere__iexact=filiere_nom,
#                         niveau__iexact=niveau_libelle,
#                         annee_academique=annee_academique,
#                         is_active=True
#                     ).first()
                    
#                     # Si pas trouvé, essayer une correspondance partielle
#                     if not classe:
#                         classe = Classe.objects.filter(
#                             filiere__icontains=filiere_nom[:20],  # Les 20 premiers caractères
#                             niveau__icontains=niveau_libelle,
#                             annee_academique=annee_academique,
#                             is_active=True
#                         ).first()
                    
#                     if classe:
#                         logger.debug(f"✅ Maquette {external_id} liée à classe {classe.id}")
#                     else:
#                         logger.warning(
#                             f"⚠️ Pas de classe trouvée pour maquette {external_id}: "
#                             f"{filiere_nom} - {niveau_libelle}"
#                         )
                
#                 defaults = {
#                     'classe': classe,
#                     'filiere_id': maquette_data.get('filiere_id', 0),
#                     'niveau_id': maquette_data.get('niveau_id', 0),
#                     'anneeacademique_id': maquette_data.get('anneeacademique_id', 0),
#                     'filiere_nom': filiere_nom,
#                     'filiere_sigle': maquette_data.get('filiere_sigle', ''),
#                     'niveau_libelle': niveau_libelle,
#                     'annee_academique': annee_academique,
#                     'parcour': maquette_data.get('parcour', ''),
#                     'date_creation_api': date_creation_api,
#                     'raw_data': maquette_data,
#                     'last_synced': timezone.now(),
#                     'is_active': True
#                 }
                
#                 maquette, created = Maquette.objects.update_or_create(
#                     external_id=external_id,
#                     defaults=defaults
#                 )
                
#                 if created:
#                     created_count += 1
#                     logger.info(f"✅ Maquette créée: {maquette}")
#                 else:
#                     updated_count += 1
#                     logger.debug(f"♻️ Maquette mise à jour: {maquette}")
                
#                 # Synchroniser les UEs de cette maquette
#                 self._sync_maquette_ues(maquette, force=force)
                
#             except Exception as e:
#                 error_msg = f"Erreur maquette {external_id}: {str(e)}"
#                 logger.error(f"❌ {error_msg}")
#                 import traceback
#                 logger.error(traceback.format_exc())
#                 errors.append(error_msg)
        
#         # Désactiver les maquettes qui n'existent plus
#         deactivated = Maquette.objects.exclude(
#             external_id__in=api_external_ids
#         ).update(is_active=False)
        
#         result = {
#             'created': created_count,
#             'updated': updated_count,
#             'deactivated': deactivated,
#             'errors': errors
#         }
        
#         logger.info(
#             f"✅ Sync maquettes terminée: "
#             f"{created_count} créées, {updated_count} mises à jour, "
#             f"{len(errors)} erreur(s)"
#         )
        
#         return True, result
    
#     def _sync_maquette_ues(self, maquette, force=False):
#         """
#         Synchronise les unités d'enseignement d'une maquette
        
#         Args:
#             maquette: Instance de Maquette
#             force: Ignore le cache
#         """
#         try:
#             ues_data, error = self.client.get_maquette_ues(
#                 maquette.external_id,
#                 use_cache=not force
#             )
            
#             if error or not ues_data:
#                 return
            
#             # Sauvegarder les UEs dans le champ JSON
#             maquette.unites_enseignement = ues_data
#             maquette.save(update_fields=['unites_enseignement'])
            
#             logger.debug(f"✅ UEs synchronisées pour maquette {maquette.external_id}")
            
#         except Exception as e:
#             logger.error(f"❌ Erreur sync UEs maquette {maquette.external_id}: {e}")
    
#     def full_sync(self, force=False, departement_id=1, annee_id=1):
#         """
#         Synchronisation complète: classes + maquettes
        
#         Args:
#             force: Ignore le cache
#             departement_id: ID du département
#             annee_id: ID de l'année académique
            
#         Returns:
#             tuple: (success, result_dict)
#         """
#         logger.info("🔄🔄 SYNCHRONISATION COMPLÈTE")
        
#         # 1. Sync classes
#         success, classes_result = self.sync_classes(
#             departement_id=departement_id,
#             annee_id=annee_id,
#             force=force
#         )
#         if not success:
#             return False, {'error': f"Échec sync classes: {classes_result}"}
        
#         # 2. Sync maquettes
#         success, maquettes_result = self.sync_maquettes(force=force)
        
#         result = {
#             'classes': classes_result,
#             'maquettes': maquettes_result
#         }
        
#         logger.info("✅✅ SYNCHRONISATION COMPLÈTE TERMINÉE")
#         return True, result