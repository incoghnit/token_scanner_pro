# 🔧 Fix WebSocket 400 Error - Instructions de Redémarrage

## 🎯 Problème
```
GET /socket.io/?EIO=4&transport=websocket HTTP/1.1" 400
```

Les tokens découverts automatiquement ne s'affichent pas en temps réel.

## ✅ Solution Appliquée

### 1. Table BDD créée ✅
La table `scanned_tokens` a été créée dans `token_scanner.db`.

### 2. Configuration CORS mise à jour ✅
Le fichier `.env` a été modifié pour autoriser les connexions réseau:
```bash
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://0.0.0.0:5000,http://21.0.0.104:5000,http://192.168.1.12:5000,*
```

## 🚀 REDÉMARRAGE REQUIS

**⚠️ ACTION NÉCESSAIRE:** Vous DEVEZ redémarrer le serveur Flask pour que les changements prennent effet.

### Étapes de redémarrage:

#### 1. Arrêter le serveur actuel
```bash
# Dans le terminal où le serveur tourne:
# Appuyez sur Ctrl + C
```

#### 2. Relancer le serveur
```bash
cd /home/user/token_scanner_pro/token_scanner_pro
python app.py
```

#### 3. Vérifier le démarrage
Vous devriez voir:
```
╔═══════════════════════════════════════════════════════════╗
║   TOKEN SCANNER PRO - UX PREMIUM + DISCOVERY SERVICE     ║
║                                                           ║
║   🌐 Accès local:    http://localhost:5000               ║
║   🌐 Accès réseau:   http://21.0.0.104:5000              ║
║   🔌 WebSocket:      ws://localhost:5000                 ║
║                                                           ║
║   ✅ Système d'authentification activé                    ║
║   ✅ Token Discovery Service (centralisé)                 ║
║   ✅ WebSocket temps réel activé                          ║
║   ✅ Auto-scan + Cache MongoDB activé                     ║
╚═══════════════════════════════════════════════════════════╝

✅ Auto-discovery démarré (intervalle: 180s, max_tokens: 20)
```

## 🧪 Tests à effectuer après redémarrage

### Test 1: Connexion WebSocket
1. Ouvrez la console du navigateur (F12)
2. Rechargez la page
3. Vous devriez voir:
   ```
   🔌 Initialisation Discovery Service...
   ✅ Connecté au Discovery Service
   ```

### Test 2: Badge de statut
Le badge en haut de la page devrait afficher:
- **Connecté** (vert) ✅

Au lieu de:
- **En attente...** (orange) ⏳

### Test 3: Affichage des tokens
Dans la section **"🆕 Derniers Tokens Découverts"**, vous devriez voir:
- Des cartes de tokens apparaître automatiquement
- Animation fadeInScale au chargement
- Mise à jour toutes les 3 minutes

### Test 4: Logs serveur
Dans les logs du serveur, vous devriez voir (toutes les 3 min):
```
🔍 Discovery scan démarré - Max tokens: 20
💾 X/20 tokens stockés dans la BDD
📡 Broadcasting X tokens to all connected clients
✅ Discovery scan terminé
```

### Test 5: Aucune erreur WebSocket
Les logs NE doivent PLUS afficher:
```
❌ GET /socket.io/?EIO=4&transport=websocket HTTP/1.1" 400
```

Mais plutôt:
```
✅ GET /socket.io/?EIO=4&transport=websocket HTTP/1.1" 101 (Switching Protocols)
```

## 🔍 Vérification de la BDD

Pour vérifier que la table existe bien:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('token_scanner.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM scanned_tokens')
print(f'Tokens dans BDD: {cursor.fetchone()[0]}')
conn.close()
"
```

## 📊 Architecture du système

```
┌─────────────────────────────────────────────────────┐
│              TOKEN DISCOVERY SYSTEM                 │
└─────────────────────────────────────────────────────┘

SERVEUR PYTHON (Flask + SocketIO)
    │
    ├─→ 1. Timer automatique (toutes les 3 minutes)
    │      └─→ trigger_scan()
    │
    ├─→ 2. Appels API (DexScreener, GoPlus, etc.)
    │      └─→ Récupère 20 nouveaux tokens
    │
    ├─→ 3. Stockage dans SQLite
    │      └─→ INSERT INTO scanned_tokens
    │
    ├─→ 4. Broadcasting WebSocket
    │      └─→ socketio.emit('new_token')
    │
    ↓

CLIENT JAVASCRIPT (Browser)
    │
    ├─→ 5. Réception événement 'new_token'
    │      └─→ socket.on('new_token', callback)
    │
    └─→ 6. Affichage dynamique
           └─→ addDiscoveredToken() → Création carte HTML
```

## ⚙️ Configuration CORS

Pour autoriser d'autres IPs réseau, modifiez `.env`:
```bash
# Trouver votre IP serveur:
hostname -I

# Exemple avec IP 192.168.1.100:
ALLOWED_ORIGINS=http://localhost:5000,http://192.168.1.100:5000,*
```

⚠️ Le wildcard `*` est **UNIQUEMENT pour le développement**, pas pour la production!

## 🆘 Dépannage

### WebSocket toujours en erreur 400
- ✅ Vérifiez que le serveur a bien été redémarré
- ✅ Vérifiez que `.env` contient votre IP réseau
- ✅ Videz le cache du navigateur (Ctrl + Shift + R)

### Aucun token ne s'affiche
- ✅ Vérifiez que la table existe: `SELECT name FROM sqlite_master WHERE name='scanned_tokens'`
- ✅ Vérifiez les logs serveur pour voir si le scan démarre
- ✅ Attendez 3 minutes pour le premier scan

### Rate limiting 429
- ✅ Rafraîchissez moins souvent la page
- ✅ Les limites: 200 requêtes/jour, 50 requêtes/heure

## 📝 Fichiers modifiés

- ✅ `.env` - Configuration CORS mise à jour
- ✅ `.env.example` - Documentation ajoutée
- ✅ `token_scanner.db` - Table scanned_tokens créée
- ✅ `index.html` - UI dual-section implémentée

## 🎯 Résultat attendu

Une fois redémarré correctement:
1. ✅ WebSocket connecté (badge vert)
2. ✅ Tokens apparaissent automatiquement toutes les 3 minutes
3. ✅ Section 1: Tokens découverts (partagés avec tous)
4. ✅ Section 2: Recherche spécifique (privée)
5. ✅ Animations fluides (fadeInScale, pulse)

---

**Date de création:** 27 octobre 2025
**Commit:** `2beaecf` - Document CORS configuration for WebSocket network access
