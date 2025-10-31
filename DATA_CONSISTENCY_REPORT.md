# 📊 Rapport d'Analyse de Cohérence des Données

**Date:** 2025-10-31
**Analysé par:** Claude Code
**Scope:** MongoDB, Redis, Scanner Core, Application

---

## 🔴 PROBLÈMES CRITIQUES IDENTIFIÉS

### 1. **INCOHÉRENCE MAJEURE: Noms de Champs dans `scanned_tokens`**

**Gravité:** 🔴 CRITIQUE - Empêche la création d'index unique

#### Problème:
- **scanner_core.py** retourne: `"address"` et `"chain"`
- **mongodb_manager.py** stocke comme: `"token_address"` et `"token_chain"`
- **add_mongodb_indexes.py** essaie de créer index sur: `"address"` et `"chain"` ❌

#### Impact:
- ❌ Création d'index unique ÉCHOUE (erreur E11000)
- ⚠️  Requêtes LENTES (pas d'index optimisé)
- ⚠️  Risque de doublons dans la BDD

#### Localisation:
```
scanner_core.py:903-904
    return {
        "address": address,  ← Clé retournée
        "chain": chain,      ← Clé retournée
        ...
    }

mongodb_manager.py:486-487
    token_doc = {
        'token_address': token_address,  ← Clé stockée (différente!)
        'token_chain': token_chain,      ← Clé stockée (différente!)
        ...
    }

mongodb_manager.py:528-529 (add_scanned_tokens_batch)
    result = self.add_scanned_token(
        token_address=token.get('address'),  ← Lit 'address'
        token_chain=token.get('chain', 'solana'),  ← Lit 'chain'
        ...
    )

add_mongodb_indexes.py:131
    [("address", 1), ("chain", 1)]  ← Index sur mauvais champs! ❌
```

#### Solution Requise:
**Option A (Recommandée):** Corriger `add_mongodb_indexes.py`
```python
# Ligne 131 - AVANT (INCORRECT)
[("address", 1), ("chain", 1)]

# Ligne 131 - APRÈS (CORRECT)
[("token_address", 1), ("token_chain", 1)]

# Ligne 145 - AVANT (INCORRECT)
"chain"

# Ligne 145 - APRÈS (CORRECT)
"token_chain"
```

**Option B:** Corriger `mongodb_manager.py` (plus de travail)
- Changer tous les `token_address` → `address`
- Changer tous les `token_chain` → `chain`
- Mettre à jour tous les index existants
- Migrer les données existantes

**Recommandation:** ✅ **Option A** (moins risqué, plus rapide)

---

### 2. **INCOHÉRENCE: Champ `chain` dans `favorites`**

**Gravité:** 🟡 MODÉRÉ

#### Problème:
- **mongodb_manager.py** stocke: `"token_chain"`
- **add_mongodb_indexes.py** essaie d'indexer: `"chain"` ❌

#### Localisation:
```
mongodb_manager.py:220
    'token_chain': token_chain,  ← Stocké comme token_chain

add_mongodb_indexes.py:116
    "chain"  ← Index sur mauvais champ! ❌
```

#### Solution:
```python
# add_mongodb_indexes.py:116 - AVANT
if create_index_safe(db.favorites, "chain", name="idx_chain"):

# add_mongodb_indexes.py:116 - APRÈS
if create_index_safe(db.favorites, "token_chain", name="idx_chain"):
```

---

### 3. **DOCUMENTS INVALIDES: Champs NULL dans `scanned_tokens`**

**Gravité:** 🔴 CRITIQUE

#### Problème:
Des documents existent avec `address: null` et `chain: null`, empêchant la création d'index unique.

#### Preuve:
```
E11000 duplicate key error collection: token_scanner_pro.scanned_tokens
index: idx_address_chain_unique dup key: { address: null, chain: null }
```

#### Solution:
✅ **Script créé:** `cleanup_invalid_tokens.py`

**Commande:**
```bash
python cleanup_invalid_tokens.py
```

**Ce que fait le script:**
1. Trouve tous les documents avec `address: null` ou `chain: null`
2. Les supprime de la collection
3. Vérifie l'intégrité des données restantes

---

## 🟡 PROBLÈMES MODÉRÉS

### 4. **Index Dupliqués/Conflictuels**

#### Problème:
Certains index existent déjà avec des noms différents:
- `email_1` existe, mais script essaie de créer `idx_email_unique`
- `username_1` existe, mais script essaie de créer `idx_username_unique`
- `scanned_at_-1` existe, mais script essaie de créer `idx_scanned_at_desc`

#### Impact:
⚠️  Messages d'avertissement (mais pas d'erreur grâce à `create_index_safe`)

#### Solution:
✅ **Déjà résolu** par la fonction `create_index_safe()` qui détecte les index existants.

---

## 🟢 BONNES PRATIQUES RESPECTÉES

### ✅ Séparation des Préoccupations
- `scanner_core.py` = Logique de scan
- `mongodb_manager.py` = Gestion BDD
- `app.py` = API/Routes

### ✅ Gestion des Dates
Utilisation cohérente de `datetime.utcnow()`:
- `created_at` pour users, tokens_cache
- `scanned_at` pour scanned_tokens
- `added_at` pour favorites
- `scan_date` pour scan_history

### ✅ Index TTL
- `tokens_cache` : TTL 24h auto-cleanup ✅
- `scanned_tokens` : TTL 48h auto-cleanup (à créer) ⏳

---

## 🔵 REDIS - État Actuel

### Statut: ❌ **NON INTÉGRÉ**

#### Fichiers Créés (Non Utilisés):
- `config.py` - Configuration Redis + cache decorator
- `app_improvements.py` - Intégration Flask-Limiter avec Redis
- `scanner_cache_improvements.py` - Cache pour scanner_core.py

#### Utilisation Actuelle:
```python
# app.py:123
storage_uri="memory://",  # ← Mode mémoire (pas Redis)
```

#### Pour Activer Redis:
```python
# app.py:123 - Changer en:
storage_uri="redis://localhost:6379"
```

**Note:** Redis n'est pas encore installé sur le serveur.

---

## 📋 PLAN D'ACTION RECOMMANDÉ

### Phase 1: Corrections Critiques (URGENT)

1. **Nettoyer les documents invalides**
   ```bash
   cd /home/jimmy/script/claude_V4/token_scanner_pro/token_scanner_pro
   python cleanup_invalid_tokens.py
   ```

2. **Corriger add_mongodb_indexes.py**
   - Ligne 131: `("address", 1), ("chain", 1)` → `("token_address", 1), ("token_chain", 1)`
   - Ligne 145: `"chain"` → `"token_chain"`
   - Ligne 116: `"chain"` → `"token_chain"` (favorites)

3. **Relancer la création d'index**
   ```bash
   python add_mongodb_indexes.py
   ```

### Phase 2: Optimisations (OPTIONNEL)

4. **Installer Redis (optionnel)**
   ```bash
   docker run -d --name redis-cache -p 6379:6379 redis:alpine
   ```

5. **Intégrer les améliorations Redis**
   - Suivre `IMPROVEMENTS_README.md`

### Phase 3: Tests

6. **Tester les requêtes**
   ```python
   # Vérifier que les index fonctionnent
   db.scanned_tokens.find({"token_address": "xxx", "token_chain": "solana"}).explain()
   ```

---

## 📊 RÉSUMÉ DES COLLECTIONS

| Collection | Champs Clés | Index Actuels | Index Manquants |
|------------|-------------|---------------|-----------------|
| **users** | email, username | ✅ email_1, username_1 | ✅ role, created_at |
| **favorites** | user_id, token_address, token_chain | ✅ compound unique | ❌ token_chain (pas chain) |
| **scanned_tokens** | token_address, token_chain | ❌ INCORRECT (address, chain) | ✅ Tous (après correction) |
| **tokens_cache** | token_address, token_chain, created_at | ✅ TTL 24h | ✅ Complet |
| **scan_history** | user_id, scan_date | ✅ compound | ✅ Complet |
| **positions** | user_id, token_address | ⏳ À créer | ⏳ À créer |
| **alerts** | user_id, token_address, is_active | ⏳ À créer | ⏳ À créer |

---

## 🎯 PRIORITÉS

### 🔴 URGENT (À faire MAINTENANT)
1. Nettoyer documents invalides (`cleanup_invalid_tokens.py`)
2. Corriger `add_mongodb_indexes.py` (3 lignes)
3. Relancer `add_mongodb_indexes.py`

### 🟡 IMPORTANT (Cette semaine)
4. Tester les requêtes avec les nouveaux index
5. Monitorer les performances

### 🟢 OPTIONNEL (Quand possible)
6. Installer Redis
7. Intégrer cache Redis
8. Activer rate limiting Redis

---

## 📝 NOTES TECHNIQUES

### Mapping des Champs Token

#### Scanner Core → MongoDB
```
scanner_core.py retourne:   mongodb_manager.py stocke:
├─ "address"            →   token_doc["token_address"]
├─ "chain"              →   token_doc["token_chain"]
├─ "name"               →   token_data["name"]
├─ "symbol"             →   token_data["symbol"]
├─ "risk_score"         →   token_doc["risk_score"]
├─ "is_safe"            →   token_doc["is_safe"]
└─ [tout le reste]      →   token_data[...]
```

#### Transformation dans `add_scanned_tokens_batch`:
```python
# Line 528-529
token_address = token.get('address')     # Lit "address"
token_chain = token.get('chain')         # Lit "chain"
# Puis stocke comme "token_address" et "token_chain"
```

### Structure de Document `scanned_tokens`
```json
{
  "_id": ObjectId("..."),
  "token_address": "0x123...",           // ← Pas "address"!
  "token_chain": "solana",               // ← Pas "chain"!
  "token_data": {
    "address": "0x123...",               // ← Original du scanner
    "chain": "solana",                   // ← Original du scanner
    "name": "Token Name",
    "symbol": "TKN",
    ...
  },
  "risk_score": 25,
  "is_safe": true,
  "is_pump_dump_suspect": false,
  "scanned_at": ISODate("2025-10-31...")
}
```

---

## ✅ CHECKLIST FINALE

Avant de considérer la cohérence des données comme résolue:

- [ ] Documents invalides supprimés
- [ ] Index `idx_address_chain_unique` créé avec succès
- [ ] Index sur `token_chain` (pas `chain`) créé
- [ ] Tous les 30 index créés sans erreur
- [ ] Test: Recherche par address + chain fonctionne
- [ ] Test: Pas de doublons dans scanned_tokens
- [ ] Monitoring: Temps de réponse des requêtes < 50ms

---

**Fin du Rapport**
