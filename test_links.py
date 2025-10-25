#!/usr/bin/env python3
"""Script de débogage pour vérifier l'extraction des liens sociaux"""
import requests
import json

print("Test 1: DexScreener Profiles API (comme fetch_latest_tokens)")
print("="*80)

# Test avec l'API profiles
url = "https://api.dexscreener.com/token-profiles/latest/v1"
response = requests.get(url, timeout=10)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} tokens")

    # Prendre les 5 premiers tokens
    for i, item in enumerate(data[:5]):
        print(f"\n{'='*80}")
        print(f"TOKEN {i+1}: {item.get('description', 'N/A')}")
        print(f"Address: {item.get('tokenAddress', 'N/A')}")
        print(f"Chain: {item.get('chainId', 'N/A')}")
        print(f"{'='*80}")

        # Afficher les liens
        links = item.get('links', [])
        print(f"\nLinks array ({len(links)} links):")
        for link in links:
            print(f"  - Type: '{link.get('type')}', URL: {link.get('url')}")

        # Tester l'extraction comme dans scanner_core.py
        website = None
        telegram = None
        discord = None
        twitter = None

        for link in links:
            link_type = link.get('type', '').lower()
            link_url = link.get('url', '')

            if link_type == 'website':
                website = link_url
            elif link_type == 'telegram':
                telegram = link_url
            elif link_type == 'discord':
                discord = link_url
            elif link_type == 'twitter':
                twitter = link_url

        print(f"\nExtracted links:")
        print(f"  Website: {website}")
        print(f"  Twitter: {twitter}")
        print(f"  Telegram: {telegram}")
        print(f"  Discord: {discord}")

        if i == 0:
            print(f"\nFull structure:")
            print(json.dumps(item, indent=2)[:1000])

print("\n" + "="*80)
print("Test terminé")
