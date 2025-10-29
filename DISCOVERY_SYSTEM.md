# Token Discovery System - Documentation Complète

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Problème résolu](#problème-résolu)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Utilisation Backend](#utilisation-backend)
7. [Utilisation Frontend](#utilisation-frontend)
8. [API REST](#api-rest)
9. [WebSocket Events](#websocket-events)
10. [Exemples de code](#exemples-de-code)
11. [Production](#production)

---

## 🎯 Vue d'ensemble

Le **Token Discovery System** est un système centralisé de découverte de nouveaux tokens crypto qui **élimine les appels API redondants** en partageant un seul scan entre tous les utilisateurs connectés.

### Avant (Problème)
```
User 1 clique "Rechercher" → API Call 1 (DexScreener, GoPlus, etc.)
User 2 clique "Rechercher" → API Call 2 (DexScreener, GoPlus, etc.)
User 3 clique "Rechercher" → API Call 3 (DexScreener, GoPlus, etc.)
...
User N clique "Rechercher" → API Call N

❌ N appels API
❌ Coûts élevés
❌ Rate limits atteints
❌ Performances médiocres
```

### Après (Solution)
```
User 1/2/3/.../N connectés → WebSocket

Backend déclenche 1 scan centralisé → API Call (DexScreener, GoPlus, etc.)
                                    ↓
                          Stockage dans BDD
                                    ↓
                  Broadcast WebSocket → Tous les users

✅ 1 seul appel API
✅ Coûts réduits
✅ Rate limits respectés
✅ Expérience temps réel
✅ Performance optimale
```

---

## ❌ Problème résolu

### Ancien système (`/api/scan/start`)
- Chaque utilisateur déclenchait un scan individuel
- 10 utilisateurs = 10 scans = 10× les coûts API
- Risque de rate limiting
- Aucun partage des résultats
- Expérience isolée par utilisateur

### Nouveau système (`Token Discovery Service`)
- **1 scan centralisé** partagé entre tous les users
- **WebSocket** pour broadcast temps réel
- **Cache BDD** avec rotation FIFO (max 200 tokens)
- **Auto-discovery** optionnel (scans périodiques)
- **Expérience collaborative** - tous voient les mêmes tokens

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Browser)                      │
│                                                               │
│  ┌──────────────────┐       ┌──────────────────┐            │
│  │ TokenDiscovery   │       │  User Interface  │            │
│  │     Client       │◄──────┤   (index.html)   │            │
│  │  (WebSocket JS)  │       │                  │            │
│  └────────┬─────────┘       └──────────────────┘            │
│           │                                                   │
└───────────┼───────────────────────────────────────────────────┘
            │
            │ WebSocket (Socket.IO)
            │
┌───────────▼───────────────────────────────────────────────────┐
│                      BACKEND (Flask + SocketIO)               │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           Token Discovery Service                     │    │
│  │                                                        │    │
│  │  • Centralized scanning                               │    │
│  │  • WebSocket broadcasting                             │    │
│  │  • Auto-discovery (optional)                          │    │
│  │  • Thread-safe operations                             │    │
│  └───────────────┬──────────────────────────────────────┘    │
│                  │                                             │
│  ┌───────────────▼──────────┐    ┌──────────────────────┐    │
│  │    TokenScanner          │    │      Database        │    │
│  │  (DexScreener, GoPlus)   │    │   (SQLite/MongoDB)   │    │
│  └──────────────────────────┘    └──────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### Composants

1. **TokenDiscoveryService** (`token_discovery_service.py`)
   - Service principal de découverte centralisée
   - Gestion des scans (manuel + auto)
   - Broadcasting WebSocket
   - Thread-safe avec locks

2. **Flask-SocketIO** (intégré dans `app.py`)
   - Server WebSocket
   - Gestion des connexions clients
   - Broadcasting aux rooms

3. **TokenDiscoveryClient** (`token_discovery_client.js`)
   - Client JavaScript WebSocket
   - Auto-reconnexion
   - Événements personnalisables
   - API simple

4. **Database** (`database.py`)
   - Table `scanned_tokens` (max 200 tokens FIFO)
   - Méthodes de stockage/récupération
   - Thread-safe

---

## 📦 Installation

### 1. Installer les dépendances

```bash
cd token_scanner_pro
pip install -r requirements.txt
```

Les nouvelles dépendances ajoutées :
- `flask-socketio==5.3.5` - WebSocket server
- `python-socketio==5.10.0` - SocketIO implementation
- `python-engineio==4.8.0` - Engine.IO protocol

### 2. Vérifier l'installation

```python
python -c "import flask_socketio; print('✅ Flask-SocketIO installé')"
```

---

## ⚙️ Configuration

### Variables d'environnement (.env)

```bash
# ==================== TOKEN DISCOVERY CONFIGURATION ====================

# Auto-start Discovery Service au démarrage
AUTO_START_DISCOVERY=false

# Intervalle entre chaque scan automatique (en secondes)
# Recommandé: 300 (5 minutes) minimum
DISCOVERY_INTERVAL=300

# Nombre de tokens par scan automatique
DISCOVERY_MAX_TOKENS=20

# ==================== EXISTING CONFIG ====================
NITTER_URL=http://localhost:8080
CLAUDE_API_KEY=your_key_here
# ... autres configs
```

### Modes de fonctionnement

#### Mode Manuel (par défaut)
```bash
AUTO_START_DISCOVERY=false
```
- Le service attend qu'un utilisateur déclenche un scan
- Économise les ressources
- Recommandé pour développement

#### Mode Auto
```bash
AUTO_START_DISCOVERY=true
DISCOVERY_INTERVAL=300
DISCOVERY_MAX_TOKENS=20
```
- Scans automatiques périodiques
- Tous les utilisateurs reçoivent les nouveaux tokens
- Recommandé pour production

---

## 🔧 Utilisation Backend

### Initialisation automatique

Le service est automatiquement initialisé dans `app.py` :

```python
# Déjà fait dans app.py - pas besoin de toucher
from token_discovery_service import TokenDiscoveryService
from flask_socketio import SocketIO

socketio = SocketIO(app, cors_allowed_origins=allowed_origins)
token_discovery = TokenDiscoveryService(database=db, socketio=socketio)
```

### Déclencher un scan manuel (Python)

```python
# Dans une route Flask ou un script
result = token_discovery.trigger_scan(max_tokens=20)

if result['success']:
    print(f"✅ {result['tokens_found']} tokens découverts")
    print(f"💾 {result['tokens_stored']} tokens stockés")
else:
    print(f"❌ Erreur: {result['error']}")
```

### Callbacks personnalisés

```python
def on_new_token(token):
    print(f"📢 Nouveau: {token.get('name')} ({token.get('symbol')})")

def on_scan_complete(results):
    print(f"✅ Scan terminé: {results.get('tokens_found')} tokens")

token_discovery.on_new_token(on_new_token)
token_discovery.on_scan_complete(on_scan_complete)
```

### Auto-discovery

```python
# Démarrer
token_discovery.start_auto_discovery(
    interval_seconds=300,  # 5 minutes
    max_tokens=20
)

# Arrêter
token_discovery.stop_auto_discovery()

# Statut
status = token_discovery.get_status()
print(f"Auto-discovery actif: {status['auto_discovery_active']}")
```

---

## 🌐 Utilisation Frontend

### 1. Inclure Socket.IO

Dans `index.html` (ou votre template) :

```html
<!-- Socket.IO Client Library -->
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

<!-- Token Discovery Client -->
<script src="/static/js/token_discovery_client.js"></script>
```

### 2. Initialiser le client

```javascript
// Créer le client
const discoveryClient = new TokenDiscoveryClient({
    serverUrl: window.location.origin,  // Auto-détecte l'URL
    autoReconnect: true,                // Reconnexion automatique
    reconnectDelay: 3000,               // Délai entre tentatives (ms)
    maxReconnectAttempts: 10            // Max tentatives
});

// Connecter au serveur
discoveryClient.connect();
```

### 3. Écouter les événements

```javascript
// Nouveau token découvert
discoveryClient.on('new_token', (token) => {
    console.log('📢 Nouveau token:', token);

    // Ajouter à l'UI
    addTokenToGrid(token);

    // Notification
    showNotification(`Nouveau token: ${token.name}`);
});

// Scan démarré
discoveryClient.on('scan_started', (data) => {
    console.log('🔍 Scan en cours...');
    showLoadingSpinner();
});

// Scan terminé
discoveryClient.on('scan_completed', (data) => {
    console.log(`✅ ${data.tokens_found} tokens découverts`);
    hideLoadingSpinner();
});

// Erreur
discoveryClient.on('scan_error', (error) => {
    console.error('❌ Erreur:', error.error);
    showErrorMessage(error.error);
});

// Connexion/Déconnexion
discoveryClient.on('connected', () => {
    console.log('✅ Connecté au Discovery Service');
    updateConnectionStatus('connected');
});

discoveryClient.on('disconnected', (data) => {
    console.log('🔌 Déconnecté:', data.reason);
    updateConnectionStatus('disconnected');
});
```

### 4. Déclencher un scan

```javascript
// Bouton "Rechercher"
document.getElementById('searchBtn').addEventListener('click', async () => {
    try {
        const result = await discoveryClient.triggerScan({
            maxTokens: 20,
            chain: null,  // Toutes les chains
            profileUrl: null  // Ou URL DexScreener spécifique
        });

        console.log('✅ Scan déclenché:', result);
    } catch (error) {
        console.error('❌ Erreur:', error);
    }
});
```

### 5. Récupérer les tokens existants

```javascript
// Au chargement de la page, récupérer les tokens déjà en BDD
async function loadExistingTokens() {
    try {
        const tokens = await discoveryClient.getRecentTokens(50);
        tokens.forEach(token => addTokenToGrid(token.token_data));
    } catch (error) {
        console.error('❌ Erreur chargement tokens:', error);
    }
}

// Appeler au chargement
window.addEventListener('DOMContentLoaded', loadExistingTokens);
```

---

## 🔌 API REST

### Déclencher un scan

```http
POST /api/discovery/trigger
Content-Type: application/json

{
  "max_tokens": 20,
  "chain": "ethereum",  // optionnel
  "profile_url": "https://dexscreener.com/..."  // optionnel
}
```

**Réponse:**
```json
{
  "success": true,
  "tokens_found": 15,
  "tokens_stored": 15,
  "scan_timestamp": "2025-10-27T10:30:00",
  "total_scans": 42
}
```

### Obtenir le statut

```http
GET /api/discovery/status
```

**Réponse:**
```json
{
  "success": true,
  "status": {
    "scanning": false,
    "auto_discovery_active": true,
    "auto_discovery_interval": 300,
    "last_scan_timestamp": "2025-10-27T10:30:00",
    "total_scans": 42,
    "tokens_in_database": 198,
    "database_capacity": 200
  }
}
```

### Obtenir les statistiques

```http
GET /api/discovery/stats
```

**Réponse:**
```json
{
  "success": true,
  "stats": {
    "total_scans": 42,
    "total_tokens_discovered": 198,
    "safe_tokens": 145,
    "risky_tokens": 53,
    "last_scan": "2025-10-27T10:30:00",
    "auto_discovery_active": true,
    "database_usage": "198/200",
    "database_usage_percent": 99.0
  }
}
```

### Récupérer les tokens récents

```http
GET /api/discovery/recent?limit=50&chain=ethereum
```

**Réponse:**
```json
{
  "success": true,
  "tokens": [
    {
      "id": 1,
      "token_address": "0x...",
      "token_chain": "ethereum",
      "token_data": { /* ... */ },
      "risk_score": 25,
      "is_safe": true,
      "scanned_at": "2025-10-27T10:30:00"
    }
  ],
  "count": 50
}
```

### Démarrer l'auto-discovery (Admin only)

```http
POST /api/discovery/auto/start
Content-Type: application/json

{
  "interval_seconds": 300,
  "max_tokens": 20
}
```

### Arrêter l'auto-discovery (Admin only)

```http
POST /api/discovery/auto/stop
```

---

## 📡 WebSocket Events

### Events envoyés par le serveur

| Event | Description | Payload |
|-------|-------------|---------|
| `connected` | Connexion établie | `{ message, timestamp }` |
| `joined_discovery` | Room discovery rejointe | `{ message, timestamp }` |
| `new_token` | Nouveau token découvert | `{ token_data }` |
| `scan_started` | Scan démarré | `{ timestamp, max_tokens }` |
| `scan_completed` | Scan terminé | `{ timestamp, tokens_found, tokens_stored }` |
| `scan_error` | Erreur lors du scan | `{ timestamp, error }` |
| `discovery_status` | Statut du service | `{ status_object }` |

### Events envoyés par le client

| Event | Description | Payload |
|-------|-------------|---------|
| `connect` | Se connecter | - |
| `disconnect` | Se déconnecter | - |
| `join_discovery` | Rejoindre la room | - |
| `leave_discovery` | Quitter la room | - |
| `request_status` | Demander le statut | - |

---

## 💡 Exemples de code

### Exemple complet Frontend

```html
<!DOCTYPE html>
<html>
<head>
    <title>Token Discovery Demo</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="/static/js/token_discovery_client.js"></script>
</head>
<body>
    <h1>Token Discovery Service</h1>

    <div id="status">Déconnecté</div>
    <button id="searchBtn">Rechercher des tokens</button>
    <div id="tokens-grid"></div>

    <script>
        // Initialiser le client
        const client = new TokenDiscoveryClient();

        // Connexion
        client.on('connected', () => {
            document.getElementById('status').textContent = '✅ Connecté';
        });

        // Nouveau token
        client.on('new_token', (token) => {
            const grid = document.getElementById('tokens-grid');
            const tokenDiv = document.createElement('div');
            tokenDiv.className = 'token-card';
            tokenDiv.innerHTML = `
                <h3>${token.name || 'Unknown'}</h3>
                <p>Symbol: ${token.symbol || '?'}</p>
                <p>Chain: ${token.chain || '?'}</p>
                <p class="${token.is_safe ? 'safe' : 'risky'}">
                    ${token.is_safe ? '✅ Safe' : '⚠️ Risky'}
                </p>
            `;
            grid.prepend(tokenDiv);
        });

        // Scan started/completed
        client.on('scan_started', () => {
            document.getElementById('searchBtn').disabled = true;
            document.getElementById('searchBtn').textContent = 'Scan en cours...';
        });

        client.on('scan_completed', (data) => {
            document.getElementById('searchBtn').disabled = false;
            document.getElementById('searchBtn').textContent = 'Rechercher des tokens';
            alert(`✅ ${data.tokens_found} tokens découverts!`);
        });

        // Bouton recherche
        document.getElementById('searchBtn').addEventListener('click', () => {
            client.triggerScan({ maxTokens: 20 });
        });

        // Connecter au démarrage
        client.connect();

        // Charger les tokens existants
        client.getRecentTokens(50).then(tokens => {
            tokens.forEach(t => {
                // Trigger 'new_token' event pour chaque token
                client._triggerEvent('new_token', t.token_data);
            });
        });
    </script>
</body>
</html>
```

### Exemple Backend personnalisé

```python
from token_discovery_service import TokenDiscoveryService
from database import Database

# Initialiser
db = Database()
discovery = TokenDiscoveryService(database=db, socketio=None)

# Callbacks
def log_new_token(token):
    print(f"📢 {token.get('name')} discovered")

discovery.on_new_token(log_new_token)

# Scan manuel
result = discovery.trigger_scan(max_tokens=20)
print(result)

# Auto-discovery
discovery.start_auto_discovery(interval_seconds=300, max_tokens=20)

# Laisser tourner
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    discovery.shutdown()
```

---

## 🚀 Production

### 1. Configuration recommandée

```bash
# .env
AUTO_START_DISCOVERY=true
DISCOVERY_INTERVAL=300
DISCOVERY_MAX_TOKENS=20

# Rate limiting plus strict
FLASK_LIMITER_ENABLED=true
```

### 2. Utiliser Gunicorn avec eventlet

```bash
# Installer eventlet pour async WebSocket
pip install eventlet

# Démarrer avec gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

**⚠️ IMPORTANT:** Avec WebSocket, utilisez **1 worker uniquement** (`-w 1`)

### 3. Redis pour session partagée (multi-workers)

Si vous avez besoin de plusieurs workers, utilisez Redis :

```python
# app.py
from flask_socketio import SocketIO

socketio = SocketIO(
    app,
    message_queue='redis://localhost:6379',  # Redis message queue
    cors_allowed_origins=allowed_origins
)
```

```bash
# Démarrer avec plusieurs workers
gunicorn --worker-class eventlet -w 4 --bind 0.0.0.0:5000 app:app
```

### 4. Monitoring

```python
# Ajouter des logs
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('token_discovery')

# Dans token_discovery_service.py
logger.info(f"Scan completed: {tokens_found} tokens")
```

---

## 📊 Comparaison performances

### Ancien système (individuel)

| Métrique | Valeur |
|----------|--------|
| Utilisateurs simultanés | 10 |
| Appels API par scan | 10× (1 par user) |
| Coût moyen par scan | 10× plus élevé |
| Délai de réception | Variable (chacun attend son scan) |
| Rate limits | Risque élevé |

### Nouveau système (centralisé)

| Métrique | Valeur |
|----------|--------|
| Utilisateurs simultanés | ∞ (illimité) |
| Appels API par scan | 1× (partagé) |
| Coût moyen par scan | 90% moins cher |
| Délai de réception | ~0ms (WebSocket temps réel) |
| Rate limits | Risque minimal |

**Économies estimées:**
- 10 users → 90% de réduction d'API calls
- 100 users → 99% de réduction d'API calls

---

## 🔒 Sécurité

### Rate limiting

Les routes Discovery sont protégées par Flask-Limiter :

```python
# Déjà configuré dans app.py
limiter = Limiter(
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
```

### Admin-only routes

Certaines routes nécessitent les droits admin :
- `/api/discovery/auto/start`
- `/api/discovery/auto/stop`

```python
# Vérifie automatiquement
user_id = session.get('user_id')
if not user_id or not db.is_admin(user_id):
    return jsonify({"error": "Admin access required"}), 403
```

### CORS

WebSocket est protégé par CORS :

```python
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
socketio = SocketIO(app, cors_allowed_origins=allowed_origins)
```

---

## 🐛 Troubleshooting

### WebSocket ne se connecte pas

1. Vérifier que Socket.IO est chargé :
```html
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
```

2. Vérifier la console :
```javascript
console.log('Socket.IO loaded:', typeof io !== 'undefined');
```

3. Vérifier les CORS :
```bash
# .env
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
```

### Scans ne se déclenchent pas

1. Vérifier le statut :
```bash
curl http://localhost:5000/api/discovery/status
```

2. Vérifier les logs serveur :
```
🔍 Scan centralisé démarré - Max tokens: 20
```

3. Vérifier qu'un scan n'est pas déjà en cours :
```json
{
  "success": false,
  "error": "Un scan est déjà en cours"
}
```

### Tokens ne s'affichent pas

1. Vérifier l'événement `new_token` :
```javascript
client.on('new_token', (token) => {
    console.log('Token reçu:', token);
});
```

2. Vérifier la room :
```javascript
// Le client doit rejoindre la room
client.socket.emit('join_discovery');
```

---

## 📝 Notes importantes

1. **Un seul worker en production** avec WebSocket (sauf si Redis)
2. **Auto-discovery** recommandé en production pour expérience continue
3. **Limite BDD:** 200 tokens max (FIFO automatique)
4. **Rate limiting:** Respecter les quotas API externes
5. **Monitoring:** Logger tous les scans pour analytics

---

## 🎉 Résultat final

✅ **1 scan partagé** entre tous les utilisateurs
✅ **Temps réel** via WebSocket
✅ **90-99% de réduction** des coûts API
✅ **Expérience collaborative** - tous voient les mêmes tokens
✅ **Performance optimale** - pas de délai
✅ **Rate limits respectés** - 1 appel au lieu de N

---

**Made with ❤️ by Claude Code**
