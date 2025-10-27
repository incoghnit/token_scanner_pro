# 🚀 Token Scanner Pro - Guide de Démarrage Rapide

Ce guide vous permet de lancer l'application en **moins de 15 minutes**.

---

## 📋 Prérequis

- **Python 3.9+** installé
- **pip** (gestionnaire de paquets Python)
- Connexion Internet

---

## ⚡ Installation en 5 Étapes

### 1️⃣ Cloner le Repository

```bash
git clone <repository-url>
cd token_scanner_pro
```

### 2️⃣ Créer un Environnement Virtuel

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur Windows:
venv\Scripts\activate
# Sur Linux/Mac:
source venv/bin/activate
```

### 3️⃣ Installer les Dépendances

```bash
pip install -r token_scanner_pro/requirements.txt
```

**Note**: Si `TA-Lib` pose problème, commentez cette ligne dans `requirements.txt` (la librairie `ta` est déjà incluse comme alternative).

### 4️⃣ Configurer les Clés API

Copiez le fichier d'exemple et éditez-le :

```bash
cp .env.example .env
nano .env  # ou utilisez votre éditeur préféré
```

**Remplacez les valeurs suivantes** (OBLIGATOIRE) :

```bash
# Ligne 52 - Moralis API (GRATUIT)
MORALIS_API_KEY=votre_clé_moralis_ici

# Lignes 8-9 - Claude API (PAYANT)
CLAUDE_API_KEY=votre_clé_claude_ici
ANTHROPIC_API_KEY=votre_clé_claude_ici

# Ligne 57 - Birdeye API (GRATUIT)
BIRDEYE_API_KEY=votre_clé_birdeye_ici
```

### 5️⃣ Lancer l'Application

```bash
python start_server.py
```

Ou directement :

```bash
python token_scanner_pro/app.py
```

**Accédez à l'application** : [http://localhost:5000](http://localhost:5000)

---

## 🔑 Obtenir les Clés API Gratuites

### 1. **Moralis API** (5 minutes) - ✅ GRATUIT

1. Allez sur [https://admin.moralis.io/web3apis](https://admin.moralis.io/web3apis)
2. Créez un compte gratuit
3. Créez un nouveau projet
4. Copiez la clé API depuis le dashboard
5. Collez-la dans `.env` à la ligne `MORALIS_API_KEY=`

**Utilisé pour** : Prix en temps réel, métadonnées des tokens

---

### 2. **Claude AI API** (10 minutes) - ⚠️ PAYANT (~$0.003/requête)

1. Allez sur [https://console.anthropic.com/](https://console.anthropic.com/)
2. Créez un compte Anthropic
3. Ajoutez des crédits (minimum $5)
4. Copiez la clé API
5. Collez-la dans `.env` aux lignes `CLAUDE_API_KEY=` et `ANTHROPIC_API_KEY=`

**Utilisé pour** : Analyse IA des tokens, validation des trades

**Alternative GRATUITE** : Commentez les fonctions d'IA dans `api_routes.py` si vous ne voulez pas payer

---

### 3. **Birdeye API** (5 minutes) - ✅ GRATUIT

1. Allez sur [https://birdeye.so/developers](https://birdeye.so/developers)
2. Créez un compte gratuit
3. Générez une clé API
4. Collez-la dans `.env` à la ligne `BIRDEYE_API_KEY=`

**Utilisé pour** : Analyse technique (RSI, MACD, signaux de trading)

---

## ✅ Clés API Déjà Configurées (Aucune Action Requise)

- **CoinDesk API** - Flux d'actualités crypto
- **CoinMarketCap API** - Recherche de tokens
- **DexScreener API** - Données de marché (pas de clé nécessaire)
- **GoPlus Labs API** - Sécurité des tokens (pas de clé nécessaire)

---

## 🎯 Fonctionnalités Disponibles Immédiatement

### Sans Aucune Clé API (Mode Limité)
- ✅ Scan de tokens via URL DexScreener
- ✅ Détection de sécurité (GoPlus)
- ✅ Détection de pump & dump
- ✅ Affichage des holders
- ✅ Liens sociaux (Twitter, Telegram, Discord)

### Avec Moralis API
- ✅ **Rafraîchissement des prix en temps réel**
- ✅ Métadonnées complètes des tokens
- ✅ Support multi-chain (Ethereum, BSC, Solana, etc.)

### Avec Claude API
- ✅ **Analyse IA approfondie des tokens**
- ✅ Validation des stratégies de trading
- ✅ Recommandations personnalisées

### Avec Birdeye API
- ✅ **Analyse technique complète** (RSI, MACD, Bollinger Bands)
- ✅ **Signaux de trading** (BUY/SELL/HOLD)
- ✅ Support/Résistance
- ✅ Niveaux de Fibonacci

---

## 🔧 Dépannage Rapide

### Erreur: "Module not found"
```bash
# Assurez-vous que l'environnement virtuel est activé
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Réinstallez les dépendances
pip install -r token_scanner_pro/requirements.txt
```

### Erreur: "TA-Lib installation failed"
```bash
# Option 1: Supprimer TA-Lib de requirements.txt (ligne 36)
# L'app utilisera automatiquement la librairie 'ta' à la place

# Option 2: Installer les dépendances système
# Ubuntu/Debian:
sudo apt-get install ta-lib
# macOS:
brew install ta-lib
```

### Erreur: "Port 5000 already in use"
```bash
# Changez le port dans .env
PORT=5001

# Ou tuez le processus sur le port 5000
# Linux/Mac:
lsof -ti:5000 | xargs kill -9
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Les prix ne se rafraîchissent pas
1. Vérifiez que `MORALIS_API_KEY` est correctement configuré dans `.env`
2. Vérifiez que votre clé Moralis est valide (testez sur leur dashboard)
3. Redémarrez le serveur

### L'analyse IA ne fonctionne pas
1. Vérifiez que `CLAUDE_API_KEY` est configuré
2. Vérifiez que vous avez des crédits sur votre compte Anthropic
3. Testez la clé API sur [https://console.anthropic.com/](https://console.anthropic.com/)

---

## 📊 Base de Données (Optionnel)

Par défaut, l'application utilise **SQLite** (fichier local, aucune configuration requise).

Pour utiliser **MongoDB** (recommandé pour production) :

```bash
# Installer MongoDB
# Ubuntu/Debian:
sudo apt-get install mongodb

# macOS:
brew install mongodb-community

# Démarrer MongoDB
sudo systemctl start mongodb  # Linux
brew services start mongodb-community  # macOS

# Modifier .env
MONGODB_URI=mongodb://localhost:27017/token_scanner_pro
```

---

## 🌐 Accès depuis d'autres Appareils

Pour accéder à l'application depuis d'autres appareils sur votre réseau local :

1. Trouvez votre adresse IP locale :
```bash
# Linux/Mac:
ifconfig | grep inet
# Windows:
ipconfig
```

2. Modifiez `.env` :
```bash
HOST=0.0.0.0  # Écouter sur toutes les interfaces
PORT=5000
```

3. Accédez depuis un autre appareil :
```
http://VOTRE_IP_LOCALE:5000
# Exemple: http://192.168.1.100:5000
```

**Consultez** : `ACCES_VIA_IP_RESEAU.md` pour plus de détails

---

## 📚 Documentation Complète

- **README.md** - Documentation principale
- **BUSINESS_PLAN.md** - Plan d'affaires et modèle économique
- **DATABASE_STRATEGY.md** - Architecture base de données
- **TOKEN_PERSISTENCE_GUIDE.md** - Persistance des données
- **AUTO_SCAN_GUIDE.md** - Configuration du scanner automatique
- **ACCES_VIA_IP_RESEAU.md** - Accès réseau local

---

## 🆘 Support

Si vous rencontrez des problèmes :

1. Consultez la section **Dépannage Rapide** ci-dessus
2. Vérifiez les logs dans le terminal
3. Lisez la documentation complète dans `README.md`
4. Ouvrez une issue sur GitHub

---

## 🎉 C'est Parti !

L'application devrait maintenant fonctionner. Testez en scannant un token :

1. Allez sur [DexScreener](https://dexscreener.com/)
2. Trouvez un token (ex: Solana token)
3. Copiez l'URL
4. Collez-la dans la barre de recherche de Token Scanner Pro
5. Analysez ! 🚀

---

**Version** : 2.0
**Dernière mise à jour** : 2025-10-27
**Auteur** : Token Scanner Pro Team
