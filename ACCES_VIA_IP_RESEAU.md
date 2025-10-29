# 🌐 ACCÈS VIA IP RÉSEAU LOCAL

## ✅ OUI, vous pouvez accéder depuis n'importe quel appareil sur votre réseau !

L'application Flask est configurée avec `host='0.0.0.0'`, ce qui signifie qu'elle écoute sur **toutes les interfaces réseau**.

---

## 📋 ÉTAPES POUR ACCÉDER VIA IP

### 1. **Démarrer l'application Flask**

```bash
cd /home/user/token_scanner_pro/token_scanner_pro
python app.py
```

### 2. **Trouver l'IP de la machine serveur**

Quand Flask démarre, il affiche automatiquement l'IP :

```
╔═══════════════════════════════════════════════════════════╗
║   🌐 Accès local:    http://localhost:5000               ║
║   🌐 Accès réseau:   http://192.168.1.19:5000            ║  ← CETTE IP !
╚═══════════════════════════════════════════════════════════╝
```

**Ou trouvez-la manuellement** :

```bash
# Linux/Mac
hostname -I | awk '{print $1}'

# Ou
ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1

# Exemple de résultat: 192.168.1.19
```

### 3. **Accéder depuis un autre appareil**

Sur **n'importe quel appareil** connecté au même WiFi/réseau :

- **Ordinateur** : Ouvrir le navigateur → `http://192.168.1.19:5000`
- **Téléphone** : Ouvrir Chrome/Safari → `http://192.168.1.19:5000`
- **Tablette** : Ouvrir le navigateur → `http://192.168.1.19:5000`

**Remplacez** `192.168.1.19` par **votre IP réelle** affichée dans le terminal.

---

## ⚙️ CONFIGURATION CORS (IMPORTANT)

### Vérifier le .env

Pour que l'accès depuis d'autres IPs fonctionne, **ajoutez l'IP au CORS** :

```bash
# Éditez le fichier .env
nano .env
```

**Ajoutez votre IP réseau** :

```bash
# Avant (par défaut)
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000

# Après (ajoutez votre IP)
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://192.168.1.19:5000
```

**Ou autorisez tout le réseau local** (moins sécurisé mais pratique) :

```bash
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://192.168.*:5000
```

**Puis redémarrez Flask** pour appliquer les changements.

---

## 🔥 PROBLÈMES COURANTS

### 1. **Erreur CORS** (Cross-Origin Request Blocked)

**Symptôme** : Page charge mais les requêtes API échouent

**Solution** :
```bash
# Ajouter votre IP dans .env
ALLOWED_ORIGINS=http://localhost:5000,http://192.168.1.19:5000

# Redémarrer Flask
```

### 2. **Connexion refusée** (Connection Refused)

**Causes possibles** :

#### A. Firewall bloque le port 5000

**Linux** :
```bash
# Autoriser le port 5000
sudo ufw allow 5000

# Vérifier
sudo ufw status
```

**macOS** :
```bash
# Désactiver temporairement le firewall pour tester
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# Réactiver après test
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

**Windows** :
```powershell
# Ouvrir PowerShell en Admin
New-NetFirewallRule -DisplayName "Flask App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

#### B. Flask n'écoute que sur localhost

**Vérifiez dans `app.py` ligne 632** :

```python
# ✅ BON (écoute sur toutes les interfaces)
app.run(host='0.0.0.0', port=5000)

# ❌ MAUVAIS (écoute uniquement en local)
app.run(host='127.0.0.1', port=5000)
```

Le code actuel utilise déjà `0.0.0.0`, donc c'est bon ✅

### 3. **Page s'affiche mais API ne répond pas**

**Symptôme** : Page HTML charge mais les données ne s'affichent pas

**Cause** : Le JavaScript essaie d'appeler `http://localhost:5000/api/...` au lieu de l'IP

**Solution** : Le code est déjà configuré pour utiliser des URLs relatives (`/api/...`), donc ça devrait fonctionner automatiquement.

### 4. **"Aucune route" / "Cannot GET /"**

**Symptôme** : Erreur 404 ou "Cannot GET /"

**Cause** : Flask n'a pas démarré correctement

**Solution** :
```bash
# Arrêter Flask (Ctrl+C)
# Vérifier les erreurs dans le terminal
# Redémarrer
cd token_scanner_pro
python app.py
```

---

## 🧪 TESTER LA CONNEXION

### Test 1 : Ping depuis l'autre appareil

```bash
# Sur l'autre appareil (ordinateur/téléphone en SSH)
ping 192.168.1.19

# Devrait répondre avec des temps de réponse
```

### Test 2 : Tester l'API directement

```bash
# Sur l'autre appareil
curl http://192.168.1.19:5000/api/health

# Devrait retourner du JSON avec "success": true
```

### Test 3 : Ouvrir dans le navigateur

```
http://192.168.1.19:5000
```

Vous devriez voir la page d'accueil avec navigation.

---

## 📱 ACCÈS DEPUIS TÉLÉPHONE

### Sur iPhone/iPad (Safari)

1. Ouvrir Safari
2. Aller à : `http://192.168.1.19:5000`
3. Ajouter à l'écran d'accueil : Bouton Partager → "Sur l'écran d'accueil"
4. L'app s'ouvre comme une app native !

### Sur Android (Chrome)

1. Ouvrir Chrome
2. Aller à : `http://192.168.1.19:5000`
3. Menu (3 points) → "Ajouter à l'écran d'accueil"
4. L'app s'ouvre comme une app native !

---

## 🔒 SÉCURITÉ

### ⚠️ ATTENTION : Accès réseau local uniquement

L'application est accessible **uniquement sur votre réseau local** (WiFi).

**PAS accessible depuis Internet** (bon pour la sécurité).

### Pour accès depuis Internet (NON RECOMMANDÉ sans HTTPS)

Si vous voulez vraiment rendre l'app accessible depuis Internet :

1. **Configurer un tunnel** (Ngrok, Cloudflare Tunnel)
2. **Ou configurer un reverse proxy** (Nginx) avec HTTPS
3. **Ou déployer sur un serveur** (VPS, cloud)

**⚠️ Ne PAS exposer directement le port 5000 sur Internet sans HTTPS !**

---

## 📊 RÉCAPITULATIF RAPIDE

```bash
# 1. Démarrer Flask
cd /home/user/token_scanner_pro/token_scanner_pro
python app.py

# 2. Noter l'IP affichée (ex: 192.168.1.19)

# 3. Ajouter l'IP au .env
nano .env
# Ajouter: ALLOWED_ORIGINS=...,http://192.168.1.19:5000

# 4. Redémarrer Flask

# 5. Accéder depuis autre appareil
# http://192.168.1.19:5000
```

---

## ✅ CHECKLIST

- [ ] Flask démarre sans erreur
- [ ] IP réseau affichée dans le terminal
- [ ] IP ajoutée dans `ALLOWED_ORIGINS` du .env
- [ ] Firewall autorise le port 5000 (si activé)
- [ ] Les deux appareils sont sur le même WiFi/réseau
- [ ] Peut ping l'IP depuis l'autre appareil
- [ ] URL : `http://[VOTRE_IP]:5000` (pas `https://`)
- [ ] Ouvrir dans navigateur de l'autre appareil

---

## 💡 ASTUCE : URL QR Code

Pour faciliter l'accès depuis mobile :

```bash
# Installer qrencode
sudo apt-get install qrencode  # Linux
brew install qrencode          # Mac

# Générer un QR code de l'URL
qrencode -t ANSIUTF8 "http://192.168.1.19:5000"
```

Scannez le QR code avec votre téléphone → Accès direct !

---

**En résumé** : Oui, vous pouvez accéder via IP ! Il suffit de :
1. Démarrer Flask
2. Ajouter l'IP dans ALLOWED_ORIGINS
3. Ouvrir `http://[VOTRE_IP]:5000` depuis n'importe quel appareil du réseau
