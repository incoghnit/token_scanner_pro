# ⚠️ IMPORTANT: Deux Systèmes de Recherche Distincts

Token Scanner Pro possède **DEUX systèmes de recherche complètement séparés** :

---

## 🆕 1. Discovery Service (NOUVEAU - Centralisé & Partagé)

### 🎯 Objectif
Découvrir les **DERNIERS tokens du marché** (nouveaux listings)

### 🔧 Comment ça marche
```
User 1, 2, 3... N connectés
         ↓
    Bouton "Rechercher les derniers tokens"
         ↓
    1 seul scan API (DexScreener derniers tokens)
         ↓
    Stockage dans BDD (table scanned_tokens)
         ↓
    Broadcast WebSocket → TOUS les users reçoivent
```

### ✅ Caractéristiques
- **PARTAGÉ** entre tous les utilisateurs connectés
- **1 appel API** pour tout le monde (économies 90-99%)
- **Temps réel** via WebSocket
- **Automatique** (optionnel avec auto-discovery)
- **Public** - tous voient les mêmes tokens

### 📍 Routes API
```javascript
// Déclencher un scan discovery
POST /api/discovery/trigger
{
    "max_tokens": 20,
    "chain": "ethereum"  // optionnel
}

// Obtenir le statut
GET /api/discovery/status

// Récupérer les tokens découverts
GET /api/discovery/recent?limit=50
```

### 🌐 Utilisation Frontend
```javascript
// 1. Se connecter au WebSocket
const client = new TokenDiscoveryClient();
client.connect();

// 2. Écouter les nouveaux tokens
client.on('new_token', (token) => {
    console.log('Nouveau token découvert:', token);
    addTokenToGrid(token);
});

// 3. Déclencher un scan (bouton "Rechercher")
document.getElementById('discoverBtn').onclick = () => {
    client.triggerScan({ maxTokens: 20 });
};
```

### 📊 Use Case
- Bouton "🔍 Rechercher les derniers tokens"
- Page "Découverte" avec feed en temps réel
- Auto-refresh toutes les 5 minutes
- **Tous les users voient la même liste**

---

## 🔍 2. Scan Spécifique (ANCIEN - Individuel & Privé)

### 🎯 Objectif
Analyser **UN token précis** (adresse contractuelle ou URL DexScreener)

### 🔧 Comment ça marche
```
User 1 entre une adresse: 0xabc123...
         ↓
    Bouton "Analyser ce token"
         ↓
    Scan individuel pour ce user uniquement
         ↓
    Résultats privés (non partagés)
```

### ✅ Caractéristiques
- **PRIVÉ** - chaque user a ses propres scans
- **Individuel** - 1 appel API par user
- **Synchrone** - attendre le résultat
- **Non partagé** - autres users ne voient pas
- **Sur demande** - pas automatique

### 📍 Routes API
```javascript
// Scanner un token spécifique (EXISTANT, ne PAS toucher)
POST /api/scan/start
{
    "profile_url": "https://dexscreener.com/ethereum/0xabc123...",
    "max_tokens": 1,
    "nitter_url": "http://localhost:8080"
}

// Progression du scan
GET /api/scan/progress

// Résultats du scan
GET /api/scan/results
```

### 🌐 Utilisation Frontend
```javascript
// Scanner un token spécifique (code existant, ne pas modifier)
async function scanSpecificToken(profileUrl) {
    const response = await fetch('/api/scan/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            profile_url: profileUrl,
            max_tokens: 1
        })
    });

    // Attendre les résultats
    const result = await response.json();

    // Résultats PRIVÉS pour cet utilisateur uniquement
    displayTokenAnalysis(result);
}
```

### 📊 Use Case
- Champ de recherche: "Entrez une adresse ou URL"
- Bouton "🔎 Analyser"
- Page de détails d'un token spécifique
- **Résultats privés pour l'utilisateur**

---

## 📋 Comparaison Directe

| Critère | Discovery Service (NOUVEAU) | Scan Spécifique (ANCIEN) |
|---------|----------------------------|--------------------------|
| **Objectif** | Derniers tokens du marché | Un token précis |
| **Partage** | ✅ PARTAGÉ entre tous | ❌ PRIVÉ par user |
| **API Calls** | 1× pour tous les users | 1× par user |
| **Temps réel** | ✅ WebSocket broadcast | ❌ Synchrone |
| **Auto** | ✅ Optionnel | ❌ Manuel uniquement |
| **Route** | `/api/discovery/trigger` | `/api/scan/start` |
| **Input** | `max_tokens`, `chain` | `profile_url` |
| **Output** | Liste de tokens (BDD) | 1 token analysé |
| **Coût** | Très faible (mutualisé) | Normal (par user) |

---

## 🎨 Exemples d'UI

### Discovery Service - Bouton "Découvrir"
```html
<button id="discoverBtn" class="btn-primary">
    🔍 Découvrir les derniers tokens
</button>
<div id="discovery-feed">
    <!-- Tokens découverts apparaissent ici en temps réel -->
    <!-- TOUS les users voient les mêmes tokens -->
</div>

<script>
    // WebSocket pour recevoir les tokens en temps réel
    const client = new TokenDiscoveryClient();
    client.on('new_token', (token) => {
        addTokenToFeed(token);
    });
    client.connect();

    // Déclencher un scan discovery
    discoverBtn.onclick = () => {
        client.triggerScan({ maxTokens: 20 });
    };
</script>
```

### Scan Spécifique - Champ de recherche
```html
<input
    type="text"
    id="tokenInput"
    placeholder="Entrez adresse ou URL DexScreener"
/>
<button id="analyzeBtn" class="btn-secondary">
    🔎 Analyser ce token
</button>
<div id="token-details">
    <!-- Résultats PRIVÉS de l'analyse -->
</div>

<script>
    // Scan individuel (existant, ne pas toucher)
    analyzeBtn.onclick = async () => {
        const profileUrl = tokenInput.value;

        const response = await fetch('/api/scan/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_url: profileUrl,
                max_tokens: 1
            })
        });

        const result = await response.json();
        displayTokenDetails(result);
    };
</script>
```

---

## ⚠️ RÈGLES IMPORTANTES

### ✅ À FAIRE

1. **Discovery Service** → Utiliser pour:
   - Feed de découverte
   - Liste des derniers tokens
   - Scan automatique périodique
   - Expérience collaborative

2. **Scan Spécifique** → Utiliser pour:
   - Recherche d'un token par adresse
   - Analyse détaillée d'un token
   - Résultats privés par user
   - Favoris individuels

### ❌ À NE PAS FAIRE

1. ❌ **NE PAS** utiliser Discovery pour scanner un token spécifique
   ```javascript
   // ❌ MAUVAIS - Ne pas faire ça
   client.triggerScan({
       maxTokens: 1,
       profileUrl: "https://dexscreener.com/..."
   });
   ```

2. ❌ **NE PAS** broadcaster les scans spécifiques via WebSocket
   ```javascript
   // ❌ MAUVAIS - Les scans spécifiques sont PRIVÉS
   socketio.emit('new_token', specificTokenResult);  // NON !
   ```

3. ❌ **NE PAS** stocker les scans spécifiques dans scanned_tokens
   ```javascript
   // ❌ MAUVAIS - Cette table est pour Discovery uniquement
   db.add_scanned_token(specificToken);  // NON !
   ```

---

## 🔄 Flux de Données

### Discovery Service
```
Déclencheur: Auto (5min) OU Bouton "Découvrir"
     ↓
Scanner.scan_tokens(max_tokens=20)  ← Derniers tokens du marché
     ↓
BDD: scanned_tokens (FIFO 200 tokens)
     ↓
WebSocket broadcast → TOUS les users connectés
     ↓
Frontend: Grille de tokens (partagée)
```

### Scan Spécifique
```
Input User: "0xabc123..." OU "dexscreener.com/ethereum/0xabc..."
     ↓
Scanner.analyze_token(token_info)  ← Ce token uniquement
     ↓
Session user (temporaire)
     ↓
Frontend: Page de détails (privée)
```

---

## 📝 Résumé pour les développeurs

**Si vous voulez:**

1. **Afficher les derniers tokens du marché**
   - ✅ Utilisez Discovery Service
   - Route: `/api/discovery/trigger`
   - WebSocket: `new_token` event

2. **Analyser un token précis par adresse**
   - ✅ Utilisez Scan Spécifique
   - Route: `/api/scan/start`
   - Pas de WebSocket (privé)

3. **Feed temps réel partagé**
   - ✅ Discovery Service
   - WebSocket obligatoire

4. **Résultats privés par user**
   - ✅ Scan Spécifique
   - Pas de partage

---

## 🚀 Migration du code existant

Si vous aviez du code utilisant `/api/scan/start` pour découvrir les derniers tokens, **migrez vers Discovery**:

### Avant (ancien système)
```javascript
// ❌ Chaque user déclenche un scan individuel
fetch('/api/scan/start', {
    method: 'POST',
    body: JSON.stringify({ max_tokens: 20 })
});
```

### Après (nouveau système)
```javascript
// ✅ Un scan partagé entre tous
const client = new TokenDiscoveryClient();
client.connect();
client.triggerScan({ maxTokens: 20 });
```

---

**Conclusion:** Les deux systèmes coexistent et ont des objectifs différents. Ne les mélangez pas !

🤖 Generated with [Claude Code](https://claude.com/claude-code)
