"""
Serveur Flask pour l'interface web du Token Scanner
Avec système d'authentification et favoris
Version améliorée avec recherche et timestamps
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

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

# Configuration
app.config['CLAUDE_API_KEY'] = 'votre_clé_claude_api'

# Instances globales
db = Database()
scanner = None
scan_in_progress = False
current_scan_results = None
last_scan_timestamp = None

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

@app.route('/api/admin/user/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Active/Désactive un utilisateur"""
    admin_id = session.get('user_id')
    success = db.toggle_user_status(user_id)
    
    if success:
        db.log_admin_action(admin_id, "toggle_status", user_id, 
                          f"Changement statut utilisateur", 
                          request.remote_addr)
    
    return jsonify({
        "success": success,
        "message": "Statut modifié" if success else "Erreur"
    })

@app.route('/api/admin/user/<int:user_id>/toggle-premium', methods=['POST'])
@admin_required
def toggle_user_premium(user_id):
    """Active/Désactive le premium d'un utilisateur"""
    admin_id = session.get('user_id')
    success = db.toggle_premium(user_id)
    
    if success:
        db.log_admin_action(admin_id, "toggle_premium", user_id, 
                          f"Changement statut premium", 
                          request.remote_addr)
    
    return jsonify({
        "success": success,
        "message": "Premium modifié" if success else "Erreur"
    })

@app.route('/api/admin/user/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role_api(user_id):
    """Change le rôle d'un utilisateur"""
    admin_id = session.get('user_id')
    data = request.json
    new_role = data.get('role')
    
    if new_role not in ['user', 'admin']:
        return jsonify({
            "success": False,
            "error": "Rôle invalide"
        }), 400
    
    success = db.update_user_role(user_id, new_role)
    
    if success:
        db.log_admin_action(admin_id, "change_role", user_id, 
                          f"Changement rôle vers: {new_role}", 
                          request.remote_addr)
    
    return jsonify({
        "success": success,
        "message": "Rôle modifié" if success else "Erreur"
    })

@app.route('/api/admin/user/<int:user_id>/delete', methods=['DELETE'])
@admin_required
def delete_user_api(user_id):
    """Supprime un utilisateur"""
    admin_id = session.get('user_id')
    
    if user_id == admin_id:
        return jsonify({
            "success": False,
            "error": "Vous ne pouvez pas supprimer votre propre compte"
        }), 400
    
    success = db.delete_user(user_id)
    
    if success:
        db.log_admin_action(admin_id, "delete_user", user_id, 
                          f"Suppression utilisateur", 
                          request.remote_addr)
    
    return jsonify({
        "success": success,
        "message": "Utilisateur supprimé" if success else "Erreur"
    })

@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_admin_logs():
    """Récupère les logs admin"""
    limit = request.args.get('limit', 50, type=int)
    logs = db.get_admin_logs(limit=limit)
    
    return jsonify({
        "success": True,
        "logs": logs
    })

# ==================== AUTHENTIFICATION ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    if not email or not username or not password:
        return jsonify({
            "success": False,
            "error": "Tous les champs sont requis"
        }), 400
    
    if len(password) < 6:
        return jsonify({
            "success": False,
            "error": "Le mot de passe doit contenir au moins 6 caractères"
        }), 400
    
    user_id = db.create_user(email, username, password)
    
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            "success": True,
            "message": "Compte créé avec succès",
            "user": {
                "id": user_id,
                "username": username,
                "email": email
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "Email ou nom d'utilisateur déjà utilisé"
        }), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Connexion utilisateur"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email et mot de passe requis"
        }), 400
    
    user = db.verify_password_with_email(email, password)
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        db.update_last_login(user['id'])
        
        return jsonify({
            "success": True,
            "message": "Connexion réussie",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_premium": user['is_premium'],
                "is_admin": user.get('role') == 'admin'
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "Email ou mot de passe incorrect"
        }), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Déconnexion"""
    session.clear()
    return jsonify({
        "success": True,
        "message": "Déconnexion réussie"
    })

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Récupère l'utilisateur connecté"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Non connecté"
        }), 401
    
    user = db.get_user_by_id(user_id)
    
    if user:
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_premium": user['is_premium'],
                "is_admin": user.get('role') == 'admin',
                "scan_count": user['scan_count']
            }
        })
    else:
        return jsonify({
            "success": False,
            "error": "Utilisateur non trouvé"
        }), 404

@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    """Récupère les statistiques de l'utilisateur"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Non connecté"
        }), 401
    
    stats = db.get_user_stats(user_id)
    
    return jsonify({
        "success": True,
        "stats": stats
    })

# ==================== GESTION DES FAVORIS ====================

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
    
    data = request.json
    token_address = data.get('token_address')
    token_chain = data.get('token_chain')
    token_data = data.get('token_data', {})
    notes = data.get('notes', '')
    
    if not token_address or not token_chain:
        return jsonify({
            "success": False,
            "error": "Données manquantes"
        }), 400
    
    success = db.add_favorite(user_id, token_address, token_chain, token_data, notes)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Ajouté aux favoris"
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
    
    data = request.json
    token_address = data.get('token_address')
    token_chain = data.get('token_chain')
    
    success = db.remove_favorite(user_id, token_address, token_chain)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Retiré des favoris"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Token non trouvé dans les favoris"
        }), 404

@app.route('/api/favorites/check', methods=['POST'])
def check_favorite():
    """Vérifie si un token est dans les favoris"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": True,
            "is_favorite": False
        })
    
    data = request.json
    token_address = data.get('token_address')
    token_chain = data.get('token_chain')
    
    is_fav = db.is_favorite(user_id, token_address, token_chain)
    
    return jsonify({
        "success": True,
        "is_favorite": is_fav
    })

@app.route('/api/favorites/notes', methods=['POST'])
def update_favorite_notes():
    """Met à jour les notes d'un favori"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401
    
    data = request.json
    token_address = data.get('token_address')
    token_chain = data.get('token_chain')
    notes = data.get('notes', '')
    
    success = db.update_favorite_notes(user_id, token_address, token_chain, notes)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Notes mises à jour"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Favori non trouvé"
        }), 404

# ==================== HISTORIQUE ====================

@app.route('/api/history', methods=['GET'])
def get_history():
    """Récupère l'historique des scans"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401
    
    limit = request.args.get('limit', 10, type=int)
    history = db.get_scan_history(user_id, limit)
    
    return jsonify({
        "success": True,
        "history": history
    })

@app.route('/api/history/<int:scan_id>', methods=['GET'])
def get_scan_details(scan_id):
    """Récupère les détails d'un scan"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Connexion requise"
        }), 401
    
    scan = db.get_scan_details(scan_id)
    
    if scan:
        return jsonify({
            "success": True,
            "scan": scan
        })
    else:
        return jsonify({
            "success": False,
            "error": "Scan non trouvé"
        }), 404

# ==================== SCAN ====================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Récupère la configuration actuelle"""
    return jsonify({
        "nitter_url": "http://192.168.1.19:8080",
        "max_tokens": 10,
        "risk_threshold": 50
    })

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Démarre un nouveau scan"""
    global scanner, scan_in_progress, current_scan_results, last_scan_timestamp
    
    if scan_in_progress:
        return jsonify({
            "success": False,
            "error": "Un scan est déjà en cours"
        }), 400
    
    data = request.json
    max_tokens = data.get('max_tokens', 10)
    nitter_url = data.get('nitter_url', 'http://192.168.1.19:8080')
    
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
            scanner = TokenScanner(nitter_url=nitter_url)
            current_scan_results = scanner.scan_tokens(max_tokens=max_tokens)
            scan_in_progress = False
            last_scan_timestamp = datetime.now().isoformat()
            
            if user_id and current_scan_results.get('success'):
                db.save_scan_history(user_id, current_scan_results)
                db.update_scan_count(user_id)
                
        except Exception as e:
            current_scan_results = {
                "success": False,
                "error": str(e)
            }
            scan_in_progress = False
    
    scan_in_progress = True
    current_scan_results = None
    
    thread = threading.Thread(target=run_scan)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Scan démarré",
        "scan_id": datetime.now().isoformat()
    })

@app.route('/api/scan/progress', methods=['GET'])
def get_progress():
    """Récupère la progression du scan en cours"""
    global scanner, scan_in_progress
    
    if not scan_in_progress:
        return jsonify({
            "in_progress": False,
            "completed": current_scan_results is not None
        })
    
    if scanner:
        progress = scanner.get_progress()
        return jsonify({
            "in_progress": True,
            "current": progress['current'],
            "total": progress['total'],
            "percentage": progress['percentage']
        })
    
    return jsonify({
        "in_progress": True,
        "current": 0,
        "total": 0,
        "percentage": 0
    })

@app.route('/api/scan/results', methods=['GET'])
def get_results():
    """Récupère les résultats du dernier scan avec timestamp"""
    global current_scan_results, last_scan_timestamp
    
    if current_scan_results is None:
        return jsonify({
            "success": False,
            "error": "Aucun résultat disponible"
        }), 404
    
    results_with_timestamp = current_scan_results.copy()
    results_with_timestamp['last_scan_timestamp'] = last_scan_timestamp
    
    return jsonify(results_with_timestamp)

@app.route('/api/scan/search', methods=['POST'])
def search_token():
    """Recherche un token par adresse dans les résultats actuels"""
    global current_scan_results
    
    if current_scan_results is None or not current_scan_results.get('success'):
        return jsonify({
            "success": False,
            "error": "Aucun résultat de scan disponible"
        }), 404
    
    data = request.json
    search_query = data.get('query', '').lower()
    
    if not search_query:
        return jsonify({
            "success": False,
            "error": "Requête de recherche vide"
        }), 400
    
    results = current_scan_results.get('results', [])
    filtered_results = [
        token for token in results
        if search_query in token.get('address', '').lower()
        or search_query in token.get('chain', '').lower()
    ]
    
    return jsonify({
        "success": True,
        "results": filtered_results,
        "count": len(filtered_results)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérifie que l'API fonctionne"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "scan_in_progress": scan_in_progress,
        "authenticated": session.get('user_id') is not None,
        "last_scan": last_scan_timestamp
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
    
    # IMPORTANT : Enregistrer les routes API AVANT de démarrer le serveur
    register_api_routes(app)
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   TOKEN SCANNER PRO - Interface Web + Auth + Trading      ║
    ║                                                            ║
    ║   🌐 Accès local:    http://localhost:5000                ║
    ║   🌐 Accès réseau:   http://192.168.1.19:5000            ║
    ║   🌐 IP détectée:    http://""" + local_ip + """:5000      ║
    ║                                                             ║
    ║   ✅ Système de comptes activé                             ║
    ║   ✅ Favoris activés                                       ║
    ║   ✅ Historique activé                                     ║
    ║   ✅ Trading system activé                                 ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )