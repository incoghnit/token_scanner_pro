# 📊 Comparaison des Méthodes de Scan

**Date:** 2025-10-31
**Application:** Token Scanner Pro

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'Ensemble](#vue-densemble)
2. [Scan Auto-Discovery (24h)](#scan-auto-discovery-24h)
3. [Scan Spécifique (Individuel)](#scan-spécifique-individuel)
4. [Tableau Comparatif](#tableau-comparatif)
5. [Analyse Technique](#analyse-technique)

---

## 🎯 VUE D'ENSEMBLE

Les deux méthodes de scan utilisent **la même fonction d'analyse** (`analyze_token()`), mais diffèrent dans leur **point d'entrée** et les **données initiales** disponibles.

| Aspect | Scan 24h | Scan Spécifique |
|--------|----------|-----------------|
| **Point d'entrée** | `scan_tokens()` → `fetch_latest_tokens()` | URL DexScreener extraite |
| **Nombre de tokens** | 10-50 tokens (configurable) | 1 token unique |
| **Fonction d'analyse** | `analyze_token()` | `analyze_token()` |
| **Données initiales** | Profil complet (DexScreener) | URL → address + chain |

---

## 🔄 SCAN AUTO-DISCOVERY (24h)

### Flux d'Exécution

```
1. fetch_latest_tokens()
   ↓
2. Pour chaque token: analyze_token(token_info)
   ↓
3. Retourne liste complète avec statistiques
```

### 📡 Appels API - Étape 1: Récupération Liste

**Fonction:** `fetch_latest_tokens()`

| API | Endpoint | Méthode | Données Retournées |
|-----|----------|---------|-------------------|
| **DexScreener** | `/token-profiles/latest/v1` | GET | Array de tokens avec profils actifs |

**Données récupérées (par token):**
```json
{
  "chainId": "solana",
  "tokenAddress": "abc123...",
  "icon": "https://...",
  "description": "Description du projet",
  "url": "https://dexscreener.com/solana/abc123...",
  "links": [
    {"type": "twitter", "url": "https://x.com/..."},
    {"type": "website", "url": "https://..."},
    {"type": "telegram", "url": "https://t.me/..."}
  ]
}
```

**token_info créé:**
```python
{
    "address": "abc123...",
    "chain": "solana",
    "url": "https://dexscreener.com/solana/abc123...",
    "icon": "https://...",
    "description": "Description du projet",
    "twitter": "https://x.com/...",
    "links": [...]
}
```

### 📡 Appels API - Étape 2: Analyse de Chaque Token

**Fonction:** `analyze_token(token_info)`

#### Appel 1: Market Data (OBLIGATOIRE)

| API | Endpoint | Méthode | Timeout | Retry |
|-----|----------|---------|---------|-------|
| **DexScreener** | `/latest/dex/tokens/{address}` | GET | 10s | 3x |

**Données extraites:**
- ✅ `token_name` (baseToken.name)
- ✅ `token_symbol` (baseToken.symbol)
- ✅ `price_usd`
- ✅ `price_change_24h`, `price_change_6h`, `price_change_1h`
- ✅ `volume_24h`, `volume_6h`
- ✅ `liquidity_usd` ← **LIQUIDITÉ**
- ✅ `market_cap`
- ✅ `txns_24h_buys`, `txns_24h_sells`
- ✅ `pair_created_at` (timestamp création)

**Pause:** 0.5s

---

#### Appel 2: Security Check (OBLIGATOIRE)

| API | Endpoint | Méthode | Timeout | Retry |
|-----|----------|---------|---------|-------|
| **GoPlus** | `/token_security/{chain_id}?contract_addresses={address}` | GET | 10s | 3x |

**Données extraites:**
- ✅ `is_honeypot` (0 ou 1)
- ✅ `is_open_source` (0 ou 1)
- ✅ `is_mintable` (0 ou 1)
- ✅ `buy_tax`, `sell_tax` (%)
- ✅ `holder_count`
- ✅ `total_supply`
- ✅ `creator_address`, `owner_address`
- ✅ `creator_percent`, `owner_percent`
- ✅ **`holders` (Top 10 holders)** ← **TOP HOLDERS**
  ```json
  [
    {
      "address": "0x...",
      "tag": "Liquidity Pool",
      "is_locked": true,
      "is_contract": true,
      "balance": "1000000",
      "percent": "15.5"
    },
    ...
  ]
  ```

**Pause:** 0.5s

---

#### Appel 3: Creator Security (CONDITIONNEL)

**Condition:** Si `creator_address` ou `owner_address` présent ET != 0x0000...

| API | Endpoint | Méthode | Timeout | Retry |
|-----|----------|---------|---------|-------|
| **GoPlus** | `/address_security/{chain_id}?addresses={creator_address}` | GET | 10s | 3x |

**Données extraites:**
- ✅ `is_malicious` (true/false)
- ✅ `phishing_activities` (count)
- ✅ `honeypot_related_address` (true/false)
- ✅ `darkweb_transactions` (true/false)

**Impact:** +50 au risk_score si créateur blacklisté

**Pause:** 0.5s

---

#### Appel 4: Rug-Pull Detection (CONDITIONNEL)

**Condition:** Si security check réussi (pas d'erreur)

| API | Endpoint | Méthode | Timeout | Retry |
|-----|----------|---------|---------|-------|
| **GoPlus** | `/RugPull_Detection/{chain_id}?contract_addresses={address}` | GET | 10s | 3x |

**Données extraites:**
- ✅ `is_rugpull_risk` (true/false)
- ✅ `rugpull_risk_level` (low/medium/high)
- ✅ `liquidity_removable` (true/false)
- ✅ `ownership_renounced` (true/false)
- ✅ `transfer_pausable` (true/false)
- ✅ `can_take_back_ownership` (true/false)

**Impact:** +15 à +40 au risk_score selon niveau

**Pause:** 0.5s

---

#### Appel 5: Twitter Data (CONDITIONNEL)

**Condition:** Si `token_info.twitter` présent

| API | Endpoint | Méthode | Timeout |
|-----|----------|---------|---------|
| **Nitter** | `/{username}` | GET | 10s |

**Données extraites:**
- ✅ `followers`
- ✅ `following`
- ✅ `tweets_count`
- ✅ `verified` (blue check)
- ✅ `account_age_days`
- ✅ `last_tweet_date`
- ✅ `last_tweet_text`

**Calcul:** Social score (0-100) basé sur ces métriques

**Pause:** 1s

---

#### Appel 6: OHLCV Data (CONDITIONNEL - TOKENS > 48h)

**Condition:** Si `pair_created_at` > 48 heures

| API | Endpoint | Méthode | Timeout | Retry |
|-----|----------|---------|---------|-------|
| **BirdEye** | `/defi/ohlcv?address={address}&type=1H&time_from={}&time_to={}` | GET | 10s | 3x |

**Headers:** `X-API-KEY: {BIRDEYE_API_KEY}`

**Données extraites:**
- ✅ `opens[]` (prix d'ouverture)
- ✅ `highs[]` (prix max)
- ✅ `lows[]` (prix min)
- ✅ `closes[]` (prix de clôture)
- ✅ `volumes[]` (volume)

**Limite:** 200 bougies (8 jours d'historique en 1H)

**Pause:** 0.5s

---

#### Calcul 7: Technical Analysis (CONDITIONNEL)

**Condition:** Si OHLCV data disponible

**Calculs locaux (pas d'API):**
- ✅ **RSI** (Relative Strength Index)
- ✅ **MACD** (Moving Average Convergence Divergence)
- ✅ **Bollinger Bands**
- ✅ **EMAs** (9, 21, 50, 200)
- ✅ **Support/Resistance Levels**
- ✅ **Fibonacci Retracement Levels** ← **FIBONACCI**
- ✅ **Trend Analysis**
- ✅ **Trading Signal** (BUY/SELL/HOLD)

**Données retournées:**
```json
{
  "rsi": 65.3,
  "macd": {...},
  "fibonacci": {
    "0.0": 0.00045,
    "0.236": 0.00052,
    "0.382": 0.00058,
    "0.5": 0.00062,
    "0.618": 0.00067,
    "1.0": 0.00085
  },
  "trading_signal": {
    "signal": "BUY",
    "confidence": 75,
    "reasons": [...]
  }
}
```

---

### 📦 Données Finales Retournées (Scan 24h)

**Structure complète par token:**
```json
{
  "address": "abc123...",
  "chain": "solana",
  "url": "https://dexscreener.com/solana/abc123...",
  "icon": "https://...",
  "name": "Token Name",          // ← NOM
  "symbol": "TKN",                // ← SYMBOL
  "description": "Project desc",
  "twitter": "https://x.com/...",
  "website": "https://...",
  "telegram": "https://t.me/...",
  "discord": "https://discord.gg/...",

  "market": {
    "price_usd": 0.0045,
    "price_change_24h": 15.3,
    "liquidity_usd": 45000,       // ← LIQUIDITÉ
    "volume_24h": 125000,
    "market_cap": 450000,
    "txns_24h_buys": 150,
    "txns_24h_sells": 120,
    "token_name": "Token Name",
    "token_symbol": "TKN"
  },

  "security": {
    "is_honeypot": false,
    "is_mintable": false,
    "buy_tax": 0.0,
    "sell_tax": 0.0,
    "holder_count": 1234,
    "holders": [                  // ← TOP HOLDERS
      {
        "address": "0x...",
        "percent": "15.5",
        "is_locked": true
      },
      // ... 9 autres
    ]
  },

  "risk_score": 35,
  "is_safe": true,
  "warnings": [...],

  "pump_dump_score": 25,
  "is_pump_dump_suspect": false,

  "analysis_type": "established_token_analysis",  // ou "recent_token_scan"
  "technical_analysis": {         // ← SI TOKEN > 48h
    "rsi": 65.3,
    "fibonacci": {...},           // ← FIBONACCI
    "trading_signal": {...}
  },

  "timestamp": "2025-10-31T12:34:56"
}
```

**Statistiques globales:**
```json
{
  "success": true,
  "results": [... array de tokens ...],
  "total_analyzed": 20,
  "safe_count": 12,
  "dangerous_count": 8,
  "pump_dump_suspects_count": 5
}
```

---

## 🎯 SCAN SPÉCIFIQUE (INDIVIDUEL)

### Flux d'Exécution

```
1. Extraction URL DexScreener
   ↓
2. Parsing: chain + address
   ↓
3. Création token_info minimal
   ↓
4. analyze_token(token_info)  ← MÊME FONCTION QUE SCAN 24h
   ↓
5. Retourne 1 token avec statistiques
```

### 📝 Données Initiales

**Input:** URL DexScreener fournie par l'utilisateur

```
https://dexscreener.com/solana/abc123def456...
```

**Parsing regex:**
```python
match = re.search(r'dexscreener\.com/([^/]+)/(.+?)(?:\?|$)', profile_url)
chain = match.group(1)      # "solana"
address = match.group(2)    # "abc123def456..."
```

**token_info créé:**
```python
{
    "address": "abc123def456...",
    "chain": "solana",
    "url": "https://dexscreener.com/solana/abc123...",  # URL complète
    "icon": "",                    # Vide au départ
    "description": "",             # Vide au départ
    "twitter": None,               # Pas de social links au départ
    "links": []                    # Array vide
}
```

### 📡 Appels API

**À partir d'ici, EXACTEMENT LES MÊMES APPELS que Scan 24h:**

1. ✅ **Market Data** (DexScreener `/tokens/{address}`)
2. ✅ **Security Check** (GoPlus token_security)
3. ✅ **Creator Security** (GoPlus address_security) - si créateur présent
4. ✅ **Rug-Pull Detection** (GoPlus RugPull_Detection) - si pas d'erreur
5. ✅ **Twitter Data** (Nitter) - si twitter URL présent (NON dans scan spécifique)
6. ✅ **OHLCV Data** (BirdEye) - si token > 48h
7. ✅ **Technical Analysis** (calculs locaux) - si OHLCV disponible

**Différence clé:** Pas de Twitter data car `token_info.twitter = None` au départ

### 📦 Données Finales Retournées (Scan Spécifique)

**Structure identique à scan 24h:**
```json
{
  "address": "abc123...",
  "chain": "solana",
  "url": "https://dexscreener.com/solana/abc123...",
  "icon": "",                     // ← Vide (pas récupéré)
  "name": "Token Name",           // ← NOM (depuis market data)
  "symbol": "TKN",                // ← SYMBOL (depuis market data)
  "description": "",              // ← Vide (pas récupéré)
  "twitter": null,                // ← NULL
  "website": null,
  "telegram": null,
  "discord": null,

  "twitter_data": {},             // ← VIDE (pas de social scan)
  "social_score": 0,              // ← 0 (pas de social)

  "market": { ... },              // ← IDENTIQUE
  "security": { ... },            // ← IDENTIQUE (avec TOP HOLDERS)
  "risk_score": 35,
  "technical_analysis": { ... },  // ← SI TOKEN > 48h (avec FIBONACCI)
  "timestamp": "2025-10-31T12:34:56"
}
```

**Enveloppe de réponse:**
```json
{
  "success": true,
  "results": [... 1 token ...],
  "total_analyzed": 1,
  "safe_count": 1,           // ou 0
  "dangerous_count": 0,      // ou 1
  "pump_dump_suspects_count": 0  // ou 1
}
```

---

## 📊 TABLEAU COMPARATIF

| Aspect | Scan 24h | Scan Spécifique |
|--------|----------|-----------------|
| **Point d'entrée** | `fetch_latest_tokens()` | URL DexScreener |
| **Nombre de tokens** | 10-50 | 1 |
| **Appel initial** | ✅ DexScreener `/token-profiles/latest/v1` | ❌ Aucun (extraction URL) |
| **Icon** | ✅ Récupéré | ❌ Vide |
| **Description** | ✅ Récupérée | ❌ Vide |
| **Social Links** | ✅ Récupérés (twitter, website, etc.) | ❌ Vides |
| | | |
| **Appels d'analyse** | ⬇️ IDENTIQUES ⬇️ | ⬇️ IDENTIQUES ⬇️ |
| Market Data | ✅ DexScreener `/tokens/{address}` | ✅ DexScreener `/tokens/{address}` |
| Token Name | ✅ baseToken.name | ✅ baseToken.name |
| Token Symbol | ✅ baseToken.symbol | ✅ baseToken.symbol |
| Liquidité | ✅ liquidity.usd | ✅ liquidity.usd |
| Prix, Volume | ✅ Complets | ✅ Complets |
| Security Check | ✅ GoPlus token_security | ✅ GoPlus token_security |
| **Top Holders** | ✅ Top 10 avec % | ✅ Top 10 avec % |
| Creator Security | ✅ GoPlus address_security | ✅ GoPlus address_security |
| Rug-Pull Detection | ✅ GoPlus RugPull_Detection | ✅ GoPlus RugPull_Detection |
| Twitter Scraping | ✅ Si twitter URL | ❌ Pas de twitter URL |
| Social Score | ✅ Calculé (0-100) | ❌ 0 (pas de data) |
| OHLCV Data | ✅ BirdEye (si > 48h) | ✅ BirdEye (si > 48h) |
| **RSI** | ✅ Si > 48h | ✅ Si > 48h |
| **Fibonacci** | ✅ Si > 48h | ✅ Si > 48h |
| Technical Analysis | ✅ Complète (si > 48h) | ✅ Complète (si > 48h) |
| Trading Signal | ✅ BUY/SELL/HOLD | ✅ BUY/SELL/HOLD |

---

## 📈 ANALYSE TECHNIQUE

### Condition d'Activation

**Les deux méthodes de scan appliquent EXACTEMENT la même règle:**

```python
age_hours = (datetime.now().timestamp() - int(pair_created_at)/1000) / 3600

if age_hours >= 48:
    # ✅ TECHNICAL ANALYSIS MODE
    analysis_type = "established_token_analysis"
    # → RSI, MACD, Fibonacci, Support/Resistance, Trading Signal
else:
    # ❌ FRAUD DETECTION MODE
    analysis_type = "recent_token_scan"
    # → Pas d'analyse technique
```

### Données Techniques Complètes

**Si token ≥ 48h:**

| Indicateur | Description | Valeurs |
|------------|-------------|---------|
| **RSI** | Relative Strength Index | 0-100 (>70 = suracheté, <30 = survendu) |
| **MACD** | Moving Average Convergence | `{macd_line, signal_line, histogram}` |
| **Bollinger Bands** | Volatilité | `{upper, middle, lower}` |
| **EMAs** | Exponential Moving Averages | `{ema_9, ema_21, ema_50, ema_200}` |
| **Support/Resistance** | Niveaux clés | Array de prix |
| **Fibonacci** | Retracement Fibonacci | `{0.0, 0.236, 0.382, 0.5, 0.618, 1.0}` |
| **Trend** | Tendance du marché | `{direction: "up/down/sideways", strength: 0-100}` |
| **Trading Signal** | Signal de trading | `{signal: "BUY/SELL/HOLD", confidence: 0-100}` |

**Exemple complet:**
```json
{
  "analysis_type": "established_token_analysis",
  "technical_analysis": {
    "rsi": 65.3,
    "macd": {
      "macd_line": 0.000012,
      "signal_line": 0.000008,
      "histogram": 0.000004
    },
    "bollinger_bands": {
      "upper": 0.0052,
      "middle": 0.0045,
      "lower": 0.0038
    },
    "emas": {
      "ema_9": 0.0046,
      "ema_21": 0.0044,
      "ema_50": 0.0042,
      "ema_200": 0.0038
    },
    "support_resistance": {
      "support": [0.0040, 0.0038, 0.0035],
      "resistance": [0.0050, 0.0055, 0.0060]
    },
    "fibonacci": {
      "0.0": 0.00035,
      "0.236": 0.00042,
      "0.382": 0.00048,
      "0.5": 0.00052,
      "0.618": 0.00057,
      "1.0": 0.00070
    },
    "trend": {
      "direction": "up",
      "strength": 78
    },
    "trading_signal": {
      "signal": "BUY",
      "confidence": 75,
      "reasons": [
        "RSI indicates moderate buying pressure (65.3)",
        "MACD shows bullish crossover",
        "Price above EMA 50",
        "Strong uptrend detected"
      ]
    },
    "token_age_hours": 156.5
  }
}
```

---

## 🎯 RÉSUMÉ FINAL

### Ce qui est IDENTIQUE

✅ **Nom du token** (market data → baseToken.name)
✅ **Symbol** (market data → baseToken.symbol)
✅ **Liquidité** (market data → liquidity.usd)
✅ **Prix et volumes** (market data)
✅ **Top holders** (GoPlus security → top 10 avec %)
✅ **Security checks** (GoPlus → honeypot, taxes, etc.)
✅ **Creator checks** (GoPlus → blacklist)
✅ **Rug-pull detection** (GoPlus)
✅ **RSI** (si token > 48h)
✅ **Fibonacci** (si token > 48h)
✅ **Analyse technique complète** (si token > 48h)

### Ce qui DIFFÈRE

| Donnée | Scan 24h | Scan Spécifique |
|--------|----------|-----------------|
| **Icon** | ✅ URL complète | ❌ Vide |
| **Description** | ✅ Texte complet | ❌ Vide |
| **Social Links** | ✅ Twitter, Website, Telegram, Discord | ❌ Tous NULL |
| **Twitter Data** | ✅ Followers, tweets, verified | ❌ Vide |
| **Social Score** | ✅ 0-100 | ❌ 0 |

---

## ✅ CONCLUSION

**Votre affirmation initiale était PARTIELLEMENT INCORRECTE:**

> "Scan spécifique de token il y a le rsi et le fibo et pas de top 5holders"

**CORRECTION:**

- ✅ RSI et Fibonacci : **PRÉSENTS dans les deux scans** (si token > 48h)
- ❌ Top holders : **PRÉSENTS dans les deux scans** (toujours récupérés)

**La VRAIE différence:**

| Scan 24h | Scan Spécifique |
|----------|-----------------|
| + Icon | - Pas d'icon |
| + Description | - Pas de description |
| + Social links (twitter, website, etc.) | - Pas de social links |
| + Social score | - Social score = 0 |
| **Sinon IDENTIQUE** | **Sinon IDENTIQUE** |

Les deux scans utilisent la **même fonction d'analyse** (`analyze_token()`), donc ils ont accès aux **mêmes données de marché, sécurité, holders et analyse technique**.

---

**Questions ?**

Si vous voulez que les scans spécifiques aient des infos différentes (par exemple, sans holders), il faudrait modifier la fonction `analyze_token()` pour accepter un paramètre `scan_type` et conditionner certains appels.
