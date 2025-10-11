"""
Routes API Flask pour Token Scanner Pro - Trading System
Intègre tous les modules : Scanner, IA Validator, Trading, Monitoring
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import traceback
import asyncio
import os
import json

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

# Instances globales (à initialiser dans app.py)
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
        claude_api_key = app.config.get('CLAUDE_API_KEY')
        
        if not claude_api_key or claude_api_key == 'votre_clé_claude_api':
            print("⚠️ Clé Claude API non configurée")
            print("   Définissez CLAUDE_API_KEY dans app.config ou variable d'environnement")
            print("   La validation IA sera désactivée")
            ai_validator = None
        elif TRADING_VALIDATOR_AVAILABLE:
            try:
                ai_validator = TradingValidator(claude_api_key)
                print("✅ AI Validator initialisé")
            except Exception as e:
                print(f"❌ Erreur AI Validator: {e}")
                print(f"   Vérifiez que votre clé API est valide")
                ai_validator = None
        else:
            print("⚠️ Trading Validator module non disponible")
        
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


# ==================== DECORATEURS ====================

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
                'traceback': traceback.format_exc() if app.debug else None
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
                'scanner': (scanner, SCANNER_AVAILABLE),
            }
            
            if module_name in module_checks:
                instance, available = module_checks[module_name]
                if not available or instance is None:
                    return jsonify({
                        'success': False,
                        'error': f'Module {module_name} non disponible',
                        'message': 'Cette fonctionnalité nécessite des modules additionnels'
                    }), 503
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== ROUTES SCANNER & ANALYSE ====================

@api.route('/scan/token', methods=['POST'])
@login_required
@handle_errors
@require_module('scanner')
@require_module('trading_engine')
def scan_token():
    """
    Scanne et analyse un token crypto
    
    Body: {
        "address": "0x...",
        "chain": "ethereum" | "bsc" | "solana"
    }
    """
    data = request.get_json()
    address = data.get('address')
    chain = data.get('chain', 'ethereum')
    
    if not address:
        return jsonify({
            'success': False,
            'error': 'Adresse du token requise'
        }), 400
    
    # Créer token_info pour le scanner
    token_info = {
        'address': address,
        'chain': chain,
        'url': f"https://dexscreener.com/{chain}/{address}",
        'icon': '',
        'description': '',
        'twitter': '',
        'links': []
    }
    
    # Analyser le token avec le scanner
    token_data = scanner.analyze_token(token_info)
    
    if not token_data:
        return jsonify({
            'success': False,
            'error': 'Échec de l\'analyse du token'
        }), 500
    
    # Calculer le score de trading
    signal = trading_engine.analyze_token(token_data)
    trading_score = trading_engine.signal_to_dict(signal)
    
    return jsonify({
        'success': True,
        'token': token_data,
        'trading_score': trading_score,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/scan/batch', methods=['POST'])
@login_required
@handle_errors
@require_module('scanner')
@require_module('trading_engine')
def scan_batch():
    """
    Scanne plusieurs tokens en batch
    
    Body: {
        "addresses": ["0x...", "0x..."],
        "chain": "ethereum" | "bsc"
    }
    """
    data = request.get_json()
    addresses = data.get('addresses', [])
    chain = data.get('chain', 'ethereum')
    
    if not addresses or len(addresses) == 0:
        return jsonify({
            'success': False,
            'error': 'Liste d\'adresses requise'
        }), 400
    
    results = []
    for address in addresses[:10]:  # Limiter à 10 tokens max
        try:
            token_info = {
                'address': address,
                'chain': chain,
                'url': '',
                'icon': '',
                'description': '',
                'twitter': '',
                'links': []
            }
            
            token_data = scanner.analyze_token(token_info)
            signal = trading_engine.analyze_token(token_data)
            
            results.append({
                'address': address,
                'score': signal.score,
                'action': signal.action,
                'confidence': signal.confidence,
                'success': True
            })
        except Exception as e:
            results.append({
                'address': address,
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'success': True,
        'results': results,
        'total': len(results)
    })


# ==================== ROUTES IA VALIDATION ====================

@api.route('/ai/validate', methods=['POST'])
@login_required
@handle_errors
@require_module('ai_validator')
def validate_with_ai():
    """
    Valide une opportunité de trading avec l'IA Claude
    
    Body: {
        "token_data": {...},
        "trading_score": {...},
        "action": "BUY" | "SELL"
    }
    """
    if not ai_validator:
        return jsonify({
            'success': False,
            'error': 'Validation IA non disponible',
            'message': 'Clé API Claude non configurée'
        }), 503
    
    data = request.get_json()
    token_data = data.get('token_data', {})
    trading_score = data.get('trading_score', {})
    
    if not token_data:
        return jsonify({
            'success': False,
            'error': 'Données du token requises'
        }), 400
    
    # Reconstruire le signal depuis trading_score
    from trading_engine import TradingSignal
    
    signal = TradingSignal(
        action=trading_score.get('action', 'HOLD'),
        confidence=trading_score.get('confidence', 0),
        score=trading_score.get('score', 0),
        reasons=trading_score.get('reasons', []),
        entry_price=trading_score.get('entry_price', 0),
        suggested_stop_loss=trading_score.get('suggested_stop_loss', 0),
        suggested_take_profit=trading_score.get('suggested_take_profit', 0),
        risk_reward_ratio=trading_score.get('risk_reward_ratio', 0),
        position_size_percentage=trading_score.get('position_size_percentage', 0),
        timestamp=trading_score.get('timestamp', datetime.now().isoformat()),
        technical_score=trading_score.get('technical_score', 0),
        fundamental_score=trading_score.get('fundamental_score', 0),
        sentiment_score=trading_score.get('sentiment_score', 0),
        risk_score=trading_score.get('risk_score', 0),
        rsi_value=trading_score.get('rsi_value', 50),
        fibonacci_position=trading_score.get('fibonacci_position', 50),
        pump_dump_score=trading_score.get('pump_dump_score', 0),
        liquidity_score=trading_score.get('liquidity_score', 0),
        holder_concentration=trading_score.get('holder_concentration', 0)
    )
    
    # Valider avec Claude API
    user_profile = {
        'risk_tolerance': session.get('risk_tolerance', 'modéré'),
        'capital_size': session.get('capital_size', 'moyen'),
        'experience': session.get('experience', 'intermédiaire')
    }
    
    validation = ai_validator.validate_signal(signal, token_data, user_profile)
    
    return jsonify({
        'success': True,
        'validation': validation,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/ai/analyze/market', methods=['POST'])
@login_required
@handle_errors
@require_module('ai_validator')
def analyze_market():
    """
    Analyse du sentiment de marché via IA
    
    Body: {
        "tokens": ["0x...", "0x..."],
        "timeframe": "1h" | "4h" | "1d"
    }
    """
    if not ai_validator:
        return jsonify({
            'success': False,
            'error': 'Analyse IA non disponible'
        }), 503
    
    data = request.get_json()
    tokens = data.get('tokens', [])
    timeframe = data.get('timeframe', '1h')
    
    # TODO: Implémenter l'analyse de marché
    analysis = {
        'market_sentiment': 'neutral',
        'trend': 'sideways',
        'recommendations': ['Attendre de meilleurs signaux'],
        'confidence': 50
    }
    
    return jsonify({
        'success': True,
        'analysis': analysis,
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES WALLET ====================

@api.route('/wallet/connect', methods=['POST'])
@login_required
@handle_errors
@require_module('wallet_connector')
def connect_wallet():
    """
    Connecte un wallet (MetaMask, WalletConnect, ou Binance)
    
    Body: {
        "type": "metamask" | "walletconnect" | "binance",
        "address": "0x..." (pour MetaMask/WalletConnect),
        "api_key": "...", "api_secret": "..." (pour Binance)
    }
    """
    data = request.get_json()
    wallet_type = data.get('type')
    
    if wallet_type in ['metamask', 'walletconnect']:
        address = data.get('address')
        chain = data.get('chain', 'ethereum')
        
        if not address:
            return jsonify({
                'success': False,
                'error': 'Adresse du wallet requise'
            }), 400
        
        result = wallet_connector.connect_web3_wallet(address, chain)
        
        if result['success']:
            session['wallet_address'] = address
            session['wallet_type'] = wallet_type
            session['chain'] = chain
        
        return jsonify(result)
        
    elif wallet_type == 'binance':
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'Clés API Binance requises'
            }), 400
        
        result = wallet_connector.connect_binance(api_key, api_secret)
        
        if result['success']:
            session['wallet_type'] = 'binance'
        
        return jsonify(result)
    
    else:
        return jsonify({
            'success': False,
            'error': 'Type de wallet non supporté'
        }), 400


@api.route('/wallet/balance', methods=['GET'])
@login_required
@handle_errors
@require_module('wallet_connector')
def get_wallet_balance():
    """Récupère le solde du wallet connecté"""
    
    if not wallet_connector.is_connected():
        return jsonify({
            'success': False,
            'error': 'Aucun wallet connecté'
        }), 400
    
    balances = wallet_connector.get_balances()
    
    return jsonify({
        'success': True,
        'balances': balances,
        'wallet_type': session.get('wallet_type'),
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
        "platform": "uniswap" | "pancakeswap" | "binance",
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
    
    # TODO: Implémenter l'exécution réelle du trade
    # Pour l'instant, retourner un mock
    
    result = {
        'success': True,
        'tx_hash': '0xmock_transaction_hash',
        'action': action,
        'token_address': token_address,
        'amount': amount,
        'price': 0.00045,
        'timestamp': datetime.now().isoformat(),
        'message': 'Trade simulé (implémentation complète requise)'
    }
    
    # Si position monitor disponible, ouvrir une position
    if position_monitor and action == 'BUY':
        try:
            position = position_monitor.open_position(
                user_id=session['user_id'],
                token_address=token_address,
                token_chain=session.get('chain', 'ethereum'),
                entry_price=0.00045,
                entry_amount=amount / 0.00045,
                entry_tx_hash=result['tx_hash'],
                stop_loss_price=0.00045 * (1 - stop_loss/100) if stop_loss else 0,
                take_profit_price=0.00045 * (1 + take_profit/100) if take_profit else 0,
                dex_name=platform
            )
            result['position_id'] = position.id
        except Exception as e:
            print(f"Erreur création position: {e}")
    
    return jsonify(result)


@api.route('/trade/estimate', methods=['POST'])
@login_required
@handle_errors
@require_module('dex_executor')
def estimate_trade():
    """
    Estime le prix d'un trade sans l'exécuter
    
    Body: {
        "action": "BUY" | "SELL",
        "token_address": "0x...",
        "amount": 100,
        "platform": "uniswap" | "pancakeswap"
    }
    """
    data = request.get_json()
    
    # TODO: Implémenter l'estimation réelle
    estimate = {
        'amount_in': data.get('amount'),
        'amount_out': data.get('amount') * 2000,  # Mock
        'price_impact': 0.5,
        'gas_estimate': 150000,
        'platform': data.get('platform', 'uniswap')
    }
    
    return jsonify({
        'success': True,
        'estimate': estimate,
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES POSITIONS ====================

@api.route('/positions/list', methods=['GET'])
@login_required
@handle_errors
@require_module('position_monitor')
def list_positions():
    """Liste toutes les positions ouvertes"""
    
    user_id = session['user_id']
    positions = position_monitor.db.get_open_positions(user_id)
    
    # Convertir les positions en dict
    positions_list = []
    for pos in positions:
        positions_list.append({
            'id': pos.id,
            'token_address': pos.token_address,
            'token_chain': pos.token_chain,
            'entry_price': pos.entry_price,
            'current_price': pos.current_price,
            'amount': pos.entry_amount,
            'pnl': pos.pnl_percentage,
            'status': pos.status,
            'stop_loss': pos.stop_loss_price,
            'take_profit': pos.take_profit_price,
            'entry_timestamp': pos.entry_timestamp
        })
    
    return jsonify({
        'success': True,
        'positions': positions_list,
        'total': len(positions_list)
    })


@api.route('/positions/<int:position_id>', methods=['GET'])
@login_required
@handle_errors
@require_module('position_monitor')
def get_position(position_id):
    """Récupère les détails d'une position"""
    
    position = position_monitor.db.get_position_by_id(position_id)
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Position non trouvée'
        }), 404
    
    # Vérifier que la position appartient à l'utilisateur
    if position.user_id != session['user_id']:
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    return jsonify({
        'success': True,
        'position': {
            'id': position.id,
            'token_address': position.token_address,
            'token_chain': position.token_chain,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'amount': position.entry_amount,
            'pnl_usd': position.pnl_usd,
            'pnl_percentage': position.pnl_percentage,
            'status': position.status,
            'stop_loss': position.stop_loss_price,
            'take_profit': position.take_profit_price,
            'entry_timestamp': position.entry_timestamp,
            'dex_name': position.dex_name,
            'notes': position.notes
        }
    })


@api.route('/positions/<int:position_id>/close', methods=['POST'])
@login_required
@handle_errors
@require_module('position_monitor')
def close_position(position_id):
    """Ferme une position manuellement"""
    
    position = position_monitor.db.get_position_by_id(position_id)
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Position non trouvée'
        }), 404
    
    if position.user_id != session['user_id']:
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    # Fermer la position
    success = position_monitor.close_position_manual(
        position_id=position_id,
        exit_price=position.current_price,
        exit_tx_hash=f"0xMANUAL_{position_id}_{int(datetime.now().timestamp())}",
        notes="Fermeture manuelle via API"
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Position fermée',
            'position_id': position_id
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Échec de la fermeture'
        }), 500


@api.route('/positions/<int:position_id>/update', methods=['PUT'])
@login_required
@handle_errors
@require_module('position_monitor')
def update_position(position_id):
    """
    Modifie les paramètres d'une position (SL/TP)
    
    Body: {
        "stop_loss": 10.0,
        "take_profit": 20.0
    }
    """
    position = position_monitor.db.get_position_by_id(position_id)
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Position non trouvée'
        }), 404
    
    if position.user_id != session['user_id']:
        return jsonify({
            'success': False,
            'error': 'Accès refusé'
        }), 403
    
    data = request.get_json()
    stop_loss_pct = data.get('stop_loss')
    take_profit_pct = data.get('take_profit')
    
    # Calculer les nouveaux prix
    if stop_loss_pct:
        position.stop_loss_price = position.entry_price * (1 - stop_loss_pct / 100)
    
    if take_profit_pct:
        position.take_profit_price = position.entry_price * (1 + take_profit_pct / 100)
    
    # Sauvegarder
    position_monitor.db.update_position(position)
    
    return jsonify({
        'success': True,
        'message': 'Position mise à jour',
        'position': {
            'id': position.id,
            'stop_loss': position.stop_loss_price,
            'take_profit': position.take_profit_price
        }
    })


@api.route('/positions/stats', methods=['GET'])
@login_required
@handle_errors
@require_module('position_monitor')
def positions_stats():
    """Statistiques globales des positions"""
    
    user_id = session['user_id']
    summary = position_monitor.get_user_summary(user_id)
    
    return jsonify({
        'success': True,
        'stats': summary
    })


# ==================== ROUTES BOT AUTOMATIQUE ====================

@api.route('/bot/start', methods=['POST'])
@login_required
@handle_errors
def start_bot():
    """
    Démarre le bot de trading automatique
    
    Body: {
        "tokens": ["0x...", "0x..."],
        "config": {
            "max_positions": 5,
            "risk_per_trade": 2.0,
            "min_confidence": 70
        }
    }
    """
    if not TRADING_BOT_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Trading bot non disponible'
        }), 503
    
    data = request.get_json()
    tokens = data.get('tokens', [])
    config_data = data.get('config', {})
    
    # TODO: Implémenter le démarrage réel du bot
    
    return jsonify({
        'success': True,
        'message': 'Bot démarré (implémentation complète requise)',
        'tokens': tokens,
        'config': config_data
    })


@api.route('/bot/stop', methods=['POST'])
@login_required
@handle_errors
def stop_bot():
    """Arrête le bot de trading automatique"""
    
    # TODO: Implémenter l'arrêt du bot
    
    return jsonify({
        'success': True,
        'message': 'Bot arrêté',
        'timestamp': datetime.now().isoformat()
    })


@api.route('/bot/status', methods=['GET'])
@login_required
@handle_errors
def bot_status():
    """Récupère le statut du bot"""
    
    status = {
        'running': False,
        'positions_open': 0,
        'trades_today': 0,
        'pnl_today': 0.0
    }
    
    return jsonify({
        'success': True,
        'status': status
    })


# ==================== ROUTES MONITORING ====================

@api.route('/monitor/start', methods=['POST'])
@login_required
@handle_errors
@require_module('position_monitor')
def start_monitoring():
    """Démarre le monitoring automatique"""
    
    if not position_monitor.monitoring:
        position_monitor.start_monitoring()
    
    return jsonify({
        'success': True,
        'message': 'Monitoring démarré'
    })


@api.route('/monitor/stop', methods=['POST'])
@login_required
@handle_errors
@require_module('position_monitor')
def stop_monitoring():
    """Arrête le monitoring automatique"""
    
    position_monitor.stop_monitoring()
    
    return jsonify({
        'success': True,
        'message': 'Monitoring arrêté'
    })


@api.route('/monitor/alerts', methods=['GET'])
@login_required
@handle_errors
def get_alerts():
    """Récupère toutes les alertes"""
    
    # TODO: Implémenter le système d'alertes
    alerts = []
    
    return jsonify({
        'success': True,
        'alerts': alerts,
        'total': len(alerts)
    })


# ==================== ROUTES CONFIGURATION ====================

@api.route('/config/get', methods=['GET'])
@login_required
@handle_errors
def get_config():
    """Récupère la configuration utilisateur"""
    
    user_id = session.get('user_id')
    
    config = {
        'user_id': user_id,
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