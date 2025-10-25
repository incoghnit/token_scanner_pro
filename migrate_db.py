#!/usr/bin/env python3
"""
Script de migration pour ajouter la table scanned_tokens
"""

import sqlite3
import sys

print("=" * 60)
print("🔧 MIGRATION DE LA BASE DE DONNÉES")
print("=" * 60)

db_path = 'token_scanner_pro/token_scanner.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n1️⃣ Vérification de la table scanned_tokens...")
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='scanned_tokens'
    """)

    if cursor.fetchone():
        print("   ✅ Table scanned_tokens existe déjà")
        conn.close()
        sys.exit(0)

    print("   ⚠️ Table scanned_tokens n'existe pas")
    print("\n2️⃣ Création de la table scanned_tokens...")

    # Créer la table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanned_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            token_chain TEXT NOT NULL DEFAULT 'solana',
            token_data TEXT NOT NULL,
            risk_score INTEGER,
            is_safe INTEGER DEFAULT 0,
            is_pump_dump_suspect INTEGER DEFAULT 0,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(token_address, token_chain)
        )
    ''')

    print("   ✅ Table scanned_tokens créée")

    print("\n3️⃣ Création des index...")

    # Créer les index
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_scanned_tokens_date
        ON scanned_tokens(scanned_at DESC)
    ''')
    print("   ✅ Index idx_scanned_tokens_date créé")

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_scanned_tokens_chain
        ON scanned_tokens(token_chain)
    ''')
    print("   ✅ Index idx_scanned_tokens_chain créé")

    # Commit les changements
    conn.commit()
    print("\n4️⃣ Vérification finale...")

    cursor.execute("SELECT COUNT(*) FROM scanned_tokens")
    count = cursor.fetchone()[0]
    print(f"   📊 Tokens en BDD: {count}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ MIGRATION RÉUSSIE !")
    print("=" * 60)
    print("\n💡 Prochaines étapes:")
    print("   1. Lance un scan de tokens")
    print("   2. Rafraîchis la page (F5)")
    print("   3. Les tokens devraient rester !")

except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
