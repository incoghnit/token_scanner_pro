"""
Module de scanning de tokens crypto
Optimisé pour utilisation avec interface web
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
    
    def fetch_latest_tokens(self) -> List[Dict]:
        """Récupère les derniers tokens listés sur DexScreener"""
        try:
            response = requests.get(self.dexscreener_profiles_api, timeout=15)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            if not data:
                return []
            
            filtered_tokens = []
            for token in data:
                chain = token.get('chainId', '').lower()
                if chain in ['solana', 'ethereum', 'base', 'bsc', 'arbitrum']:
                    twitter = None
                    links = token.get('links', [])
                    for link in links:
                        if link.get('type') == 'twitter':
                            twitter = link.get('url')
                            break
                    
                    filtered_tokens.append({
                        'address': token.get('tokenAddress'),
                        'chain': chain,
                        'url': token.get('url'),
                        'description': token.get('description', 'N/A'),
                        'twitter': twitter,
                        'links': links
                    })
            
            return filtered_tokens
            
        except Exception as e:
            print(f"Erreur lors de la récupération: {e}")
            return []
    
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
                "volume_24h": float(main_pair.get("volume", {}).get("h24", 0) or 0),
                "liquidity_usd": float(main_pair.get("liquidity", {}).get("usd", 0) or 0),
                "market_cap": float(main_pair.get("marketCap", 0) or 0),
                "txns_24h_buys": main_pair.get("txns", {}).get("h24", {}).get("buys", 0),
                "txns_24h_sells": main_pair.get("txns", {}).get("h24", {}).get("sells", 0),
                "pair_created_at": main_pair.get("pairCreatedAt", "N/A"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_security(self, address: str, chain: str) -> Dict[str, Any]:
        """Vérifie la sécurité via GoPlus"""
        chain_ids = {
            "ethereum": "1",
            "bsc": "56",
            "base": "8453",
            "arbitrum": "42161",
            "solana": "solana"
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
            }
        except Exception as e:
            return {"error": str(e)}
    
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
    
    def analyze_token(self, token_info: Dict) -> Dict[str, Any]:
        """Analyse complète d'un token"""
        address = token_info['address']
        chain = token_info['chain']
        
        market = self.get_market_data(address)
        time.sleep(0.5)
        
        security = self.check_security(address, chain)
        time.sleep(0.5)
        
        risk_score, warnings = self.calculate_risk_score(security, market)
        
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
            "timestamp": datetime.now().isoformat()
        }
    
    def scan_tokens(self, max_tokens: int = 10) -> Dict[str, Any]:
        """Scanner principal avec retour structuré"""
        tokens = self.fetch_latest_tokens()
        
        if not tokens:
            return {
                "success": False,
                "error": "Aucun token trouvé",
                "results": []
            }
        
        tokens = tokens[:max_tokens]
        self.total_tokens = len(tokens)
        self.current_progress = 0
        
        results = []
        safe_tokens = []
        dangerous_tokens = []
        
        for token in tokens:
            try:
                result = self.analyze_token(token)
                results.append(result)
                
                if result['is_safe']:
                    safe_tokens.append(result)
                else:
                    dangerous_tokens.append(result)
            except Exception as e:
                print(f"Erreur analyse token: {e}")
                continue
        
        return {
            "success": True,
            "total_analyzed": len(results),
            "safe_count": len(safe_tokens),
            "dangerous_count": len(dangerous_tokens),
            "results": results,
            "safe_tokens": sorted(safe_tokens, key=lambda x: x['risk_score']),
            "dangerous_tokens": sorted(dangerous_tokens, key=lambda x: x['risk_score'], reverse=True),
            "timestamp": datetime.now().isoformat()
        }
