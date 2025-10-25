#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier la persistence des tokens
"""

import sys
import os
sys.path.insert(0, 'token_scanner_pro')

import sqlite3
from database import Database

print("=" * 70)
print("🔍 DIAGNOSTIC DE PERSISTENCE DES TOKENS")
print("=" * 70)
print()

# 1. Vérifier la base de données
db_path = 'token_scanner_pro/token_scanner.db'
print(f"📂 Chemin BDD: {db_path}")
print(f"   Existe: {os.path.exists(db_path)}")
print()

# 2. Vérifier la table
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scanned_tokens'")
table_exists = cursor.fetchone()

if table_exists:
    print("✅ Table scanned_tokens existe")

    # Vérifier la structure
    cursor.execute("PRAGMA table_info(scanned_tokens)")
    columns = cursor.fetchall()
    print(f"   Colonnes: {len(columns)}")
    for col in columns:
        print(f"      - {col[1]} ({col[2]})")
else:
    print("❌ Table scanned_tokens n'existe PAS!")
    print("   → Exécutez: python3 migrate_db.py")
    sys.exit(1)

print()

# 3. Compter les tokens
cursor.execute("SELECT COUNT(*) FROM scanned_tokens")
count = cursor.fetchone()[0]

print(f"📊 Tokens dans la BDD: {count}/200")
print()

if count > 0:
    # Afficher les 5 derniers
    cursor.execute("""
        SELECT token_address, token_chain, is_safe, scanned_at
        FROM scanned_tokens
        ORDER BY scanned_at DESC
        LIMIT 5
    """)
    tokens = cursor.fetchall()

    print("📝 Derniers tokens:")
    for i, token in enumerate(tokens, 1):
        safe_emoji = "✅" if token[2] else "⚠️ "
        print(f"   {i}. {safe_emoji} {token[0][:25]}... ({token[1]}) - {token[3]}")
    print()
else:
    print("📭 Aucun token dans la BDD")
    print()
    print("💡 Que faire:")
    print("   1. Démarrez Flask: cd token_scanner_pro && python3 app.py")
    print("   2. Ouvrez http://localhost:5000")
    print("   3. Lancez un scan")
    print("   4. Vérifiez les logs Flask - vous devriez voir:")
    print("      🔍 DEBUG - Scan results success: True")
    print("      🔍 DEBUG - Scan results count: X")
    print("      💾 X/X tokens stockés dans la BDD")
    print()

conn.close()

# 4. Tester Database class
print("🧪 Test de la classe Database:")
try:
    db = Database()
    total = db.get_scanned_tokens_count()
    max_cap = db.MAX_SCANNED_TOKENS
    print(f"   ✅ Database connection OK")
    print(f"   📊 Count: {total}/{max_cap}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print()
print("=" * 70)
print("🎯 INSTRUCTIONS")
print("=" * 70)
print()
print("Si les tokens ne persistent pas après F5:")
print()
print("1. Vérifiez que Flask est redémarré (pour charger le nouveau code)")
print("2. Lancez un scan et vérifiez les logs Flask")
print("3. Cherchez ces messages de débogage:")
print("   🔍 DEBUG - Scan results success: True/False")
print("   🔍 DEBUG - Scan results count: X")
print()
print("Si count = 0:")
print("   → Le scanner ne trouve pas de tokens")
print("   → Vérifiez votre connexion internet et les APIs")
print()
print("Si success = False:")
print("   → Le scan a échoué")
print("   → Regardez l'erreur dans les logs Flask")
print()
print("Si les messages n'apparaissent pas:")
print("   → Flask n'est pas redémarré avec le nouveau code")
print("   → Arrêtez Flask (Ctrl+C) et relancez: python3 app.py")
print()
print("=" * 70)
