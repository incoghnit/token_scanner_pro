#!/usr/bin/env python3
"""Vérifier les liens dans les tokens de la BDD"""
import sqlite3
import json

db_path = 'token_scanner_pro/token_scanner.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT token_data FROM scanned_tokens LIMIT 10')
rows = cursor.fetchall()

print(f"Tokens dans la BDD: {len(rows)}")
print("="*80)

for i, row in enumerate(rows):
    token_data = json.loads(row[0])
    print(f"\nToken {i+1}: {token_data.get('description', 'N/A')[:50]}")
    print(f"Address: {token_data.get('address', 'N/A')}")

    # Vérifier les liens
    website = token_data.get('website')
    telegram = token_data.get('telegram')
    discord = token_data.get('discord')
    twitter = token_data.get('twitter')

    print(f"  Website: {website if website else '❌ MISSING'}")
    print(f"  Twitter: {twitter if twitter else '❌ MISSING'}")
    print(f"  Telegram: {telegram if telegram else '❌ MISSING'}")
    print(f"  Discord: {discord if discord else '❌ MISSING'}")

conn.close()
print("\n" + "="*80)
