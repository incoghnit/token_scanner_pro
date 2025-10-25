import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

class Database:
    """Gestion de la base de données SQLite pour Token Scanner Pro"""
    
    def __init__(self, db_name='token_scanner.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialise la base de données avec toutes les tables nécessaires"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                is_premium INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                telegram_id TEXT,
                email_alerts INTEGER DEFAULT 0,
                telegram_alerts INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                scan_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_address TEXT NOT NULL,
                token_chain TEXT NOT NULL,
                address TEXT,
                name TEXT,
                symbol TEXT,
                notes TEXT,
                token_data TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, token_address, token_chain)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                address TEXT,
                scan_data TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Table pour stocker individuellement les tokens scannés
        # Avec rotation automatique (max 200 tokens, FIFO)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanned_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                token_chain TEXT NOT NULL DEFAULT 'solana',
                token_data TEXT NOT NULL,
                risk_score INTEGER,
                is_safe INTEGER DEFAULT 0,
                is_pump_dump_suspect INTEGER DEFAULT 0,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(token_address, token_chain)
            )
        ''')

        # Index pour optimiser les requêtes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scanned_tokens_date
            ON scanned_tokens(scanned_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scanned_tokens_chain
            ON scanned_tokens(token_chain)
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Base de données initialisée avec succès")
    
    def create_user(self, email_or_username, username_or_password, password=None):
        """Crée un nouvel utilisateur"""
        try:
            if password is None:
                username = email_or_username
                password = username_or_password
                email = None
            else:
                email = email_or_username
                username = username_or_password
            
            hashed_password = generate_password_hash(password)
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, password, email)
                VALUES (?, ?, ?)
            ''', (username, hashed_password, email))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error:
            return None
    
    def get_user(self, username):
        """Récupère un utilisateur par son nom"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password, email, is_premium, role, is_active, scan_count
                FROM users WHERE username = ?
            ''', (username,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'password': row[2],
                    'email': row[3],
                    'is_premium': row[4],
                    'role': row[5],
                    'is_active': row[6],
                    'scan_count': row[7] if len(row) > 7 else 0
                }
            return None
        except sqlite3.Error:
            return None
    
    def get_user_by_id(self, user_id):
        """Récupère un utilisateur par son ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, is_premium, role, created_at,
                       telegram_id, email_alerts, telegram_alerts, is_active, scan_count
                FROM users WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_premium': row[3],
                    'role': row[4],
                    'created_at': row[5],
                    'telegram_id': row[6],
                    'email_alerts': row[7],
                    'telegram_alerts': row[8],
                    'is_active': row[9],
                    'scan_count': row[10] if len(row) > 10 else 0
                }
            return None
        except sqlite3.Error:
            return None
    
    def verify_password(self, username, password):
        """Vérifie le mot de passe d'un utilisateur"""
        user = self.get_user(username)
        if user and check_password_hash(user['password'], password):
            return True
        return False
    
    def verify_password_with_email(self, email, password):
        """Vérifie le mot de passe avec email et retourne l'utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password, is_premium, role, is_active, scan_count
                FROM users WHERE email = ?
            ''', (email,))

            row = cursor.fetchone()
            conn.close()

            if row and check_password_hash(row[3], password):
                if not row[6]:
                    return None

                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_premium': row[4],
                    'role': row[5],
                    'is_admin': row[5] == 'admin',
                    'scan_count': row[7] if len(row) > 7 else 0
                }
            return None
        except sqlite3.Error:
            return None

    def authenticate_user(self, email, password):
        """Authentifie un utilisateur par email et mot de passe (alias pour verify_password_with_email)"""
        return self.verify_password_with_email(email, password)
    
    def is_admin(self, user_id):
        """Vérifie si un utilisateur est admin"""
        user = self.get_user_by_id(user_id)
        return user and user.get('role') == 'admin'
    
    def update_last_login(self, user_id):
        """Met à jour la dernière connexion"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().isoformat(), user_id)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def update_user_role(self, user_id, role):
        """Met à jour le rôle d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET role = ? WHERE id = ?',
                (role, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def update_user_premium(self, user_id, is_premium):
        """Active/désactive le statut premium"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET is_premium = ? WHERE id = ?',
                (1 if is_premium else 0, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def update_user_status(self, user_id, is_active):
        """Active/désactive un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET is_active = ? WHERE id = ?',
                (1 if is_active else 0, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def toggle_user_status(self, user_id):
        """Inverse le statut actif"""
        user = self.get_user_by_id(user_id)
        if user:
            new_status = not user.get('is_active', True)
            return self.update_user_status(user_id, new_status)
        return False
    
    def toggle_premium(self, user_id):
        """Inverse le statut premium"""
        user = self.get_user_by_id(user_id)
        if user:
            new_status = not user.get('is_premium', False)
            return self.update_user_premium(user_id, new_status)
        return False
    
    def delete_user(self, user_id):
        """Supprime un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM favorites WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM scan_history WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def get_all_users(self, limit=None, offset=0):
        """Récupère tous les utilisateurs"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if limit:
                cursor.execute('''
                    SELECT id, username, email, is_premium, role, created_at, is_active, scan_count
                    FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?
                ''', (limit, offset))
            else:
                cursor.execute('''
                    SELECT id, username, email, is_premium, role, created_at, is_active, scan_count
                    FROM users ORDER BY created_at DESC
                ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_premium': row[3],
                    'role': row[4],
                    'created_at': row[5],
                    'is_active': row[6],
                    'scan_count': row[7] if len(row) > 7 else 0
                })
            
            conn.close()
            return users
        except sqlite3.Error:
            return []
    
    def get_users_count(self):
        """Compte le nombre total d'utilisateurs"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except sqlite3.Error:
            return 0
    
    def get_user_stats(self, user_id):
        """Récupère les statistiques d'un utilisateur"""
        scan_count = self.get_user_scan_count(user_id)
        favorites = self.get_user_favorites(user_id)
        
        return {
            'scan_count': scan_count,
            'favorites_count': len(favorites),
            'days_active': self.get_user_days_active(user_id)
        }
    
    def get_global_stats(self):
        """Récupère les statistiques globales"""
        users = self.get_all_users()
        
        return {
            'total_users': len(users),
            'active_users': len([u for u in users if u.get('is_active')]),
            'premium_users': len([u for u in users if u.get('is_premium')]),
            'admin_users': len([u for u in users if u.get('role') == 'admin'])
        }
    
    def update_scan_count(self, user_id):
        """Incrémente le compteur de scans"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET scan_count = scan_count + 1 WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def add_favorite(self, user_id, token_address, token_chain=None, token_data=None, notes=None, name=None, symbol=None):
        """Ajoute un token aux favoris"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if token_chain is None:
                address = token_address
                token_address = address
                token_chain = 'solana'
                token_data_json = None
            else:
                address = token_address
                token_data_json = json.dumps(token_data) if token_data else None
            
            cursor.execute('''
                INSERT INTO favorites (user_id, token_address, token_chain, address, name, symbol, token_data, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, token_address, token_chain, address, name, symbol, token_data_json, notes))
            conn.commit()
            favorite_id = cursor.lastrowid
            conn.close()
            return favorite_id
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error:
            return None
    
    def get_user_favorites(self, user_id):
        """Récupère les favoris d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, token_address, token_chain, address, name, symbol, token_data, notes, added_at
                FROM favorites WHERE user_id = ? ORDER BY added_at DESC
            ''', (user_id,))
            
            favorites = []
            for row in cursor.fetchall():
                token_data = json.loads(row[6]) if row[6] else {}
                favorites.append({
                    'id': row[0],
                    'token_address': row[1],
                    'token_chain': row[2],
                    'address': row[3] or row[1],
                    'name': row[4],
                    'symbol': row[5],
                    'token_data': token_data,
                    'notes': row[7],
                    'added_at': row[8]
                })
            
            conn.close()
            return favorites
        except sqlite3.Error:
            return []
    
    def remove_favorite(self, user_id, token_address, token_chain=None):
        """Retire un token des favoris"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if token_chain:
                cursor.execute('''
                    DELETE FROM favorites
                    WHERE user_id = ? AND token_address = ? AND token_chain = ?
                ''', (user_id, token_address, token_chain))
            else:
                cursor.execute('''
                    DELETE FROM favorites
                    WHERE user_id = ? AND (token_address = ? OR address = ?)
                ''', (user_id, token_address, token_address))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def is_favorite(self, user_id, token_address, token_chain):
        """Vérifie si un token est dans les favoris"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM favorites
                WHERE user_id = ? AND token_address = ? AND token_chain = ?
            ''', (user_id, token_address, token_chain))
            
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except sqlite3.Error:
            return False
    
    def update_favorite_notes(self, user_id, token_address, token_chain_or_notes, notes=None):
        """Met à jour les notes d'un favori"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if notes is None:
                address = token_address
                notes = token_chain_or_notes
                cursor.execute('''
                    UPDATE favorites SET notes = ?
                    WHERE user_id = ? AND (token_address = ? OR address = ?)
                ''', (notes, user_id, address, address))
            else:
                token_chain = token_chain_or_notes
                cursor.execute('''
                    UPDATE favorites SET notes = ?
                    WHERE user_id = ? AND token_address = ? AND token_chain = ?
                ''', (notes, user_id, token_address, token_chain))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def save_scan_history(self, user_id, scan_results):
        """Sauvegarde l'historique d'un scan"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            scan_data_json = json.dumps(scan_results)
            cursor.execute('''
                INSERT INTO scan_history (user_id, scan_data)
                VALUES (?, ?)
            ''', (user_id, scan_data_json))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def get_scan_history(self, user_id, limit=10):
        """Récupère l'historique des scans"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, scan_data, scan_date, address
                FROM scan_history WHERE user_id = ?
                ORDER BY scan_date DESC LIMIT ?
            ''', (user_id, limit))
            
            history = []
            for row in cursor.fetchall():
                scan_data = json.loads(row[1]) if row[1] else {}
                history.append({
                    'id': row[0],
                    'scan_data': scan_data,
                    'scan_date': row[2],
                    'address': row[3]
                })
            
            conn.close()
            return history
        except sqlite3.Error:
            return []
    
    def get_scan_details(self, scan_id):
        """Récupère les détails d'un scan"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, scan_data, scan_date, address
                FROM scan_history WHERE id = ?
            ''', (scan_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                scan_data = json.loads(row[2]) if row[2] else {}
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'scan_data': scan_data,
                    'scan_date': row[3],
                    'address': row[4]
                }
            return None
        except sqlite3.Error:
            return None
    
    def get_user_scan_count(self, user_id):
        """Compte le nombre total de scans"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM scan_history WHERE user_id = ?',
                (user_id,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except sqlite3.Error:
            return 0
    
    def get_user_days_active(self, user_id):
        """Calcule le nombre de jours depuis la création"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT created_at FROM users WHERE id = ?',
                (user_id,)
            )
            created_at = cursor.fetchone()[0]
            conn.close()
            
            created_date = datetime.fromisoformat(created_at)
            days = (datetime.now() - created_date).days
            return max(1, days)
        except Exception:
            return 0
    
    def log_admin_action(self, admin_id, action, target_user_id, details, ip_address):
        """Log une action admin"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admin_logs (admin_id, action, target_user_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_id, action, target_user_id, details, ip_address))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    # ==================== GESTION DES TOKENS SCANNÉS ====================
    # Système de rotation FIFO : max 200 tokens, suppression des plus anciens

    MAX_SCANNED_TOKENS = 200  # Limite maximale de tokens stockés

    def add_scanned_token(self, token_address, token_chain, token_data, risk_score=None, is_safe=False, is_pump_dump_suspect=False):
        """
        Ajoute un token scanné à la base de données avec rotation automatique FIFO

        Logique de rotation:
        - Si le token existe déjà (même adresse + chain), on le met à jour
        - Si on atteint 200 tokens, on supprime les 10 plus anciens avant d'ajouter
        - Les favoris ne sont JAMAIS supprimés (table séparée)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Vérifier si le token existe déjà (update au lieu d'insert)
            cursor.execute('''
                SELECT id FROM scanned_tokens
                WHERE token_address = ? AND token_chain = ?
            ''', (token_address, token_chain))

            existing = cursor.fetchone()
            token_data_json = json.dumps(token_data) if isinstance(token_data, dict) else token_data

            if existing:
                # Update du token existant avec nouveau timestamp
                cursor.execute('''
                    UPDATE scanned_tokens
                    SET token_data = ?, risk_score = ?, is_safe = ?,
                        is_pump_dump_suspect = ?, scanned_at = CURRENT_TIMESTAMP
                    WHERE token_address = ? AND token_chain = ?
                ''', (token_data_json, risk_score, 1 if is_safe else 0,
                      1 if is_pump_dump_suspect else 0, token_address, token_chain))
            else:
                # Vérifier le nombre total de tokens
                cursor.execute('SELECT COUNT(*) FROM scanned_tokens')
                count = cursor.fetchone()[0]

                # Si on atteint la limite, supprimer les 10 plus anciens
                if count >= self.MAX_SCANNED_TOKENS:
                    cursor.execute('''
                        DELETE FROM scanned_tokens
                        WHERE id IN (
                            SELECT id FROM scanned_tokens
                            ORDER BY scanned_at ASC
                            LIMIT 10
                        )
                    ''')
                    print(f"🗑️  Nettoyage auto: 10 tokens les plus anciens supprimés (limite {self.MAX_SCANNED_TOKENS} atteinte)")

                # Insérer le nouveau token
                cursor.execute('''
                    INSERT INTO scanned_tokens (token_address, token_chain, token_data, risk_score, is_safe, is_pump_dump_suspect)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (token_address, token_chain, token_data_json, risk_score,
                      1 if is_safe else 0, 1 if is_pump_dump_suspect else 0))

            conn.commit()
            token_id = cursor.lastrowid if not existing else existing[0]
            conn.close()
            return token_id
        except sqlite3.Error as e:
            print(f"❌ Erreur add_scanned_token: {e}")
            return None

    def add_scanned_tokens_batch(self, tokens_list):
        """
        Ajoute plusieurs tokens en batch avec rotation automatique

        Args:
            tokens_list: Liste de dict avec keys: address, chain, token_data, risk_score, is_safe, is_pump_dump_suspect

        Returns:
            Nombre de tokens ajoutés
        """
        count = 0
        for token in tokens_list:
            result = self.add_scanned_token(
                token_address=token.get('address'),
                token_chain=token.get('chain', 'solana'),
                token_data=token.get('token_data', token),
                risk_score=token.get('risk_score'),
                is_safe=token.get('is_safe', False),
                is_pump_dump_suspect=token.get('is_pump_dump_suspect', False)
            )
            if result:
                count += 1

        return count

    def get_scanned_tokens(self, limit=50, offset=0, chain=None, safe_only=False):
        """
        Récupère les tokens scannés (les plus récents en premier)

        Args:
            limit: Nombre de tokens à récupérer
            offset: Offset pour pagination
            chain: Filtrer par blockchain (None = toutes)
            safe_only: Si True, ne retourne que les tokens sûrs
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = 'SELECT id, token_address, token_chain, token_data, risk_score, is_safe, is_pump_dump_suspect, scanned_at FROM scanned_tokens'
            params = []

            conditions = []
            if chain:
                conditions.append('token_chain = ?')
                params.append(chain)
            if safe_only:
                conditions.append('is_safe = 1')

            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)

            query += ' ORDER BY scanned_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)

            tokens = []
            for row in cursor.fetchall():
                token_data = json.loads(row[3]) if row[3] else {}
                tokens.append({
                    'id': row[0],
                    'token_address': row[1],
                    'token_chain': row[2],
                    'token_data': token_data,
                    'risk_score': row[4],
                    'is_safe': bool(row[5]),
                    'is_pump_dump_suspect': bool(row[6]),
                    'scanned_at': row[7]
                })

            conn.close()
            return tokens
        except sqlite3.Error as e:
            print(f"❌ Erreur get_scanned_tokens: {e}")
            return []

    def get_scanned_tokens_count(self, chain=None):
        """Compte le nombre de tokens scannés"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if chain:
                cursor.execute('SELECT COUNT(*) FROM scanned_tokens WHERE token_chain = ?', (chain,))
            else:
                cursor.execute('SELECT COUNT(*) FROM scanned_tokens')

            count = cursor.fetchone()[0]
            conn.close()
            return count
        except sqlite3.Error:
            return 0

    def get_scanned_token(self, token_address, token_chain='solana'):
        """Récupère un token scanné spécifique"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, token_address, token_chain, token_data, risk_score, is_safe, is_pump_dump_suspect, scanned_at
                FROM scanned_tokens
                WHERE token_address = ? AND token_chain = ?
            ''', (token_address, token_chain))

            row = cursor.fetchone()
            conn.close()

            if row:
                token_data = json.loads(row[3]) if row[3] else {}
                return {
                    'id': row[0],
                    'token_address': row[1],
                    'token_chain': row[2],
                    'token_data': token_data,
                    'risk_score': row[4],
                    'is_safe': bool(row[5]),
                    'is_pump_dump_suspect': bool(row[6]),
                    'scanned_at': row[7]
                }
            return None
        except sqlite3.Error as e:
            print(f"❌ Erreur get_scanned_token: {e}")
            return None

    def cleanup_old_scanned_tokens(self, keep_count=190):
        """
        Nettoie les vieux tokens scannés (garde seulement keep_count tokens les plus récents)

        Args:
            keep_count: Nombre de tokens à garder (par défaut 190, laisse de la marge avant 200)

        Returns:
            Nombre de tokens supprimés
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Compter les tokens
            cursor.execute('SELECT COUNT(*) FROM scanned_tokens')
            total = cursor.fetchone()[0]

            if total <= keep_count:
                conn.close()
                return 0

            # Supprimer les plus anciens
            to_delete = total - keep_count
            cursor.execute('''
                DELETE FROM scanned_tokens
                WHERE id IN (
                    SELECT id FROM scanned_tokens
                    ORDER BY scanned_at ASC
                    LIMIT ?
                )
            ''', (to_delete,))

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            print(f"🗑️  Nettoyage manuel: {deleted} tokens supprimés (garde {keep_count} tokens)")
            return deleted
        except sqlite3.Error as e:
            print(f"❌ Erreur cleanup_old_scanned_tokens: {e}")
            return 0

    def delete_scanned_token(self, token_address, token_chain='solana'):
        """Supprime un token scanné spécifique (n'affecte PAS les favoris)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM scanned_tokens
                WHERE token_address = ? AND token_chain = ?
            ''', (token_address, token_chain))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False

    # ==================== FIN GESTION TOKENS SCANNÉS ====================

    def get_admin_logs(self, limit=50):
        """Récupère les logs admin"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT al.id, al.admin_id, u.username as admin_username, 
                       al.action, al.target_user_id, al.details, al.created_at, al.ip_address
                FROM admin_logs al
                JOIN users u ON al.admin_id = u.id
                ORDER BY al.created_at DESC LIMIT ?
            ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'admin_id': row[1],
                    'admin_username': row[2],
                    'action': row[3],
                    'target_user_id': row[4],
                    'details': row[5],
                    'created_at': row[6],
                    'ip_address': row[7] if len(row) > 7 else None
                })
            
            conn.close()
            return logs
        except sqlite3.Error:
            return []


if __name__ == "__main__":
    print("Initialisation de Token Scanner Pro Database")
    db = Database()
    print("Base de données prête")