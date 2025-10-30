"""
MongoDB Manager pour Token Scanner Pro
Gestion de la base de données MongoDB avec cache automatique des tokens
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from werkzeug.security import generate_password_hash, check_password_hash


class MongoDBManager:
    """Gestionnaire MongoDB pour Token Scanner Pro"""
    
    def __init__(self, connection_string: str = None):
        """
        Initialise la connexion MongoDB
        
        Args:
            connection_string: URI de connexion MongoDB
                              (par défaut: mongodb://localhost:27017/)
        """
        if connection_string is None:
            connection_string = os.getenv(
                'MONGODB_URI', 
                'mongodb://localhost:27017/'
            )
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Test de connexion
            self.client.admin.command('ping')
            print("✅ Connexion MongoDB établie")
        except ConnectionFailure as e:
            print(f"❌ Erreur connexion MongoDB: {e}")
            raise
        
        # Base de données principale
        self.db = self.client['token_scanner_pro']
        
        # Collections
        self.users = self.db['users']
        self.favorites = self.db['favorites']
        self.tokens_cache = self.db['tokens_cache']  # 🆕 Cache 24h
        self.scanned_tokens = self.db['scanned_tokens']  # Cache global tokens scannés
        self.scan_history = self.db['scan_history']
        self.positions = self.db['positions']
        self.alerts = self.db['alerts']

        # Configuration rotation tokens (FIFO)
        self.MAX_SCANNED_TOKENS = 200
        
        # Créer les indexes
        self._create_indexes()
        
        print("✅ MongoDB Manager initialisé")
    
    def _create_indexes(self):
        """Crée les indexes pour optimiser les requêtes"""
        try:
            # Users
            self.users.create_index([('email', ASCENDING)], unique=True)
            self.users.create_index([('username', ASCENDING)], unique=True)
            
            # Favorites
            self.favorites.create_index([
                ('user_id', ASCENDING),
                ('token_address', ASCENDING),
                ('token_chain', ASCENDING)
            ], unique=True)
            
            # 🆕 Tokens Cache - INDEX CRUCIAL POUR TTL
            self.tokens_cache.create_index([
                ('token_address', ASCENDING),
                ('token_chain', ASCENDING)
            ], unique=True)
            
            # TTL Index - supprime automatiquement après 24h
            self.tokens_cache.create_index(
                [('created_at', ASCENDING)],
                expireAfterSeconds=86400  # 24 heures
            )
            
            # Index pour recherche rapide
            self.tokens_cache.create_index([('created_at', DESCENDING)])
            self.tokens_cache.create_index([('risk_score', ASCENDING)])
            self.tokens_cache.create_index([('is_safe', ASCENDING)])
            
            # Scanned Tokens (cache global avec rotation FIFO)
            self.scanned_tokens.create_index([
                ('token_address', ASCENDING),
                ('token_chain', ASCENDING)
            ], unique=True)
            self.scanned_tokens.create_index([('scanned_at', DESCENDING)])
            self.scanned_tokens.create_index([('is_safe', ASCENDING)])
            self.scanned_tokens.create_index([('risk_score', ASCENDING)])

            # Scan History
            self.scan_history.create_index([
                ('user_id', ASCENDING),
                ('scan_date', DESCENDING)
            ])

            # Positions
            self.positions.create_index([
                ('user_id', ASCENDING),
                ('status', ASCENDING)
            ])
            
            print("✅ Index MongoDB créés")
        except Exception as e:
            print(f"⚠️ Erreur création indexes: {e}")
    
    # ==================== USERS ====================
    
    def create_user(self, email: str, username: str, password: str, 
                   role: str = 'user') -> Optional[str]:
        """Crée un nouvel utilisateur"""
        try:
            user_doc = {
                'email': email.lower(),
                'username': username,
                'password_hash': generate_password_hash(password),
                'role': role,
                'is_premium': False,
                'is_active': True,
                'scan_count': 0,
                'created_at': datetime.utcnow(),
                'last_login': None,
                'telegram_id': None,
                'email_alerts': False,
                'telegram_alerts': False
            }
            
            result = self.users.insert_one(user_doc)
            return str(result.inserted_id)
        except DuplicateKeyError:
            return None
        except Exception as e:
            print(f"Erreur create_user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Récupère un utilisateur par email"""
        try:
            user = self.users.find_one({'email': email.lower()})
            if user:
                user['id'] = str(user['_id'])
            return user
        except Exception as e:
            print(f"Erreur get_user_by_email: {e}")
            return None
    
    def verify_password(self, email: str, password: str) -> Optional[Dict]:
        """Vérifie les identifiants"""
        user = self.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            # Update last login
            self.users.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
            return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Récupère un utilisateur par son ID"""
        try:
            from bson.objectid import ObjectId
            user = self.users.find_one({'_id': ObjectId(user_id)})
            if user:
                user['id'] = str(user['_id'])
                user['is_admin'] = user.get('role') == 'admin'
            return user
        except Exception as e:
            print(f"Erreur get_user_by_id: {e}")
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authentifie un utilisateur (alias pour verify_password)"""
        return self.verify_password(email, password)

    def is_admin(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur est admin"""
        try:
            from bson.objectid import ObjectId
            user = self.users.find_one({'_id': ObjectId(user_id)})
            return user and user.get('role') == 'admin'
        except:
            return False
    
    def update_scan_count(self, user_id: str):
        """Incrémente le compteur de scans"""
        try:
            from bson.objectid import ObjectId
            self.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$inc': {'scan_count': 1},
                    '$set': {'last_scan': datetime.utcnow()}
                }
            )
        except Exception as e:
            print(f"Erreur update_scan_count: {e}")
    
    # ==================== FAVORITES ====================
    
    def add_favorite(self, user_id: str, token_address: str, 
                    token_chain: str, token_data: Dict, 
                    notes: str = "") -> bool:
        """Ajoute un token aux favoris"""
        try:
            from bson.objectid import ObjectId
            
            favorite_doc = {
                'user_id': ObjectId(user_id),
                'token_address': token_address,
                'token_chain': token_chain,
                'token_data': token_data,
                'notes': notes,
                'added_at': datetime.utcnow()
            }
            
            self.favorites.insert_one(favorite_doc)
            return True
        except DuplicateKeyError:
            return False
        except Exception as e:
            print(f"Erreur add_favorite: {e}")
            return False
    
    def remove_favorite(self, user_id: str, token_address: str, 
                       token_chain: str) -> bool:
        """Retire un token des favoris"""
        try:
            from bson.objectid import ObjectId
            result = self.favorites.delete_one({
                'user_id': ObjectId(user_id),
                'token_address': token_address,
                'token_chain': token_chain
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Erreur remove_favorite: {e}")
            return False
    
    def get_user_favorites(self, user_id: str) -> List[Dict]:
        """Récupère les favoris d'un utilisateur"""
        try:
            from bson.objectid import ObjectId
            favorites = list(self.favorites.find(
                {'user_id': ObjectId(user_id)}
            ).sort('added_at', DESCENDING))
            
            for fav in favorites:
                fav['id'] = str(fav['_id'])
            
            return favorites
        except Exception as e:
            print(f"Erreur get_user_favorites: {e}")
            return []
    
    def is_favorite(self, user_id: str, token_address: str, 
                   token_chain: str) -> bool:
        """Vérifie si un token est favori"""
        try:
            from bson.objectid import ObjectId
            count = self.favorites.count_documents({
                'user_id': ObjectId(user_id),
                'token_address': token_address,
                'token_chain': token_chain
            })
            return count > 0
        except:
            return False
    
    # ==================== TOKENS CACHE (🆕) ====================
    
    def add_token_to_cache(self, token_data: Dict) -> bool:
        """
        Ajoute un token au cache (TTL 24h automatique)
        
        Args:
            token_data: Données complètes du token (analyse + trading)
        """
        try:
            token_doc = {
                'token_address': token_data['address'],
                'token_chain': token_data['chain'],
                'created_at': datetime.utcnow(),
                'data': token_data
            }
            
            # Upsert pour éviter les doublons
            self.tokens_cache.update_one(
                {
                    'token_address': token_data['address'],
                    'token_chain': token_data['chain']
                },
                {'$set': token_doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Erreur add_token_to_cache: {e}")
            return False
    
    def get_cached_tokens(self, limit: int = 100, 
                         filters: Dict = None) -> List[Dict]:
        """
        Récupère les tokens du cache des dernières 24h
        
        Args:
            limit: Nombre maximum de tokens
            filters: Filtres optionnels (is_safe, min_liquidity, etc.)
        """
        try:
            query = {}
            
            # Appliquer les filtres
            if filters:
                if 'is_safe' in filters:
                    query['data.is_safe'] = filters['is_safe']
                if 'min_liquidity' in filters:
                    query['data.market_data.liquidity_usd'] = {
                        '$gte': filters['min_liquidity']
                    }
                if 'max_risk_score' in filters:
                    query['data.risk_score'] = {
                        '$lte': filters['max_risk_score']
                    }
                if 'chain' in filters:
                    query['token_chain'] = filters['chain']
            
            tokens = list(self.tokens_cache.find(query)
                         .sort('created_at', DESCENDING)
                         .limit(limit))
            
            # Extraire les données
            return [token['data'] for token in tokens]
        except Exception as e:
            print(f"Erreur get_cached_tokens: {e}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        try:
            total = self.tokens_cache.count_documents({})
            
            # Compter par chaîne
            pipeline = [
                {'$group': {
                    '_id': '$token_chain',
                    'count': {'$sum': 1}
                }}
            ]
            by_chain = list(self.tokens_cache.aggregate(pipeline))
            
            # Tokens sûrs vs dangereux
            safe_count = self.tokens_cache.count_documents({'data.is_safe': True})
            dangerous_count = total - safe_count
            
            # Plus ancien token dans le cache
            oldest = self.tokens_cache.find_one(
                sort=[('created_at', ASCENDING)]
            )
            oldest_age = None
            if oldest:
                age = datetime.utcnow() - oldest['created_at']
                oldest_age = age.total_seconds() / 3600  # heures
            
            return {
                'total_tokens': total,
                'safe_tokens': safe_count,
                'dangerous_tokens': dangerous_count,
                'by_chain': {item['_id']: item['count'] for item in by_chain},
                'oldest_token_age_hours': oldest_age
            }
        except Exception as e:
            print(f"Erreur get_cache_stats: {e}")
            return {}
    
    def clear_cache(self) -> int:
        """Vide complètement le cache"""
        try:
            result = self.tokens_cache.delete_many({})
            return result.deleted_count
        except Exception as e:
            print(f"Erreur clear_cache: {e}")
            return 0
    
    # ==================== SCAN HISTORY ====================
    
    def save_scan_history(self, user_id: str, scan_results: Dict) -> bool:
        """Sauvegarde l'historique d'un scan"""
        try:
            from bson.objectid import ObjectId
            
            history_doc = {
                'user_id': ObjectId(user_id) if user_id else None,
                'scan_date': datetime.utcnow(),
                'tokens_scanned': scan_results.get('total_analyzed', 0),
                'safe_count': scan_results.get('safe_count', 0),
                'dangerous_count': scan_results.get('dangerous_count', 0),
                'results': scan_results
            }
            
            self.scan_history.insert_one(history_doc)
            return True
        except Exception as e:
            print(f"Erreur save_scan_history: {e}")
            return False
    
    def get_scan_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Récupère l'historique des scans"""
        try:
            from bson.objectid import ObjectId
            
            history = list(self.scan_history.find(
                {'user_id': ObjectId(user_id)}
            ).sort('scan_date', DESCENDING).limit(limit))
            
            for scan in history:
                scan['id'] = str(scan['_id'])
            
            return history
        except Exception as e:
            print(f"Erreur get_scan_history: {e}")
            return []
    
    # ==================== UTILITY ====================
    
    def get_all_users(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Récupère tous les utilisateurs (admin)"""
        try:
            query = self.users.find().skip(offset)
            if limit:
                query = query.limit(limit)

            users = list(query.sort('created_at', DESCENDING))
            for user in users:
                user['id'] = str(user['_id'])
                user['is_admin'] = user.get('role') == 'admin'

            return users
        except Exception as e:
            print(f"Erreur get_all_users: {e}")
            return []

    def get_users_count(self) -> int:
        """Retourne le nombre total d'utilisateurs"""
        try:
            return self.users.count_documents({})
        except Exception as e:
            print(f"Erreur get_users_count: {e}")
            return 0
    
    def get_global_stats(self) -> Dict[str, int]:
        """Statistiques globales de la plateforme"""
        try:
            total_users = self.users.count_documents({})
            active_users = self.users.count_documents({'is_active': True})
            premium_users = self.users.count_documents({'is_premium': True})
            admin_users = self.users.count_documents({'role': 'admin'})
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'premium_users': premium_users,
                'admin_users': admin_users
            }
        except Exception as e:
            print(f"Erreur get_global_stats: {e}")
            return {}
    
    # ==================== SCANNED TOKENS (Cache global avec rotation FIFO) ====================

    def add_scanned_token(self, token_address: str, token_chain: str,
                         token_data: Dict, risk_score: int = 0,
                         is_safe: bool = False, is_pump_dump_suspect: bool = False) -> bool:
        """Ajoute un token scanné au cache global"""
        try:
            token_doc = {
                'token_address': token_address,
                'token_chain': token_chain,
                'token_data': token_data,
                'risk_score': risk_score,
                'is_safe': is_safe,
                'is_pump_dump_suspect': is_pump_dump_suspect,
                'scanned_at': datetime.utcnow()
            }

            # Upsert pour éviter doublons
            self.scanned_tokens.update_one(
                {
                    'token_address': token_address,
                    'token_chain': token_chain
                },
                {'$set': token_doc},
                upsert=True
            )

            # Rotation FIFO : garder max MAX_SCANNED_TOKENS
            total = self.scanned_tokens.count_documents({})
            if total > self.MAX_SCANNED_TOKENS:
                to_delete = total - self.MAX_SCANNED_TOKENS
                # Supprimer les plus vieux
                oldest_tokens = list(
                    self.scanned_tokens.find()
                    .sort('scanned_at', ASCENDING)
                    .limit(to_delete)
                )
                for old_token in oldest_tokens:
                    self.scanned_tokens.delete_one({'_id': old_token['_id']})

            return True
        except Exception as e:
            print(f"Erreur add_scanned_token: {e}")
            return False

    def add_scanned_tokens_batch(self, tokens_list: List[Dict]) -> int:
        """Ajoute plusieurs tokens en batch"""
        count = 0
        for token in tokens_list:
            result = self.add_scanned_token(
                token_address=token.get('address'),
                token_chain=token.get('chain', 'solana'),
                token_data=token,
                risk_score=token.get('risk_score', 0),
                is_safe=token.get('is_safe', False),
                is_pump_dump_suspect=token.get('is_pump_dump_suspect', False)
            )
            if result:
                count += 1
        return count

    def get_scanned_tokens(self, limit: int = 50, offset: int = 0,
                          chain: str = None, safe_only: bool = False) -> List[Dict]:
        """Récupère les tokens scannés (les plus récents en premier)"""
        try:
            query = {}

            if chain:
                query['token_chain'] = chain
            if safe_only:
                query['is_safe'] = True

            tokens = list(
                self.scanned_tokens.find(query)
                .sort('scanned_at', DESCENDING)
                .skip(offset)
                .limit(limit)
            )

            result = []
            for token in tokens:
                result.append({
                    'id': str(token['_id']),
                    'token_address': token['token_address'],
                    'token_chain': token['token_chain'],
                    'token_data': token['token_data'],
                    'risk_score': token.get('risk_score', 0),
                    'is_safe': token.get('is_safe', False),
                    'is_pump_dump_suspect': token.get('is_pump_dump_suspect', False),
                    'scanned_at': token['scanned_at'].isoformat()
                })

            return result
        except Exception as e:
            print(f"Erreur get_scanned_tokens: {e}")
            return []

    def get_scanned_token(self, address: str, chain: str = 'solana') -> Optional[Dict]:
        """Récupère un token scanné spécifique"""
        try:
            token = self.scanned_tokens.find_one({
                'token_address': address,
                'token_chain': chain
            })

            if token:
                return {
                    'id': str(token['_id']),
                    'token_address': token['token_address'],
                    'token_chain': token['token_chain'],
                    'token_data': token['token_data'],
                    'risk_score': token.get('risk_score', 0),
                    'is_safe': token.get('is_safe', False),
                    'is_pump_dump_suspect': token.get('is_pump_dump_suspect', False),
                    'scanned_at': token['scanned_at'].isoformat()
                }
            return None
        except Exception as e:
            print(f"Erreur get_scanned_token: {e}")
            return None

    def get_scanned_tokens_count(self, chain: str = None) -> int:
        """Compte le nombre de tokens scannés"""
        try:
            query = {}
            if chain:
                query['token_chain'] = chain
            return self.scanned_tokens.count_documents(query)
        except Exception as e:
            print(f"Erreur get_scanned_tokens_count: {e}")
            return 0

    def cleanup_tokens_older_than(self, hours: int = 24) -> int:
        """Supprime les tokens scannés plus vieux que X heures"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(hours=hours)
            result = self.scanned_tokens.delete_many({
                'scanned_at': {'$lt': cutoff_date}
            })
            return result.deleted_count
        except Exception as e:
            print(f"Erreur cleanup_tokens_older_than: {e}")
            return 0

    def close(self):
        """Ferme la connexion MongoDB"""
        try:
            self.client.close()
            print("✅ Connexion MongoDB fermée")
        except Exception as e:
            print(f"Erreur fermeture MongoDB: {e}")