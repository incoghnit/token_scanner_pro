"""
Token Discovery Service - Centralized Token Scanning
====================================================

Ce service centralise la découverte de nouveaux tokens pour éviter les appels API redondants.
Au lieu que chaque utilisateur fasse un scan individuel, un seul scan est effectué et
les résultats sont partagés avec tous les utilisateurs connectés via WebSocket.

Architecture:
- Un seul scanner par instance d'application
- Stockage dans la BDD (table scanned_tokens)
- Broadcasting temps réel via Flask-SocketIO
- Scan périodique automatique OU manuel
- Thread-safe avec locks

Avantages:
✅ Réduction des coûts d'API (1 appel au lieu de N)
✅ Amélioration des performances
✅ Expérience collaborative en temps réel
✅ Évite les rate limits
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from scanner_core import TokenScanner
from database import Database


class TokenDiscoveryService:
    """
    Service de découverte centralisée de tokens

    Usage:
        discovery = TokenDiscoveryService(database, socketio)
        discovery.start_auto_discovery(interval_seconds=300)

        # Ou scan manuel
        results = discovery.trigger_scan(max_tokens=20)
    """

    def __init__(self, database: Database, socketio=None, nitter_url: str = None):
        """
        Initialise le service de découverte

        Args:
            database: Instance de Database pour stocker les tokens
            socketio: Instance Flask-SocketIO pour broadcaster (optionnel)
            nitter_url: URL de l'instance Nitter pour scraping Twitter
        """
        self.db = database
        self.socketio = socketio
        self.scanner = TokenScanner(nitter_url=nitter_url)

        # État du service
        self._lock = threading.Lock()
        self._scan_in_progress = False
        self._last_scan_timestamp = None
        self._last_scan_results = None
        self._scan_count = 0

        # Auto-discovery configuration
        self._auto_discovery_active = False
        self._auto_discovery_thread = None
        self._auto_discovery_interval = 300  # 5 minutes par défaut
        self._stop_auto_discovery = threading.Event()

        # Callbacks pour événements
        self._on_scan_start_callbacks: List[Callable] = []
        self._on_scan_complete_callbacks: List[Callable] = []
        self._on_new_token_callbacks: List[Callable] = []

        print("✅ Token Discovery Service initialisé")

    # ==================== PROPRIÉTÉS ====================

    @property
    def is_scanning(self) -> bool:
        """Retourne True si un scan est en cours"""
        with self._lock:
            return self._scan_in_progress

    @property
    def last_scan_time(self) -> Optional[datetime]:
        """Retourne le timestamp du dernier scan"""
        with self._lock:
            return self._last_scan_timestamp

    @property
    def last_scan_results(self) -> Optional[Dict[str, Any]]:
        """Retourne les résultats du dernier scan"""
        with self._lock:
            return self._last_scan_results

    @property
    def scan_count(self) -> int:
        """Retourne le nombre total de scans effectués"""
        with self._lock:
            return self._scan_count

    @property
    def is_auto_discovery_active(self) -> bool:
        """Retourne True si l'auto-discovery est activé"""
        with self._lock:
            return self._auto_discovery_active

    # ==================== SCAN MANUEL ====================

    def trigger_scan(self, max_tokens: int = 20, chain: Optional[str] = None) -> Dict[str, Any]:
        """
        Déclenche un scan manuel des DERNIERS tokens du marché (découverte)

        ⚠️ IMPORTANT: Ce scan est PARTAGÉ entre tous les utilisateurs connectés.
        Pour scanner un token spécifique (adresse/URL), utilisez /api/scan/start à la place.

        Args:
            max_tokens: Nombre maximum de tokens à scanner
            chain: Blockchain spécifique (None = toutes)

        Returns:
            Dict avec les résultats du scan
        """
        # Vérifier si un scan est déjà en cours
        with self._lock:
            if self._scan_in_progress:
                return {
                    "success": False,
                    "error": "Un scan est déjà en cours",
                    "in_progress": True
                }

            # Marquer le scan comme en cours
            self._scan_in_progress = True

        try:
            # Notifier les callbacks de démarrage
            self._trigger_callbacks(self._on_scan_start_callbacks, {
                "max_tokens": max_tokens,
                "chain": chain
            })

            # Broadcaster le début du scan
            if self.socketio:
                self.socketio.emit('scan_started', {
                    "timestamp": datetime.now().isoformat(),
                    "max_tokens": max_tokens,
                    "scan_type": "discovery"  # Indiquer que c'est une découverte
                }, namespace='/')

            print(f"🔍 Discovery scan démarré - Max tokens: {max_tokens}")

            # Effectuer le scan des derniers tokens (DISCOVERY uniquement)
            results = self.scanner.scan_tokens(max_tokens=max_tokens)

            # Traiter les résultats
            if results.get('success') and results.get('results'):
                tokens = results['results']

                # Stocker dans la BDD
                stored_count = self.db.add_scanned_tokens_batch(tokens)
                print(f"💾 {stored_count}/{len(tokens)} tokens stockés dans la BDD")

                # Broadcaster chaque nouveau token
                if self.socketio:
                    for token in tokens:
                        self.socketio.emit('new_token', token, namespace='/')

                        # Notifier les callbacks
                        self._trigger_callbacks(self._on_new_token_callbacks, token)

                # Mettre à jour l'état
                with self._lock:
                    self._last_scan_timestamp = datetime.now()
                    self._last_scan_results = results
                    self._scan_count += 1

                # Notifier les callbacks de fin
                self._trigger_callbacks(self._on_scan_complete_callbacks, results)

                # Broadcaster la fin du scan
                if self.socketio:
                    self.socketio.emit('scan_completed', {
                        "timestamp": datetime.now().isoformat(),
                        "tokens_found": len(tokens),
                        "tokens_stored": stored_count,
                        "total_scans": self._scan_count
                    }, namespace='/')

                return {
                    "success": True,
                    "tokens_found": len(tokens),
                    "tokens_stored": stored_count,
                    "scan_timestamp": self._last_scan_timestamp.isoformat(),
                    "total_scans": self._scan_count
                }
            else:
                error = results.get('error', 'Erreur inconnue')
                print(f"❌ Erreur lors du scan: {error}")

                if self.socketio:
                    self.socketio.emit('scan_error', {
                        "timestamp": datetime.now().isoformat(),
                        "error": error
                    }, namespace='/')

                return {
                    "success": False,
                    "error": error
                }

        except Exception as e:
            error_msg = f"Exception lors du scan: {str(e)}"
            print(f"❌ {error_msg}")

            if self.socketio:
                self.socketio.emit('scan_error', {
                    "timestamp": datetime.now().isoformat(),
                    "error": error_msg
                }, namespace='/')

            return {
                "success": False,
                "error": error_msg
            }

        finally:
            # Toujours libérer le lock
            with self._lock:
                self._scan_in_progress = False


    # ==================== AUTO-DISCOVERY ====================

    def start_auto_discovery(self, interval_seconds: int = 300, max_tokens: int = 20):
        """
        Démarre l'auto-discovery périodique

        Args:
            interval_seconds: Intervalle entre chaque scan (défaut: 5 minutes)
            max_tokens: Nombre de tokens par scan
        """
        with self._lock:
            if self._auto_discovery_active:
                print("⚠️  Auto-discovery déjà actif")
                return False

            self._auto_discovery_interval = interval_seconds
            self._auto_discovery_active = True
            self._stop_auto_discovery.clear()

        # Lancer le thread d'auto-discovery
        self._auto_discovery_thread = threading.Thread(
            target=self._auto_discovery_loop,
            args=(max_tokens,),
            daemon=True
        )
        self._auto_discovery_thread.start()

        print(f"✅ Auto-discovery démarré (intervalle: {interval_seconds}s, max_tokens: {max_tokens})")
        return True

    def stop_auto_discovery(self):
        """Arrête l'auto-discovery"""
        with self._lock:
            if not self._auto_discovery_active:
                print("⚠️  Auto-discovery déjà arrêté")
                return False

            self._auto_discovery_active = False
            self._stop_auto_discovery.set()

        # Attendre que le thread se termine
        if self._auto_discovery_thread:
            self._auto_discovery_thread.join(timeout=5)

        print("✅ Auto-discovery arrêté")
        return True

    def _auto_discovery_loop(self, max_tokens: int):
        """Boucle principale de l'auto-discovery"""
        print(f"🔄 Auto-discovery loop démarrée")

        while not self._stop_auto_discovery.is_set():
            try:
                # Effectuer un scan
                print(f"🔍 Auto-discovery: démarrage d'un scan...")
                self.trigger_scan(max_tokens=max_tokens)

                # Attendre l'intervalle (ou jusqu'au signal d'arrêt)
                print(f"⏳ Auto-discovery: attente de {self._auto_discovery_interval}s...")
                self._stop_auto_discovery.wait(timeout=self._auto_discovery_interval)

            except Exception as e:
                print(f"❌ Erreur dans auto-discovery loop: {e}")
                # Attendre un peu avant de réessayer
                time.sleep(30)

        print("🔄 Auto-discovery loop terminée")

    # ==================== CALLBACKS ====================

    def on_scan_start(self, callback: Callable):
        """Enregistre un callback appelé au début d'un scan"""
        self._on_scan_start_callbacks.append(callback)

    def on_scan_complete(self, callback: Callable):
        """Enregistre un callback appelé à la fin d'un scan"""
        self._on_scan_complete_callbacks.append(callback)

    def on_new_token(self, callback: Callable):
        """Enregistre un callback appelé pour chaque nouveau token découvert"""
        self._on_new_token_callbacks.append(callback)

    def _trigger_callbacks(self, callbacks: List[Callable], data: Any):
        """Déclenche une liste de callbacks avec des données"""
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"❌ Erreur dans callback: {e}")

    # ==================== ÉTAT & STATISTIQUES ====================

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut complet du service"""
        with self._lock:
            return {
                "scanning": self._scan_in_progress,
                "auto_discovery_active": self._auto_discovery_active,
                "auto_discovery_interval": self._auto_discovery_interval,
                "last_scan_timestamp": self._last_scan_timestamp.isoformat() if self._last_scan_timestamp else None,
                "total_scans": self._scan_count,
                "tokens_in_database": self.db.get_scanned_tokens_count(),
                "database_capacity": self.db.MAX_SCANNED_TOKENS
            }

    def get_recent_tokens(self, limit: int = 50, chain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les tokens récemment découverts depuis la BDD

        Args:
            limit: Nombre de tokens à récupérer
            chain: Filtrer par blockchain (None = toutes)

        Returns:
            Liste de tokens
        """
        return self.db.get_scanned_tokens(limit=limit, chain=chain)

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du service"""
        total_tokens = self.db.get_scanned_tokens_count()
        safe_tokens = len(self.db.get_scanned_tokens(limit=1000, safe_only=True))

        return {
            "total_scans": self.scan_count,
            "total_tokens_discovered": total_tokens,
            "safe_tokens": safe_tokens,
            "risky_tokens": total_tokens - safe_tokens,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "auto_discovery_active": self.is_auto_discovery_active,
            "database_usage": f"{total_tokens}/{self.db.MAX_SCANNED_TOKENS}",
            "database_usage_percent": round((total_tokens / self.db.MAX_SCANNED_TOKENS) * 100, 1)
        }

    # ==================== CLEANUP ====================

    def shutdown(self):
        """Arrête proprement le service"""
        print("🛑 Arrêt du Token Discovery Service...")

        # Arrêter l'auto-discovery si actif
        if self.is_auto_discovery_active:
            self.stop_auto_discovery()

        print("✅ Token Discovery Service arrêté")


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    # Exemple d'utilisation standalone
    from database import Database

    db = Database()
    discovery = TokenDiscoveryService(database=db, socketio=None)

    # Callbacks d'exemple
    def on_scan_start(data):
        print(f"📢 Scan démarré avec {data['max_tokens']} tokens max")

    def on_new_token(token):
        print(f"📢 Nouveau token découvert: {token.get('name', 'Unknown')} ({token.get('symbol', '?')})")

    def on_scan_complete(results):
        print(f"📢 Scan terminé: {results.get('tokens_found', 0)} tokens trouvés")

    discovery.on_scan_start(on_scan_start)
    discovery.on_new_token(on_new_token)
    discovery.on_scan_complete(on_scan_complete)

    # Test scan manuel
    print("\n=== TEST SCAN MANUEL ===")
    result = discovery.trigger_scan(max_tokens=10)
    print(f"Résultat: {result}")

    # Test auto-discovery
    print("\n=== TEST AUTO-DISCOVERY ===")
    discovery.start_auto_discovery(interval_seconds=60, max_tokens=5)

    # Laisser tourner 3 minutes
    try:
        time.sleep(180)
    except KeyboardInterrupt:
        pass

    discovery.shutdown()
    print("\n=== STATISTIQUES ===")
    print(discovery.get_stats())
