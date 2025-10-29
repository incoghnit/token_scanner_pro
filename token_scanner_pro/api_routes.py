"""
Routes API Flask pour Token Scanner Pro - Trading System
Intègre tous les modules : Scanner, IA Validator, Trading, Monitoring
Version corrigée - Variables globales fixées
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import traceback
import os

# Import de vos modules existants avec gestion d'erreurs
try:
    from trading_engine import TradingEngine
    TRADING_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ TradingEngine non disponible: {e}")
    TradingEngine = None
    TRADING_ENGINE_AVAILABLE = False

try:
    from trading_validator import TradingValidator
    TRADING_VALIDATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ TradingValidator non disponible: {e}")
    TradingValidator = None
    TRADING_VALIDATOR_AVAILABLE = False

try:
    from wallet_connector import WalletConnector
    WALLET_CONNECTOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ WalletConnector non disponible: {e}")
    WalletConnector = None
    WALLET_CONNECTOR_AVAILABLE = False

try:
    from dex_executor import DEXExecutor
    DEX_EXECUTOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ DEXExecutor non disponible: {e}")
    DEXExecutor = None
    DEX_EXECUTOR_AVAILABLE = False

try:
    from position_monitor import PositionMonitor
    POSITION_MONITOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PositionMonitor non disponible: {e}")
    PositionMonitor = None
    POSITION_MONITOR_AVAILABLE = False

try:
    from trading_bot import TradingBot, BotConfig
    TRADING_BOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ TradingBot non disponible: {e}")
    TradingBot = None
    BotConfig = None
    TRADING_BOT_AVAILABLE = False

try:
    from scanner_core import TokenScanner
    SCANNER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Scanner non disponible: {e}")
    TokenScanner = None
    SCANNER_AVAILABLE = False

try:
    from database import Database
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Database non disponible: {e}")
    Database = None
    DATABASE_AVAILABLE = False

# Créer le Blueprint pour les routes API
api = Blueprint('api', __name__, url_prefix='/api')

# ==================== INSTANCES GLOBALES ====================
# ✅ CORRECTION : Déclaration unique des variables globales
trading_engine = None
ai_validator = None
wallet_connector = None
dex_executor = None
position_monitor = None
trading_bot = None
scanner = None
database = None


def init_trading_system(app):
    """
    Initialise tous les modules du système de trading
    À appeler depuis app.py au démarrage
    """
    # ✅ CORRECTION : Déclaration global une seule fois
    global trading_engine, ai_validator, wallet_connector
    global dex_executor, position_monitor, trading_bot, scanner, database
    
    print("\n" + "="*80)
    print("🚀 INITIALISATION SYSTÈME DE TRADING")
    print("="*80)
    
    initialization_success = True
    
    try:
        # 1. Database
        if DATABASE_AVAILABLE:
            try:
                database = Database()
                print("✅ Database initialisée")
            except Exception as e:
                print(f"❌ Erreur Database: {e}")
                initialization_success = False
        else:
            print("⚠️ Database module non disponible")
        
        # 2. Scanner
        if SCANNER_AVAILABLE:
            try:
                scanner = TokenScanner()
                print("✅ Scanner initialisé")
            except Exception as e:
                print(f"❌ Erreur Scanner: {e}")
                initialization_success = False
        else:
            print("⚠️ Scanner module non disponible")
        
        # 3. Trading Engine
        if TRADING_ENGINE_AVAILABLE:
            try:
                trading_engine = TradingEngine()
                print("✅ Trading Engine initialisé")
            except Exception as e:
                print(f"❌ Erreur Trading Engine: {e}")
                initialization_success = False
        else:
            print("⚠️ Trading Engine module non disponible")
        
        # 4. AI Validator
        if TRADING_VALIDATOR_AVAILABLE:
            try:
                claude_api_key = os.getenv('ANTHROPIC_API_KEY') or app.config.get('CLAUDE_API_KEY')
                if claude_api_key:
                    ai_validator = TradingValidator(claude_api_key)
                    print("✅ AI Validator initialisé")
                else:
                    print("⚠️ AI Validator: Clé API Claude manquante")
                    initialization_success = False
            except Exception as e:
                print(f"❌ Erreur AI Validator: {e}")
                initialization_success = False
        else:
            print("⚠️ AI Validator module non disponible")
        
        # 5. Wallet Connector
        if WALLET_CONNECTOR_AVAILABLE:
            try:
                wallet_connector = WalletConnector()
                print("✅ Wallet Connector initialisé")
            except Exception as e:
                print(f"❌ Erreur Wallet Connector: {e}")
                initialization_success = False
        else:
            print("⚠️ Wallet Connector module non disponible")
        
        # 6. DEX Executor
        if DEX_EXECUTOR_AVAILABLE and wallet_connector:
            try:
                dex_executor = DEXExecutor(wallet_connector)
                print("✅ DEX Executor initialisé")
            except Exception as e:
                print(f"❌ Erreur DEX Executor: {e}")
                initialization_success = False
        else:
            print("⚠️ DEX Executor non initialisé (dépendances manquantes)")
        
        # 7. Position Monitor
        if POSITION_MONITOR_AVAILABLE and dex_executor:
            try:
                position_monitor = PositionMonitor(dex_executor)
                position_monitor.start_monitoring()
                print("✅ Position Monitor initialisé et démarré")
            except Exception as e:
                print(f"❌ Erreur Position Monitor: {e}")
                initialization_success = False
        else:
            print("⚠️ Position Monitor non initialisé (dépendances manquantes)")
        
        # Note: trading_bot sera initialisé par utilisateur avec BotConfig
        
        print("="*80)
        if initialization_success:
            print("✅ SYSTÈME DE TRADING INITIALISÉ AVEC SUCCÈS")
        else:
            print("⚠️ SYSTÈME PARTIELLEMENT INITIALISÉ")
            print("   Certaines fonctionnalités peuvent être indisponibles")
        print("="*80 + "\n")
        
        return initialization_success
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE D'INITIALISATION: {e}")
        traceback.print_exc()
        print("="*80 + "\n")
        return False


# ==================== DÉCORATEURS ====================

def login_required(f):
    """Vérifie que l'utilisateur est authentifié"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Authentification requise'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def handle_errors(f):
    """Gestion globale des erreurs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"❌ Erreur dans {f.__name__}: {e}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc() if api.app and api.app.debug else None
            }), 500
    return decorated_function


def require_module(module_name):
    """Vérifie qu'un module est disponible"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            module_checks = {
                'trading_engine': (trading_engine, TRADING_ENGINE_AVAILABLE),
                'ai_validator': (ai_validator, TRADING_VALIDATOR_AVAILABLE),
                'wallet_connector': (wallet_connector, WALLET_CONNECTOR_AVAILABLE),
                'dex_executor': (dex_executor, DEX_EXECUTOR_AVAILABLE),
                'position_monitor': (position_monitor, POSITION_MONITOR_AVAILABLE),
                'scanner': (scanner, SCANNER_AVAILABLE)
            }
            
            if module_name not in module_checks:
                return jsonify({
                    'success': False,
                    'error': f'Module {module_name} inconnu'
                }), 500
            
            instance, available = module_checks[module_name]
            
            if not available or instance is None:
                return jsonify({
                    'success': False,
                    'error': f'Module {module_name} non disponible'
                }), 503
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== ROUTES ANALYSE ====================

@api.route('/analyze', methods=['POST'])
@login_required
@handle_errors
@require_module('trading_engine')
def analyze_token():
    """
    Analyse un token et génère un signal de trading
    
    Body: {
        "token_address": "0x...",
        "token_chain": "ethereum"
    }
    """
    data = request.get_json()
    token_address = data.get('token_address')
    token_chain = data.get('token_chain')
    
    if not token_address or not token_chain:
        return jsonify({
            'success': False,
            'error': 'Adresse token et chaîne requis'
        }), 400
    
    # Scanner le token
    if not scanner:
        return jsonify({
            'success': False,
            'error': 'Scanner non disponible'
        }), 503
    
    token_info = {
        'address': token_address,
        'chain': token_chain,
        'url': f"https://dexscreener.com/{token_chain}/{token_address}"
    }
    
    token_data = scanner.analyze_token(token_info)
    
    if not token_data or 'error' in token_data:
        return jsonify({
            'success': False,
            'error': 'Impossible d\'analyser ce token',
            'details': token_data
        }), 400
    
    # Analyse technique
    signal = trading_engine.analyze_token(token_data)
    
    return jsonify({
        'success': True,
        'token_data': token_data,
        'signal': {
            'action': signal.action,
            'confidence': signal.confidence,
            'score': signal.score,
            'entry_price': signal.entry_price,
            'stop_loss': signal.suggested_stop_loss,
            'take_profit': signal.suggested_take_profit,
            'position_size': signal.position_size_percentage,
            'reasons': signal.reasons
        }
    })


@api.route('/validate', methods=['POST'])
@login_required
@handle_errors
@require_module('ai_validator')
def validate_signal():
    """
    Valide un signal avec l'IA Claude
    
    Body: {
        "token_data": {...},
        "signal": {...},
        "user_profile": {
            "risk_tolerance": "low|medium|high",
            "capital": 1000,
            "experience": "beginner|intermediate|expert"
        }
    }
    """
    data = request.get_json()
    token_data = data.get('token_data')
    signal_data = data.get('signal')
    user_profile = data.get('user_profile', {})
    
    if not token_data or not signal_data:
        return jsonify({
            'success': False,
            'error': 'Token data et signal requis'
        }), 400
    
    # Valider avec l'IA
    validation = ai_validator.validate_trade(
        token_data=token_data,
        signal=signal_data,
        user_profile=user_profile
    )
    
    return jsonify({
        'success': True,
        'validation': validation
    })


# ==================== ROUTES WALLET ====================

@api.route('/wallet/connect', methods=['POST'])
@login_required
@handle_errors
@require_module('wallet_connector')
def connect_wallet():
    """
    Connecte un wallet
    
    Body: {
        "wallet_type": "metamask|walletconnect",
        "private_key": "...",  (pour test uniquement)
        "chain": "ethereum|bsc|base"
    }
    """
    data = request.get_json()
    wallet_type = data.get('wallet_type', 'metamask')
    private_key = data.get('private_key')
    chain = data.get('chain', 'ethereum')
    
    # Pour démo/test avec clé privée
    if private_key:
        success = wallet_connector.connect_private_key(private_key, chain)
        if success:
            address = wallet_connector.get_address()
            session['wallet_address'] = address
            session['wallet_type'] = wallet_type
            session['chain'] = chain
            
            return jsonify({
                'success': True,
                'address': address,
                'chain': chain,
                'balance': wallet_connector.get_balance()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Connexion échouée'
            }), 400
    
    # Pour production : utiliser Web3Modal/WalletConnect
    return jsonify({
        'success': False,
        'error': 'Méthode de connexion non implémentée. Utilisez private_key pour test.'
    }), 501


@api.route('/wallet/balance', methods=['GET'])
@login_required
@handle_errors
@require_module('wallet_connector')
def get_wallet_balance():
    """Récupère le solde du wallet connecté"""
    
    if not wallet_connector.is_connected():
        return jsonify({
            'success': False,
            'error': 'Wallet non connecté'
        }), 400
    
    balance = wallet_connector.get_balance()
    address = wallet_connector.get_address()
    
    return jsonify({
        'success': True,
        'address': address,
        'balance': balance,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/wallet/disconnect', methods=['POST'])
@login_required
@handle_errors
def disconnect_wallet():
    """Déconnecte le wallet actuel"""
    
    if wallet_connector:
        wallet_connector.disconnect()
    
    session.pop('wallet_address', None)
    session.pop('wallet_type', None)
    session.pop('chain', None)
    
    return jsonify({
        'success': True,
        'message': 'Wallet déconnecté',
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES TRADING ====================

@api.route('/trade/execute', methods=['POST'])
@login_required
@handle_errors
@require_module('dex_executor')
def execute_trade():
    """
    Exécute un trade (BUY ou SELL)
    
    Body: {
        "action": "BUY" | "SELL",
        "token_address": "0x...",
        "amount": 100,
        "platform": "uniswap" | "pancakeswap",
        "slippage": 1.0,
        "stop_loss": 10.0,
        "take_profit": 20.0
    }
    """
    data = request.get_json()
    action = data.get('action')
    token_address = data.get('token_address')
    amount = float(data.get('amount', 0))
    platform = data.get('platform', 'uniswap')
    slippage = float(data.get('slippage', 1.0))
    stop_loss = data.get('stop_loss')
    take_profit = data.get('take_profit')
    
    # Validation
    if not action or action not in ['BUY', 'SELL']:
        return jsonify({
            'success': False,
            'error': 'Action BUY ou SELL requise'
        }), 400
    
    if not token_address:
        return jsonify({
            'success': False,
            'error': 'Adresse du token requise'
        }), 400
    
    if amount <= 0:
        return jsonify({
            'success': False,
            'error': 'Montant invalide'
        }), 400
    
    if not wallet_connector or not wallet_connector.is_connected():
        return jsonify({
            'success': False,
            'error': 'Wallet non connecté'
        }), 400
    
    # Exécuter le trade
    try:
        if action == 'BUY':
            result = dex_executor.buy_token(
                token_address=token_address,
                amount_in=amount,
                slippage_tolerance=slippage
            )
        else:
            result = dex_executor.sell_token(
                token_address=token_address,
                amount_in=amount,
                slippage_tolerance=slippage
            )
        
        # Si succès, ouvrir une position dans le monitor
        if result['success'] and action == 'BUY' and position_monitor:
            try:
                position = position_monitor.open_position(
                    user_id=session['user_id'],
                    token_address=token_address,
                    token_chain=session.get('chain', 'ethereum'),
                    entry_price=result['price'],
                    entry_amount=result['amount_out'],
                    entry_tx_hash=result['tx_hash'],
                    stop_loss_price=stop_loss if stop_loss else result['price'] * 0.9,
                    take_profit_price=take_profit if take_profit else result['price'] * 1.2,
                    dex_name=platform
                )
                result['position_id'] = position.id
            except Exception as e:
                print(f"Erreur création position: {e}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== ROUTES POSITIONS ====================

@api.route('/positions', methods=['GET'])
@login_required
@handle_errors
@require_module('position_monitor')
def get_positions():
    """
    Récupère les positions de l'utilisateur
    
    Query params:
        - status: "open" | "closed" | "all" (default: open)
        - limit: nombre max de positions (default: 50)
    """
    status = request.args.get('status', 'open')
    limit = int(request.args.get('limit', 50))
    
    positions = position_monitor.db.get_user_positions(
        user_id=session['user_id'],
        status=status if status != 'all' else None,
        limit=limit
    )
    
    positions_list = [
        {
            'id': p.id,
            'token_address': p.token_address,
            'token_chain': p.token_chain,
            'entry_price': p.entry_price,
            'entry_amount': p.entry_amount,
            'current_price': p.current_price,
            'current_value': p.current_value,
            'pnl_usd': p.pnl_usd,
            'pnl_percentage': p.pnl_percentage,
            'status': p.status,
            'stop_loss': p.stop_loss_price,
            'take_profit': p.take_profit_price,
            'entry_timestamp': p.entry_timestamp,
            'exit_timestamp': p.exit_timestamp,
            'exit_reason': p.exit_reason
        }
        for p in positions
    ]
    
    return jsonify({
        'success': True,
        'positions': positions_list,
        'count': len(positions_list)
    })


@api.route('/positions/<int:position_id>/close', methods=['POST'])
@login_required
@handle_errors
@require_module('position_monitor')
def close_position(position_id):
    """
    Ferme une position manuellement
    
    Body: {
        "reason": "manual_close"
    }
    """
    data = request.get_json()
    reason = data.get('reason', 'manual_close')
    
    # Récupérer la position
    positions = position_monitor.db.get_user_positions(
        user_id=session['user_id'],
        status='open',
        limit=1000
    )
    
    position = next((p for p in positions if p.id == position_id), None)
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Position non trouvée'
        }), 404
    
    # Fermer la position
    try:
        result = position_monitor.close_position(
            position=position,
            reason=reason
        )
        
        return jsonify({
            'success': True,
            'position': {
                'id': position.id,
                'exit_price': position.exit_price,
                'pnl_usd': position.pnl_usd,
                'pnl_percentage': position.pnl_percentage
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api.route('/positions/stats', methods=['GET'])
@login_required
@handle_errors
@require_module('position_monitor')
def get_position_stats():
    """Récupère les statistiques de trading de l'utilisateur"""
    
    all_positions = position_monitor.db.get_user_positions(
        user_id=session['user_id'],
        status=None,
        limit=1000
    )
    
    total_positions = len(all_positions)
    open_positions = len([p for p in all_positions if p.status == 'open'])
    closed_positions = len([p for p in all_positions if p.status == 'closed'])
    
    profitable = [p for p in all_positions if p.status == 'closed' and p.pnl_usd > 0]
    losing = [p for p in all_positions if p.status == 'closed' and p.pnl_usd < 0]
    
    total_pnl = sum(p.pnl_usd for p in all_positions if p.status == 'closed')
    win_rate = (len(profitable) / max(closed_positions, 1)) * 100
    
    return jsonify({
        'success': True,
        'stats': {
            'total_positions': total_positions,
            'open_positions': open_positions,
            'closed_positions': closed_positions,
            'winning_trades': len(profitable),
            'losing_trades': len(losing),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'average_win': round(sum(p.pnl_usd for p in profitable) / max(len(profitable), 1), 2),
            'average_loss': round(sum(p.pnl_usd for p in losing) / max(len(losing), 1), 2)
        }
    })


# ==================== ROUTES CONFIG ====================

@api.route('/config', methods=['GET'])
@login_required
@handle_errors
def get_config():
    """Récupère la configuration utilisateur"""
    
    config = {
        'default_slippage': session.get('default_slippage', 1.0),
        'default_stop_loss': session.get('default_stop_loss', 10.0),
        'default_take_profit': session.get('default_take_profit', 20.0),
        'notifications_enabled': session.get('notifications_enabled', True),
        'risk_tolerance': session.get('risk_tolerance', 'modéré'),
        'capital_size': session.get('capital_size', 'moyen'),
        'experience': session.get('experience', 'intermédiaire')
    }
    
    return jsonify({
        'success': True,
        'config': config
    })


@api.route('/config/update', methods=['PUT'])
@login_required
@handle_errors
def update_config():
    """
    Met à jour la configuration utilisateur
    
    Body: {
        "default_slippage": 1.0,
        "default_stop_loss": 10.0,
        "default_take_profit": 20.0,
        "notifications_enabled": true
    }
    """
    data = request.get_json()
    
    # Mettre à jour la session
    for key, value in data.items():
        session[key] = value
    
    return jsonify({
        'success': True,
        'message': 'Configuration mise à jour'
    })


# ==================== ROUTES HEALTH CHECK ====================

@api.route('/health', methods=['GET'])
def health_check():
    """Vérifie que l'API est opérationnelle"""
    
    status = {
        'api': 'online',
        'modules': {
            'scanner': SCANNER_AVAILABLE and scanner is not None,
            'trading_engine': TRADING_ENGINE_AVAILABLE and trading_engine is not None,
            'ai_validator': TRADING_VALIDATOR_AVAILABLE and ai_validator is not None,
            'wallet_connector': WALLET_CONNECTOR_AVAILABLE and wallet_connector is not None,
            'dex_executor': DEX_EXECUTOR_AVAILABLE and dex_executor is not None,
            'position_monitor': POSITION_MONITOR_AVAILABLE and position_monitor is not None,
            'trading_bot': TRADING_BOT_AVAILABLE,
            'database': DATABASE_AVAILABLE and database is not None
        },
        'monitoring_active': position_monitor.monitoring if position_monitor else False,
        'timestamp': datetime.now().isoformat()
    }
    
    all_critical_modules = all([
        status['modules']['scanner'],
        status['modules']['trading_engine'],
        status['modules']['database']
    ])
    
    return jsonify({
        'success': True,
        'status': status,
        'operational': all_critical_modules
    })


# ==================== EXPORT ====================

def register_api_routes(app):
    """
    Enregistre toutes les routes API dans l'application Flask
    À appeler depuis app.py
    """
    app.register_blueprint(api)
    
    # Initialiser le système de trading
    init_trading_system(app)
    
    print("✅ Routes API enregistrées avec succès")