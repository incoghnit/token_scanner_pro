"""
Système de monitoring 24/7 des positions de trading
Surveillance automatique avec Stop-Loss et Take-Profit
"""

import sqlite3
import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

class PositionStatus(Enum):
    """Status des positions"""
    OPEN = "open"
    CLOSED_TP = "closed_take_profit"
    CLOSED_SL = "closed_stop_loss"
    CLOSED_MANUAL = "closed_manual"
    ERROR = "error"

@dataclass
class Position:
    """Représente une position de trading"""
    id: Optional[int]
    user_id: int
    token_address: str
    token_chain: str
    
    # Informations d'entrée
    entry_price: float
    entry_amount: float
    entry_tx_hash: str
    entry_timestamp: str
    
    # Cibles
    stop_loss_price: float
    take_profit_price: float
    
    # Status
    status: str
    current_price: float
    current_value: float
    pnl_usd: float
    pnl_percentage: float
    
    # Informations de sortie (si fermée)
    exit_price: Optional[float] = None
    exit_amount: Optional[float] = None
    exit_tx_hash: Optional[str] = None
    exit_timestamp: Optional[str] = None
    exit_reason: Optional[str] = None
    
    # Métadonnées
    dex_name: Optional[str] = None
    slippage_tolerance: float = 1.0
    notes: Optional[str] = None
    last_check: Optional[str] = None


class PositionDatabase:
    """Gestionnaire de base de données pour les positions"""
    
    def __init__(self, db_path: str = "token_scanner.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialise la table des positions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_address TEXT NOT NULL,
                token_chain TEXT NOT NULL,
                
                entry_price REAL NOT NULL,
                entry_amount REAL NOT NULL,
                entry_tx_hash TEXT NOT NULL,
                entry_timestamp TEXT NOT NULL,
                
                stop_loss_price REAL NOT NULL,
                take_profit_price REAL NOT NULL,
                
                status TEXT NOT NULL,
                current_price REAL NOT NULL,
                current_value REAL NOT NULL,
                pnl_usd REAL NOT NULL,
                pnl_percentage REAL NOT NULL,
                
                exit_price REAL,
                exit_amount REAL,
                exit_tx_hash TEXT,
                exit_timestamp TEXT,
                exit_reason TEXT,
                
                dex_name TEXT,
                slippage_tolerance REAL DEFAULT 1.0,
                notes TEXT,
                last_check TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Index pour performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_positions_user_status 
            ON trading_positions(user_id, status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_positions_status 
            ON trading_positions(status)
        ''')
        
        conn.commit()
        conn.close()
        
        print("💾 Base de données positions initialisée")
    
    def save_position(self, position: Position) -> int:
        """Sauvegarde une nouvelle position"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trading_positions (
                user_id, token_address, token_chain,
                entry_price, entry_amount, entry_tx_hash, entry_timestamp,
                stop_loss_price, take_profit_price,
                status, current_price, current_value, pnl_usd, pnl_percentage,
                dex_name, slippage_tolerance, notes, last_check
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.user_id, position.token_address, position.token_chain,
            position.entry_price, position.entry_amount, position.entry_tx_hash, position.entry_timestamp,
            position.stop_loss_price, position.take_profit_price,
            position.status, position.current_price, position.current_value,
            position.pnl_usd, position.pnl_percentage,
            position.dex_name, position.slippage_tolerance, position.notes, position.last_check
        ))
        
        position_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return position_id
    
    def update_position(self, position: Position):
        """Met à jour une position existante"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trading_positions SET
                current_price = ?,
                current_value = ?,
                pnl_usd = ?,
                pnl_percentage = ?,
                status = ?,
                exit_price = ?,
                exit_amount = ?,
                exit_tx_hash = ?,
                exit_timestamp = ?,
                exit_reason = ?,
                last_check = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            position.current_price, position.current_value,
            position.pnl_usd, position.pnl_percentage, position.status,
            position.exit_price, position.exit_amount, position.exit_tx_hash,
            position.exit_timestamp, position.exit_reason, position.last_check,
            position.id
        ))
        
        conn.commit()
        conn.close()
    
    def get_open_positions(self, user_id: Optional[int] = None) -> List[Position]:
        """Récupère toutes les positions ouvertes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM trading_positions 
                WHERE status = ? AND user_id = ?
                ORDER BY entry_timestamp DESC
            ''', (PositionStatus.OPEN.value, user_id))
        else:
            cursor.execute('''
                SELECT * FROM trading_positions 
                WHERE status = ?
                ORDER BY entry_timestamp DESC
            ''', (PositionStatus.OPEN.value,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_position(row) for row in rows]
    
    def get_position_by_id(self, position_id: int) -> Optional[Position]:
        """Récupère une position par ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trading_positions WHERE id = ?', (position_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_position(row)
        return None
    
    def get_user_positions(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Position]:
        """Récupère les positions d'un utilisateur"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM trading_positions 
                WHERE user_id = ? AND status = ?
                ORDER BY entry_timestamp DESC LIMIT ?
            ''', (user_id, status, limit))
        else:
            cursor.execute('''
                SELECT * FROM trading_positions 
                WHERE user_id = ?
                ORDER BY entry_timestamp DESC LIMIT ?
            ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_position(row) for row in rows]
    
    def _row_to_position(self, row) -> Position:
        """Convertit une row SQL en Position"""
        return Position(
            id=row['id'],
            user_id=row['user_id'],
            token_address=row['token_address'],
            token_chain=row['token_chain'],
            entry_price=row['entry_price'],
            entry_amount=row['entry_amount'],
            entry_tx_hash=row['entry_tx_hash'],
            entry_timestamp=row['entry_timestamp'],
            stop_loss_price=row['stop_loss_price'],
            take_profit_price=row['take_profit_price'],
            status=row['status'],
            current_price=row['current_price'],
            current_value=row['current_value'],
            pnl_usd=row['pnl_usd'],
            pnl_percentage=row['pnl_percentage'],
            exit_price=row['exit_price'],
            exit_amount=row['exit_amount'],
            exit_tx_hash=row['exit_tx_hash'],
            exit_timestamp=row['exit_timestamp'],
            exit_reason=row['exit_reason'],
            dex_name=row['dex_name'],
            slippage_tolerance=row['slippage_tolerance'],
            notes=row['notes'],
            last_check=row['last_check']
        )


class PositionMonitor:
    """Moniteur principal des positions de trading"""
    
    def __init__(self, dex_executor, price_fetcher=None):
        """
        Initialise le moniteur
        
        Args:
            dex_executor: Instance de DEXExecutor
            price_fetcher: Fonction pour récupérer les prix (optionnel)
        """
        self.db = PositionDatabase()
        self.dex_executor = dex_executor
        self.price_fetcher = price_fetcher
        
        # Monitoring
        self.monitoring = False
        self.check_interval = 30  # Vérification toutes les 30 secondes
        self.monitor_thread = None
        
        # Statistiques
        self.stats = {
            'checks_performed': 0,
            'positions_closed': 0,
            'stop_loss_triggered': 0,
            'take_profit_triggered': 0,
            'errors': 0
        }
        
        print("📊 Position Monitor initialisé")
    
    # ==================== GESTION DES POSITIONS ====================
    
    def open_position(
        self,
        user_id: int,
        token_address: str,
        token_chain: str,
        entry_price: float,
        entry_amount: float,
        entry_tx_hash: str,
        stop_loss_price: float,
        take_profit_price: float,
        dex_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Position:
        """
        Enregistre une nouvelle position ouverte
        
        Args:
            user_id: ID de l'utilisateur
            token_address: Adresse du token
            token_chain: Blockchain
            entry_price: Prix d'entrée
            entry_amount: Montant acheté
            entry_tx_hash: Hash de la transaction
            stop_loss_price: Prix Stop-Loss
            take_profit_price: Prix Take-Profit
            dex_name: Nom du DEX
            notes: Notes optionnelles
            
        Returns:
            Position créée
        """
        print(f"\n{'='*80}")
        print(f"📈 OUVERTURE POSITION")
        print(f"{'='*80}")
        
        position = Position(
            id=None,
            user_id=user_id,
            token_address=token_address,
            token_chain=token_chain,
            entry_price=entry_price,
            entry_amount=entry_amount,
            entry_tx_hash=entry_tx_hash,
            entry_timestamp=datetime.now().isoformat(),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            status=PositionStatus.OPEN.value,
            current_price=entry_price,
            current_value=entry_price * entry_amount,
            pnl_usd=0.0,
            pnl_percentage=0.0,
            dex_name=dex_name,
            notes=notes,
            last_check=datetime.now().isoformat()
        )
        
        position_id = self.db.save_position(position)
        position.id = position_id
        
        print(f"✅ Position #{position_id} ouverte")
        print(f"   Token: {token_address[:10]}...{token_address[-8:]}")
        print(f"   Entry: ${entry_price:.8f}")
        print(f"   Amount: {entry_amount:.6f}")
        print(f"   Stop-Loss: ${stop_loss_price:.8f} ({self._calc_percentage(entry_price, stop_loss_price):.1f}%)")
        print(f"   Take-Profit: ${take_profit_price:.8f} ({self._calc_percentage(entry_price, take_profit_price):.1f}%)")
        print(f"{'='*80}\n")
        
        return position
    
    def close_position_manual(
        self,
        position_id: int,
        exit_price: float,
        exit_tx_hash: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Ferme une position manuellement
        
        Args:
            position_id: ID de la position
            exit_price: Prix de sortie
            exit_tx_hash: Hash de la transaction
            notes: Notes optionnelles
            
        Returns:
            True si succès
        """
        position = self.db.get_position_by_id(position_id)
        
        if not position:
            print(f"❌ Position #{position_id} non trouvée")
            return False
        
        if position.status != PositionStatus.OPEN.value:
            print(f"❌ Position #{position_id} déjà fermée")
            return False
        
        # Calculer le P&L
        pnl_usd = (exit_price - position.entry_price) * position.entry_amount
        pnl_percentage = ((exit_price - position.entry_price) / position.entry_price) * 100
        
        # Mettre à jour la position
        position.status = PositionStatus.CLOSED_MANUAL.value
        position.exit_price = exit_price
        position.exit_amount = position.entry_amount
        position.exit_tx_hash = exit_tx_hash
        position.exit_timestamp = datetime.now().isoformat()
        position.exit_reason = f"Fermeture manuelle. {notes if notes else ''}"
        position.current_price = exit_price
        position.current_value = exit_price * position.entry_amount
        position.pnl_usd = pnl_usd
        position.pnl_percentage = pnl_percentage
        position.last_check = datetime.now().isoformat()
        
        self.db.update_position(position)
        
        print(f"✅ Position #{position_id} fermée manuellement")
        print(f"   P&L: ${pnl_usd:.2f} ({pnl_percentage:+.2f}%)")
        
        return True
    
    # ==================== MONITORING ====================
    
    def start_monitoring(self):
        """Démarre le monitoring automatique"""
        if self.monitoring:
            print("⚠️ Monitoring déjà actif")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        print("✅ Monitoring démarré (vérification toutes les 30s)")
    
    def stop_monitoring(self):
        """Arrête le monitoring"""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("🛑 Monitoring arrêté")
    
    def _monitoring_loop(self):
        """Boucle principale de monitoring"""
        print(f"\n{'='*80}")
        print("🔄 MONITORING ACTIF")
        print(f"{'='*80}\n")
        
        while self.monitoring:
            try:
                self._check_all_positions()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ Erreur monitoring: {e}")
                self.stats['errors'] += 1
                time.sleep(self.check_interval)
    
    def _check_all_positions(self):
        """Vérifie toutes les positions ouvertes"""
        positions = self.db.get_open_positions()
        
        if not positions:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] 🔍 Vérification de {len(positions)} position(s)...")
        
        for position in positions:
            try:
                self._check_position(position)
            except Exception as e:
                print(f"  ❌ Erreur position #{position.id}: {e}")
                self.stats['errors'] += 1
        
        self.stats['checks_performed'] += 1
    
    def _check_position(self, position: Position):
        """Vérifie une position individuelle"""
        # 1. Récupérer le prix actuel
        current_price = self._get_current_price(position.token_address, position.token_chain)
        
        if current_price is None or current_price <= 0:
            print(f"  ⚠️ Position #{position.id}: Prix indisponible")
            return
        
        # 2. Calculer les métriques
        current_value = current_price * position.entry_amount
        pnl_usd = (current_price - position.entry_price) * position.entry_amount
        pnl_percentage = ((current_price - position.entry_price) / position.entry_price) * 100
        
        # 3. Mettre à jour les données
        position.current_price = current_price
        position.current_value = current_value
        position.pnl_usd = pnl_usd
        position.pnl_percentage = pnl_percentage
        position.last_check = datetime.now().isoformat()
        
        # 4. Vérifier Stop-Loss
        if current_price <= position.stop_loss_price:
            print(f"\n  🚨 STOP-LOSS DÉCLENCHÉ - Position #{position.id}")
            print(f"     Prix actuel: ${current_price:.8f}")
            print(f"     Stop-Loss: ${position.stop_loss_price:.8f}")
            print(f"     P&L: ${pnl_usd:.2f} ({pnl_percentage:+.2f}%)")
            
            self._execute_stop_loss(position)
            return
        
        # 5. Vérifier Take-Profit
        if current_price >= position.take_profit_price:
            print(f"\n  🎯 TAKE-PROFIT DÉCLENCHÉ - Position #{position.id}")
            print(f"     Prix actuel: ${current_price:.8f}")
            print(f"     Take-Profit: ${position.take_profit_price:.8f}")
            print(f"     P&L: ${pnl_usd:.2f} ({pnl_percentage:+.2f}%)")
            
            self._execute_take_profit(position)
            return
        
        # 6. Sinon, juste mettre à jour
        self.db.update_position(position)
        
        # Afficher un update tous les 10 checks
        if self.stats['checks_performed'] % 10 == 0:
            print(f"  📊 Position #{position.id}: ${current_price:.8f} | P&L: {pnl_percentage:+.2f}%")
    
    def _execute_stop_loss(self, position: Position):
        """Exécute un Stop-Loss"""
        try:
            # En production, exécuter le swap sur le DEX
            # Pour l'instant, on simule la fermeture
            
            # TODO: Implémenter l'exécution réelle via dex_executor
            # result = self.dex_executor.execute_swap(...)
            
            # Simuler la transaction
            exit_tx_hash = f"0xSL_{position.id}_{int(time.time())}"
            
            position.status = PositionStatus.CLOSED_SL.value
            position.exit_price = position.current_price
            position.exit_amount = position.entry_amount
            position.exit_tx_hash = exit_tx_hash
            position.exit_timestamp = datetime.now().isoformat()
            position.exit_reason = f"Stop-Loss déclenché à ${position.current_price:.8f}"
            
            self.db.update_position(position)
            
            self.stats['positions_closed'] += 1
            self.stats['stop_loss_triggered'] += 1
            
            print(f"  ✅ Stop-Loss exécuté pour position #{position.id}")
            
        except Exception as e:
            print(f"  ❌ Erreur exécution Stop-Loss: {e}")
            position.status = PositionStatus.ERROR.value
            position.notes = f"Erreur SL: {str(e)}"
            self.db.update_position(position)
    
    def _execute_take_profit(self, position: Position):
        """Exécute un Take-Profit"""
        try:
            # En production, exécuter le swap sur le DEX
            # Pour l'instant, on simule la fermeture
            
            # TODO: Implémenter l'exécution réelle via dex_executor
            # result = self.dex_executor.execute_swap(...)
            
            # Simuler la transaction
            exit_tx_hash = f"0xTP_{position.id}_{int(time.time())}"
            
            position.status = PositionStatus.CLOSED_TP.value
            position.exit_price = position.current_price
            position.exit_amount = position.entry_amount
            position.exit_tx_hash = exit_tx_hash
            position.exit_timestamp = datetime.now().isoformat()
            position.exit_reason = f"Take-Profit déclenché à ${position.current_price:.8f}"
            
            self.db.update_position(position)
            
            self.stats['positions_closed'] += 1
            self.stats['take_profit_triggered'] += 1
            
            print(f"  ✅ Take-Profit exécuté pour position #{position.id}")
            
        except Exception as e:
            print(f"  ❌ Erreur exécution Take-Profit: {e}")
            position.status = PositionStatus.ERROR.value
            position.notes = f"Erreur TP: {str(e)}"
            self.db.update_position(position)
    
    def _get_current_price(self, token_address: str, chain: str) -> Optional[float]:
        """
        Récupère le prix actuel d'un token
        
        Returns:
            Prix en USD ou None
        """
        # Si un price_fetcher personnalisé est fourni
        if self.price_fetcher:
            return self.price_fetcher(token_address, chain)
        
        # Sinon, utiliser DexScreener API (par défaut)
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                
                if pairs:
                    # Prendre la paire avec le plus de liquidité
                    main_pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                    price = float(main_pair.get('priceUsd', 0))
                    return price
            
            return None
            
        except Exception as e:
            print(f"    ⚠️ Erreur récupération prix: {e}")
            return None
    
    # ==================== STATISTIQUES ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques du moniteur"""
        open_positions = self.db.get_open_positions()
        
        total_pnl = sum(p.pnl_usd for p in open_positions)
        total_value = sum(p.current_value for p in open_positions)
        
        return {
            'monitoring_active': self.monitoring,
            'open_positions': len(open_positions),
            'total_value_usd': total_value,
            'total_pnl_usd': total_pnl,
            'checks_performed': self.stats['checks_performed'],
            'positions_closed': self.stats['positions_closed'],
            'stop_loss_triggered': self.stats['stop_loss_triggered'],
            'take_profit_triggered': self.stats['take_profit_triggered'],
            'errors': self.stats['errors']
        }
    
    def get_user_summary(self, user_id: int) -> Dict[str, Any]:
        """Résumé des positions d'un utilisateur"""
        open_pos = self.db.get_open_positions(user_id)
        all_pos = self.db.get_user_positions(user_id)
        
        closed_pos = [p for p in all_pos if p.status != PositionStatus.OPEN.value]
        
        total_invested = sum(p.entry_price * p.entry_amount for p in open_pos)
        total_pnl = sum(p.pnl_usd for p in open_pos)
        
        # Calculer win rate sur positions fermées
        winning_trades = len([p for p in closed_pos if p.pnl_usd > 0])
        total_trades = len(closed_pos)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'open_positions': len(open_pos),
            'total_positions': len(all_pos),
            'closed_positions': len(closed_pos),
            'total_invested': total_invested,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades
        }
    
    # ==================== HELPERS ====================
    
    def _calc_percentage(self, entry: float, target: float) -> float:
        """Calcule le pourcentage de changement"""
        if entry == 0:
            return 0.0
        return ((target - entry) / entry) * 100


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    import requests
    
    print("="*80)
    print("TEST POSITION MONITOR")
    print("="*80)
    
    # Mock DEX executor
    class MockDEXExecutor:
        pass
    
    # Initialiser le monitor
    monitor = PositionMonitor(MockDEXExecutor())
    
    # 1. Ouvrir une position de test
    print("\n1️⃣ TEST OUVERTURE POSITION")
    
    position = monitor.open_position(
        user_id=1,
        token_address="0x1234567890abcdef1234567890abcdef12345678",
        token_chain="ethereum",
        entry_price=0.00045,
        entry_amount=1000,
        entry_tx_hash="0xabc123...",
        stop_loss_price=0.00040,  # -11%
        take_profit_price=0.00056,  # +24%
        dex_name="Uniswap V3",
        notes="Position de test"
    )
    
    # 2. Afficher les statistiques
    print("\n2️⃣ STATISTIQUES")
    stats = monitor.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # 3. Résumé utilisateur
    print("\n3️⃣ RÉSUMÉ UTILISATEUR")
    summary = monitor.get_user_summary(user_id=1)
    print(json.dumps(summary, indent=2))
    
    # 4. Tester le monitoring (simulation)
    print("\n4️⃣ TEST MONITORING (10 secondes)")
    monitor.check_interval = 2  # Vérifier toutes les 2s
    monitor.start_monitoring()
    
    time.sleep(10)
    
    monitor.stop_monitoring()
    
    # 5. Fermer la position manuellement
    print("\n5️⃣ FERMETURE MANUELLE")
    monitor.close_position_manual(
        position_id=position.id,
        exit_price=0.00050,
        exit_tx_hash="0xdef456...",
        notes="Test de fermeture"
    )
    
    print("\n" + "="*80)
    print("TESTS TERMINÉS")
    print("="*80)