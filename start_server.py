#!/usr/bin/env python3
"""
Script de démarrage pour Token Scanner Pro
S'assure que la base de données est correctement initialisée avant de démarrer
"""

import os
import sys
import subprocess

print("=" * 70)
print("🚀 TOKEN SCANNER PRO - STARTUP SCRIPT")
print("=" * 70)
print()

# 1. Verify we're in the right directory
current_dir = os.getcwd()
print(f"📂 Current directory: {current_dir}")

if not os.path.exists('token_scanner_pro'):
    print("❌ Error: token_scanner_pro directory not found!")
    print("   Please run this script from the project root directory")
    sys.exit(1)

print("✅ Project structure OK")
print()

# 2. Run database migration
print("🔧 Running database migration...")
try:
    result = subprocess.run(
        ['python3', 'migrate_db.py'],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        print("✅ Database migration completed")
        if "Table scanned_tokens existe déjà" in result.stdout:
            print("   → Table already exists")
        elif "Table scanned_tokens créée" in result.stdout:
            print("   → Table created successfully")
    else:
        print(f"⚠️  Migration warning: {result.stderr}")
except Exception as e:
    print(f"⚠️  Migration error: {e}")

print()

# 3. Check database
print("📊 Checking database...")
import sqlite3

db_path = 'token_scanner_pro/token_scanner.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check scanned_tokens table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scanned_tokens'")
    if cursor.fetchone():
        cursor.execute('SELECT COUNT(*) FROM scanned_tokens')
        count = cursor.fetchone()[0]
        print(f"✅ scanned_tokens table exists: {count} tokens")
    else:
        print("❌ scanned_tokens table MISSING!")
        print("   Running migration again...")
        subprocess.run(['python3', 'migrate_db.py'])

    conn.close()
else:
    print(f"⚠️  Database will be created at: {os.path.abspath(db_path)}")

print()

# 4. Start Flask
print("=" * 70)
print("🌐 STARTING FLASK SERVER")
print("=" * 70)
print()
print("Server will start on: http://localhost:5000")
print()
print("📝 Important notes:")
print("   • Tokens are auto-saved to database (max 200)")
print("   • Press F5 to see tokens persist after page refresh")
print("   • Auto-scan runs every 5 minutes")
print("   • Press Ctrl+C to stop the server")
print()
print("=" * 70)
print()

# Change to app directory and start
os.chdir('token_scanner_pro')

try:
    subprocess.run(['python3', 'app.py'])
except KeyboardInterrupt:
    print("\n\n👋 Server stopped by user")
except Exception as e:
    print(f"\n\n❌ Error starting server: {e}")
    sys.exit(1)
