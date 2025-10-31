"""
Routes API pour le Scan Automatique
Gestion du cache des tokens et du service de scan
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime


# Blueprint pour les routes auto-scan
auto_scan_api = Blueprint('auto_scan', __name__, url_prefix='/api/auto-scan')

# Instances globales (à initialiser dans app.py)
auto_scanner = None
scheduler = None
mongodb = None
limiter = None  # Flask-Limiter instance (injected from app.py)


def login_required(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Authentification requise'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Décorateur pour vérifier les droits admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentification requise'
            }), 401
        
        if not mongodb or not mongodb.is_admin(user_id):
            return jsonify({
                'success': False,
                'error': 'Droits administrateur requis'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


# ==================== ROUTES PUBLIQUES ====================

@auto_scan_api.route('/status', methods=['GET'])
def get_status():
    """
    Récupère le statut du service de scan automatique

    NOTE: Cette route est exemptée du rate limiting car elle est
    pollée fréquemment par le frontend (toutes les 2s) pour afficher
    le statut en temps réel.
    """
    if not auto_scanner:
        return jsonify({
            'success': False,
            'error': 'Service non initialisé'
        }), 503

    status = auto_scanner.get_status()

    return jsonify({
        'success': True,
        'status': status,
        'timestamp': datetime.now().isoformat()
    })


@auto_scan_api.route('/tokens/recent', methods=['GET'])
def get_recent_tokens():
    """
    Récupère les tokens récents du cache (24h)
    
    Query params:
        - limit: nombre de tokens (défaut: 50, max: 200)
        - is_safe: true/false pour filtrer
        - min_liquidity: liquidité minimale
        - chain: blockchain (ethereum, bsc, solana, etc.)
    """
    try:
        # Paramètres
        limit = min(int(request.args.get('limit', 50)), 200)
        
        # Filtres optionnels
        filters = {}
        if request.args.get('is_safe'):
            filters['is_safe'] = request.args.get('is_safe').lower() == 'true'
        
        if request.args.get('min_liquidity'):
            filters['min_liquidity'] = float(request.args.get('min_liquidity'))
        
        if request.args.get('chain'):
            filters['chain'] = request.args.get('chain').lower()
        
        # Récupérer les tokens du cache
        tokens = auto_scanner.get_recent_tokens(limit=limit, filters=filters)
        
        return jsonify({
            'success': True,
            'tokens': tokens,
            'count': len(tokens),
            'filters': filters,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auto_scan_api.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """Récupère les statistiques du cache"""
    if not mongodb:
        return jsonify({
            'success': False,
            'error': 'MongoDB non initialisé'
        }), 503
    
    stats = mongodb.get_cache_stats()
    
    return jsonify({
        'success': True,
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    })


# ==================== ROUTES ADMIN ====================

@auto_scan_api.route('/start', methods=['POST'])
@admin_required
def start_auto_scan():
    """Démarre le service de scan automatique (Admin)"""
    if not auto_scanner:
        return jsonify({
            'success': False,
            'error': 'Service non initialisé'
        }), 503
    
    if auto_scanner.start():
        return jsonify({
            'success': True,
            'message': 'Service de scan automatique démarré',
            'status': auto_scanner.get_status()
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Échec du démarrage (déjà en cours ?)'
        }), 400


@auto_scan_api.route('/stop', methods=['POST'])
@admin_required
def stop_auto_scan():
    """Arrête le service de scan automatique (Admin)"""
    if not auto_scanner:
        return jsonify({
            'success': False,
            'error': 'Service non initialisé'
        }), 503
    
    auto_scanner.stop()
    
    return jsonify({
        'success': True,
        'message': 'Service de scan automatique arrêté',
        'status': auto_scanner.get_status()
    })


@auto_scan_api.route('/config', methods=['GET', 'PUT'])
@admin_required
def manage_config():
    """Récupère ou modifie la configuration du scan automatique (Admin)"""
    if not auto_scanner:
        return jsonify({
            'success': False,
            'error': 'Service non initialisé'
        }), 503
    
    if request.method == 'GET':
        # Récupérer la config actuelle
        return jsonify({
            'success': True,
            'config': {
                'scan_interval': auto_scanner.scan_interval,
                'tokens_per_scan': auto_scanner.tokens_per_scan
            }
        })
    
    elif request.method == 'PUT':
        # Modifier la config
        data = request.get_json()
        
        scan_interval = data.get('scan_interval')
        tokens_per_scan = data.get('tokens_per_scan')
        
        # Validation
        if scan_interval is not None:
            if scan_interval < 60 or scan_interval > 3600:
                return jsonify({
                    'success': False,
                    'error': 'scan_interval doit être entre 60 et 3600 secondes'
                }), 400
        
        if tokens_per_scan is not None:
            if tokens_per_scan < 1 or tokens_per_scan > 50:
                return jsonify({
                    'success': False,
                    'error': 'tokens_per_scan doit être entre 1 et 50'
                }), 400
        
        # Appliquer les changements
        if auto_scanner.update_config(
            scan_interval=scan_interval,
            tokens_per_scan=tokens_per_scan
        ):
            return jsonify({
                'success': True,
                'message': 'Configuration mise à jour',
                'config': {
                    'scan_interval': auto_scanner.scan_interval,
                    'tokens_per_scan': auto_scanner.tokens_per_scan
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Échec de la mise à jour'
            }), 500


@auto_scan_api.route('/force-scan', methods=['POST'])
@admin_required
def force_scan():
    """Force un scan immédiat (Admin)"""
    if not auto_scanner:
        return jsonify({
            'success': False,
            'error': 'Service non initialisé'
        }), 503
    
    result = auto_scanner.force_scan()
    
    return jsonify(result)


@auto_scan_api.route('/cache/clear', methods=['POST'])
@admin_required
def clear_cache():
    """Vide complètement le cache (Admin)"""
    if not mongodb:
        return jsonify({
            'success': False,
            'error': 'MongoDB non initialisé'
        }), 503
    
    deleted_count = mongodb.clear_cache()
    
    return jsonify({
        'success': True,
        'message': f'{deleted_count} tokens supprimés du cache',
        'deleted_count': deleted_count
    })


# ==================== ROUTES UTILISATEUR ====================

@auto_scan_api.route('/search', methods=['POST'])
@login_required
def search_and_cache():
    """
    Recherche un token spécifique, l'analyse et l'ajoute au cache
    
    Body: {
        "address": "0x...",
        "chain": "ethereum" | "bsc" | "solana"
    }
    """
    try:
        data = request.get_json()
        address = data.get('address')
        chain = data.get('chain', 'ethereum')
        
        if not address:
            return jsonify({
                'success': False,
                'error': 'Adresse du token requise'
            }), 400
        
        # Vérifier si déjà dans le cache
        cached_tokens = mongodb.get_cached_tokens(limit=1, filters={
            'chain': chain
        })
        
        for token in cached_tokens:
            if token['address'].lower() == address.lower():
                return jsonify({
                    'success': True,
                    'token': token,
                    'from_cache': True,
                    'message': 'Token trouvé dans le cache'
                })
        
        # Si pas dans le cache, analyser
        if not auto_scanner or not auto_scanner.scanner:
            return jsonify({
                'success': False,
                'error': 'Scanner non disponible'
            }), 503
        
        # Créer token_info
        token_info = {
            'address': address,
            'chain': chain,
            'url': f"https://dexscreener.com/{chain}/{address}",
            'icon': '',
            'description': '',
            'twitter': '',
            'links': []
        }
        
        # Analyser
        token_data = auto_scanner.scanner.analyze_token(token_info)
        
        if not token_data:
            return jsonify({
                'success': False,
                'error': 'Échec de l\'analyse du token'
            }), 500
        
        # Ajouter trading signal
        if auto_scanner.trading_engine:
            signal = auto_scanner.trading_engine.analyze_token(token_data)
            token_data['trading_signal'] = auto_scanner.trading_engine.signal_to_dict(signal)
        
        # Ajouter au cache
        mongodb.add_token_to_cache(token_data)
        
        return jsonify({
            'success': True,
            'token': token_data,
            'from_cache': False,
            'message': 'Token analysé et ajouté au cache'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== INITIALISATION ====================

def register_auto_scan_routes(app, scanner_service, scheduler_service, mongodb_manager, rate_limiter=None):
    """
    Enregistre les routes et initialise les services

    Args:
        app: Instance Flask
        scanner_service: Instance AutoScannerService
        scheduler_service: Instance SchedulerService
        mongodb_manager: Instance MongoDBManager
        rate_limiter: Instance Flask-Limiter (optionnel)
    """
    global auto_scanner, scheduler, mongodb, limiter

    auto_scanner = scanner_service
    scheduler = scheduler_service
    mongodb = mongodb_manager
    limiter = rate_limiter

    # Enregistrer le blueprint
    app.register_blueprint(auto_scan_api)

    # Exempter la route /status du rate limiting (pollée toutes les 2s)
    if limiter:
        # Exempter /api/auto-scan/status (très fréquent, lecture seule, pas dangereux)
        limiter.exempt(get_status)
        # Exempter /api/auto-scan/cache/stats (lecture seule, stats publiques)
        limiter.exempt(get_cache_stats)
        print("✅ Routes auto-scan exemptées du rate limiting: /status, /cache/stats")

    print("✅ Routes auto-scan enregistrées")