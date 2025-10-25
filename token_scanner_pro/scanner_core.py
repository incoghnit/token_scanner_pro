"""
Module de scanning de tokens crypto
Optimisé pour utilisation avec interface web
Version améliorée avec récupération des icons + DÉTECTION PUMP & DUMP
"""

import requests
import json
import time
import re
import os
from html import unescape
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

def retry_api_call(func: Callable, max_retries: int = 3, initial_delay: float = 2.0, backoff_factor: float = 2.0) -> Any:
    """
    Retry an API call with exponential backoff

    Args:
        func: Function to execute (should return a response or raise an exception)
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 2.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)

    Returns:
        Result from the function call

    Raises:
        Exception: If all retries fail, raises the last exception
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return func()
        except (requests.exceptions.RequestException, requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            last_exception = e

            if attempt < max_retries:
                print(f"⚠️  API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                print(f"   Retrying in {delay}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                print(f"❌ API call failed after {max_retries + 1} attempts")
                raise last_exception
        except Exception as e:
            # Non-network errors should not be retried
            print(f"❌ Non-retryable error: {e}")
            raise e

class TokenScanner:
    def __init__(self, nitter_url: str = None):
        self.dexscreener_profiles_api = "https://api.dexscreener.com/token-profiles/latest/v1"
        self.goplus_api = "https://api.gopluslabs.io/api/v1"
        self.dexscreener_api = "https://api.dexscreener.com/latest/dex"
        self.nitter_instance = nitter_url or os.getenv('NITTER_URL', 'http://localhost:8080')
        self.current_progress = 0
        self.total_tokens = 0

        # New APIs - Load from environment variables for security
        self.coindesk_api = "https://data-api.coindesk.com/news/v1/article/list"
        self.coindesk_token = os.getenv('COINDESK_API_KEY', '')
        self.coinmarketcap_api = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info"
        self.coinmarketcap_key = os.getenv('COINMARKETCAP_API_KEY', '')

        # Validate API keys are present
        if not self.coindesk_token:
            print("⚠️  WARNING: COINDESK_API_KEY not set in environment variables")
        if not self.coinmarketcap_key:
            print("⚠️  WARNING: COINMARKETCAP_API_KEY not set in environment variables")

        # Cache system (in-memory)
        self._news_cache = None
        self._news_cache_time = None
        self._news_cache_duration = 1800  # 30 minutes in seconds

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
        match = re.search(r'(?:twitter\.com|x\.com)/([^/?#]+)', twitter_url)
        return match.group(1) if match else None

    def scrape_twitter_profile(self, username: str) -> Dict[str, Any]:
        """Scrape un profil Twitter via Nitter"""
        try:
            url = f"{self.nitter_instance}/{username}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return {"error": "Profil non trouvé"}

            html = response.text

            followers_match = re.search(r'<span[^>]*class="profile-stat-num"[^>]*>([^<]+)</span>\s*<span[^>]*class="profile-stat-header"[^>]*>Followers', html)
            following_match = re.search(r'<span[^>]*class="profile-stat-num"[^>]*>([^<]+)</span>\s*<span[^>]*class="profile-stat-header"[^>]*>Following', html)
            tweets_match = re.search(r'<span[^>]*class="profile-stat-num"[^>]*>([^<]+)</span>\s*<span[^>]*class="profile-stat-header"[^>]*>Tweets', html)

            bio_match = re.search(r'<div[^>]*class="profile-bio"[^>]*>(.*?)</div>', html, re.DOTALL)

            def parse_count(match_obj):
                if not match_obj:
                    return 0
                count_str = unescape(match_obj.group(1)).strip().replace(',', '')
                if 'K' in count_str:
                    return int(float(count_str.replace('K', '')) * 1000)
                elif 'M' in count_str:
                    return int(float(count_str.replace('M', '')) * 1000000)
                try:
                    return int(count_str)
                except:
                    return 0

            return {
                "username": username,
                "followers": parse_count(followers_match),
                "following": parse_count(following_match),
                "tweets": parse_count(tweets_match),
                "bio": unescape(bio_match.group(1)).strip() if bio_match else "",
                "url": f"https://twitter.com/{username}"
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_social_score(self, twitter_data: Dict) -> tuple[int, Dict[str, Any]]:
        """Calcule le score social basé sur Twitter"""
        if "error" in twitter_data:
            return 0, {}

        score = 0
        details = {}

        followers = twitter_data.get("followers", 0)
        following = twitter_data.get("following", 0)
        tweets = twitter_data.get("tweets", 0)

        if followers > 10000:
            score += 30
            details["followers_status"] = "Excellent (>10K)"
        elif followers > 5000:
            score += 20
            details["followers_status"] = "Bon (>5K)"
        elif followers > 1000:
            score += 10
            details["followers_status"] = "Moyen (>1K)"
        else:
            details["followers_status"] = "Faible (<1K)"

        if following > 0:
            ratio = followers / following
            if ratio > 2:
                score += 20
                details["ratio_status"] = f"Excellent ({ratio:.1f}:1)"
            elif ratio > 1:
                score += 10
                details["ratio_status"] = f"Bon ({ratio:.1f}:1)"
            else:
                details["ratio_status"] = f"Faible ({ratio:.1f}:1)"

        if tweets > 500:
            score += 20
            details["activity_status"] = "Très actif (>500 tweets)"
        elif tweets > 100:
            score += 15
            details["activity_status"] = "Actif (>100 tweets)"
        elif tweets > 50:
            score += 10
            details["activity_status"] = "Modéré (>50 tweets)"
        else:
            details["activity_status"] = "Peu actif (<50 tweets)"

        bio = twitter_data.get("bio", "")
        if len(bio) > 50:
            score += 10
            details["bio_status"] = "Bio complète"
        else:
            details["bio_status"] = "Bio incomplète"

        if followers < 100 and tweets < 20:
            score -= 20
            details["warning"] = "Compte très récent ou inactif"

        details["total_score"] = max(0, min(100, score))

        return max(0, min(100, score)), details

    def fetch_latest_tokens(self) -> List[Dict]:
        """Récupère les derniers tokens depuis DexScreener"""
        try:
            response = requests.get(self.dexscreener_profiles_api, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            tokens = []

            for item in data:
                if item.get("chainId") and item.get("tokenAddress"):
                    icon = item.get("icon") or ""
                    links = item.get("links", [])

                    # Debug: log how many links each token has
                    if links:
                        print(f"📋 Token {item['tokenAddress'][:8]}... has {len(links)} links")

                    tokens.append({
                        "address": item["tokenAddress"],
                        "chain": item["chainId"],
                        "url": item.get("url", ""),
                        "icon": icon,
                        "description": item.get("description", ""),
                        "twitter": next((link["url"] for link in links if link.get("type") == "twitter"), None),
                        "links": links
                    })

            return tokens
        except Exception as e:
            print(f"Erreur fetch tokens: {e}")
            return []

    def get_market_data(self, address: str) -> Dict[str, Any]:
        """Récupère les données de marché via DexScreener"""
        try:
            url = f"{self.dexscreener_api}/tokens/{address}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return {"error": "API non disponible"}

            data = response.json()

            if "pairs" not in data or not data["pairs"]:
                return {"error": "Aucune paire trouvée"}

            pairs = data["pairs"]
            main_pair = max(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0))

            return {
                "price_usd": float(main_pair.get("priceUsd", 0)),
                "price_change_24h": float(main_pair.get("priceChange", {}).get("h24", 0) or 0),
                "price_change_6h": float(main_pair.get("priceChange", {}).get("h6", 0) or 0),
                "price_change_1h": float(main_pair.get("priceChange", {}).get("h1", 0) or 0),
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
                "total_supply": result.get("total_supply", "N/A"),
                "creator_balance": result.get("creator_balance", "0"),
                "owner_balance": result.get("owner_balance", "0"),
            }
        except Exception as e:
            return {"error": str(e)}

    def detect_pump_dump(self, market: Dict, security: Dict, pair_created_at: str) -> Dict[str, Any]:
        """
        🆕 DÉTECTEUR DE PUMP & DUMP
        Analyse les indicateurs suspects de manipulation de marché
        """
        score = 0
        warnings = []
        indicators = {}

        if "error" in market or "error" in security:
            return {
                "pump_dump_score": 0,
                "pump_dump_risk": "UNKNOWN",
                "pump_dump_warnings": ["Données insuffisantes pour l'analyse"],
                "pump_dump_indicators": {},
                "is_pump_dump_suspect": False
            }

        # ===== 1. ÂGE DU TOKEN =====
        try:
            if pair_created_at and pair_created_at != "N/A":
                created_timestamp = int(pair_created_at) / 1000
                age_hours = (datetime.now().timestamp() - created_timestamp) / 3600

                indicators["token_age_hours"] = round(age_hours, 2)

                if age_hours < 1:
                    score += 30
                    warnings.append(f"Token ULTRA récent ({age_hours:.1f}h)")
                elif age_hours < 6:
                    score += 20
                    warnings.append(f"Token très récent ({age_hours:.1f}h)")
                elif age_hours < 24:
                    score += 10
                    warnings.append(f"Token récent ({age_hours:.1f}h)")
        except:
            pass

        # ===== 2. VARIATION DE PRIX SUSPECTE =====
        price_change_24h = market.get("price_change_24h", 0)
        price_change_6h = market.get("price_change_6h", 0)
        price_change_1h = market.get("price_change_1h", 0)

        indicators["price_change_24h"] = price_change_24h
        indicators["price_change_6h"] = price_change_6h
        indicators["price_change_1h"] = price_change_1h

        if price_change_1h > 100:
            score += 25
            warnings.append(f"Pump violent: +{price_change_1h:.0f}% en 1h")
        elif price_change_1h > 50:
            score += 15
            warnings.append(f"Hausse suspecte: +{price_change_1h:.0f}% en 1h")

        if price_change_6h > 500:
            score += 20
            warnings.append(f"Pump massif: +{price_change_6h:.0f}% en 6h")

        if price_change_24h < -50:
            score += 25
            warnings.append(f"Dump en cours: {price_change_24h:.0f}% en 24h")

        # ===== 3. RATIO VOLUME / LIQUIDITÉ =====
        volume_24h = market.get("volume_24h", 0)
        liquidity = market.get("liquidity_usd", 1)

        if liquidity > 0:
            vol_liq_ratio = volume_24h / liquidity
            indicators["volume_liquidity_ratio"] = round(vol_liq_ratio, 2)

            if vol_liq_ratio > 5:
                score += 20
                warnings.append(f"Ratio Vol/Liq anormal: {vol_liq_ratio:.1f}x")
            elif vol_liq_ratio > 3:
                score += 10
                warnings.append(f"Ratio Vol/Liq élevé: {vol_liq_ratio:.1f}x")

        # ===== 4. LIQUIDITÉ FAIBLE =====
        if liquidity < 5000:
            score += 15
            warnings.append(f"Liquidité très faible: ${liquidity:,.0f}")
            indicators["low_liquidity"] = True

        # ===== 5. DÉSÉQUILIBRE BUY/SELL =====
        buys = market.get("txns_24h_buys", 0)
        sells = market.get("txns_24h_sells", 0)

        if buys > 0 and sells > 0:
            buy_sell_ratio = buys / sells if sells > 0 else 10
            indicators["buy_sell_ratio"] = round(buy_sell_ratio, 2)

            if buy_sell_ratio > 5:
                score += 15
                warnings.append(f"Déséquilibre achats/ventes: {buy_sell_ratio:.1f}:1")
            elif buy_sell_ratio < 0.2:
                score += 15
                warnings.append(f"Ventes massives: ratio {buy_sell_ratio:.2f}:1")

        # ===== 6. TAXES SUSPICIEUSES =====
        buy_tax = security.get("buy_tax", 0)
        sell_tax = security.get("sell_tax", 0)

        if sell_tax > buy_tax + 5:
            score += 10
            warnings.append(f"Tax vente élevée: {sell_tax}% vs {buy_tax}%")

        if buy_tax > 15 or sell_tax > 15:
            score += 10
            warnings.append("Taxes excessives (>15%)")

        # ===== CALCUL DU RISQUE FINAL =====
        score = min(score, 100)

        if score >= 70:
            risk_level = "EXTREME"
        elif score >= 50:
            risk_level = "HIGH"
        elif score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "pump_dump_score": score,
            "pump_dump_risk": risk_level,
            "pump_dump_warnings": warnings,
            "pump_dump_indicators": indicators,
            "is_pump_dump_suspect": score >= 50
        }

    def calculate_risk_score(self, security: Dict, market: Dict) -> tuple[int, List[str]]:
        """Calcule le score de risque global"""
        score = 0
        warnings = []

        if "error" in security:
            return 50, ["Impossible de vérifier la sécurité"]

        if security.get("is_honeypot"):
            score += 50
            warnings.append("⚠️ HONEYPOT DÉTECTÉ")

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
        icon = token_info.get('icon', '')

        market = self.get_market_data(address)
        time.sleep(0.5)

        security = self.check_security(address, chain)
        time.sleep(0.5)

        risk_score, warnings = self.calculate_risk_score(security, market)

        pair_created_at = market.get("pair_created_at", "N/A")
        pump_dump_analysis = self.detect_pump_dump(market, security, pair_created_at)

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

        # Extract social links from links array (support multiple type variants)
        links = token_info.get('links', [])
        website = None
        telegram = None
        discord = None

        # Debug: log available link types
        if links:
            link_types = [link.get('type', 'unknown') for link in links]
            print(f"🔗 DEBUG - Token {address[:8]}... has links: {link_types}")

        for link in links:
            link_type = link.get('type', '').lower()
            link_url = link.get('url', '')

            if not link_url:
                continue

            # Website variants: website, homepage, web, site
            if link_type in ['website', 'homepage', 'web', 'site']:
                if not website:  # Take first website found
                    website = link_url
                    print(f"  ✅ Website found: {website[:50]}...")

            # Telegram variants: telegram, tg
            elif link_type in ['telegram', 'tg']:
                if not telegram:
                    telegram = link_url
                    print(f"  ✅ Telegram found: {telegram[:50]}...")

            # Discord variants: discord, disc
            elif link_type in ['discord', 'disc']:
                if not discord:
                    discord = link_url
                    print(f"  ✅ Discord found: {discord[:50]}...")

            else:
                # Log unknown link types to help debug
                print(f"  ℹ️  Unknown link type '{link_type}': {link_url[:50]}...")

        self.current_progress += 1

        return {
            "address": address,
            "chain": chain,
            "url": token_info.get('url'),
            "icon": icon,
            "description": token_info.get('description'),
            "twitter": token_info.get('twitter'),
            "website": website,
            "telegram": telegram,
            "discord": discord,
            "twitter_data": twitter_data,
            "social_score": social_score,
            "social_details": social_details,
            "market": market,
            "security": security,
            "risk_score": risk_score,
            "warnings": warnings,
            "is_safe": risk_score < 50,
            "pump_dump_score": pump_dump_analysis["pump_dump_score"],
            "pump_dump_risk": pump_dump_analysis["pump_dump_risk"],
            "pump_dump_warnings": pump_dump_analysis["pump_dump_warnings"],
            "pump_dump_indicators": pump_dump_analysis["pump_dump_indicators"],
            "is_pump_dump_suspect": pump_dump_analysis["is_pump_dump_suspect"],
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
                print(f"Erreur analyse token: {e}")
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

    def fetch_crypto_news(self, limit: int = 10, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Récupère les actualités crypto depuis CoinDesk API avec cache de 30 minutes

        Args:
            limit: Nombre d'articles à récupérer (max 10)
            force_refresh: Force le rechargement même si le cache est valide

        Returns:
            Dict avec success, articles, cache_info
        """
        try:
            # Vérifier le cache
            current_time = time.time()
            if (not force_refresh and
                self._news_cache is not None and
                self._news_cache_time is not None and
                (current_time - self._news_cache_time) < self._news_cache_duration):

                print(f"📰 Using cached news (age: {int(current_time - self._news_cache_time)}s)")
                return {
                    "success": True,
                    "articles": self._news_cache[:limit],
                    "total": len(self._news_cache),
                    "cached": True,
                    "cache_age_seconds": int(current_time - self._news_cache_time),
                    "cache_expires_in": int(self._news_cache_duration - (current_time - self._news_cache_time))
                }

            # Récupérer depuis l'API avec retry logic
            print(f"📰 Fetching fresh news from CoinDesk API...")
            url = f"{self.coindesk_api}?lang=EN&limit={limit}"
            headers = {
                "Authorization": f"Bearer {self.coindesk_token}"
            }

            # API call with retry logic
            def api_call():
                return requests.get(url, headers=headers, timeout=10)

            try:
                response = retry_api_call(api_call, max_retries=3)
            except Exception as e:
                # If cache exists, return stale cache as fallback
                if self._news_cache is not None:
                    print(f"⚠️  API failed, returning stale cache as fallback")
                    return {
                        "success": True,
                        "articles": self._news_cache[:limit],
                        "total": len(self._news_cache),
                        "cached": True,
                        "stale_cache": True,
                        "error_message": f"Using stale cache due to API error: {str(e)}",
                        "cache_age_seconds": int(time.time() - self._news_cache_time) if self._news_cache_time else None
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API call failed and no cache available: {str(e)}",
                        "cached": False
                    }

            if response.status_code != 200:
                # If cache exists, return it as fallback
                if self._news_cache is not None:
                    print(f"⚠️  API returned {response.status_code}, using stale cache")
                    return {
                        "success": True,
                        "articles": self._news_cache[:limit],
                        "total": len(self._news_cache),
                        "cached": True,
                        "stale_cache": True,
                        "error_message": f"API returned status {response.status_code}",
                        "cache_age_seconds": int(time.time() - self._news_cache_time) if self._news_cache_time else None
                    }
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "cached": False
                }

            data = response.json()

            if "Data" not in data:
                return {
                    "success": False,
                    "error": "Invalid API response format",
                    "cached": False
                }

            # Formatter les articles
            articles = []
            for item in data["Data"]:
                article = {
                    "id": item.get("ID"),
                    "guid": item.get("GUID"),
                    "title": item.get("TITLE"),
                    "subtitle": item.get("SUBTITLE"),
                    "body": item.get("BODY", "")[:300] + "..." if item.get("BODY") else "",  # Preview only
                    "url": item.get("URL"),
                    "image_url": item.get("IMAGE_URL"),
                    "published_on": item.get("PUBLISHED_ON"),
                    "published_date": datetime.fromtimestamp(item.get("PUBLISHED_ON", 0)).strftime("%Y-%m-%d %H:%M") if item.get("PUBLISHED_ON") else "N/A",
                    "authors": item.get("AUTHORS"),
                    "keywords": item.get("KEYWORDS", "").split("|") if item.get("KEYWORDS") else [],
                    "sentiment": item.get("SENTIMENT", "NEUTRAL"),
                    "source": item.get("SOURCE_DATA", {}).get("NAME", "Unknown"),
                    "categories": [cat.get("NAME") for cat in item.get("CATEGORY_DATA", [])]
                }
                articles.append(article)

            # Mettre en cache
            self._news_cache = articles
            self._news_cache_time = current_time

            print(f"✅ Fetched and cached {len(articles)} articles")

            return {
                "success": True,
                "articles": articles,
                "total": len(articles),
                "cached": False,
                "cache_age_seconds": 0,
                "cache_expires_in": self._news_cache_duration
            }

        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            return {
                "success": False,
                "error": str(e),
                "cached": False
            }

    def search_token_info(self, query: str, by_symbol: bool = True) -> Dict[str, Any]:
        """
        Recherche un token sur CoinMarketCap API

        Args:
            query: Symbol (BTC, ETH) ou slug (bitcoin, ethereum) ou address
            by_symbol: True pour recherche par symbol, False pour slug

        Returns:
            Dict avec success, tokens (array car symbol peut correspondre à plusieurs tokens)
        """
        try:
            print(f"🔍 Searching token: {query}")

            # Construire l'URL selon le type de recherche
            if by_symbol:
                url = f"{self.coinmarketcap_api}?symbol={query.upper()}"
            else:
                url = f"{self.coinmarketcap_api}?slug={query.lower()}"

            headers = {
                "X-CMC_PRO_API_KEY": self.coinmarketcap_key,
                "Accept": "application/json"
            }

            # API call with retry logic
            def api_call():
                return requests.get(url, headers=headers, timeout=10)

            try:
                response = retry_api_call(api_call, max_retries=3)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"API call failed after retries: {str(e)}"
                }

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}"
                }

            data = response.json()

            if data.get("status", {}).get("error_code") != 0:
                return {
                    "success": False,
                    "error": data.get("status", {}).get("error_message", "Unknown error")
                }

            # V2 API returns data differently for symbol vs slug
            # Symbol: {"ETH": [array of tokens]}
            # Slug/ID: {"1027": {token object}}
            token_data = data.get("data", {})

            if not token_data:
                return {
                    "success": False,
                    "error": "No token found with this query"
                }

            # Formatter les résultats
            tokens = []

            for key, value in token_data.items():
                # Check if value is a list (symbol search) or dict (slug/id search)
                if isinstance(value, list):
                    # Symbol search returns array of tokens
                    for token_info in value:
                        token = {
                            "id": token_info.get("id"),
                            "name": token_info.get("name"),
                            "symbol": token_info.get("symbol"),
                            "slug": token_info.get("slug"),
                            "description": token_info.get("description"),
                            "logo": token_info.get("logo"),
                            "date_added": token_info.get("date_added"),
                            "date_launched": token_info.get("date_launched"),
                            "tags": token_info.get("tags", []),
                            "category": token_info.get("category"),
                            "platform": token_info.get("platform"),
                            "urls": token_info.get("urls", {}),
                            "infinite_supply": token_info.get("infinite_supply", False),
                            "notice": token_info.get("notice")
                        }
                        tokens.append(token)
                elif isinstance(value, dict):
                    # Slug/ID search returns single token object
                    token = {
                        "id": value.get("id"),
                        "name": value.get("name"),
                        "symbol": value.get("symbol"),
                        "slug": value.get("slug"),
                        "description": value.get("description"),
                        "logo": value.get("logo"),
                        "date_added": value.get("date_added"),
                        "date_launched": value.get("date_launched"),
                        "tags": value.get("tags", []),
                        "category": value.get("category"),
                        "platform": value.get("platform"),
                        "urls": value.get("urls", {}),
                        "infinite_supply": value.get("infinite_supply", False),
                        "notice": value.get("notice")
                    }
                    tokens.append(token)

            print(f"✅ Found {len(tokens)} token(s)")

            return {
                "success": True,
                "tokens": tokens,
                "total": len(tokens),
                "query": query,
                "search_type": "symbol" if by_symbol else "slug"
            }

        except Exception as e:
            print(f"❌ Error searching token: {e}")
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    print("🚀 Démarrage du scanner...")
    scanner = TokenScanner()
    results = scanner.scan_tokens(max_tokens=5)

    if results["success"]:
        print(f"\n✅ {results['total_analyzed']} tokens analysés")
        print(f"   Sûrs: {results['safe_count']}")
        print(f"   Risqués: {results['dangerous_count']}")
        print(f"   Pump & Dump suspects: {results['pump_dump_suspects_count']}")
    else:
        print(f"\n❌ Erreur: {results.get('error')}")
