# 🚨 PROBLÈME: Index.html ne charge plus

## ❌ LE PROBLÈME

Vous essayez probablement d'ouvrir `index.html` **directement dans le navigateur** (file:///).

**Cela ne peut PAS fonctionner** car:

1. **Jinja2 Templates** : Le fichier utilise `{% include 'components_nav.html' %}` qui ne fonctionne que via Flask
2. **Appels API** : Le JavaScript fait des appels à `/api/me`, `/api/favorites`, etc. qui n'existent pas en `file://`
3. **Pas de serveur** : Il n'y a pas de backend pour traiter les requêtes

## ✅ LA SOLUTION

Vous devez **démarrer l'application Flask** via le serveur.

---

## 📋 INSTRUCTIONS ÉTAPE PAR ÉTAPE

### 1. **Vérifier que vous êtes dans le bon répertoire**

```bash
cd /home/user/token_scanner_pro
pwd  # Devrait afficher: /home/user/token_scanner_pro
```

### 2. **Activer l'environnement virtuel Python**

```bash
# Si venv existe déjà
source venv/bin/activate

# Vous devriez voir (venv) devant votre prompt
```

### 3. **Installer les dépendances** (si pas déjà fait)

```bash
pip install -r token_scanner_pro/requirements.txt
```

### 4. **Configurer le fichier .env** (IMPORTANT)

```bash
# Copier l'exemple
cp .env.example .env

# Éditer le fichier
nano .env
```

**Ajouter au minimum ces variables** :

```bash
# Dans .env
SECRET_KEY=votre-cle-secrete-aleatoire-minimum-32-caracteres

# Nitter Configuration
NITTER_URL=http://localhost:8080

# CORS Security
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000

# MongoDB (optionnel si vous l'utilisez)
MONGODB_URI=mongodb://localhost:27017/

# Anthropic API (pour Claude AI - optionnel)
ANTHROPIC_API_KEY=sk-ant-votre-cle-ici
```

### 5. **Démarrer l'application Flask**

```bash
cd token_scanner_pro
python app.py
```

Vous devriez voir quelque chose comme :

```
✅ Services auto-scan initialisés
✅ Système d'alertes initialisé

╔═══════════════════════════════════════════════════════════╗
║   TOKEN SCANNER PRO - UX PREMIUM + AUTO-SCAN             ║
║                                                           ║
║   🌐 Accès local:    http://localhost:5000               ║
║   🌐 Accès réseau:   http://192.168.x.x:5000             ║
║                                                           ║
║   ✅ Système d'authentification activé                    ║
║   ✅ Auto-scan + Cache MongoDB activé                     ║
║   ✅ Favoris + Historique activés                         ║
║   ✅ Routes API complètes                                 ║
╚═══════════════════════════════════════════════════════════╝

 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.x.x:5000
```

### 6. **Ouvrir dans le navigateur**

```
http://localhost:5000
```

**PAS** `file:///chemin/vers/index.html` ❌
**MAIS** `http://localhost:5000` ✅

---

## 🐛 SI ÇA NE FONCTIONNE PAS

### Erreur: `ModuleNotFoundError: No module named 'flask'`

```bash
# Activer venv
source venv/bin/activate

# Installer Flask
pip install flask flask-cors

# Ou installer tout
pip install -r token_scanner_pro/requirements.txt
```

### Erreur: `AttributeError: 'Database' object has no attribute 'authenticate_user'`

```bash
# Pull les dernières modifications
git pull origin claude/code-review-011CUM3mdzTijSH9qxijjbWU

# Redémarrer l'app
cd token_scanner_pro
python app.py
```

### Erreur: Port 5000 déjà utilisé

```bash
# Option 1: Tuer le processus existant
lsof -ti:5000 | xargs kill -9

# Option 2: Utiliser un autre port
# Éditer app.py, ligne 632:
port=5001  # Au lieu de 5000
```

### Page blanche / Pas de chargement

1. **Ouvrir la Console JavaScript** (F12 → Console)
2. **Vérifier les erreurs** dans l'onglet Network
3. **Vérifier que Flask tourne** dans le terminal

---

## 📊 VÉRIFICATION

Une fois l'app démarrée, testez:

```bash
# Dans un autre terminal
curl http://localhost:5000/api/health

# Devrait retourner du JSON avec "success": true
```

---

## 🎯 CHECKLIST

- [ ] `cd /home/user/token_scanner_pro`
- [ ] `source venv/bin/activate` (si venv existe)
- [ ] `pip install -r token_scanner_pro/requirements.txt`
- [ ] Créer/éditer `.env` avec SECRET_KEY
- [ ] `cd token_scanner_pro && python app.py`
- [ ] Ouvrir `http://localhost:5000` (PAS file://)
- [ ] Voir la page charger avec navigation

---

## 💡 POURQUOI ÇA NE MARCHE PAS EN FILE:// ?

```html
<!-- Ce code dans index.html -->
{% include 'components_nav.html' %}
```

**Jinja2** (template engine) ne fonctionne que côté serveur (Flask).
En ouvrant directement le fichier HTML, le navigateur voit littéralement `{% include ... %}` comme du texte, pas comme une instruction.

**De plus**, tous les appels JavaScript:

```javascript
fetch('/api/me')  // ❌ Ne fonctionne pas en file://
fetch('/api/favorites')  // ❌ Besoin d'un serveur Flask
```

Ces endpoints n'existent QUE quand Flask tourne !

---

## 🚀 COMMANDE RAPIDE (TOUT EN UN)

```bash
cd /home/user/token_scanner_pro && \
source venv/bin/activate && \
cd token_scanner_pro && \
python app.py
```

Puis ouvrir: **http://localhost:5000**

---

**Résumé**: Vous devez démarrer Flask, pas ouvrir index.html directement !
