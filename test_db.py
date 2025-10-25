#!/usr/bin/env python3
"""
Script de test pour vérifier la base de données
"""

import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, '/home/user/token_scanner_pro/token_scanner_pro')

from database import Database
import json

print("=" * 60)
print("🔍 TEST DE LA BASE DE DONNÉES")
print("=" * 60)

# Initialiser la base de données
db = Database('token_scanner_pro/token_scanner.db')

print("\n1️⃣ Vérification de la table scanned_tokens...")
try:
    conn = db.get_connection()
    cursor = conn.cursor()

    # Vérifier si la table existe
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='scanned_tokens'
    """)

    table_exists = cursor.fetchone()
    if table_exists:
        print("   ✅ Table scanned_tokens existe")
    else:
        print("   ❌ Table scanned_tokens N'EXISTE PAS !")
        conn.close()
        sys.exit(1)

    # Compter les tokens
    cursor.execute("SELECT COUNT(*) FROM scanned_tokens")
    count = cursor.fetchone()[0]
    print(f"   📊 Nombre de tokens en BDD: {count}")

    # Afficher les 5 derniers tokens
    if count > 0:
        print("\n2️⃣ Les 5 derniers tokens scannés:")
        cursor.execute("""
            SELECT token_address, token_chain, risk_score, is_safe, scanned_at
            FROM scanned_tokens
            ORDER BY scanned_at DESC
            LIMIT 5
        """)

        for row in cursor.fetchall():
            address = row[0][:10] + "..." + row[0][-6:] if len(row[0]) > 20 else row[0]
            print(f"   • {address} ({row[1]}) - Risk: {row[2]} - Safe: {bool(row[3])} - {row[4]}")
    else:
        print("\n   ⚠️ Aucun token en base de données")
        print("   💡 Lancez un scan pour ajouter des tokens")

    conn.close()

except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n3️⃣ Test de l'API...")
print("   📡 Pour tester l'API, ouvrez dans votre navigateur:")
print("   http://localhost:5000/api/scanned-tokens")
print("   ou utilisez: curl http://localhost:5000/api/scanned-tokens")

print("\n" + "=" * 60)
print("✅ Test terminé")
print("=" * 60)
