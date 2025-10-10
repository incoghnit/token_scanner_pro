"""
Module de scanning de tokens crypto
Version améliorée avec RSI, Fibonacci, analyse Pump & Dump pour nouveaux tokens
et recherche de tokens - VERSION FINALE CORRIGÉE
"""

import requests
import json
import time
import re
from html import unescape
from datetime import datetime
from typing import Dict, Any, List, Optional

class TokenScanner:
    def __init__(self, nitter_url: str = "http://192.168.1.19:8080"):
        self.dexscreener_profiles_api = "https://api.dexscreener.com/token-profiles/latest/v1"
        self.dexscreener_search_api = "https://api.dexscreener.com/latest/dex/search"
        self.goplus_api = "https://api.gopluslabs.io/api/v1"
        self.dexscreener_api = "https://api.dexscreener.com/latest/dex"
        self.nitter_instance = nitter_url
        self.current_progress = 0
        self.total_tokens = 0
    
    def get_progress(self) -> Dict[str, Any]:
        """Retourne la progression actuelle"""
        return {
            "current": self.current_progress,
            "total": self.total_tokens,
            "percentage": (self.current_progress / self.total_tokens * 100) if self.total_tokens > 0 else 0
        }
    
    # ==================== 🆕 RECHERCHE DE TOKENS ====================
    
    def search_token(self, query: str) -> List[Dict]:
        """
        Recherche un token via l'API DexScreener
        """
        try:
            url = f"{self.dexscreener_search_api}?q={query}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            pairs = data.get('pairs', [])
            
            # Transformer en format utilisable
            tokens = []
            for pair in pairs:
                base_token = pair.get('baseToken', {})
                info = pair.get('info', {})
                
                # Extraire le Twitter depuis les socials
                twitter = None
                socials = info.get('socials', [])
                for social in socials:
                    if social.get('platform') == 'twitter':
                        handle = social.get('handle', '')
                        twitter = f"https://twitter.com/{handle}" if handle else None
                        break
                
                tokens.append({
                    'address': base_token.get('address'),
                    'chain': pair.get('chainId'),
                    'name': base_token.get('name'),
                    'symbol': base_token.get('symbol'),
                    'url': pair.get('url'),
                    'icon': info.get('imageUrl'),
                    'description': '',
                    'twitter': twitter,
                    'links': [],
                    'priceUsd': pair.get('priceUsd'),
                    'liquidity': pair.get('liquidity', {}).get('usd'),
                    'fdv': pair.get('fdv'),
                    'marketCap': pair.get('marketCap'),
                    'pairCreatedAt': pair.get('pairCreatedAt')
                })
            
            return tokens
            
        except Exception as e:
            print(f"Erreur recherche token: {e}")
            return []
    
    # ==================== TWITTER SCRAPING ====================
    
    def extract_twitter_username(self, twitter_url: str) -> Optional[str]:
        """Extrait le username depuis une URL Twitter"""
        if not twitter_url:
            return None
        match = re.search(r'(?:twitter\.com|x\.com)/([^/?]+)', twitter_url)
        return match.group(1) if match else None
    
    def scrape_twitter_profile(self, username: str) -> Dict[str, Any]:
        """Scrape un profil Twitter via Nitter local"""
        if not username:
            return {"error": "Username manquant"}
        
        username = username.strip('@')
        
        try:
            url = f"{self.nitter_instance}/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"error": f"Profil non accessible (HTTP {response.status_code})"}
            
            html = response.text
            
            profile_data = {
                "username": username,
                "followers": 0,
                "following": 0,
                "tweets": 0,
                "bio": "",
                "verified": False
            }
            
            stats_pattern = r'<span class="profile-stat-header">([^<]+)</span>\s*<span class="profile-stat-num">([^<]+)</span>'
            for stat_match in re.finditer(stats_pattern, html):
                stat_name = stat_match.group(1).strip().lower()
                stat_value = stat_match.group(2).strip()
                
                try:
                    clean_value = stat_value.replace(',', '').replace(' ', '')
                    
                    if 'k' in clean_value.lower():
                        value = int(float(clean_value.lower().replace('k', '')) * 1000)
                    elif 'm' in clean_value.lower():
                        value = int(float(clean_value.lower().replace('m', '')) * 1000000)
                    else:
                        value = int(clean_value) if clean_value.isdigit() else 0
                    
                    if 'follower' in stat_name:
                        profile_data['followers'] = value
                    elif 'following' in stat_name:
                        profile_data['following'] = value
                    elif 'tweet' in stat_name or 'post' in stat_name:
                        profile_data['tweets'] = value
                except ValueError:
                    pass
            
            bio_match = re.search(r'<div class="profile-bio"><p[^>]*>(.*?)</p>', html, re.DOTALL)
            if bio_match:
                bio_text = re.sub(r'<[^>]+>', '', bio_match.group(1))
                profile_data['bio'] = unescape(bio_text.strip())[:200]
            
            profile_data['verified'] = bool(re.search(r'verified-icon', html))
            
            return profile_data
            
        except requests.exceptions.Timeout:
            return {"error": "Timeout lors de la connexion à Nitter"}
        except requests.exceptions.ConnectionError:
            return {"error": "Impossible de se connecter à Nitter"}
        except Exception as e:
            return {"error": f"Erreur lors du scraping: {str(e)}"}
    
    def calculate_social_score(self, twitter_data: Dict) -> tuple:
        """Calcule un score social de 0 à 100"""
        if "error" in twitter_data:
            return 0, {"status": "Twitter non disponible"}
        
        score = 0
        details = {}
        
        followers = twitter_data.get('followers', 0)
        following = twitter_data.get('following', 0)
        tweets = twitter_data.get('tweets', 0)
        verified = twitter_data.get('verified', False)
        
        # Score followers (40 points max)
        if followers >= 100000:
            score += 40
            details['followers_score'] = "Excellent (100k+)"
        elif followers >= 50000:
            score += 35
            details['followers_score'] = "Très bon (50k+)"
        elif followers >= 10000:
            score += 30
            details['followers_score'] = "Bon (10k+)"
        elif followers >= 5000:
            score += 25
            details['followers_score'] = "Moyen (5k+)"
        elif followers >= 1000:
            score += 15
            details['followers_score'] = "Faible (1k+)"
        elif followers >= 100:
            score += 5
            details['followers_score'] = "Très faible (100+)"
        else:
            details['followers_score'] = "Quasi inexistant"
        
        # Ratio followers/following (20 points max)
        if following > 0:
            ratio = followers / following
            if ratio >= 10:
                score += 20
                details['ratio_score'] = "Excellent (10:1+)"
            elif ratio >= 3:
                score += 15
                details['ratio_score'] = "Bon (3:1+)"
            elif ratio >= 1:
                score += 10
                details['ratio_score'] = "Moyen (1:1+)"
            else:
                score += 5
                details['ratio_score'] = "Faible"
        
        # Score activité (20 points max)
        if tweets >= 1000:
            score += 20
            details['activity_score'] = "Très actif (1k+ tweets)"
        elif tweets >= 500:
            score += 15
            details['activity_score'] = "Actif (500+)"
        elif tweets >= 100:
            score += 10
            details['activity_score'] = "Moyen (100+)"
        elif tweets >= 10:
            score += 5
            details['activity_score'] = "Faible (10+)"
        else:
            details['activity_score'] = "Inactif"
        
        # Badge vérifié (20 points)
        if verified:
            score += 20
            details['verified'] = "Oui ✓"
        else:
            details['verified'] = "Non"
        
        details['total_score'] = score
        details['followers'] = followers
        details['following'] = following
        details['tweets'] = tweets
        
        return score, details
    
    # ==================== 🔧 RÉCUPÉRATION DES TOKENS (CORRIGÉ) ====================
    
    def fetch_latest_tokens(self) -> List[Dict]:
        """Récupère les derniers tokens listés sur DexScreener - VERSION CORRIGÉE"""
        try:
            response = requests.get(self.dexscreener_profiles_api, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ Erreur API DexScreener: Status {response.status_code}")
                return []
            
            data = response.json()
            
            if not data:
                print("❌ Aucune donnée retournée par l'API")
                return []
            
            print(f"📡 API retourne {len(data)} tokens au total")
            
            # 🔧 Mapping étendu des chaînes pour supporter toutes les variantes
            chain_mapping = {
                'solana': 'solana',
                'sol': 'solana',
                'ethereum': 'ethereum',
                'eth': 'ethereum',
                'base': 'base',
                'bsc': 'bsc',
                'bnb': 'bsc',  # ⚠️ BSC peut être retourné comme "bnb"
                'binance': 'bsc',
                'arbitrum': 'arbitrum',
                'arb': 'arbitrum',
                'polygon': 'polygon',
                'matic': 'polygon',
                'avalanche': 'avalanche',
                'avax': 'avalanche',
                'optimism': 'optimism',
                'op': 'optimism'
            }
            
            # Chaînes acceptées (normalisées)
            accepted_chains = ['solana', 'ethereum', 'base', 'bsc', 'arbitrum', 'polygon', 'avalanche', 'optimism']
            
            filtered_tokens = []
            chain_stats = {}
            
            for token in data:
                chain_id = token.get('chainId', '').lower()
                
                # 🔍 Debug: compter les tokens par chaîne d'origine
                if chain_id not in chain_stats:
                    chain_stats[chain_id] = 0
                chain_stats[chain_id] += 1
                
                # Normaliser le nom de la chaîne
                normalized_chain = chain_mapping.get(chain_id, chain_id)
                
                # Filtrer seulement les chaînes acceptées
                if normalized_chain in accepted_chains:
                    twitter = None
                    links = token.get('links', [])
                    for link in links:
                        if link.get('type') == 'twitter':
                            twitter = link.get('url')
                            break
                    
                    icon_url = token.get('icon', '')
                    
                    filtered_tokens.append({
                        'address': token.get('tokenAddress'),
                        'chain': normalized_chain,  # Utiliser le nom normalisé
                        'url': token.get('url'),
                        'icon': icon_url,
                        'description': token.get('description', 'N/A'),
                        'twitter': twitter,
                        'links': links
                    })
            
            # 📊 Afficher les statistiques
            print(f"\n📊 Statistiques des chaînes (API brute):")
            for chain, count in sorted(chain_stats.items(), key=lambda x: x[1], reverse=True):
                normalized = chain_mapping.get(chain, chain)
                accepted_marker = "✅" if normalized in accepted_chains else "❌"
                print(f"   {accepted_marker} {chain}: {count} tokens → {normalized}")
            
            print(f"\n✅ {len(filtered_tokens)} tokens acceptés après filtrage")
            
            # Afficher la répartition finale
            final_stats = {}
            for token in filtered_tokens:
                chain = token['chain']
                if chain not in final_stats:
                    final_stats[chain] = 0
                final_stats[chain] += 1
            
            print(f"\n📊 Répartition finale:")
            for chain, count in sorted(final_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"   {chain.upper()}: {count} tokens")
            print()
            
            return filtered_tokens
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def fetch_tokens_by_chains(self, max_per_chain: int = 5) -> List[Dict]:
        """
        🆕 Récupère les tokens récents en cherchant par chaîne
        Alternative à fetch_latest_tokens si l'API profile ne retourne pas assez de résultats
        """
        try:
            all_tokens = []
            chains_to_search = ['solana', 'ethereum', 'base', 'bsc', 'arbitrum', 'polygon']
            
            print(f"🔍 Recherche sur {len(chains_to_search)} chaînes...")
            
            for chain in chains_to_search:
                try:
                    # Utiliser l'API de recherche avec un terme générique
                    url = f"{self.dexscreener_search_api}?q={chain}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code != 200:
                        print(f"   ⚠️ {chain}: API erreur {response.status_code}")
                        continue
                    
                    data = response.json()
                    pairs = data.get('pairs', [])
                    
                    if not pairs:
                        print(f"   ❌ {chain}: aucun token trouvé")
                        continue
                    
                    # Prendre les N premiers tokens de cette chaîne
                    chain_tokens = []
                    for pair in pairs[:max_per_chain * 3]:  # Prendre plus pour filtrer ensuite
                        pair_chain = pair.get('chainId', '').lower()
                        
                        # Normaliser le nom de chaîne
                        if pair_chain in ['bnb', 'binance']:
                            pair_chain = 'bsc'
                        
                        if pair_chain != chain.lower():
                            continue
                        
                        base_token = pair.get('baseToken', {})
                        info = pair.get('info', {})
                        
                        # Extraire Twitter
                        twitter = None
                        socials = info.get('socials', [])
                        for social in socials:
                            if social.get('platform') == 'twitter':
                                handle = social.get('handle', '')
                                twitter = f"https://twitter.com/{handle}" if handle else None
                                break
                        
                        chain_tokens.append({
                            'address': base_token.get('address'),
                            'chain': chain,
                            'url': pair.get('url'),
                            'icon': info.get('imageUrl'),
                            'description': '',
                            'twitter': twitter,
                            'links': []
                        })
                        
                        if len(chain_tokens) >= max_per_chain:
                            break
                    
                    all_tokens.extend(chain_tokens)
                    print(f"   ✅ {chain.upper()}: {len(chain_tokens)} tokens récupérés")
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"   ❌ {chain}: Erreur - {e}")
                    continue
            
            print(f"\n✅ Total: {len(all_tokens)} tokens récupérés\n")
            return all_tokens
            
        except Exception as e:
            print(f"❌ Erreur générale: {e}")
            return []
    
    # ==================== MARKET DATA ====================
    
    def get_market_data(self, address: str) -> Dict[str, Any]:
        """Récupère les données de marché"""
        try:
            url = f"{self.dexscreener_api}/tokens/{address}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return {"error": "API non disponible"}
            
            data = response.json()
            pairs = data.get("pairs", [])
            
            if not pairs:
                return {"error": "Aucune paire trouvée"}
            
            main_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))
            
            return {
                "price_usd": float(main_pair.get("priceUsd", 0)),
                "price_change_24h": float(main_pair.get("priceChange", {}).get("h24", 0) or 0),
                "price_change_6h": float(main_pair.get("priceChange", {}).get("h6", 0) or 0),
                "price_change_1h": float(main_pair.get("priceChange", {}).get("h1", 0) or 0),
                "price_change_5m": float(main_pair.get("priceChange", {}).get("m5", 0) or 0),
                "volume_24h": float(main_pair.get("volume", {}).get("h24", 0) or 0),
                "volume_6h": float(main_pair.get("volume", {}).get("h6", 0) or 0),
                "liquidity_usd": float(main_pair.get("liquidity", {}).get("usd", 0) or 0),
                "market_cap": float(main_pair.get("marketCap", 0) or 0),
                "txns_24h_buys": main_pair.get("txns", {}).get("h24", {}).get("buys", 0),
                "txns_24h_sells": main_pair.get("txns", {}).get("h24", {}).get("sells", 0),
                "pair_created_at": main_pair.get("pairCreatedAt", "N/A"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== RSI CALCULATION ====================
    
    def calculate_rsi(self, market: Dict) -> Dict[str, Any]:
        """
        Calcule le RSI (Relative Strength Index) approximatif
        RSI > 70 = Suracheté (risque de dump)
        RSI < 30 = Survendu (potentiel rebond)
        """
        try:
            # Récupérer les variations de prix
            change_5m = market.get('price_change_5m', 0)
            change_1h = market.get('price_change_1h', 0)
            change_6h = market.get('price_change_6h', 0)
            change_24h = market.get('price_change_24h', 0)
            
            # Calculer les gains et pertes
            changes = [change_5m, change_1h, change_6h, change_24h]
            gains = [max(0, c) for c in changes]
            losses = [abs(min(0, c)) for c in changes]
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            # Calculer le RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Interprétation
            if rsi >= 70:
                signal = "SURACHETÉ"
                interpretation = "Fort risque de correction/dump"
                risk_level = "HIGH"
            elif rsi >= 50:
                signal = "HAUSSIER"
                interpretation = "Momentum positif"
                risk_level = "MEDIUM"
            elif rsi >= 30:
                signal = "NEUTRE"
                interpretation = "Pas de signal clair"
                risk_level = "LOW"
            else:
                signal = "SURVENDU"
                interpretation = "Potentiel rebond"
                risk_level = "LOW"
            
            return {
                "rsi_value": round(rsi, 2),
                "rsi_signal": signal,
                "rsi_interpretation": interpretation,
                "rsi_risk_level": risk_level
            }
            
        except Exception as e:
            return {
                "rsi_value": 50,
                "rsi_signal": "ERREUR",
                "rsi_interpretation": "Calcul impossible",
                "rsi_risk_level": "UNKNOWN"
            }
    
    # ==================== FIBONACCI ANALYSIS ====================
    
    def calculate_fibonacci(self, market: Dict) -> Dict[str, Any]:
        """
        Analyse Fibonacci - Identifie les niveaux clés de support/résistance
        """
        try:
            price = market.get('price_usd', 0)
            change_24h = market.get('price_change_24h', 0)
            
            if price == 0 or change_24h == 0:
                return {
                    "fibonacci_levels": {},
                    "current_position": "N/A",
                    "interpretation": "Données insuffisantes"
                }
            
            # Estimer le high et low des 24h
            if change_24h > 0:
                high_24h = price
                low_24h = price / (1 + (change_24h / 100))
            else:
                low_24h = price
                high_24h = price / (1 + (change_24h / 100))
            
            # Calculer les niveaux de Fibonacci
            diff = high_24h - low_24h
            
            levels = {
                "0%": low_24h,
                "23.6%": low_24h + (diff * 0.236),
                "38.2%": low_24h + (diff * 0.382),
                "50%": low_24h + (diff * 0.5),
                "61.8%": low_24h + (diff * 0.618),
                "78.6%": low_24h + (diff * 0.786),
                "100%": high_24h
            }
            
            # Déterminer la position actuelle
            position_pct = ((price - low_24h) / diff * 100) if diff > 0 else 50
            
            if position_pct >= 78.6:
                position = "Près de la résistance (danger)"
                risk = "HIGH"
            elif position_pct >= 61.8:
                position = "Zone de résistance forte"
                risk = "MEDIUM"
            elif position_pct >= 38.2:
                position = "Zone neutre"
                risk = "LOW"
            elif position_pct >= 23.6:
                position = "Zone de support fort"
                risk = "LOW"
            else:
                position = "Près du support (opportunité?)"
                risk = "LOW"
            
            return {
                "fibonacci_levels": levels,
                "current_position": position,
                "position_percentage": round(position_pct, 2),
                "risk_level": risk,
                "interpretation": f"Prix à {position_pct:.1f}% entre low et high 24h"
            }
            
        except Exception as e:
            return {
                "fibonacci_levels": {},
                "current_position": "ERREUR",
                "interpretation": "Calcul impossible"
            }
    
    # ==================== SECURITY CHECK ====================
    
    def check_security(self, address: str, chain: str) -> Dict[str, Any]:
        """Vérifie la sécurité via GoPlus et récupère le top 5 des holders"""
        chain_ids = {
            "ethereum": "1",
            "bsc": "56",
            "base": "8453",
            "arbitrum": "42161",
            "solana": "solana",
            "polygon": "137",
            "avalanche": "43114",
            "optimism": "10"
        }
        
        chain_id = chain_ids.get(chain.lower(), chain)
        
        try:
            url = f"{self.goplus_api}/token_security/{chain_id}?contract_addresses={address}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return {"error": "API non disponible"}
            
            data = response.json()
            
            if data.get("code") != 1:
                return {"error": "Token non trouvé"}
            
            result = data.get("result", {}).get(address.lower(), {})
            
            # 🆕 Récupérer et parser les top holders
            top_holders = []
            holders_data = result.get("holders", [])
            
            for i, holder in enumerate(holders_data[:5], 1):  # Top 5
                try:
                    address_holder = holder.get("address", "N/A")
                    balance = float(holder.get("balance", 0))
                    percent = float(holder.get("percent", 0))
                    is_locked = holder.get("is_locked", False)
                    is_contract = holder.get("is_contract", False)
                    
                    top_holders.append({
                        "rank": i,
                        "address": address_holder,
                        "balance": balance,
                        "percent": round(percent * 100, 2),  # Convertir en %
                        "is_locked": is_locked,
                        "is_contract": is_contract
                    })
                except Exception as e:
                    print(f"Erreur parsing holder {i}: {e}")
            
            # 🔧 CORRECTION DU BUG DE CONCENTRATION
            try:
                creator_balance = float(result.get("creator_balance", "0") or 0)
                owner_balance = float(result.get("owner_balance", "0") or 0)
                
                # Limiter à 100% maximum
                creator_balance = min(creator_balance, 100)
                owner_balance = min(owner_balance, 100)
            except:
                creator_balance = 0
                owner_balance = 0
            
            return {
                "is_honeypot": result.get("is_honeypot", "unknown") == "1",
                "is_open_source": result.get("is_open_source", "0") == "1",
                "is_mintable": result.get("is_mintable", "0") == "1",
                "owner_change_balance": result.get("owner_change_balance", "0") == "1",
                "hidden_owner": result.get("hidden_owner", "0") == "1",
                "selfdestruct": result.get("selfdestruct", "0") == "1",
                "buy_tax": float(result.get("buy_tax", "0")) if result.get("buy_tax") else 0,
                "sell_tax": float(result.get("sell_tax", "0")) if result.get("sell_tax") else 0,
                "holder_count": result.get("holder_count", "N/A"),
                "total_supply": result.get("total_supply", "N/A"),
                "creator_balance": creator_balance,
                "owner_balance": owner_balance,
                "top_holders": top_holders  # 🆕 Top 5 holders
            }
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== 🔧 PUMP & DUMP DETECTION (CORRIGÉ) ====================
    
    def detect_pump_dump(self, market: Dict, security: Dict, pair_created_at: str) -> Dict[str, Any]:
        """
        🆕 DÉTECTEUR DE PUMP & DUMP ADAPTÉ AUX NOUVEAUX TOKENS - VERSION CORRIGÉE
        """
        score = 0
        warnings = []
        indicators = {}
        token_age_hours = "N/A"
        
        if "error" in market or "error" in security:
            return {
                "pump_dump_score": 0,
                "pump_dump_risk": "UNKNOWN",
                "pump_dump_warnings": ["Données insuffisantes"],
                "pump_dump_indicators": {},
                "is_pump_dump_suspect": False,
                "token_age_hours": "N/A"
            }
        
        # Calculer l'âge du token
        try:
            if pair_created_at and pair_created_at != "N/A":
                created_timestamp = int(pair_created_at) / 1000
                token_age_hours = round((time.time() - created_timestamp) / 3600, 1)
        except Exception as e:
            print(f"⚠️ Erreur calcul âge token: {e}")
            token_age_hours = "N/A"
        
        is_new_token = isinstance(token_age_hours, (int, float)) and token_age_hours < 72
        
        # ===== 1. SPIKE DE VOLUME (adapté aux nouveaux tokens) =====
        volume_24h = market.get("volume_24h", 0)
        liquidity = market.get("liquidity_usd", 0)
        
        if liquidity > 0 and volume_24h > 0:
            volume_to_liquidity_ratio = volume_24h / liquidity
            
            # Seuils adaptés pour nouveaux tokens
            if is_new_token:
                # Plus tolérant pour les nouveaux tokens
                if volume_to_liquidity_ratio > 20:
                    score += 25
                    indicators['volume_spike'] = 100
                    warnings.append(f"🚨 Volume explosif suspect: {volume_to_liquidity_ratio:.1f}x la liquidité")
                elif volume_to_liquidity_ratio > 10:
                    score += 15
                    indicators['volume_spike'] = 70
                    warnings.append(f"⚠️ Volume très élevé: {volume_to_liquidity_ratio:.1f}x")
                elif volume_to_liquidity_ratio > 5:
                    score += 5
                    indicators['volume_spike'] = 40
                else:
                    indicators['volume_spike'] = 20
            else:
                # Seuils normaux pour tokens établis
                if volume_to_liquidity_ratio > 10:
                    score += 25
                    indicators['volume_spike'] = 100
                    warnings.append(f"🚨 Volume explosif: {volume_to_liquidity_ratio:.1f}x")
                elif volume_to_liquidity_ratio > 5:
                    score += 20
                    indicators['volume_spike'] = 80
                    warnings.append(f"⚠️ Volume spike: {volume_to_liquidity_ratio:.1f}x")
                elif volume_to_liquidity_ratio > 3:
                    score += 10
                    indicators['volume_spike'] = 50
                else:
                    indicators['volume_spike'] = 20
        else:
            indicators['volume_spike'] = 0
        
        # ===== 2. SPIKE DE PRIX (adapté aux nouveaux tokens) =====
        price_change_24h = market.get("price_change_24h", 0)
        price_change_1h = market.get("price_change_1h", 0)
        
        # Pour les nouveaux tokens, la volatilité est normale
        if is_new_token:
            if price_change_24h > 500:
                score += 30
                indicators['price_spike'] = 100
                warnings.append(f"🚨 Pump massif: +{price_change_24h:.0f}% en 24h")
            elif price_change_24h > 200:
                score += 20
                indicators['price_spike'] = 70
                warnings.append(f"⚠️ Hausse importante: +{price_change_24h:.0f}%")
            elif price_change_24h > 100:
                score += 5
                indicators['price_spike'] = 40
            else:
                indicators['price_spike'] = max(0, int(price_change_24h * 0.5))
            
            # Pump ultra-rapide (1h) est toujours suspect
            if price_change_1h > 100:
                score += 15
                warnings.append(f"🚨 Pump 1h: +{price_change_1h:.0f}%")
        else:
            # Tokens établis - seuils normaux
            if price_change_24h > 200:
                score += 30
                indicators['price_spike'] = 100
                warnings.append(f"🚨 PUMP: +{price_change_24h:.0f}%")
            elif price_change_24h > 100:
                score += 25
                indicators['price_spike'] = 85
                warnings.append(f"🚨 Pump fort: +{price_change_24h:.0f}%")
            elif price_change_24h > 50:
                score += 15
                indicators['price_spike'] = 60
            else:
                indicators['price_spike'] = max(0, int(price_change_24h * 1.5))
        
        # ===== 3. CONCENTRATION DES HOLDERS (🔧 CORRIGÉ) =====
        try:
            creator_balance = security.get("creator_balance", 0)
            owner_balance = security.get("owner_balance", 0)
            
            max_concentration = max(creator_balance, owner_balance)
            
            if max_concentration > 50:
                score += 20
                indicators['holder_concentration'] = 100
                warnings.append(f"🚨 Concentration extrême: {max_concentration:.1f}%")
            elif max_concentration > 30:
                score += 15
                indicators['holder_concentration'] = 75
                warnings.append(f"⚠️ Forte concentration: {max_concentration:.1f}%")
            elif max_concentration > 20:
                score += 10
                indicators['holder_concentration'] = 50
            else:
                indicators['holder_concentration'] = int(max_concentration * 2)
        except Exception as e:
            print(f"⚠️ Erreur concentration holders: {e}")
            indicators['holder_concentration'] = 0
        
        # ===== 4. LIQUIDITÉ CRITIQUE (adapté aux nouveaux tokens) =====
        if is_new_token:
            # Plus tolérant pour nouveaux tokens
            if liquidity < 1000:
                score += 20
                indicators['low_liquidity'] = 100
                warnings.append(f"🚨 Liquidité très faible: ${liquidity:,.0f}")
            elif liquidity < 3000:
                score += 10
                indicators['low_liquidity'] = 60
            else:
                indicators['low_liquidity'] = 0
        else:
            if liquidity < 5000:
                score += 15
                indicators['low_liquidity'] = 100
                warnings.append(f"🚨 Liquidité faible: ${liquidity:,.0f}")
            elif liquidity < 10000:
                score += 10
                indicators['low_liquidity'] = 70
            else:
                indicators['low_liquidity'] = 0
        
        # ===== 5. TOKEN RÉCENT (moins pénalisant maintenant) =====
        if isinstance(token_age_hours, (int, float)):
            if token_age_hours < 6:
                score += 5
                indicators['new_token'] = 80
                warnings.append(f"⚠️ Token très récent ({token_age_hours:.1f}h)")
            elif token_age_hours < 24:
                score += 3
                indicators['new_token'] = 50
            elif token_age_hours < 72:
                indicators['new_token'] = 30
            else:
                indicators['new_token'] = 0
        else:
            indicators['new_token'] = 0
        
        # ===== CALCUL DU NIVEAU DE RISQUE =====
        if score >= 70:
            risk_level = "CRITICAL"
        elif score >= 50:
            risk_level = "HIGH"
        elif score >= 30:
            risk_level = "MEDIUM"
        elif score >= 15:
            risk_level = "LOW"
        else:
            risk_level = "SAFE"
        
        is_suspect = score >= 50
        
        return {
            "pump_dump_score": min(score, 100),
            "pump_dump_risk": risk_level,
            "pump_dump_warnings": warnings,
            "pump_dump_indicators": indicators,
            "is_pump_dump_suspect": is_suspect,
            "token_age_hours": token_age_hours
        }
    
    # ==================== RISK SCORE ====================
    
    def calculate_risk_score(self, security: Dict, market: Dict) -> tuple:
        """Calcule le score de risque"""
        score = 0
        warnings = []
        
        if security.get("is_honeypot"):
            score += 50
            warnings.append("HONEYPOT DÉTECTÉ")
        
        if security.get("is_mintable"):
            score += 10
            warnings.append("Token mintable")
        
        if security.get("owner_change_balance"):
            score += 15
            warnings.append("Owner peut modifier balances")
        
        if security.get("hidden_owner"):
            score += 10
            warnings.append("Propriétaire caché")
        
        if security.get("selfdestruct"):
            score += 20
            warnings.append("Contract destructible")
        
        if not security.get("is_open_source"):
            score += 5
            warnings.append("Code non vérifié")
        
        buy_tax = security.get("buy_tax", 0)
        sell_tax = security.get("sell_tax", 0)
        
        if buy_tax > 10 or sell_tax > 10:
            score += 15
            warnings.append(f"Taxes élevées: {buy_tax}%/{sell_tax}%")
        
        if "error" not in market:
            liquidity = market.get("liquidity_usd", 0)
            volume = market.get("volume_24h", 0)
            txns = market.get("txns_24h_buys", 0) + market.get("txns_24h_sells", 0)
            
            if liquidity < 5000:
                score += 15
                warnings.append(f"Liquidité très faible: ${liquidity:,.0f}")
            elif liquidity < 10000:
                score += 10
                warnings.append(f"Liquidité faible: ${liquidity:,.0f}")
            
            if volume < 1000:
                score += 10
                warnings.append("Volume très faible")
            
            if txns < 10:
                score += 10
                warnings.append("Peu de transactions")
        
        return min(score, 100), warnings
    
    # ==================== 🔧 ANALYZE TOKEN (CORRIGÉ) ====================
    
    def analyze_token(self, token_info: Dict) -> Dict[str, Any]:
        """Analyse complète d'un token avec gestion d'erreur robuste"""
        address = token_info['address']
        chain = token_info['chain']
        icon = token_info.get('icon', '')
        
        try:
            market = self.get_market_data(address)
            time.sleep(0.5)
            
            security = self.check_security(address, chain)
            time.sleep(0.5)
            
            risk_score, warnings = self.calculate_risk_score(security, market)
            
            # RSI Calculation
            rsi_data = self.calculate_rsi(market)
            
            # Fibonacci Analysis
            fibonacci_data = self.calculate_fibonacci(market)
            
            # Pump & Dump (adapté nouveaux tokens)
            pair_created_at = market.get("pair_created_at", "N/A")
            pump_dump_analysis = self.detect_pump_dump(market, security, pair_created_at)
            
            # Twitter
            twitter_data = {}
            social_score = 0
            social_details = {}
            
            if token_info.get('twitter'):
                username = self.extract_twitter_username(token_info['twitter'])
                if username:
                    twitter_data = self.scrape_twitter_profile(username)
                    if "error" not in twitter_data:
                        social_score, social_details = self.calculate_social_score(twitter_data)
                    time.sleep(1)
            
            self.current_progress += 1
            
            return {
                "address": address,
                "chain": chain,
                "url": token_info.get('url'),
                "icon": icon,
                "description": token_info.get('description'),
                "twitter": token_info.get('twitter'),
                "twitter_data": twitter_data,
                "social_score": social_score,
                "social_details": social_details,
                "market": market,
                "security": security,
                "risk_score": risk_score,
                "warnings": warnings,
                "is_safe": risk_score < 50,
                
                # RSI
                "rsi_value": rsi_data.get("rsi_value", 50),
                "rsi_signal": rsi_data.get("rsi_signal", "NEUTRE"),
                "rsi_interpretation": rsi_data.get("rsi_interpretation", "N/A"),
                "rsi_risk_level": rsi_data.get("rsi_risk_level", "UNKNOWN"),
                
                # Fibonacci
                "fibonacci_levels": fibonacci_data.get("fibonacci_levels", {}),
                "fibonacci_position": fibonacci_data.get("current_position", "N/A"),
                "fibonacci_percentage": fibonacci_data.get("position_percentage", 0),
                
                # Pump & Dump - 🔧 Utiliser .get() pour éviter les KeyError
                "pump_dump_score": pump_dump_analysis.get("pump_dump_score", 0),
                "pump_dump_risk": pump_dump_analysis.get("pump_dump_risk", "UNKNOWN"),
                "pump_dump_warnings": pump_dump_analysis.get("pump_dump_warnings", []),
                "pump_dump_indicators": pump_dump_analysis.get("pump_dump_indicators", {}),
                "is_pump_dump_suspect": pump_dump_analysis.get("is_pump_dump_suspect", False),
                "token_age_hours": pump_dump_analysis.get("token_age_hours", "N/A"),
                
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ Erreur critique analyse {address[:10]}...: {e}")
            import traceback
            traceback.print_exc()
            
            # Retourner un résultat minimal en cas d'erreur
            self.current_progress += 1
            return {
                "address": address,
                "chain": chain,
                "url": token_info.get('url', ''),
                "icon": icon,
                "description": "Erreur d'analyse",
                "twitter": None,
                "twitter_data": {},
                "social_score": 0,
                "social_details": {},
                "market": {"error": str(e)},
                "security": {"error": str(e)},
                "risk_score": 100,
                "warnings": ["Erreur lors de l'analyse"],
                "is_safe": False,
                "rsi_value": 50,
                "rsi_signal": "ERREUR",
                "rsi_interpretation": "Analyse impossible",
                "rsi_risk_level": "UNKNOWN",
                "fibonacci_levels": {},
                "fibonacci_position": "N/A",
                "fibonacci_percentage": 0,
                "pump_dump_score": 0,
                "pump_dump_risk": "UNKNOWN",
                "pump_dump_warnings": [],
                "pump_dump_indicators": {},
                "is_pump_dump_suspect": False,
                "token_age_hours": "N/A",
                "timestamp": datetime.now().isoformat()
            }
    
    # ==================== SCAN TOKENS ====================
    
    def scan_tokens(self, max_tokens: int = 10) -> Dict[str, Any]:
        """Scanner principal avec fallback automatique"""
        print(f"🔍 Récupération des tokens...")
        
        # Essayer d'abord l'API profiles
        tokens = self.fetch_latest_tokens()
        
        # Si pas assez de tokens, utiliser l'API de recherche
        if len(tokens) < max_tokens:
            print(f"\n⚠️ Seulement {len(tokens)} tokens via API profiles")
            print(f"🔄 Tentative avec l'API de recherche...\n")
            tokens = self.fetch_tokens_by_chains(max_per_chain=max(2, max_tokens // 6))
        
        if not tokens:
            return {
                "success": False,
                "error": "Aucun token trouvé",
                "results": []
            }
        
        tokens = tokens[:max_tokens]
        self.total_tokens = len(tokens)
        self.current_progress = 0
        
        print(f"📊 Analyse de {len(tokens)} tokens...\n")
        
        results = []
        safe_tokens = []
        dangerous_tokens = []
        pump_dump_suspects = []
        
        for token in tokens:
            try:
                result = self.analyze_token(token)
                results.append(result)
                
                if result['is_safe']:
                    safe_tokens.append(result)
                else:
                    dangerous_tokens.append(result)
                
                if result['is_pump_dump_suspect']:
                    pump_dump_suspects.append(result)
                    
            except Exception as e:
                print(f"❌ Erreur analyse {token.get('address', 'N/A')[:8]}...: {e}")
                continue
        
        return {
            "success": True,
            "total_analyzed": len(results),
            "safe_count": len(safe_tokens),
            "dangerous_count": len(dangerous_tokens),
            "pump_dump_suspects_count": len(pump_dump_suspects),
            "results": results,
            "safe_tokens": sorted(safe_tokens, key=lambda x: x['risk_score']),
            "dangerous_tokens": sorted(dangerous_tokens, key=lambda x: x['risk_score'], reverse=True),
            "pump_dump_suspects": sorted(pump_dump_suspects, key=lambda x: x['pump_dump_score'], reverse=True),
            "timestamp": datetime.now().isoformat()
        }