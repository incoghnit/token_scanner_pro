# 🚨 Analyse des Erreurs Runtime

**Date:** 2025-10-31
**Analysé depuis:** Logs Flask de production

---

## 🔴 ERREURS CRITIQUES DÉTECTÉES

### 1. **Erreur 404 : `/api/scan/results`**

**Fréquence:** Très élevée (à chaque requête de progression)

**Logs:**
```
"GET /api/scan/results HTTP/1.1" 404
```

#### 🔍 Analyse:

**Localisation:** `app.py:679-698`

```python
@app.route('/api/scan/results', methods=['GET'])
def scan_results():
    current_scan_results = get_scanner_state('current_scan_results')

    if current_scan_results:
        return jsonify({...})
    else:
        return jsonify({
            "success": False,
            "error": "Aucun résultat disponible"
        }), 404  # ← ICI : 404 intentionnel
```

#### 📊 Cause:
**Ce n'est PAS un bug** - C'est le comportement normal quand :
1. Le scan n'est pas encore terminé
2. Aucun résultat n'est stocké dans `current_scan_results`
3. Le frontend poll avant que les données soient prêtes

#### ⚠️ Problème:
Le frontend fait des requêtes **trop fréquentes** avant que les résultats soient disponibles, ce qui génère beaucoup de logs 404 inutiles.

#### ✅ Solutions:

**Option A - Améliorer la Logique Frontend (Recommandé)**
```javascript
// Au lieu de retourner 404, retourner 200 avec status "pending"
// app.py:694-698 - AVANT
else:
    return jsonify({
        "success": False,
        "error": "Aucun résultat disponible"
    }), 404

// app.py:694-698 - APRÈS
else:
    return jsonify({
        "success": True,
        "status": "pending",
        "message": "Scan en cours, résultats pas encore disponibles",
        "results": []
    }), 200
```

**Option B - Ajouter un Délai Frontend**
```javascript
// index.html - Ajouter un délai progressif entre les requêtes
let pollDelay = 1000; // Commence à 1 seconde
function pollResults() {
    fetch('/api/scan/results')
        .then(response => {
            if (response.status === 404) {
                pollDelay = Math.min(pollDelay * 1.2, 5000); // Max 5 secondes
                setTimeout(pollResults, pollDelay);
            } else {
                // Traiter les résultats
            }
        });
}
```

---

### 2. **Erreur 400 : WebSocket Connection Failed**

**Fréquence:** Très élevée (tentatives répétées)

**Logs:**
```
"GET /socket.io/?EIO=4&transport=websocket HTTP/1.1" 400
```

#### 🔍 Analyse:

**Configuration Actuelle:**

**Frontend (index.html:628):**
```html
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
```

**Frontend (index.html:885):**
```javascript
socket = io(window.location.origin, {
    transports: ['websocket', 'polling']
});
```

**Backend (app.py:135-143):**
```python
socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode='threading',
    logger=False,              # ← Logs désactivés!
    engineio_logger=False,     # ← Logs Engine.IO désactivés!
    ping_timeout=60,
    ping_interval=25
)
```

#### 📊 Cause Probable:

**Incompatibilité de version entre:**
- **Frontend:** Socket.IO Client 4.5.4 (EIO=4)
- **Backend:** Flask-SocketIO (version inconnue)

#### 🔧 Diagnostic:

Pour identifier le problème exact, activons les logs:

```python
# app.py:135-143 - Temporairement activer les logs
socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode='threading',
    logger=True,               # ← Activer pour debug
    engineio_logger=True,      # ← Activer pour debug
    ping_timeout=60,
    ping_interval=25
)
```

#### ✅ Solutions:

**Solution 1 - Vérifier les Versions (URGENT)**

```bash
cd /home/jimmy/script/claude_V4/token_scanner_pro/token_scanner_pro
pip show flask-socketio python-socketio python-engineio
```

**Versions compatibles recommandées:**
- Socket.IO Client 4.5.x → Flask-SocketIO 5.3+ → python-socketio 5.9+ → python-engineio 4.7+

**Solution 2 - Mettre à Jour les Dépendances**

```bash
pip install --upgrade flask-socketio python-socketio python-engineio
```

**Solution 3 - Downgrade du Client Frontend**

Si la mise à jour backend ne fonctionne pas, utiliser une version client compatible:

```html
<!-- index.html:628 - AVANT -->
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

<!-- index.html:628 - APRÈS (si Flask-SocketIO < 5.3) -->
<script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
```

**Solution 4 - Ajouter Fallback Config**

```python
# app.py:135 - Ajouter options
socketio = SocketIO(
    app,
    cors_allowed_origins=allowed_origins,
    async_mode='threading',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    # 🆕 Options supplémentaires
    allow_upgrades=True,
    manage_session=False
)
```

---

### 3. **Tokens Analysés en Double**

**Observation:**
```
🔗 DEBUG - Token 3hEuL8jt... has links: ['unknown', 'twitter']
  ✅ Website found (empty type): https://www.reddit.com/r/Eyebleach/...
ℹ️  Token is only 0.7h old → Fraud detection mode

[1 seconde plus tard]

🔗 DEBUG - Token 3hEuL8jt... has links: ['unknown', 'twitter']
  ✅ Website found (empty type): https://www.reddit.com/r/Eyebleach/...
ℹ️  Token is only 0.7h old → Fraud detection mode
```

#### 📊 Cause:
Analyse dupliquée du même token en quelques secondes.

#### Causes Possibles:
1. **Requêtes parallèles** du frontend
2. **Pas de cache** pour les tokens récemment analysés
3. **Service d'auto-scan** + scan manuel en même temps

#### ✅ Solutions:

**Solution 1 - Vérifier Cache MongoDB**

Le cache existe déjà dans `mongodb_manager.py` avec UPSERT, donc normalement pas de duplication en BDD. Mais l'analyse se fait 2 fois quand même.

**Solution 2 - Ajouter Cache en Mémoire (Court Terme)**

```python
# scanner_core.py - Ajouter cache en mémoire
from functools import lru_cache
from datetime import datetime, timedelta

# Cache pour 5 minutes
_analysis_cache = {}
_cache_ttl = 300  # 5 minutes

def get_token_full_data(self, address: str, chain: str, token_info: Dict) -> Dict:
    # Vérifier cache
    cache_key = f"{address}_{chain}"
    now = datetime.now()

    if cache_key in _analysis_cache:
        cached_time, cached_data = _analysis_cache[cache_key]
        if (now - cached_time).total_seconds() < _cache_ttl:
            print(f"⚡ Cache hit for {address[:8]}... (age: {(now - cached_time).total_seconds():.1f}s)")
            return cached_data

    # Analyse normale...
    result = {...}  # Votre code actuel

    # Stocker dans cache
    _analysis_cache[cache_key] = (now, result)

    return result
```

**Solution 3 - Debounce Frontend**

```javascript
// index.html - Éviter les requêtes parallèles
let scanInProgress = false;

function startScan() {
    if (scanInProgress) {
        console.log('⚠️  Scan déjà en cours, requête ignorée');
        return;
    }

    scanInProgress = true;

    fetch('/api/scan/start', {
        method: 'POST',
        ...
    })
    .finally(() => {
        scanInProgress = false;
    });
}
```

---

## 🟡 OBSERVATIONS TECHNIQUES

### Tous les Tokens Sont Très Jeunes

**Observation:**
```
ℹ️  Token is only 0.6h old → Fraud detection mode
ℹ️  Token is only 0.7h old → Fraud detection mode
ℹ️  Token is only 0.9h old → Fraud detection mode
ℹ️  Token is only 1.1h old → Fraud detection mode
ℹ️  Token is only 1.2h old → Fraud detection mode
```

#### 📊 Analyse:
**C'est NORMAL et ATTENDU** ✅

Vous scannez les **nouveaux tokens** de DexScreener, donc ils ont tous moins de 2 heures. Le système bascule correctement en "Fraud detection mode" pour ces tokens jeunes.

#### Comportement Actuel:
- **< 2 heures:** Mode détection de fraude (pas d'analyse technique OHLCV)
- **≥ 2 heures:** Mode analyse technique (avec indicateurs, MACD, RSI, etc.)

Cela évite les faux signaux sur des tokens avec trop peu de données historiques. ✅

---

## 📊 RÉSUMÉ DES REQUÊTES

### Requêtes qui Fonctionnent ✅
```
✅ GET /api/scan/progress        → 200 (fonctionne)
✅ GET /api/auto-scan/status     → 200 (fonctionne)
```

### Requêtes Problématiques ❌
```
❌ GET /api/scan/results         → 404 (résultats pas prêts)
❌ GET /socket.io/?EIO=4...      → 400 (incompatibilité version)
```

---

## 🎯 PLAN D'ACTION PRIORITAIRE

### Phase 1 : Fix WebSocket (URGENT)

1. **Vérifier les versions**
   ```bash
   pip show flask-socketio python-socketio python-engineio
   ```

2. **Activer les logs temporairement**
   ```python
   # app.py:139-140
   logger=True,
   engineio_logger=True,
   ```

3. **Redémarrer l'app et capturer les logs détaillés**
   ```bash
   python app.py 2>&1 | tee websocket_debug.log
   ```

4. **Mettre à jour les dépendances si nécessaire**
   ```bash
   pip install --upgrade flask-socketio python-socketio python-engineio
   ```

### Phase 2 : Optimiser /api/scan/results

5. **Retourner 200 avec status "pending" au lieu de 404**
   - Modifier `app.py:694-698`
   - Réduire la pollution des logs

### Phase 3 : Réduire les Analyses Dupliquées

6. **Ajouter cache en mémoire court terme (5 min)**
   - Évite de réanalyser le même token 2x en quelques secondes
   - Réduit la charge API externe (DexScreener, GoPlus, etc.)

---

## 🔍 COMMANDES DE DIAGNOSTIC

### Vérifier Versions Actuelles
```bash
cd /home/jimmy/script/claude_V4/token_scanner_pro/token_scanner_pro
pip show flask-socketio python-socketio python-engineio | grep -E "Name|Version"
```

### Tester WebSocket Manuellement
```bash
# Installer wscat si besoin
npm install -g wscat

# Tester connexion WebSocket
wscat -c "ws://192.168.1.12:5000/socket.io/?EIO=4&transport=websocket"
```

### Activer Mode Debug Complet
```python
# app.py:1452
socketio.run(
    app,
    host='0.0.0.0',
    port=5000,
    debug=True,  # ← Active debug Flask
    use_reloader=False
)
```

---

## 📝 NOTES IMPORTANTES

### Comportement Attendu vs Actuel

| Fonctionnalité | Attendu | Actuel | Statut |
|----------------|---------|--------|--------|
| Scan Progress | Polling HTTP | Polling HTTP | ✅ OK |
| Scan Results | HTTP 200/pending | HTTP 404 | ⚠️  À améliorer |
| Real-time Updates | WebSocket | ❌ WebSocket échoue | 🔴 URGENT |
| Token Analysis | Pas de duplicate | Analyse 2x | ⚠️  À optimiser |
| Fraud Detection | < 2h → Fraud mode | < 2h → Fraud mode | ✅ OK |

### Impact des Problèmes

**WebSocket 400:**
- ❌ Pas de mise à jour temps réel des tokens découverts
- ⚠️  Frontend doit faire du polling HTTP (moins efficace)
- ⚠️  Plus de charge serveur

**Scan Results 404:**
- ⚠️  Logs pollués (non critique)
- ⚠️  Frontend reçoit des erreurs (gérées)
- ℹ️  UX légèrement dégradée

**Analyse Dupliquée:**
- ⚠️  Charge API externe doublée
- ⚠️  Temps de réponse rallongé
- ⚠️  Risque de rate limiting API

---

## ✅ CHECKLIST DE RÉSOLUTION

- [ ] Vérifier versions Flask-SocketIO
- [ ] Activer logs WebSocket pour diagnostic
- [ ] Mettre à jour dépendances SocketIO
- [ ] Tester connexion WebSocket manuellement
- [ ] Modifier /api/scan/results pour retourner 200
- [ ] Ajouter cache mémoire 5min pour éviter duplicates
- [ ] Ajouter debounce frontend pour scans
- [ ] Tester avec charge réelle
- [ ] Désactiver logs debug après résolution

---

**Fin du Rapport**

**Prochaine étape recommandée:** Vérifier les versions avec `pip show flask-socketio`
