# 🚀 REDÉMARRAGE DU SERVEUR - GUIDE RAPIDE

## ⚠️ POURQUOI REDÉMARRER?

Votre serveur Flask doit être redémarré pour:
1. ✅ Charger la nouvelle configuration CORS (`.env` modifié)
2. ✅ Permettre les connexions WebSocket depuis `192.168.1.19`
3. ✅ Afficher les tokens en temps réel dans le frontend

---

## 🔧 PROBLÈMES ACTUELS (AVANT REDÉMARRAGE)

### 1. WebSocket échoue ❌
```
WebSocket connection to 'ws://192.168.1.19:5000/socket.io/?EIO=4&transport=websocket' failed
```

### 2. JavaScript error corrigé ✅
```
✅ RÉSOLU: Cannot read properties of null (reading 'style')
```

### 3. Rate limiting 429 ⚠️
```
GET http://192.168.1.19:5000/api/auto-scan/status 429 (TOO MANY REQUESTS)
```
*Causé par des reconnexions WebSocket trop fréquentes*

---

## 📋 ÉTAPES DE REDÉMARRAGE

### ÉTAPE 1: Arrêter le serveur actuel

Dans le terminal où le serveur Flask tourne actuellement:

```bash
# Appuyez sur:
Ctrl + C
```

Vous devriez voir:
```
^C
Keyboard interrupt received, exiting...
```

### ÉTAPE 2: Naviguer vers le dossier

```bash
cd /home/user/token_scanner_pro/token_scanner_pro
```

### ÉTAPE 3: Vérifier que Python est disponible

```bash
python3 --version
# Devrait afficher: Python 3.x.x
```

### ÉTAPE 4: Lancer le serveur

```bash
python3 app.py
```

OU si vous utilisez `python` (sans le 3):

```bash
python app.py
```

### ÉTAPE 5: Vérifier le démarrage réussi

Vous devriez voir cette bannière:

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
║   ✅ Favoris + Historique activés                         ║
║   ✅ Routes API complètes                                 ║
╚═══════════════════════════════════════════════════════════╝

✅ Auto-discovery démarré (intervalle: 180s, max_tokens: 20)
✅ Auto-cleanup activé (intervalle: 24h, âge: 24h)
```

**Points clés à vérifier:**
- ✅ `Token Discovery Service (centralisé)` apparaît
- ✅ `WebSocket temps réel activé` apparaît
- ✅ `Auto-discovery démarré` apparaît
- ✅ Aucune erreur rouge

---

## 🧪 TESTS APRÈS REDÉMARRAGE

### Test 1: Ouvrir le navigateur

```
http://192.168.1.19:5000
```

### Test 2: Vérifier la console (F12)

Ouvrez la console JavaScript et vous devriez voir:

**✅ AVANT (échec):**
```
❌ WebSocket connection failed
```

**✅ APRÈS (succès):**
```javascript
🔌 Initialisation Discovery Service...
✅ Connecté au Discovery Service
📦 Chargement de X tokens existants
```

### Test 3: Vérifier le badge de statut

Sur la page, dans la section "🆕 Derniers Tokens Découverts":

**❌ AVANT redémarrage:**
```
⏳ En attente...  (badge orange)
```

**✅ APRÈS redémarrage:**
```
✅ Connecté  (badge vert avec pulse)
```

### Test 4: Vérifier les logs serveur

Dans le terminal du serveur, après 3 minutes maximum:

```
🔍 Discovery scan démarré - Max tokens: 20
💾 15/20 tokens stockés dans la BDD
📡 Broadcasting 15 tokens to all connected clients
✅ Discovery scan terminé
```

### Test 5: Vérifier l'affichage des tokens

Dans la section "🆕 Derniers Tokens Découverts":
- ✅ Des cartes de tokens apparaissent
- ✅ Animation fadeInScale au chargement
- ✅ Hover effect (la carte monte légèrement au survol)
- ✅ Bouton "Voir les détails" fonctionnel

---

## 🛑 EN CAS DE PROBLÈME

### Problème: "Address already in use"

**Erreur:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
Un ancien processus occupe encore le port 5000.

```bash
# Trouver le processus:
lsof -i :5000

# Ou:
ps aux | grep app.py

# Tuer le processus (remplacer PID par le numéro):
kill -9 PID
```

### Problème: "ModuleNotFoundError"

**Erreur:**
```
ModuleNotFoundError: No module named 'flask_socketio'
```

**Solution:**
Installer les dépendances manquantes:

```bash
pip install -r requirements.txt
```

### Problème: WebSocket toujours en erreur

**Vérifications:**
1. Le serveur a-t-il bien été redémarré? ✅
2. Videz le cache du navigateur: `Ctrl + Shift + R`
3. Vérifiez `.env` contient bien le wildcard `*`
4. Vérifiez que vous accédez via l'IP correcte

---

## 📊 MODIFICATIONS APPLIQUÉES

### Fichiers modifiés:

#### 1. `index.html` (lignes 1589-1594)
**AVANT:**
```javascript
function loadTokensFromDatabase() {
    // 100 lignes de code qui causaient l'erreur
    scanResults.style.display = 'block';  // ❌ scanResults est null
}
```

**APRÈS:**
```javascript
function loadTokensFromDatabase() {
    console.log('🔄 loadTokensFromDatabase() called (redirecting to loadExistingTokens)...');
    await loadExistingTokens();  // ✅ Utilise le nouveau système
}
```

#### 2. `.env` (ligne 34)
**AVANT:**
```bash
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://0.0.0.0:5000,http://21.0.0.104:5000,http://192.168.1.12:5000,*
```

**APRÈS:**
```bash
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://0.0.0.0:5000,http://21.0.0.104:5000,http://192.168.1.12:5000,http://192.168.1.19:5000,*
```

---

## ✅ RÉSULTAT ATTENDU

Une fois le serveur redémarré:

### Frontend:
1. ✅ Aucune erreur WebSocket
2. ✅ Badge "Connecté" (vert)
3. ✅ Tokens apparaissent dans "Derniers Tokens Découverts"
4. ✅ Section 1 (tokens découverts) = partagée en temps réel
5. ✅ Section 2 (recherche spécifique) = privée

### Backend (logs serveur):
1. ✅ Auto-discovery démarre au lancement
2. ✅ Scan toutes les 3 minutes
3. ✅ Broadcasting via WebSocket
4. ✅ Aucune erreur HTTP 400

---

## 🎯 COMMANDE COMPLÈTE (COPIER-COLLER)

```bash
# 1. Arrêter serveur actuel (Ctrl+C dans le terminal serveur)

# 2. Redémarrer
cd /home/user/token_scanner_pro/token_scanner_pro && python3 app.py
```

---

**Date:** 27 octobre 2025
**Problème:** WebSocket 400 + JavaScript null reference
**Solution:** Fix JS + Update CORS + Restart server
**Statut:** ⚠️ Redémarrage requis
