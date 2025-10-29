"""
Service de Scan Automatique pour Token Scanner Pro
Scanne automatiquement les nouveaux tokens toutes les X minutes
et les stocke dans MongoDB avec TTL 24h
"""

from scanner_core import TokenScanner
from trading_engine import TradingEngine
from mongodb_manager import MongoDBManager
from datetime import datetime
from typing import Dict, List
import threading
import time


class AutoScannerService:
    """Service de scan automatique des tokens"""
    
    def __init__(self, mongodb: MongoDBManager, 
                 scan_interval: int = 300,  # 5 minutes par défaut
                 tokens_per_scan: int = 10):
        """
        Initialise le service de scan automatique
        
        Args:
            mongodb: Instance MongoDB Manager
            scan_interval: Intervalle entre chaque scan (secondes)
            tokens_per_scan: Nombre de tokens à scanner à chaque fois
        """
        self.mongodb = mongodb
        self.scan_interval = scan_interval
        self.tokens_per_scan = tokens_per_scan
        
        # Instances pour le scan
        self.scanner = None
        self.trading_engine = None
        
        # État du service
        self.is_running = False
        self.thread = None
        self.last_scan_time = None
        self.total_scans = 0
        self.total_tokens_cached = 0
        
        # Stats
        self.stats = {
            'total_scans': 0,
            'total_tokens_found': 0,
            'total_tokens_cached': 0,
            'errors': 0,
            'last_scan_time': None,
            'last_scan_duration': 0,
            'average_scan_duration': 0
        }
        
        print(f"✅ AutoScannerService initialisé")
        print(f"   Intervalle: {scan_interval}s ({scan_interval/60:.1f} min)")
        print(f"   Tokens par scan: {tokens_per_scan}")
    
    def initialize_modules(self, nitter_url: str = "http://192.168.1.19:8080"):
        """Initialise le scanner et le trading engine"""
        try:
            self.scanner = TokenScanner(nitter_url=nitter_url)
            self.trading_engine = TradingEngine()
            print("✅ Modules scanner initialisés")
            return True
        except Exception as e:
            print(f"❌ Erreur initialisation modules: {e}")
            return False
    
    def scan_and_cache_tokens(self) -> Dict:
        """
        Effectue un scan complet et cache les résultats
        
        Returns:
            Dict avec les résultats du scan
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🔍 SCAN AUTOMATIQUE - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # 1. Scanner les nouveaux tokens
            print(f"📡 Récupération des {self.tokens_per_scan} derniers tokens SOLANA...")
            scan_results = self.scanner.scan_tokens(max_tokens=self.tokens_per_scan, chain_filter="solana")
            
            if not scan_results.get('success'):
                print(f"❌ Échec du scan: {scan_results.get('error')}")
                self.stats['errors'] += 1
                return {
                    'success': False,
                    'error': scan_results.get('error')
                }
            
            tokens = scan_results.get('results', [])
            print(f"✅ {len(tokens)} tokens trouvés")
            
            # 2. Analyser et ajouter au cache
            cached_count = 0
            for token in tokens:
                try:
                    # Ajouter le score de trading
                    if self.trading_engine:
                        signal = self.trading_engine.analyze_token(token)
                        token['trading_signal'] = self.trading_engine.signal_to_dict(signal)
                    
                    # Ajouter au cache MongoDB (TTL 24h)
                    if self.mongodb.add_token_to_cache(token):
                        cached_count += 1
                        print(f"   ✅ Token caché: {token['address'][:10]}... ({token['chain']})")
                    
                except Exception as e:
                    print(f"   ⚠️ Erreur token {token.get('address', 'unknown')}: {e}")
                    continue
            
            # 3. Calculer les stats
            scan_duration = time.time() - start_time
            
            self.stats['total_scans'] += 1
            self.stats['total_tokens_found'] += len(tokens)
            self.stats['total_tokens_cached'] += cached_count
            self.stats['last_scan_time'] = datetime.now().isoformat()
            self.stats['last_scan_duration'] = round(scan_duration, 2)
            
            # Moyenne des durées de scan
            if self.stats['total_scans'] > 0:
                total_duration = (self.stats['average_scan_duration'] * 
                                (self.stats['total_scans'] - 1) + scan_duration)
                self.stats['average_scan_duration'] = round(
                    total_duration / self.stats['total_scans'], 2
                )
            
            print(f"\n📊 RÉSULTATS DU SCAN:")
            print(f"   • Tokens trouvés: {len(tokens)}")
            print(f"   • Tokens cachés: {cached_count}")
            print(f"   • Durée: {scan_duration:.2f}s")
            print(f"   • Cache stats: {self.mongodb.get_cache_stats()}")
            print(f"{'='*60}\n")
            
            self.last_scan_time = datetime.now()
            
            return {
                'success': True,
                'tokens_found': len(tokens),
                'tokens_cached': cached_count,
                'scan_duration': scan_duration,
                'timestamp': self.last_scan_time.isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur scan_and_cache_tokens: {e}")
            self.stats['errors'] += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    def _scan_loop(self):
        """Boucle principale de scan (thread)"""
        print(f"\n🚀 Service de scan automatique démarré")
        print(f"   Prochain scan dans {self.scan_interval}s\n")
        
        while self.is_running:
            try:
                # Effectuer le scan
                result = self.scan_and_cache_tokens()
                
                # Attendre l'intervalle avant le prochain scan
                if self.is_running:
                    next_scan = datetime.now().timestamp() + self.scan_interval
                    print(f"⏰ Prochain scan dans {self.scan_interval}s "
                          f"({datetime.fromtimestamp(next_scan).strftime('%H:%M:%S')})")
                    
                    # Attendre avec interruption possible
                    for _ in range(self.scan_interval):
                        if not self.is_running:
                            break
                        time.sleep(1)
                
            except Exception as e:
                print(f"❌ Erreur dans la boucle de scan: {e}")
                self.stats['errors'] += 1
                time.sleep(10)  # Attendre 10s en cas d'erreur
    
    def start(self) -> bool:
        """Démarre le service de scan automatique"""
        if self.is_running:
            print("⚠️ Service déjà en cours d'exécution")
            return False
        
        # Initialiser les modules si nécessaire
        if not self.scanner or not self.trading_engine:
            if not self.initialize_modules():
                return False
        
        # Démarrer le thread
        self.is_running = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()
        
        print(f"✅ Service de scan automatique démarré")
        return True
    
    def stop(self):
        """Arrête le service de scan automatique"""
        if not self.is_running:
            print("⚠️ Service déjà arrêté")
            return
        
        print("🛑 Arrêt du service de scan automatique...")
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        print("✅ Service de scan automatique arrêté")
    
    def get_status(self) -> Dict:
        """Retourne le statut du service"""
        cache_stats = self.mongodb.get_cache_stats()
        
        return {
            'is_running': self.is_running,
            'scan_interval': self.scan_interval,
            'tokens_per_scan': self.tokens_per_scan,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'stats': self.stats,
            'cache_stats': cache_stats,
            'next_scan_in': self._get_time_until_next_scan() if self.is_running else None
        }
    
    def _get_time_until_next_scan(self) -> int:
        """Calcule le temps jusqu'au prochain scan (secondes)"""
        if not self.last_scan_time:
            return 0
        
        elapsed = (datetime.now() - self.last_scan_time).total_seconds()
        remaining = max(0, self.scan_interval - elapsed)
        return int(remaining)
    
    def update_config(self, scan_interval: int = None, 
                     tokens_per_scan: int = None) -> bool:
        """
        Met à jour la configuration du service
        
        Args:
            scan_interval: Nouvel intervalle (secondes)
            tokens_per_scan: Nouveau nombre de tokens par scan
        """
        try:
            was_running = self.is_running
            
            # Arrêter si en cours
            if was_running:
                self.stop()
            
            # Mettre à jour la config
            if scan_interval is not None:
                self.scan_interval = scan_interval
                print(f"✅ Intervalle mis à jour: {scan_interval}s")
            
            if tokens_per_scan is not None:
                self.tokens_per_scan = tokens_per_scan
                print(f"✅ Tokens par scan mis à jour: {tokens_per_scan}")
            
            # Redémarrer si nécessaire
            if was_running:
                self.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur update_config: {e}")
            return False
    
    def force_scan(self) -> Dict:
        """Force un scan immédiat (sans attendre l'intervalle)"""
        print("🔥 Scan forcé demandé...")
        return self.scan_and_cache_tokens()
    
    def get_recent_tokens(self, limit: int = 50, 
                         filters: Dict = None) -> List[Dict]:
        """
        Récupère les tokens récents du cache
        
        Args:
            limit: Nombre maximum de tokens
            filters: Filtres (is_safe, min_liquidity, etc.)
        """
        return self.mongodb.get_cached_tokens(limit=limit, filters=filters)