"""
Routes API Flask pour Token Scanner Pro - Trading System
Intègre tous les modules : Scanner, IA Validator, Trading, Monitoring
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import traceback
import asyncio

# Import de vos modules existants
from trading_engine import TradingEngine
from ai_validator import AIValidator
from wallet_connector import WalletConnector
from dex_trader import DEXTrader
from position_monitor import PositionMonitor
from trading_bot import TradingBot

# Créer le Blueprint pour les routes API
api = Blueprint('api', __name__, url_prefix='/api')

# Instances globales (à initialiser dans app.py)
trading_engine = None
ai_validator = None
wallet_connector = None
dex_trader = None
position_monitor = None
trading_bot = None


def init_trading_system(app):
    """
    Initialise tous les modules du système de trading
    À appeler depuis app.py au démarrage
    """
    global trading_engine, ai_validator, wallet_connector
    global dex_trader, position_monitor, trading_bot
    
    try:
        # Configuration depuis app.config
        claude_api_key = app.config.get('CLAUDE_API_KEY')
        
        # Initialiser les modules
        trading_engine = TradingEngine()
        ai_validator = AIValidator(claude_api_key)
        wallet_connector = WalletConnector()
        dex_trader = DEXTrader()
        position_monitor = PositionMonitor()
        trading_bot = TradingBot(
            trading_engine=trading_engine,
            ai_validator=ai_validator,
            wallet_connector=wallet_connector,
            dex_trader=dex_trader,
            position_monitor=position_monitor
        )
        
        # Démarrer le monitoring automatique
        position_monitor.start()
        
        print("✅ Système de trading initialisé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'initialisation du système: {e}")
        traceback.print_exc()
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
                'traceback': traceback.format_exc()
            }), 500
    return decorated_function


# ==================== ROUTES SCANNER & ANALYSE ====================

@api.route('/scan/token', methods=['POST'])
@login_required
@handle_errors
def scan_token():
    """
    Scanne et analyse un token crypto
    
    Body: {
        "address": "0x...",
        "chain": "ethereum" | "bsc"
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
    
    # Analyser le token avec votre scanner existant
    # (Intégrez ici votre logique de scanner_core.py)
    token_data = {
        'address': address,
        'chain': chain,
        'name': 'Example Token',
        'symbol': 'EXT',
        'price': 0.0001,
        # Ajoutez vos métriques RSI, Fibonacci, etc.
    }
    
    # Calculer le score de trading
    trading_score = trading_engine.calculate_trading_score(token_data)
    
    return jsonify({
        'success': True,
        'token': token_data,
        'trading_score': trading_score,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/scan/batch', methods=['POST'])
@login_required
@handle_errors
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
            # Analyser chaque token
            token_data = {'address': address, 'chain': chain}
            trading_score = trading_engine.calculate_trading_score(token_data)
            
            results.append({
                'address': address,
                'score': trading_score,
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
def validate_with_ai():
    """
    Valide une opportunité de trading avec l'IA Claude
    
    Body: {
        "token_address": "0x...",
        "token_data": {...},
        "trading_score": {...},
        "action": "BUY" | "SELL"
    }
    """
    data = request.get_json()
    token_data = data.get('token_data', {})
    trading_score = data.get('trading_score', {})
    action = data.get('action', 'BUY')
    
    if not token_data:
        return jsonify({
            'success': False,
            'error': 'Données du token requises'
        }), 400
    
    # Valider avec Claude API
    validation = ai_validator.validate_trade_opportunity(
        token_data=token_data,
        trading_score=trading_score,
        action=action
    )
    
    return jsonify({
        'success': True,
        'validation': validation,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/ai/analyze/market', methods=['POST'])
@login_required
@handle_errors
def analyze_market():
    """
    Analyse du sentiment de marché via IA
    
    Body: {
        "tokens": ["0x...", "0x..."],
        "timeframe": "1h" | "4h" | "1d"
    }
    """
    data = request.get_json()
    tokens = data.get('tokens', [])
    timeframe = data.get('timeframe', '1h')
    
    # Analyse de marché avec IA
    analysis = ai_validator.analyze_market_conditions(tokens, timeframe)
    
    return jsonify({
        'success': True,
        'analysis': analysis,
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES WALLET ====================

@api.route('/wallet/connect', methods=['POST'])
@login_required
@handle_errors
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
        if not address:
            return jsonify({
                'success': False,
                'error': 'Adresse du wallet requise'
            }), 400
        
        success = wallet_connector.connect_web3_wallet(wallet_type, address)
        
    elif wallet_type == 'binance':
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'Clés API Binance requises'
            }), 400
        
        success = wallet_connector.connect_binance(api_key, api_secret)
    
    else:
        return jsonify({
            'success': False,
            'error': 'Type de wallet non supporté'
        }), 400
    
    return jsonify({
        'success': success,
        'wallet_type': wallet_type,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/wallet/balance', methods=['GET'])
@login_required
@handle_errors
def get_wallet_balance():
    """Récupère le solde du wallet connecté"""
    
    balances = wallet_connector.get_balances()
    
    return jsonify({
        'success': True,
        'balances': balances,
        'timestamp': datetime.now().isoformat()
    })


@api.route('/wallet/disconnect', methods=['POST'])
@login_required
@handle_errors
def disconnect_wallet():
    """Déconnecte le wallet actuel"""
    
    wallet_connector.disconnect()
    
    return jsonify({
        'success': True,
        'message': 'Wallet déconnecté',
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES TRADING ====================

@api.route('/trade/execute', methods=['POST'])
@login_required
@handle_errors
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
    
    # Exécuter le trade
    if platform in ['uniswap', 'pancakeswap']:
        if action == 'BUY':
            result = dex_trader.buy_token(
                token_address=token_address,
                amount_in=amount,
                slippage_percent=slippage,
                dex=platform
            )
        else:
            result = dex_trader.sell_token(
                token_address=token_address,
                amount_in=amount,
                slippage_percent=slippage,
                dex=platform
            )
    
    elif platform == 'binance':
        # Trading CEX via Binance
        result = wallet_connector.binance_client.create_market_order(
            symbol=f"{data.get('symbol')}USDT",
            side='BUY' if action == 'BUY' else 'SELL',
            quantity=amount
        )
    
    else:
        return jsonify({
            'success': False,
            'error': 'Plateforme non supportée'
        }), 400
    
    # Si le trade a réussi, ouvrir une position
    if result.get('success'):
        position_id = position_monitor.open_position(
            token_address=token_address,
            action=action,
            entry_price=result.get('price'),
            amount=amount,
            stop_loss_percent=stop_loss,
            take_profit_percent=take_profit
        )
        
        result['position_id'] = position_id
    
    return jsonify(result)


@api.route('/trade/estimate', methods=['POST'])
@login_required
@handle_errors
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
    action = data.get('action')
    token_address = data.get('token_address')
    amount = float(data.get('amount', 0))
    platform = data.get('platform', 'uniswap')
    
    # Estimer le prix
    if action == 'BUY':
        estimate = dex_trader.estimate_buy(
            token_address=token_address,
            amount_in=amount,
            dex=platform
        )
    else:
        estimate = dex_trader.estimate_sell(
            token_address=token_address,
            amount_in=amount,
            dex=platform
        )
    
    return jsonify({
        'success': True,
        'estimate': estimate,
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES POSITIONS ====================

@api.route('/positions/list', methods=['GET'])
@login_required
@handle_errors
def list_positions():
    """Liste toutes les positions ouvertes"""
    
    positions = position_monitor.get_all_positions()
    
    return jsonify({
        'success': True,
        'positions': positions,
        'total': len(positions)
    })


@api.route('/positions/<position_id>', methods=['GET'])
@login_required
@handle_errors
def get_position(position_id):
    """Récupère les détails d'une position"""
    
    position = position_monitor.get_position(position_id)
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Position non trouvée'
        }), 404
    
    return jsonify({
        'success': True,
        'position': position
    })


@api.route('/positions/<position_id>/close', methods=['POST'])
@login_required
@handle_errors
def close_position(position_id):
    """Ferme une position manuellement"""
    
    result = position_monitor.close_position(position_id, reason='manual_close')
    
    return jsonify(result)


@api.route('/positions/<position_id>/update', methods=['PUT'])
@login_required
@handle_errors
def update_position(position_id):
    """
    Modifie les paramètres d'une position (SL/TP)
    
    Body: {
        "stop_loss": 10.0,
        "take_profit": 20.0
    }
    """
    data = request.get_json()
    stop_loss = data.get('stop_loss')
    take_profit = data.get('take_profit')
    
    result = position_monitor.update_position_limits(
        position_id=position_id,
        stop_loss_percent=stop_loss,
        take_profit_percent=take_profit
    )
    
    return jsonify(result)


@api.route('/positions/stats', methods=['GET'])
@login_required
@handle_errors
def positions_stats():
    """Statistiques globales des positions"""
    
    stats = position_monitor.get_statistics()
    
    return jsonify({
        'success': True,
        'stats': stats
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
    data = request.get_json()
    tokens = data.get('tokens', [])
    config = data.get('config', {})
    
    # Démarrer le bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(
        trading_bot.start_auto_trading(
            token_list=tokens,
            max_concurrent_positions=config.get('max_positions', 5),
            risk_per_trade_percent=config.get('risk_per_trade', 2.0),
            min_confidence_score=config.get('min_confidence', 70)
        )
    )
    
    return jsonify(result)


@api.route('/bot/stop', methods=['POST'])
@login_required
@handle_errors
def stop_bot():
    """Arrête le bot de trading automatique"""
    
    trading_bot.stop_auto_trading()
    
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
    
    status = trading_bot.get_status()
    
    return jsonify({
        'success': True,
        'status': status
    })


# ==================== ROUTES MONITORING ====================

@api.route('/monitor/start', methods=['POST'])
@login_required
@handle_errors
def start_monitoring():
    """Démarre le monitoring automatique"""
    
    position_monitor.start()
    
    return jsonify({
        'success': True,
        'message': 'Monitoring démarré'
    })


@api.route('/monitor/stop', methods=['POST'])
@login_required
@handle_errors
def stop_monitoring():
    """Arrête le monitoring automatique"""
    
    position_monitor.stop()
    
    return jsonify({
        'success': True,
        'message': 'Monitoring arrêté'
    })


@api.route('/monitor/alerts', methods=['GET'])
@login_required
@handle_errors
def get_alerts():
    """Récupère toutes les alertes"""
    
    alerts = position_monitor.get_alerts()
    
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
    
    # Récupérer depuis votre database.py
    config = {
        'user_id': user_id,
        'default_slippage': 1.0,
        'default_stop_loss': 10.0,
        'default_take_profit': 20.0,
        'notifications_enabled': True
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
    user_id = session.get('user_id')
    
    # Sauvegarder dans votre database.py
    # db.update_user_config(user_id, data)
    
    return jsonify({
        'success': True,
        'message': 'Configuration mise à jour'
    })


# ==================== ROUTES WEBHOOKS ====================

@api.route('/webhook/price-alert', methods=['POST'])
@handle_errors
def webhook_price_alert():
    """
    Webhook pour les alertes de prix externes
    (ex: TradingView, CoinGecko)
    """
    data = request.get_json()
    
    # Traiter l'alerte
    token_address = data.get('token')
    price = data.get('price')
    alert_type = data.get('type')
    
    # Notifier le position monitor
    position_monitor.process_external_alert(token_address, price, alert_type)
    
    return jsonify({
        'success': True,
        'message': 'Alerte traitée'
    })


# ==================== ROUTES HEALTH CHECK ====================

@api.route('/health', methods=['GET'])
def health_check():
    """Vérifie que l'API est opérationnelle"""
    
    status = {
        'api': 'online',
        'trading_engine': trading_engine is not None,
        'ai_validator': ai_validator is not None,
        'wallet_connector': wallet_connector is not None,
        'dex_trader': dex_trader is not None,
        'position_monitor': position_monitor is not None and position_monitor.is_running,
        'trading_bot': trading_bot is not None,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify({
        'success': True,
        'status': status
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