"""
Trading Bot - Orchestrateur Principal
Coordonne tous les modules : Scanning → Analyse → Validation → Exécution → Monitoring
"""

import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Import des modules du système
from trading_engine import TradingEngine, TradingSignal
from trading_validator import TradingValidator
from wallet_connector import WalletConnector
from dex_executor import DEXExecutor
from position_monitor import PositionMonitor, Position
from scanner_core import TokenScanner


class BotMode(Enum):
    """Modes de fonctionnement du bot"""
    MANUAL = "manual"           # Utilisateur valide chaque trade
    SEMI_AUTO = "semi_auto"     # Bot propose, utilisateur valide
    FULL_AUTO = "full_auto"     # Bot trade automatiquement (DANGEREUX!)


@dataclass
class BotConfig:
    """Configuration du bot de trading"""
    # Mode
    mode: str = BotMode.SEMI_AUTO.value
    
    # Wallet & Connexion
    wallet_address: Optional[str] = None
    private_key: Optional[str] = None
    chain: str = "ethereum"
    
    # API Keys
    anthropic_api_key: Optional[str] = None
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    
    # Trading
    max_position_size: float = 10.0  # % du capital max par trade
    max_open_positions: int = 5
    default_slippage: float = 1.0     # %
    
    # Sécurité
    min_confidence_to_trade: float = 70.0
    max_daily_trades: int = 10
    max_daily_loss: float = 100.0     # USD
    emergency_stop: bool = False
    
    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: int = 30     # secondes
    
    # Profil utilisateur
    risk_tolerance: str = "modéré"
    capital_size: str = "moyen"
    experience: str = "intermédiaire"


class TradingBot:
    """Bot de trading principal - Orchestre tous les modules"""
    
    def __init__(self, user_id: int, config: BotConfig):
        """
        Initialise le bot de trading
        
        Args:
            user_id: ID de l'utilisateur
            config: Configuration du bot
        """
        self.user_id = user_id
        self.config = config
        
        # États
        self.initialized = False
        self.running = False
        
        # Statistiques de session
        self.session_stats = {
            'trades_executed': 0,
            'trades_approved': 0,
            'trades_rejected': 0,
            'total_pnl': 0.0,
            'start_time': None
        }
        
        # Modules (initialisés plus tard)
        self.scanner = None
        self.engine = None
        self.validator = None
        self.wallet = None
        self.dex_executor = None
        self.monitor = None
        
        print("🤖 Trading Bot créé")
        print(f"   User ID: {user_id}")
        print(f"   Mode: {config.mode}")
    
    # ==================== INITIALISATION ====================
    
    def initialize(self) -> bool:
        """
        Initialise tous les modules du bot
        
        Returns:
            True si succès
        """
        print(f"\n{'='*80}")
        print("🚀 INITIALISATION TRADING BOT")
        print(f"{'='*80}")
        
        try:
            # 1. Scanner de tokens
            print("\n1️⃣ Initialisation du scanner...")
            self.scanner = TokenScanner()
            print("   ✅ Scanner prêt")
            
            # 2. Trading Engine (scoring)
            print("\n2️⃣ Initialisation du trading engine...")
            self.engine = TradingEngine()
            print("   ✅ Engine prêt")
            
            # 3. Validator IA (Claude)
            print("\n3️⃣ Initialisation du validator IA...")
            if not self.config.anthropic_api_key:
                print("   ⚠️ Clé API Anthropic manquante - Validation IA désactivée")
                self.validator = None
            else:
                self.validator = TradingValidator(api_key=self.config.anthropic_api_key)
                print("   ✅ Validator IA prêt")
            
            # 4. Wallet Connector
            print("\n4️⃣ Connexion au wallet...")
            self.wallet = WalletConnector()
            
            if self.config.wallet_address:
                result = self.wallet.connect_web3_wallet(
                    wallet_address=self.config.wallet_address,
                    chain=self.config.chain,
                    private_key=self.config.private_key
                )
                
                if not result['success']:
                    raise Exception(f"Échec connexion wallet: {result.get('error')}")
                
                print(f"   ✅ Wallet connecté: {result['address'][:10]}...")
            else:
                print("   ⚠️ Aucun wallet configuré - Mode lecture seule")
            
            # 5. DEX Executor
            print("\n5️⃣ Initialisation du DEX executor...")
            self.dex_executor = DEXExecutor(self.wallet)
            
            if self.wallet.is_connected():
                if self.dex_executor.initialize(self.config.chain):
                    print("   ✅ DEX executor prêt")
                else:
                    print("   ⚠️ DEX executor non initialisé")
            else:
                print("   ⏭️ DEX executor skipped (pas de wallet)")
            
            # 6. Position Monitor
            print("\n6️⃣ Initialisation du position monitor...")
            self.monitor = PositionMonitor(self.dex_executor)
            
            if self.config.enable_monitoring:
                self.monitor.check_interval = self.config.monitoring_interval
                self.monitor.start_monitoring()
                print("   ✅ Monitoring actif (30s interval)")
            else:
                print("   ⏭️ Monitoring désactivé")
            
            self.initialized = True
            self.session_stats['start_time'] = datetime.now().isoformat()
            
            print(f"\n{'='*80}")
            print("✅ BOT INITIALISÉ ET PRÊT")
            print(f"{'='*80}\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERREUR INITIALISATION: {e}")
            print(f"{'='*80}\n")
            return False
    
    # ==================== ANALYSE DE TOKEN ====================
    
    def analyze_token(
        self,
        token_address: str,
        token_chain: str,
        request_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Analyse complète d'un token
        
        Args:
            token_address: Adresse du token
            token_chain: Blockchain
            request_validation: Demander validation IA
            
        Returns:
            Dict avec analyse complète et recommandation
        """
        if not self.initialized:
            return {
                'success': False,
                'error': 'Bot non initialisé'
            }
        
        print(f"\n{'='*80}")
        print(f"🔍 ANALYSE TOKEN")
        print(f"{'='*80}")
        print(f"Adresse: {token_address}")
        print(f"Chain: {token_chain.upper()}")
        
        try:
            # 1. Scanner le token
            print(f"\n1️⃣ Scanning du token...")
            
            token_info = {
                'address': token_address,
                'chain': token_chain,
                'url': f"https://dexscreener.com/{token_chain}/{token_address}",
                'icon': '',
                'description': '',
                'twitter': '',
                'links': []
            }
            
            token_data = self.scanner.analyze_token(token_info)
            
            if not token_data:
                raise Exception("Échec du scan")
            
            # 2. Analyse par le Trading Engine
            print(f"\n2️⃣ Analyse Trading Engine...")
            signal = self.engine.analyze_token(token_data)
            
            # 3. Validation IA (optionnelle)
            validation_result = None
            
            if request_validation and self.validator and signal.action == "BUY":
                print(f"\n3️⃣ Validation IA Claude...")
                
                user_profile = {
                    'risk_tolerance': self.config.risk_tolerance,
                    'capital_size': self.config.capital_size,
                    'experience': self.config.experience
                }
                
                validation_result = self.validator.validate_signal(
                    signal,
                    token_data,
                    user_profile
                )
                
                print(f"\n   Validation: {validation_result['validation_status']}")
                print(f"   Action finale: {validation_result['final_action']}")
                print(f"   Confiance ajustée: {validation_result['adjusted_confidence']:.1f}%")
            
            # 4. Construire le résultat
            result = {
                'success': True,
                'token_address': token_address,
                'token_chain': token_chain,
                'token_data': token_data,
                'signal': self.engine.signal_to_dict(signal),
                'validation': validation_result,
                'can_execute': self._can_execute_trade(signal, validation_result),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n{'='*80}")
            print(f"✅ ANALYSE TERMINÉE")
            print(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ ERREUR ANALYSE: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== EXÉCUTION DE TRADE ====================
    
    def execute_trade(
        self,
        analysis_result: Dict[str, Any],
        amount_usd: float,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Exécute un trade basé sur une analyse
        
        Args:
            analysis_result: Résultat de analyze_token()
            amount_usd: Montant à investir en USD
            force: Forcer l'exécution (ignorer les checks)
            
        Returns:
            Dict avec résultat de l'exécution
        """
        if not self.initialized:
            return {
                'success': False,
                'error': 'Bot non initialisé'
            }
        
        print(f"\n{'='*80}")
        print(f"💰 EXÉCUTION TRADE")
        print(f"{'='*80}")
        
        try:
            # 1. Vérifications préliminaires
            if not force:
                checks = self._pre_trade_checks(analysis_result, amount_usd)
                
                if not checks['passed']:
                    return {
                        'success': False,
                        'error': 'Vérifications échouées',
                        'failed_checks': checks['failed']
                    }
            
            # 2. Récupérer les infos
            token_address = analysis_result['token_address']
            token_chain = analysis_result['token_chain']
            signal = analysis_result['signal']
            validation = analysis_result.get('validation')
            
            # Prix d'entrée
            entry_price = signal['entry_price']
            
            # Cibles (ajustées si validation IA)
            if validation and validation.get('adjusted_targets'):
                targets = validation['adjusted_targets']
                stop_loss = targets.get('stop_loss', signal['suggested_stop_loss'])
                take_profit = targets.get('take_profit', signal['suggested_take_profit'])
            else:
                stop_loss = signal['suggested_stop_loss']
                take_profit = signal['suggested_take_profit']
            
            # Calculer le montant en tokens
            amount_tokens = amount_usd / entry_price
            
            print(f"\nDétails du trade:")
            print(f"  Token: {token_address[:10]}...{token_address[-8:]}")
            print(f"  Montant: ${amount_usd:.2f} ({amount_tokens:.6f} tokens)")
            print(f"  Entry: ${entry_price:.8f}")
            print(f"  Stop-Loss: ${stop_loss:.8f}")
            print(f"  Take-Profit: ${take_profit:.8f}")
            
            # 3. Obtenir le token de paiement (USDC, USDT, etc.)
            # Pour simplifier, on assume USDC
            payment_token = self._get_payment_token(token_chain)
            
            print(f"\n📝 Vérification de la balance...")
            
            # Vérifier la balance
            balance = self.wallet.get_token_balance(payment_token['address'], payment_token['decimals'])
            
            if balance < amount_usd:
                return {
                    'success': False,
                    'error': f'Balance insuffisante: ${balance:.2f} < ${amount_usd:.2f}'
                }
            
            print(f"   ✅ Balance suffisante: ${balance:.2f}")
            
            # 4. Exécuter le swap
            print(f"\n💱 Exécution du swap...")
            
            if not self.config.private_key:
                return {
                    'success': False,
                    'error': 'Clé privée non configurée'
                }
            
            swap_result = self.dex_executor.execute_swap(
                token_in=payment_token['address'],
                token_out=token_address,
                amount_in=amount_usd,
                slippage_tolerance=self.config.default_slippage,
                fee_tier=3000,  # 0.3%
                private_key=self.config.private_key
            )
            
            if not swap_result['success']:
                return {
                    'success': False,
                    'error': f"Swap échoué: {swap_result.get('error')}"
                }
            
            print(f"\n✅ SWAP RÉUSSI!")
            print(f"   TX Hash: {swap_result['tx_hash']}")
            
            # 5. Ouvrir la position dans le monitor
            print(f"\n📊 Enregistrement de la position...")
            
            position = self.monitor.open_position(
                user_id=self.user_id,
                token_address=token_address,
                token_chain=token_chain,
                entry_price=swap_result.get('amount_out_expected', entry_price) / amount_tokens,
                entry_amount=amount_tokens,
                entry_tx_hash=swap_result['tx_hash'],
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                dex_name=self.dex_executor.router_config.get('name', 'Unknown'),
                notes=f"Signal confiance: {signal['confidence']:.1f}%"
            )
            
            # 6. Mettre à jour les stats
            self.session_stats['trades_executed'] += 1
            
            print(f"\n{'='*80}")
            print(f"✅ TRADE EXÉCUTÉ - Position #{position.id}")
            print(f"{'='*80}\n")
            
            return {
                'success': True,
                'position_id': position.id,
                'swap_result': swap_result,
                'position': position
            }
            
        except Exception as e:
            print(f"\n❌ ERREUR EXÉCUTION: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== WORKFLOW COMPLET ====================
    
    def analyze_and_trade(
        self,
        token_address: str,
        token_chain: str,
        amount_usd: float,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        Workflow complet : Analyse → Validation → (Exécution)
        
        Args:
            token_address: Adresse du token
            token_chain: Blockchain
            amount_usd: Montant à investir
            auto_execute: Exécuter automatiquement si BUY
            
        Returns:
            Dict avec résultat complet
        """
        # 1. Analyser
        analysis = self.analyze_token(token_address, token_chain)
        
        if not analysis['success']:
            return analysis
        
        # 2. Décider
        final_action = analysis['signal']['action']
        
        if analysis.get('validation'):
            final_action = analysis['validation']['final_action']
        
        # 3. Si BUY et auto-execute
        if final_action == "BUY" and auto_execute:
            # Demander confirmation en mode SEMI_AUTO
            if self.config.mode == BotMode.SEMI_AUTO.value:
                print(f"\n⚠️ Mode SEMI-AUTO: Confirmation utilisateur requise")
                return {
                    'success': True,
                    'action': 'PENDING_APPROVAL',
                    'analysis': analysis,
                    'message': 'Approbation utilisateur requise'
                }
            
            # Exécuter en mode FULL_AUTO
            if self.config.mode == BotMode.FULL_AUTO.value:
                return self.execute_trade(analysis, amount_usd)
        
        # Sinon, retourner juste l'analyse
        return {
            'success': True,
            'action': final_action,
            'analysis': analysis
        }
    
    # ==================== GESTION DES POSITIONS ====================
    
    def get_open_positions(self) -> List[Position]:
        """Récupère les positions ouvertes de l'utilisateur"""
        if not self.monitor:
            return []
        
        return self.monitor.db.get_open_positions(self.user_id)
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Résumé des positions de l'utilisateur"""
        if not self.monitor:
            return {}
        
        return self.monitor.get_user_summary(self.user_id)
    
    def close_position(
        self,
        position_id: int,
        reason: str = "Manual close"
    ) -> bool:
        """
        Ferme une position manuellement
        
        Args:
            position_id: ID de la position
            reason: Raison de la fermeture
            
        Returns:
            True si succès
        """
        if not self.monitor:
            return False
        
        position = self.monitor.db.get_position_by_id(position_id)
        
        if not position or position.user_id != self.user_id:
            print(f"❌ Position #{position_id} non trouvée ou accès refusé")
            return False
        
        try:
            # Exécuter le swap de sortie
            # TODO: Implémenter l'exécution réelle
            exit_tx_hash = f"0xMANUAL_{position_id}_{int(time.time())}"
            
            return self.monitor.close_position_manual(
                position_id=position_id,
                exit_price=position.current_price,
                exit_tx_hash=exit_tx_hash,
                notes=reason
            )
            
        except Exception as e:
            print(f"❌ Erreur fermeture: {e}")
            return False
    
    # ==================== HELPERS ====================
    
    def _can_execute_trade(
        self,
        signal: TradingSignal,
        validation_result: Optional[Dict]
    ) -> bool:
        """Détermine si un trade peut être exécuté"""
        # Utiliser la validation IA si disponible
        if validation_result:
            action = validation_result['final_action']
            confidence = validation_result['adjusted_confidence']
        else:
            action = signal.action
            confidence = signal.confidence
        
        # Vérifier le seuil de confiance
        if action == "BUY" and confidence >= self.config.min_confidence_to_trade:
            return True
        
        return False
    
    def _pre_trade_checks(
        self,
        analysis_result: Dict,
        amount_usd: float
    ) -> Dict[str, Any]:
        """Vérifications avant trade"""
        failed = []
        
        # Check 1: Analyse réussie
        if not analysis_result.get('success'):
            failed.append("Analyse échouée")
        
        # Check 2: Action = BUY
        action = analysis_result['signal']['action']
        if analysis_result.get('validation'):
            action = analysis_result['validation']['final_action']
        
        if action != "BUY":
            failed.append(f"Action finale: {action} (pas BUY)")
        
        # Check 3: Wallet connecté
        if not self.wallet or not self.wallet.is_connected():
            failed.append("Wallet non connecté")
        
        # Check 4: Emergency stop
        if self.config.emergency_stop:
            failed.append("Mode EMERGENCY STOP activé")
        
        # Check 5: Nombre max de positions
        if self.monitor:
            open_positions = len(self.monitor.db.get_open_positions(self.user_id))
            if open_positions >= self.config.max_open_positions:
                failed.append(f"Max positions atteint ({open_positions}/{self.config.max_open_positions})")
        
        # Check 6: Taille de position
        max_size_usd = self.wallet.get_native_balance() * (self.config.max_position_size / 100)
        if amount_usd > max_size_usd:
            failed.append(f"Position trop grande: ${amount_usd:.2f} > ${max_size_usd:.2f}")
        
        # Check 7: Limite journalière
        if self.session_stats['trades_executed'] >= self.config.max_daily_trades:
            failed.append(f"Limite journalière atteinte ({self.config.max_daily_trades} trades)")
        
        return {
            'passed': len(failed) == 0,
            'failed': failed
        }
    
    def _get_payment_token(self, chain: str) -> Dict[str, Any]:
        """Retourne le token de paiement par défaut pour une chaîne"""
        tokens = {
            'ethereum': {
                'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'symbol': 'USDC',
                'decimals': 6
            },
            'bsc': {
                'address': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
                'symbol': 'USDC',
                'decimals': 18
            },
            'polygon': {
                'address': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
                'symbol': 'USDC',
                'decimals': 6
            },
            'base': {
                'address': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                'symbol': 'USDC',
                'decimals': 6
            }
        }
        
        return tokens.get(chain.lower(), tokens['ethereum'])
    
    # ==================== SHUTDOWN ====================
    
    def shutdown(self):
        """Arrête proprement le bot"""
        print(f"\n{'='*80}")
        print("🛑 ARRÊT DU BOT")
        print(f"{'='*80}")
        
        if self.monitor and self.config.enable_monitoring:
            self.monitor.stop_monitoring()
        
        if self.wallet:
            self.wallet.disconnect()
        
        # Afficher les stats de session
        print(f"\n📊 STATISTIQUES DE SESSION:")
        print(f"   Durée: {self._get_session_duration()}")
        print(f"   Trades exécutés: {self.session_stats['trades_executed']}")
        print(f"   P&L total: ${self.session_stats['total_pnl']:.2f}")
        
        print(f"\n{'='*80}")
        print("✅ BOT ARRÊTÉ")
        print(f"{'='*80}\n")
    
    def _get_session_duration(self) -> str:
        """Calcule la durée de la session"""
        if not self.session_stats['start_time']:
            return "N/A"
        
        start = datetime.fromisoformat(self.session_stats['start_time'])
        duration = datetime.now() - start
        
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        
        return f"{hours}h {minutes}m"


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    import os
    
    print("="*80)
    print("TEST TRADING BOT")
    print("="*80)
    
    # Configuration
    config = BotConfig(
        mode=BotMode.SEMI_AUTO.value,
        wallet_address=os.environ.get('WALLET_ADDRESS'),
        private_key=os.environ.get('PRIVATE_KEY'),
        chain='ethereum',
        anthropic_api_key=os.environ.get('ANTHROPIC_API_KEY'),
        max_position_size=5.0,  # 5% max
        min_confidence_to_trade=70.0,
        enable_monitoring=True
    )
    
    # Créer le bot
    bot = TradingBot(user_id=1, config=config)
    
    # Initialiser
    if not bot.initialize():
        print("❌ Échec initialisation")
        exit()
    
    # Test: Analyser un token
    print("\n" + "="*80)
    print("TEST ANALYSE TOKEN")
    print("="*80)
    
    # Token de test (remplacer par une vraie adresse)
    test_token = "0x1234567890abcdef1234567890abcdef12345678"
    test_chain = "ethereum"
    
    result = bot.analyze_token(test_token, test_chain)
    
    if result['success']:
        print(f"\n✅ Analyse réussie")
        print(f"   Action: {result['signal']['action']}")
        print(f"   Confiance: {result['signal']['confidence']:.1f}%")
        
        if result.get('validation'):
            print(f"   Validation IA: {result['validation']['final_action']}")
    
    # Afficher les positions
    print("\n" + "="*80)
    print("POSITIONS ACTUELLES")
    print("="*80)
    
    summary = bot.get_position_summary()
    print(f"Positions ouvertes: {summary.get('open_positions', 0)}")
    print(f"P&L total: ${summary.get('total_pnl', 0):.2f}")
    
    # Arrêter le bot
    time.sleep(5)
    bot.shutdown()