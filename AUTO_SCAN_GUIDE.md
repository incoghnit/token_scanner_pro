# 🤖 GUIDE AUTO-SCAN & BARRE DE PROGRESSION

## ✨ NOUVEAUTÉ : Barre de Progression Automatique

Une **barre de progression discrète** apparaît en haut de l'écran lorsque l'auto-scan est actif.

### 🎯 Fonctionnalités

- **Affichage automatique** quand le scan est en cours
- **Progression en temps réel** (mise à jour toutes les 2 secondes)
- **Statistiques** : temps écoulé, tokens trouvés
- **Bouton "Masquer"** pour la cacher temporairement
- **Design discret** : se fond dans l'interface (en haut, fixe)

---

## 🚀 ACTIVER L'AUTO-SCAN AU DÉMARRAGE

### Méthode 1 : Via le fichier .env (Recommandé)

1. **Ouvrez votre fichier `.env`** :

```bash
cd /home/jimmy/script/claude_V2/token_scanner_pro
nano .env
```

2. **Ajoutez cette ligne** :

```bash
# Auto-démarrer le scanner au démarrage de l'app
AUTO_START_SCANNER=true
```

3. **Redémarrez Flask** :

```bash
# Ctrl+C pour arrêter
cd token_scanner_pro
python app.py
```

Vous devriez voir :
```
✅ Auto-scanner démarré automatiquement
```

### Méthode 2 : Démarrage manuel via API

Si vous ne voulez pas l'auto-démarrage, vous pouvez le lancer manuellement :

**Via l'interface admin** (nécessite droits admin) :
1. Connectez-vous
2. Allez sur `/auto-scan`
3. Cliquez sur "Démarrer l'auto-scan"

**Via l'API** (en tant qu'admin) :

```bash
curl -X POST http://localhost:5000/api/auto-scan/start \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

---

## ⚙️ CONFIGURATION DE L'AUTO-SCAN

### Variables d'environnement disponibles

Ajoutez ces variables dans votre `.env` :

```bash
# Auto-Scan Configuration
AUTO_START_SCANNER=true              # Démarrer automatiquement (true/false)
SCAN_INTERVAL=300                    # Intervalle entre scans (secondes, défaut: 300 = 5 min)
TOKENS_PER_SCAN=10                   # Nombre de tokens par scan (défaut: 10)

# MongoDB (requis pour l'auto-scan)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=token_scanner_cache

# Nitter (pour récupérer les tweets)
NITTER_URL=http://localhost:8080
```

### Configuration dynamique (Admin uniquement)

Vous pouvez aussi changer la config sans redémarrer :

**GET la config actuelle** :
```bash
curl http://localhost:5000/api/auto-scan/config
```

**Modifier la config** :
```bash
curl -X PUT http://localhost:5000/api/auto-scan/config \
  -H "Content-Type: application/json" \
  -d '{
    "scan_interval": 600,
    "tokens_per_scan": 20
  }'
```

**Limites** :
- `scan_interval` : entre 60s (1 min) et 3600s (1h)
- `tokens_per_scan` : entre 1 et 50

---

## 📊 COMMENT ÇA FONCTIONNE ?

### 1. Auto-Scan Service

Le service `AutoScannerService` :
- Scanne automatiquement les nouveaux tokens à intervalle régulier
- Stocke les résultats dans **MongoDB** avec **TTL 24h** (expiration automatique)
- Analyse chaque token avec le **TradingEngine**
- Détecte les pump & dump, honeypots, etc.

### 2. Barre de Progression

La barre de progression :
- Interroge l'API `/api/auto-scan/status` toutes les 2 secondes
- Calcule la progression basée sur le temps depuis le dernier scan
- Affiche les stats en temps réel
- Se masque automatiquement si le scan s'arrête

### 3. Workflow Complet

```
[App démarre]
    ↓
[AUTO_START_SCANNER=true ?]
    ↓ Oui
[Scanner démarre]
    ↓
[Toutes les 5 min]
    ↓
[Scan de 10 tokens]
    ↓
[Analyse + Trading Signal]
    ↓
[Stockage MongoDB (TTL 24h)]
    ↓
[Barre de progression s'affiche]
    ↓
[Répète indéfiniment]
```

---

## 🎨 APPARENCE DE LA BARRE

### En haut de l'écran (discrète)

```
┌──────────────────────────────────────────────────────────────┐
│ 🔍  Auto-scan actif · Scan de 10 tokens toutes les 5 min    │
│     ████████████████░░░░░░░░░░░░░░░░░░░░                    │
│     ⏱️ 2m 30s    📊 15 tokens                     [Masquer]  │
└──────────────────────────────────────────────────────────────┘
```

**Caractéristiques** :
- Fond semi-transparent avec blur
- Gradient violet/rose sur la barre
- Animation shimmer sur la progression
- Icône 🔍 qui pulse
- Stats en temps réel

---

## 🔍 ENDPOINTS API DISPONIBLES

### Publics (tous utilisateurs)

#### GET `/api/auto-scan/status`
Statut du scanner

**Réponse** :
```json
{
  "success": true,
  "status": {
    "is_running": true,
    "scan_interval": 300,
    "tokens_per_scan": 10,
    "last_scan_time": "2025-10-22T15:30:00",
    "next_scan_in": 120,
    "stats": {
      "total_scans": 50,
      "total_tokens_found": 500,
      "total_tokens_cached": 480
    }
  }
}
```

#### GET `/api/auto-scan/tokens/recent?limit=50`
Récupère les tokens du cache (24h)

**Paramètres** :
- `limit` : nombre de tokens (max 200)
- `is_safe` : filtrer sur sécurité (true/false)
- `min_liquidity` : liquidité minimale
- `chain` : blockchain (ethereum, bsc, solana, etc.)

#### GET `/api/auto-scan/cache/stats`
Statistiques du cache MongoDB

---

### Admin uniquement

#### POST `/api/auto-scan/start`
Démarre le scanner

#### POST `/api/auto-scan/stop`
Arrête le scanner

#### POST `/api/auto-scan/force-scan`
Force un scan immédiat

#### GET/PUT `/api/auto-scan/config`
Récupère/modifie la configuration

#### POST `/api/auto-scan/cache/clear`
Vide complètement le cache

---

## 🐛 DÉPANNAGE

### La barre ne s'affiche pas

**Vérifiez** :

1. **MongoDB fonctionne** :
```bash
mongosh
# ou
mongo
```

2. **Scanner est démarré** :
```bash
curl http://localhost:5000/api/auto-scan/status
# Devrait retourner "is_running": true
```

3. **Console JavaScript** (F12) :
- Pas d'erreur dans la console ?
- L'API `/api/auto-scan/status` répond ?

### Scanner ne démarre pas automatiquement

**Vérifiez le .env** :
```bash
grep AUTO_START_SCANNER .env
# Devrait afficher: AUTO_START_SCANNER=true
```

**Vérifiez les logs au démarrage** :
```
✅ Auto-scanner démarré automatiquement
```

Si absent, le scanner n'a pas démarré.

### Erreur "MongoDB non initialisé"

**Installez et démarrez MongoDB** :

```bash
# Linux (Ubuntu/Debian)
sudo apt-get install mongodb
sudo systemctl start mongodb

# macOS
brew install mongodb-community
brew services start mongodb-community

# Vérifier
mongosh
```

**Vérifiez le MONGODB_URI dans .env** :
```bash
MONGODB_URI=mongodb://localhost:27017/
```

---

## 📈 PERFORMANCES

### Recommandations

**Intervalle de scan** :
- **Development** : 300s (5 min) - bon compromis
- **Production** : 600s (10 min) - économise les ressources
- **Testing** : 60s (1 min) - tests rapides

**Tokens par scan** :
- **Light** : 5-10 tokens (rapide, moins de charge)
- **Standard** : 10-20 tokens (équilibré)
- **Aggressive** : 20-50 tokens (max d'infos, plus lent)

**Calcul de charge** :
```
Scans/jour = (24h * 3600s) / scan_interval
Tokens/jour = Scans/jour * tokens_per_scan

Exemple (défaut):
= (86400s) / 300s * 10
= 288 scans * 10 tokens
= 2,880 tokens/jour
```

---

## ✅ CHECKLIST D'ACTIVATION

- [ ] MongoDB installé et démarré
- [ ] MONGODB_URI configuré dans .env
- [ ] AUTO_START_SCANNER=true dans .env
- [ ] (Optionnel) SCAN_INTERVAL et TOKENS_PER_SCAN configurés
- [ ] Flask redémarré
- [ ] Message "✅ Auto-scanner démarré automatiquement" affiché
- [ ] Barre de progression apparaît en haut de http://localhost:5000
- [ ] API `/api/auto-scan/status` répond
- [ ] Tokens apparaissent dans le cache après 5 min

---

## 🎯 EXEMPLE COMPLET .env

```bash
# Flask
SECRET_KEY=your-super-secret-key-min-32-chars-here
FLASK_ENV=development
FLASK_DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://192.168.1.19:5000

# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=token_scanner_cache

# Auto-Scan
AUTO_START_SCANNER=true
SCAN_INTERVAL=300
TOKENS_PER_SCAN=10

# Nitter
NITTER_URL=http://localhost:8080

# Claude AI (optionnel)
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

---

## 🚀 COMMANDES UTILES

```bash
# Démarrer l'app avec auto-scan
cd /home/jimmy/script/claude_V2/token_scanner_pro/token_scanner_pro
python app.py

# Vérifier le statut
curl http://localhost:5000/api/auto-scan/status | jq

# Voir les tokens récents
curl http://localhost:5000/api/auto-scan/tokens/recent?limit=5 | jq

# Forcer un scan (admin)
curl -X POST http://localhost:5000/api/auto-scan/force-scan

# Arrêter le scan (admin)
curl -X POST http://localhost:5000/api/auto-scan/stop
```

---

**Enjoy le scanning automatique ! 🎉**
