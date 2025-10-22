"""
Serveur Flask pour l'interface web du Token Scanner Pro
✅ Avec système d'authentification
✅ Routes auto-scan
✅ MongoDB + Cache
✅ Trading system
"""

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from scanner_core import TokenScanner
from database import Database
import json
from datetime import datetime
import threading
import secrets
from functools import wraps
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

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

# Configuration
app.config['CLAUDE_API_KEY'] = os.getenv('CLAUDE_API_KEY')
app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')
app.config['FLASK_ENV'] = os.getenv('FLASK_ENV', 'development')
app.config['FLASK_DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Instances globales
db = Database()
scanner = None
scan_in_progress = False
current_scan_results = None
last_scan_timestamp = None

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

@app.route('/auto-scan')
def auto_scan_page():
    """Page Auto-Scan 24/7"""
    return render_template('auto_scan.html')

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
def login():
    """Connexion utilisateur"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email et mot de passe requis"
        }), 400
    
    user = db.authenticate_user(email, password)
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        
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
def register():
    """Inscription d'un nouvel utilisateur"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({
            "success": False,
            "error": "Tous les champs sont requis"
        }), 400
    
    if len(password) < 6:
        return jsonify({
            "success": False,
            "error": "Le mot de passe doit contenir au moins 6 caractères"
        }), 400
    
    user_id = db.create_user(username, email, password)
    
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        
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
    global scanner, scan_in_progress, current_scan_results, last_scan_timestamp
    
    if scan_in_progress:
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
        global scanner, scan_in_progress, current_scan_results, last_scan_timestamp
        try:
            scan_in_progress = True
            scanner = TokenScanner(nitter_url=nitter_url)
            current_scan_results = scanner.scan_tokens(max_tokens=max_tokens, chain_filter="solana")
            scan_in_progress = False
            last_scan_timestamp = datetime.now().isoformat()
            
            if user_id and current_scan_results.get('success'):
                db.save_scan_history(user_id, current_scan_results)
                db.update_scan_count(user_id)
                
        except Exception as e:
            scan_in_progress = False
            current_scan_results = {
                "success": False,
                "error": str(e)
            }
    
    scan_in_progress = True
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
    global scan_in_progress, current_scan_results
    
    if scan_in_progress:
        percentage = 50  # Estimation
        return jsonify({
            "success": True,
            "scanning": True,
            "progress": {
                "percentage": percentage,
                "message": "Scan en cours..."
            }
        })
    elif current_scan_results:
        return jsonify({
            "success": True,
            "scanning": False,
            "progress": {
                "percentage": 100,
                "message": "Scan terminé"
            }
        })
    else:
        return jsonify({
            "success": True,
            "scanning": False,
            "progress": {
                "percentage": 0,
                "message": "Aucun scan en cours"
            }
        })

@app.route('/api/scan/results', methods=['GET'])
def scan_results():
    """Récupère les résultats du dernier scan"""
    global current_scan_results, last_scan_timestamp
    
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
    global scan_in_progress, current_scan_results
    
    return jsonify({
        "success": True,
        "scanning": scan_in_progress,
        "results": current_scan_results
    })

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
    token_address = data.get('token_address')
    token_chain = data.get('token_chain', 'ethereum')
    token_data = data.get('token_data', {})
    
    if not token_address:
        return jsonify({
            "success": False,
            "error": "Adresse du token requise"
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
    token_address = data.get('token_address')
    token_chain = data.get('token_chain', 'ethereum')
    
    if not token_address:
        return jsonify({
            "success": False,
            "error": "Adresse du token requise"
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
        "scan_in_progress": scan_in_progress,
        "authenticated": session.get('user_id') is not None,
        "last_scan": last_scan_timestamp,
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
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )