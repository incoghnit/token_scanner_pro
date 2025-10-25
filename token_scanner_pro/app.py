"""
Serveur Flask pour l'interface web du Token Scanner Pro
✅ Avec système d'authentification
✅ Routes auto-scan
✅ MongoDB + Cache
✅ Trading system
"""

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from scanner_core import TokenScanner
from database import Database
import json
from datetime import datetime
import threading
import secrets
from functools import wraps
import os
import re
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ==================== INPUT VALIDATION HELPERS ====================

def validate_email(email: str) -> bool:
    """Valide le format d'un email"""
    if not email or len(email) > 255:
        return False
    # RFC 5322 simplified regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> tuple[bool, str]:
    """Valide un nom d'utilisateur
    Returns: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores and hyphens"
    return True, ""

def validate_password(password: str) -> tuple[bool, str]:
    """Valide un mot de passe
    Returns: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""

def validate_token_address(address: str, chain: str = None) -> bool:
    """Valide une adresse de token
    Basic validation - can be extended for chain-specific validation
    """
    if not address or not isinstance(address, str):
        return False
    # Remove whitespace
    address = address.strip()
    # Ethereum/BSC/Polygon addresses (0x + 40 hex chars)
    if chain in ['ethereum', 'bsc', 'polygon', 'arbitrum', 'base']:
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))
    # Solana addresses (base58, 32-44 chars)
    elif chain == 'solana':
        return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))
    # Generic validation if chain not specified
    else:
        # Accept both Ethereum-style and Solana-style addresses
        eth_pattern = r'^0x[a-fA-F0-9]{40}$'
        sol_pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
        return bool(re.match(eth_pattern, address) or re.match(sol_pattern, address))

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize a string input by removing dangerous characters"""
    if not value or not isinstance(value, str):
        return ""
    # Remove null bytes and limit length
    sanitized = value.replace('\x00', '')[:max_length]
    return sanitized.strip()

app = Flask(__name__)

# Configuration sécurisée
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
if not os.getenv('SECRET_KEY'):
    print("⚠️ WARNING: SECRET_KEY not set in .env - using temporary key (sessions will be lost on restart)")

# CORS configuration sécurisée
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app,
     supports_credentials=True,
     origins=allowed_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# Rate Limiter configuration - Protection contre attaques brute force
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production: redis://localhost:6379
    strategy="fixed-window"
)

# Configuration
app.config['CLAUDE_API_KEY'] = os.getenv('CLAUDE_API_KEY')
app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')
app.config['FLASK_ENV'] = os.getenv('FLASK_ENV', 'development')
app.config['FLASK_DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# ==================== APPLICATION STATE ====================
# NOTE: In production with multiple workers, use Redis or MongoDB for shared state
# This implementation uses thread locks for single-server deployments

import threading as thread_module

# Database instance (thread-safe)
db = Database()

# Scanner instance for news & search APIs (separate from scan state)
scanner = TokenScanner()

# Scanner state with thread safety
_scanner_lock = thread_module.Lock()
_scanner_state = {
    'scanner': None,
    'scan_in_progress': False,
    'current_scan_results': None,
    'last_scan_timestamp': None
}

def get_scanner_state(key: str):
    """Thread-safe getter for scanner state"""
    with _scanner_lock:
        return _scanner_state.get(key)

def set_scanner_state(key: str, value):
    """Thread-safe setter for scanner state"""
    with _scanner_lock:
        _scanner_state[key] = value

def update_scanner_state(**kwargs):
    """Thread-safe bulk update for scanner state"""
    with _scanner_lock:
        _scanner_state.update(kwargs)

# ==================== IMPORTS POUR AUTO-SCAN ====================
try:
    from mongodb_manager import MongoDBManager
    from auto_scanner_service import AutoScannerService
    from scheduler_service import SchedulerService
    from auto_scan_routes import register_auto_scan_routes

    # Initialiser les services avec configuration depuis .env
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_manager = MongoDBManager(connection_string=mongodb_uri)

    scan_interval = int(os.getenv('AUTO_SCAN_INTERVAL', 300))
    tokens_per_scan = int(os.getenv('TOKENS_PER_SCAN', 10))

    auto_scanner = AutoScannerService(
        mongodb=mongodb_manager,
        scan_interval=scan_interval,
        tokens_per_scan=tokens_per_scan
    )
    scheduler = SchedulerService()

    # Initialiser les modules du scanner avec Nitter URL depuis .env
    nitter_url = os.getenv('NITTER_URL', 'http://localhost:8080')
    auto_scanner.initialize_modules(nitter_url=nitter_url)

    # Enregistrer les routes auto-scan
    register_auto_scan_routes(app, auto_scanner, scheduler, mongodb_manager)

    # Auto-start scanner si configuré
    if os.getenv('AUTO_START_SCANNER', 'false').lower() == 'true':
        auto_scanner.start()
        print("✅ Auto-scanner démarré automatiquement")

    print("✅ Services auto-scan initialisés et routes enregistrées")

except ImportError as e:
    print(f"⚠️ Auto-scan non disponible: {e}")
    mongodb_manager = None
    auto_scanner = None
    scheduler = None
except Exception as e:
    print(f"❌ Erreur initialisation auto-scan: {e}")
    mongodb_manager = None
    auto_scanner = None
    scheduler = None

# ==================== SYSTÈME D'ALERTES ====================
try:
    from alert_system import AlertSystem

    # Initialiser le système d'alertes avec configuration depuis .env
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')

    alert_system = AlertSystem(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password
    )

    # Démarrer la surveillance si configuré
    if os.getenv('ENABLE_ALERTS', 'false').lower() == 'true':
        if smtp_user and smtp_password:
            alert_system.start_monitoring()
            print("✅ Système d'alertes démarré automatiquement")
        else:
            print("⚠️ Alertes activées mais SMTP non configuré (manque SMTP_USER/SMTP_PASSWORD)")
    else:
        print("ℹ️ Système d'alertes initialisé mais non démarré (ENABLE_ALERTS=false)")

    print("✅ Système d'alertes initialisé")

except ImportError as e:
    print(f"⚠️ Système d'alertes non disponible: {e}")
    alert_system = None
except Exception as e:
    print(f"❌ Erreur initialisation système d'alertes: {e}")
    alert_system = None

# ==================== DÉCORATEURS ====================

def admin_required(f):
    """Décorateur pour vérifier si l'utilisateur est admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not db.is_admin(user_id):
            return jsonify({
                "success": False,
                "error": "Accès non autorisé - Admin requis"
            }), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES PRINCIPALES ====================

@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')

@app.route('/favorites')
def favorites_page():
    """Page des favoris"""
    return render_template('favorites.html')

@app.route('/admin')
def admin_page():
    """Page admin - Accessible uniquement aux admins"""
    user_id = session.get('user_id')
    
    if not user_id:
        return render_template('error.html', 
                             error="Accès refusé", 
                             message="Vous devez être connecté pour accéder à cette page"), 403
    
    if not db.is_admin(user_id):
        return render_template('error.html', 
                             error="Accès refusé", 
                             message="Vous n'avez pas les permissions nécessaires pour accéder à cette page"), 403
    
    return render_template('admin.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard de trading"""
    return render_template('trading_dashboard.html')

# Auto-scan route removed - feature not useful

@app.route('/alerts')
def alerts_page():
    """Page Alertes Premium"""
    return render_template('alerts.html')

@app.route('/settings')
def settings_page():
    """Page Paramètres"""
    return render_template('settings.html')

@app.route('/premium')
def premium_page():
    """Page Premium/Pricing"""
    return render_template('premium.html')

# ==================== ROUTES API AUTH ====================

@app.route('/api/me', methods=['GET'])
def get_current_user():
    """Récupère les infos de l'utilisateur connecté"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "authenticated": False
        })
    
    user = db.get_user_by_id(user_id)
    
    if user:
        return jsonify({
            "success": True,
            "authenticated": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_admin": user.get('is_admin', False),
                "is_premium": user.get('is_premium', False)
            }
        })
    else:
        return jsonify({
            "success": False,
            "authenticated": False
        })

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
    """Connexion utilisateur"""
    data = request.get_json()
    email = sanitize_string(data.get('email', ''), 255)
    password = data.get('password', '')

    # Validate inputs
    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email et mot de passe requis"
        }), 400

    if not validate_email(email):
        return jsonify({
            "success": False,
            "error": "Format d'email invalide"
        }), 400
    
    user = db.authenticate_user(email, password)

    if user:
        # SECURITY: Regenerate session ID to prevent session fixation attacks
        # Clear old session to force Flask to create a new session ID
        session.clear()

        # Set new session data - Flask automatically generates new session ID
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = False  # Session expires when browser closes
        session.modified = True  # Force session update

        return jsonify({
            "success": True,
            "message": "Connexion réussie",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_admin": user.get('is_admin', False),
                "is_premium": user.get('is_premium', False)
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "Email ou mot de passe incorrect"
        }), 401

@app.route('/api/register', methods=['POST'])
@limiter.limit("3 per hour")  # Max 3 registrations per hour
def register():
    """Inscription d'un nouvel utilisateur"""
    data = request.get_json()
    username = sanitize_string(data.get('username', ''), 50)
    email = sanitize_string(data.get('email', ''), 255)
    password = data.get('password', '')

    # Validate all inputs
    if not username or not email or not password:
        return jsonify({
            "success": False,
            "error": "Tous les champs sont requis"
        }), 400

    # Validate email format
    if not validate_email(email):
        return jsonify({
            "success": False,
            "error": "Format d'email invalide"
        }), 400

    # Validate username
    username_valid, username_error = validate_username(username)
    if not username_valid:
        return jsonify({
            "success": False,
            "error": username_error
        }), 400

    # Validate password strength
    password_valid, password_error = validate_password(password)
    if not password_valid:
        return jsonify({
            "success": False,
            "error": password_error
        }), 400
    
    user_id = db.create_user(username, email, password)

    if user_id:
        # SECURITY: Regenerate session ID to prevent session fixation attacks
        session.clear()

        session['user_id'] = user_id
        session['username'] = username
        session.permanent = False
        session.modified = True

        return jsonify({
            "success": True,
            "message": "Compte créé avec succès",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "is_admin": False,
                "is_premium": False
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "Cet email est déjà utilisé"
        }), 400

@app.route('/api/logout', methods=['POST'])
def logout():
    """Déconnexion"""
    session.clear()
    return jsonify({
        "success": True,
        "message": "Déconnexion réussie"
    })

# ==================== ROUTES API SCAN ====================

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Démarre un nouveau scan"""
    if get_scanner_state('scan_in_progress'):
        return jsonify({
            "success": False,
            "error": "Un scan est déjà en cours"
        }), 400
    
    data = request.json or {}
    max_tokens = data.get('max_tokens', 10)
    nitter_url = data.get('nitter_url', os.getenv('NITTER_URL', 'http://localhost:8080'))
    
    user_id = session.get('user_id')
    if not user_id:
        max_tokens = min(max_tokens, 5)
    
    if max_tokens < 1 or max_tokens > 50:
        return jsonify({
            "success": False,
            "error": "Le nombre de tokens doit être entre 1 et 50"
        }), 400
    
    def run_scan():
        try:
            set_scanner_state('scan_in_progress', True)
            scanner = TokenScanner(nitter_url=nitter_url)
            set_scanner_state('scanner', scanner)

            # FIXED: scan_tokens() doesn't accept chain_filter parameter
            results = scanner.scan_tokens(max_tokens=max_tokens)

            update_scanner_state(
                current_scan_results=results,
                scan_in_progress=False,
                last_scan_timestamp=datetime.now().isoformat()
            )

            # Sauvegarder pour l'utilisateur si connecté
            if user_id and results.get('success'):
                db.save_scan_history(user_id, results)
                db.update_scan_count(user_id)

            # Stocker TOUS les tokens scannés dans la BDD avec rotation FIFO (max 200)
            # Cela permet d'avoir un cache global indépendant des utilisateurs
            print(f"🔍 DEBUG - Scan results success: {results.get('success')}")
            print(f"🔍 DEBUG - Scan results count: {len(results.get('results', []))}")

            if results.get('success') and results.get('results'):
                tokens_to_store = results.get('results', [])
                print(f"🔍 DEBUG - Tokens to store: {len(tokens_to_store)}")
                stored_count = db.add_scanned_tokens_batch(tokens_to_store)
                print(f"💾 {stored_count}/{len(tokens_to_store)} tokens stockés dans la BDD")

                # Log du nombre total de tokens en BDD
                total_in_db = db.get_scanned_tokens_count()
                print(f"📊 Total tokens en BDD: {total_in_db}/{db.MAX_SCANNED_TOKENS}")
            else:
                print(f"⚠️  DEBUG - Tokens NOT saved. Success={results.get('success')}, Results empty={not results.get('results')}")

        except Exception as e:
            print(f"❌ Erreur dans run_scan: {e}")
            update_scanner_state(
                scan_in_progress=False,
                current_scan_results={
                    "success": False,
                    "error": str(e)
                }
            )

    set_scanner_state('scan_in_progress', True)
    thread = threading.Thread(target=run_scan)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Scan démarré"
    })

@app.route('/api/scan/progress', methods=['GET'])
def scan_progress():
    """Récupère la progression du scan"""
    scan_in_progress = get_scanner_state('scan_in_progress')
    current_scan_results = get_scanner_state('current_scan_results')

    if scan_in_progress:
        percentage = 50  # Estimation
        return jsonify({
            "success": True,
            "in_progress": True,  # FIXED: Frontend expects in_progress not scanning
            "scanning": True,
            "message": "Scan en cours...",
            "progress": {
                "percentage": percentage,
                "message": "Scan en cours..."
            }
        })
    elif current_scan_results:
        return jsonify({
            "success": True,
            "in_progress": False,
            "scanning": False,
            "message": "Scan terminé",
            "progress": {
                "percentage": 100,
                "message": "Scan terminé"
            }
        })
    else:
        return jsonify({
            "success": True,
            "in_progress": False,
            "scanning": False,
            "message": "Aucun scan en cours",
            "progress": {
                "percentage": 0,
                "message": "Aucun scan en cours"
            }
        })

@app.route('/api/scan/results', methods=['GET'])
def scan_results():
    """Récupère les résultats du dernier scan"""
    current_scan_results = get_scanner_state('current_scan_results')
    last_scan_timestamp = get_scanner_state('last_scan_timestamp')

    if current_scan_results:
        return jsonify({
            "success": True,
            "results": current_scan_results.get('results', []),
            "total_analyzed": current_scan_results.get('total_analyzed', 0),
            "safe_count": current_scan_results.get('safe_count', 0),
            "dangerous_count": current_scan_results.get('dangerous_count', 0),
            "last_scan_timestamp": last_scan_timestamp
        })
    else:
        return jsonify({
            "success": False,
            "error": "Aucun résultat disponible"
        }), 404

@app.route('/api/scan/status', methods=['GET'])
def scan_status():
    """Récupère le statut du scan"""
    return jsonify({
        "success": True,
        "scanning": get_scanner_state('scan_in_progress'),
        "results": get_scanner_state('current_scan_results')
    })

# ==================== ROUTES API TOKENS SCANNÉS ====================

@app.route('/api/scanned-tokens', methods=['GET'])
def get_scanned_tokens_api():
    """Récupère les tokens scannés depuis la BDD (cache global)"""
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))
        chain = request.args.get('chain')
        safe_only = request.args.get('safe_only', 'false').lower() == 'true'

        tokens = db.get_scanned_tokens(limit=limit, offset=offset, chain=chain, safe_only=safe_only)
        total = db.get_scanned_tokens_count(chain=chain)

        return jsonify({
            "success": True,
            "tokens": tokens,
            "total": total,
            "limit": limit,
            "offset": offset,
            "max_capacity": db.MAX_SCANNED_TOKENS
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/scanned-tokens/<chain>/<address>', methods=['GET'])
def get_scanned_token_api(chain, address):
    """Récupère un token scanné spécifique"""
    try:
        token = db.get_scanned_token(address, chain)

        if token:
            return jsonify({
                "success": True,
                "token": token
            })
        else:
            return jsonify({
                "success": False,
                "error": "Token non trouvé"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/scanned-tokens/stats', methods=['GET'])
def get_scanned_tokens_stats():
    """Statistiques sur les tokens scannés"""
    try:
        total = db.get_scanned_tokens_count()
        safe_tokens = db.get_scanned_tokens(limit=1000, safe_only=True)
        safe_count = len(safe_tokens)

        return jsonify({
            "success": True,
            "stats": {
                "total_tokens": total,
                "safe_tokens": safe_count,
                "risky_tokens": total - safe_count,
                "capacity": db.MAX_SCANNED_TOKENS,
                "usage_percent": round((total / db.MAX_SCANNED_TOKENS) * 100, 1)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== ROUTES API FAVORIS ====================

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Récupère les favoris de l'utilisateur"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401
    
    favorites = db.get_user_favorites(user_id)
    
    return jsonify({
        "success": True,
        "favorites": favorites
    })

@app.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    """Ajoute un token aux favoris"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401

    data = request.get_json()
    token_address = sanitize_string(data.get('token_address', ''), 100)
    token_chain = sanitize_string(data.get('token_chain', 'ethereum'), 50).lower()
    token_data = data.get('token_data', {})

    # Validate inputs
    if not token_address:
        return jsonify({
            "success": False,
            "error": "Adresse du token requise"
        }), 400

    # Validate token address format
    if not validate_token_address(token_address, token_chain):
        return jsonify({
            "success": False,
            "error": "Format d'adresse de token invalide"
        }), 400

    # Validate chain
    valid_chains = ['ethereum', 'bsc', 'polygon', 'arbitrum', 'base', 'solana']
    if token_chain not in valid_chains:
        return jsonify({
            "success": False,
            "error": f"Blockchain non supportée. Chains valides: {', '.join(valid_chains)}"
        }), 400
    
    success = db.add_favorite(user_id, token_address, token_chain, token_data)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Token ajouté aux favoris"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Token déjà dans les favoris"
        }), 400

@app.route('/api/favorites/remove', methods=['POST'])
def remove_favorite():
    """Retire un token des favoris"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401

    data = request.get_json()
    token_address = sanitize_string(data.get('token_address', ''), 100)
    token_chain = sanitize_string(data.get('token_chain', 'ethereum'), 50).lower()

    # Validate inputs
    if not token_address:
        return jsonify({
            "success": False,
            "error": "Adresse du token requise"
        }), 400

    if not validate_token_address(token_address, token_chain):
        return jsonify({
            "success": False,
            "error": "Format d'adresse de token invalide"
        }), 400
    
    success = db.remove_favorite(user_id, token_address, token_chain)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Token retiré des favoris"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Token non trouvé dans les favoris"
        }), 400

# ==================== ROUTES API ADMIN ====================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Récupère les statistiques globales"""
    stats = db.get_global_stats()
    all_users = db.get_all_users()
    total_scans = sum(user.get('scan_count', 0) for user in all_users)
    
    stats['total_scans'] = total_scans
    stats['new_users_today'] = 0
    
    return jsonify({
        "success": True,
        "stats": stats
    })

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_admin_users():
    """Récupère la liste des utilisateurs"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = (page - 1) * limit
    
    users = db.get_all_users(limit=limit, offset=offset)
    total = db.get_users_count()
    
    return jsonify({
        "success": True,
        "users": users,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    })

# ==================== ROUTES HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérifie que l'API fonctionne"""
    return jsonify({
        "success": True,
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "scan_in_progress": get_scanner_state('scan_in_progress'),
        "authenticated": session.get('user_id') is not None,
        "last_scan": get_scanner_state('last_scan_timestamp'),
        "auto_scan_available": auto_scanner is not None
    })

# ==================== GESTION DES ERREURS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint non trouvé"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Erreur serveur interne"
    }), 500

# ==================== ANALYSE IA ====================

@app.route('/api/analyze-token', methods=['POST'])
def analyze_token_with_ai():
    """Analyse un token avec Claude IA"""
    try:
        data = request.get_json()
        address = sanitize_string(data.get('address', ''), 100)
        chain = sanitize_string(data.get('chain', ''), 50).lower()
        token_data = data.get('token_data', {})

        # Validate inputs
        if not address or not chain:
            return jsonify({
                "success": False,
                "error": "Adresse et chaîne requises"
            }), 400

        if not validate_token_address(address, chain):
            return jsonify({
                "success": False,
                "error": "Format d'adresse de token invalide"
            }), 400

        valid_chains = ['ethereum', 'bsc', 'polygon', 'arbitrum', 'base', 'solana']
        if chain not in valid_chains:
            return jsonify({
                "success": False,
                "error": f"Blockchain non supportée"
            }), 400

        # Import du trading validator
        try:
            from trading_validator import TradingValidator
            from trading_engine import TradingEngine

            # Créer un signal basique si pas de données complètes
            engine = TradingEngine()

            # Si on a toutes les données, analyser complètement
            if token_data.get('market') and token_data.get('security'):
                signal = engine.analyze_token(token_data)
                validator = TradingValidator()
                result = validator.validate_signal(signal, token_data)

                # Formater la réponse
                analysis_text = f"""
## 🎯 RECOMMANDATION: {result['final_action']}
Confiance: {result['adjusted_confidence']:.1f}%

{result.get('overall_verdict', '')}

### ⚠️ Avertissements:
"""
                for warning in result.get('ai_warnings', []):
                    analysis_text += f"• {warning}\n"

                analysis_text += "\n### 💡 Recommandations:\n"
                for rec in result.get('ai_recommendations', []):
                    analysis_text += f"• {rec}\n"

                return jsonify({
                    "success": True,
                    "analysis": analysis_text,
                    "action": result['final_action'],
                    "confidence": result['adjusted_confidence']
                })

            else:
                # Analyse simple si données incomplètes
                return jsonify({
                    "success": True,
                    "analysis": f"""
## 📊 Analyse du Token
**Adresse:** `{address}`
**Blockchain:** {chain.upper()}

⚠️ **Données insuffisantes pour une analyse complète.**

Pour obtenir une analyse IA approfondie, le scanner doit d'abord récupérer les données de marché et de sécurité du token.

### Actions recommandées:
• Lancez un scan complet du token via le scanner principal
• Attendez que les données de DexScreener et GoPlus soient récupérées
• Relancez l'analyse IA avec les données complètes
                    """,
                    "action": "HOLD",
                    "confidence": 50
                })

        except ValueError as e:
            # Clé API manquante
            return jsonify({
                "success": False,
                "error": "Configuration IA manquante. Vérifiez ANTHROPIC_API_KEY dans .env"
            }), 500

        except Exception as e:
            print(f"Erreur analyse IA: {e}")
            return jsonify({
                "success": False,
                "error": f"Erreur lors de l'analyse: {str(e)}"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== ACTUALITÉS CRYPTO ====================

@app.route('/api/news/crypto', methods=['GET'])
def get_crypto_news():
    """Récupère les actualités crypto avec cache de 30 minutes"""
    try:
        limit = request.args.get('limit', 10, type=int)
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        result = scanner.fetch_crypto_news(limit=limit, force_refresh=force_refresh)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== RECHERCHE TOKEN ====================

@app.route('/api/token/search', methods=['GET'])
def search_token():
    """Recherche un token sur CoinMarketCap"""
    try:
        query = request.args.get('query', '').strip()
        by_symbol = request.args.get('by_symbol', 'true').lower() == 'true'

        if not query:
            return jsonify({
                "success": False,
                "error": "Query parameter required"
            }), 400

        result = scanner.search_token_info(query=query, by_symbol=by_symbol)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== DÉMARRAGE ====================

if __name__ == '__main__':
    import socket
    from api_routes import register_api_routes
    
    # Enregistrer les routes API supplémentaires (trading, etc.)
    try:
        register_api_routes(app)
    except Exception as e:
        print(f"⚠️ Routes API trading non disponibles: {e}")
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║   TOKEN SCANNER PRO - UX PREMIUM + AUTO-SCAN             ║
    ║                                                           ║
    ║   🌐 Accès local:    http://localhost:5000               ║
    ║   🌐 Accès réseau:   http://{local_ip}:5000              ║
    ║                                                           ║
    ║   ✅ Système d'authentification activé                    ║
    ║   ✅ Auto-scan + Cache MongoDB activé                     ║
    ║   ✅ Favoris + Historique activés                         ║
    ║   ✅ Routes API complètes                                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # SECURITY: Never use debug=True in production
    # Use FLASK_DEBUG=true in .env for development only
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    if debug_mode:
        print("⚠️  WARNING: Running in DEBUG mode - NOT for production!")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode,
        threaded=True
    )