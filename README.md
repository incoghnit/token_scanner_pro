# 🔍 Token Scanner Pro

**Scanner de tokens crypto avancé avec détection Pump & Dump, analyse RSI, Fibonacci et recherche intelligente**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API Endpoints](#-api-endpoints)
- [Système d'alertes](#-système-dalertes)
- [Admin Panel](#-admin-panel)
- [Technologies](#-technologies)
- [Captures d'écran](#-captures-décran)
- [Contributions](#-contributions)
- [License](#-license)

---

## ✨ Fonctionnalités

### 🔬 Analyse Avancée
- **RSI (Relative Strength Index)** - Détection de zones de surachat/survente
- **Niveaux de Fibonacci** - Identification des supports et résistances
- **Détection Pump & Dump** - Adaptée aux nouveaux tokens (<72h)
- **Score de risque** - Évaluation globale de 0 à 100
- **Analyse sociale** - Scraping Twitter via Nitter
- **Top 5 Holders** - Concentration des portefeuilles

### 🔍 Recherche Intelligente
- Recherche par nom, symbole ou adresse
- API DexScreener intégrée
- Analyse instantanée de n'importe quel token
- Support multi-chaînes (Solana, Ethereum, BSC, Base, Arbitrum)

### 👤 Système de Comptes
- **Authentification** sécurisée avec hash bcrypt
- **Favoris** - Sauvegarde de tokens à surveiller
- **Historique** - Tous les scans sauvegardés
- **Statistiques** personnalisées

### 🚨 Alertes Premium
- Surveillance automatique des favoris (toutes les heures)
- **Emails HTML** élégants avec métriques
- Alertes RSI, Fibonacci, Pump & Dump
- Notifications web en temps réel

### 🛡️ Admin Panel
- Gestion des utilisateurs
- Attribution de comptes Premium
- Logs d'administration
- Statistiques globales

---

## 🏗️ Architecture

```
token_scanner_pro/
├── app.py                    # Serveur Flask principal
├── scanner_core.py           # Moteur d'analyse (RSI, Fibonacci, etc.)
├── database.py               # Gestion SQLite
├── alert_system.py           # Système d'alertes Premium
├── create_admin.py           # Script création admin
├── requirements.txt          # Dépendances Python
│
├── static/
│   ├── css/
│   │   └── style.css        # Styles CSS complets
│   └── js/
│       └── app.js           # Frontend JavaScript
│
└── templates/
    ├── index.html           # Page principale
    ├── favorites.html       # Page favoris
    ├── admin.html          # Panel admin
    └── error.html          # Page erreur
```

---

## 🚀 Installation

### Prérequis

- **Python 3.8+**
- **Nitter instance** (optionnel pour scraping Twitter)
  - Docker: `docker run -d -p 8080:8080 zedeus/nitter`
  - Ou utiliser une instance publique

### Étapes

1. **Cloner le projet**
```bash
git clone https://github.com/votre-username/token-scanner-pro.git
cd token-scanner-pro
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Initialiser la base de données**
```bash
python database.py
```

5. **Créer un compte administrateur**
```bash
python create_admin.py
```

6. **Lancer le serveur**
```bash
python app.py
```

Le serveur démarre sur `http://localhost:5000`

---

## ⚙️ Configuration

### Scanner Core

Dans `scanner_core.py`, vous pouvez modifier :

```python
class TokenScanner:
    def __init__(self, nitter_url: str = "http://192.168.1.19:8080"):
        # Changer l'URL de votre instance Nitter
        self.nitter_instance = nitter_url
```

### Système d'Alertes

Dans `alert_system.py`, configurez vos paramètres SMTP :

```python
alert_system = AlertSystem(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    smtp_user="votre.email@gmail.com",
    smtp_password="votre_app_password"  # App Password Google
)
```

**⚠️ Pour Gmail :**
1. Activez la validation en 2 étapes
2. Générez un "App Password" sur https://myaccount.google.com/apppasswords
3. Utilisez ce mot de passe (pas votre mot de passe Gmail)

### Intervalle de Surveillance

```python
self.check_interval = 3600  # 1 heure (en secondes)
```

---

## 💻 Utilisation

### Scan Automatique

1. Cliquez sur **"Nouveau Scan"**
2. L'application analyse les 10 derniers tokens de DexScreener
3. Résultats affichés avec :
   - Score de risque
   - RSI et Fibonacci
   - Détection Pump & Dump
   - Analyse sociale

### Recherche Manuelle

1. Utilisez la barre de recherche en haut
2. Entrez un nom, symbole ou adresse
3. Cliquez sur "Rechercher"
4. Sélectionnez un token et cliquez sur "Analyser"

### Ajouter aux Favoris

1. Cliquez sur l'étoile ⭐ sur une card token
2. Le token est ajouté à vos favoris
3. Accédez à vos favoris via le menu

### Activer les Alertes (Premium)

1. Un admin doit activer votre compte Premium
2. Ajoutez des tokens à vos favoris
3. Configurez votre email dans les paramètres
4. Les alertes sont envoyées automatiquement toutes les heures

---

## 🔌 API Endpoints

### Authentification

```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

### Scan

```
POST /api/scan/start
GET  /api/scan/progress
GET  /api/scan/results
POST /api/scan/search
```

### Recherche

```
GET  /api/token/search?q={query}
POST /api/token/analyze
```

### Favoris

```
GET    /api/favorites
POST   /api/favorites/add
POST   /api/favorites/remove
POST   /api/favorites/check
POST   /api/favorites/notes
```

### Admin

```
GET    /api/admin/stats
GET    /api/admin/users
POST   /api/admin/user/{id}/toggle-status
POST   /api/admin/user/{id}/toggle-premium
POST   /api/admin/user/{id}/role
DELETE /api/admin/user/{id}/delete
GET    /api/admin/logs
```

---

## 🚨 Système d'Alertes

### Types d'Alertes

| Type | Déclencheur | Criticité |
|------|-------------|-----------|
| **RSI Suracheté** | RSI ≥ 70 | 🔴 Critique |
| **RSI Survendu** | RSI ≤ 30 | 💎 Info |
| **Fibonacci Résistance** | Position ≥ 78.6% | ⚠️ Warning |
| **Fibonacci Support** | Position ≤ 23.6% | 💡 Info |
| **Pump & Dump** | Score ≥ 50 | 🔴 Critique |
| **Liquidité Faible** | < $5,000 | 🔴 Critique |
| **Honeypot** | Détecté | 🔴 Critique |
| **Concentration Holders** | Top 5 > 50% | 🔴 Critique |

### Lancer les Alertes

```python
from alert_system import AlertSystem

alert_system = AlertSystem(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    smtp_user="votre.email@gmail.com",
    smtp_password="votre_app_password"
)

alert_system.start_monitoring()
```

---

## 🛡️ Admin Panel

### Accès

1. Créez un compte admin avec `create_admin.py`
2. Connectez-vous
3. Accédez à `/admin`

### Fonctionnalités Admin

- **Gestion utilisateurs** : Activer/désactiver, supprimer
- **Attribution Premium** : Donner accès aux alertes
- **Changement de rôle** : Promouvoir en admin
- **Logs** : Historique des actions admin
- **Statistiques** : Métriques globales

---

## 🔧 Technologies

### Backend
- **Flask 3.0** - Framework web Python
- **SQLite** - Base de données
- **Requests** - Requêtes HTTP
- **Werkzeug** - Hash des mots de passe
- **SMTP** - Envoi d'emails

### Frontend
- **HTML5 / CSS3** - Interface moderne
- **JavaScript** - Logique frontend
- **Fetch API** - Communication avec le backend

### APIs Externes
- **DexScreener API** - Données de marché
- **GoPlus Labs API** - Analyse de sécurité
- **Nitter** - Scraping Twitter (optionnel)

---

## 📊 Indicateurs Techniques

### RSI (Relative Strength Index)

```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss
```

**Interprétation :**
- **RSI > 70** : Suracheté 🔥 (risque de correction)
- **RSI 50-70** : Haussier 📈 (momentum positif)
- **RSI 30-50** : Neutre ➖
- **RSI < 30** : Survendu 💎 (potentiel rebond)

### Fibonacci

Niveaux clés calculés sur le range 24h :
- **0%** : Low 24h
- **23.6%** : Premier support
- **38.2%** : Support fort
- **50%** : Milieu de range
- **61.8%** : Résistance forte (Golden Ratio)
- **78.6%** : Première résistance
- **100%** : High 24h

### Pump & Dump Score

Score de 0 à 100 basé sur :
- Volume spike (0-25 pts)
- Price spike (0-30 pts)
- Concentration holders (0-20 pts)
- Liquidité faible (0-15 pts)
- Token récent (0-10 pts)

**Seuils adaptés pour nouveaux tokens (<72h)** pour éviter les faux positifs.

---

## 📸 Captures d'écran

### Page Principale
- Barre de recherche
- Stats en temps réel
- Grille de tokens avec RSI/Fibonacci
- Filtres avancés

### Modal Token
- Analyse complète
- Graphiques RSI et Fibonacci
- Top 5 Holders
- Section Pump & Dump
- Données de marché et sécurité

### Admin Panel
- Dashboard avec stats
- Liste des utilisateurs
- Gestion Premium
- Logs d'activité

---

## 🤝 Contributions

Les contributions sont les bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📝 TODO / Améliorations Futures

- [ ] Support de plus de blockchains (Polygon, Avalanche)
- [ ] Charts en temps réel (TradingView)
- [ ] Analyse on-chain avancée
- [ ] Bot Telegram pour alertes
- [ ] Export des données (CSV, JSON)
- [ ] Backtesting de stratégies
- [ ] API REST publique
- [ ] Mode sombre/clair
- [ ] Support multi-langue
- [ ] Application mobile

---

## ⚠️ Avertissement

**Ce logiciel est fourni à des fins éducatives uniquement.**

- Ne constitue pas un conseil financier
- Le trading de crypto-monnaies comporte des risques
- Faites toujours vos propres recherches (DYOR)
- N'investissez que ce que vous pouvez vous permettre de perdre
- Les performances passées ne garantissent pas les résultats futurs

L'auteur n'est pas responsable des pertes financières.

---

## 📄 License

Ce projet est sous licence **MIT**.

```
MIT License

Copyright (c) 2025 Token Scanner Pro

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📞 Support

Pour toute question ou problème :

- **Issues GitHub** : [Ouvrir une issue](https://github.com/votre-username/token-scanner-pro/issues)
- **Email** : support@tokenscannerpro.com
- **Discord** : [Rejoindre le serveur](https://discord.gg/tokenscannerpro)

---

## 🙏 Remerciements

- **DexScreener** pour leur API publique
- **GoPlus Labs** pour l'analyse de sécurité
- **Nitter** pour le scraping Twitter
- La communauté crypto pour les retours

---

<div align="center">

**⭐ Si ce projet vous plaît, n'hésitez pas à lui donner une étoile sur GitHub ! ⭐**

Made with ❤️ by Token Scanner Pro Team

[Website](https://tokenscannerpro.com) • [Documentation](https://docs.tokenscannerpro.com) • [Discord](https://discord.gg/tokenscannerpro)

</div>
