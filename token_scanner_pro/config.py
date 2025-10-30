"""
Application Configuration
Centralized configuration for caching, rate limiting, and application settings
"""

import os
from typing import Optional
import redis
from functools import wraps
import json
import logging

# ==================== CONFIGURATION ====================

class Config:
    """Application configuration"""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB = os.getenv('MONGODB_DB', 'token_scanner')

    # Redis (Cache & Sessions)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    # Rate Limiting
    RATELIMIT_STORAGE_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True

    # Cache TTL (Time To Live in seconds)
    CACHE_TTL_SHORT = 60  # 1 minute
    CACHE_TTL_MEDIUM = 300  # 5 minutes
    CACHE_TTL_LONG = 3600  # 1 hour

    # External APIs
    DEXSCREENER_API_URL = 'https://api.dexscreener.com'
    GOPLUS_API_URL = 'https://api.gopluslabs.io'
    NITTER_URL = os.getenv('NITTER_URL', 'http://localhost:8080')

    # Anthropic Claude AI
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    # Security
    HTTPS_ONLY = os.getenv('HTTPS_ONLY', 'False').lower() == 'true'


# ==================== REDIS CLIENT ====================

class RedisClient:
    """Redis client singleton for caching"""

    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """Get or create Redis client"""
        if cls._instance is None:
            try:
                cls._instance = redis.Redis(
                    host=Config.REDIS_HOST,
                    port=Config.REDIS_PORT,
                    db=Config.REDIS_DB,
                    password=Config.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                cls._instance.ping()
                logging.info(f"✅ Redis connected: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logging.warning(f"⚠️ Redis unavailable: {e}. Caching disabled.")
                cls._instance = None
        return cls._instance

    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis is available"""
        client = cls.get_client()
        if client is None:
            return False
        try:
            client.ping()
            return True
        except:
            return False


# ==================== CACHE DECORATOR ====================

def cache(ttl: int = Config.CACHE_TTL_MEDIUM, key_prefix: str = ""):
    """
    Cache decorator for functions

    Usage:
        @cache(ttl=300, key_prefix="market_data")
        def get_market_data(address, chain):
            return expensive_api_call()

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = RedisClient.get_client()

            # If Redis not available, skip caching
            if redis_client is None:
                return func(*args, **kwargs)

            # Generate cache key
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}:{func.__name__}:{hash(args_str)}"

            try:
                # Try to get from cache
                cached = redis_client.get(cache_key)
                if cached:
                    logging.debug(f"🎯 Cache HIT: {cache_key}")
                    return json.loads(cached)

                # Cache miss - call function
                logging.debug(f"❌ Cache MISS: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                if result is not None:
                    redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )

                return result

            except Exception as e:
                logging.error(f"Cache error: {e}")
                # Fallback to direct call
                return func(*args, **kwargs)

        return wrapper
    return decorator


def cache_invalidate(key_pattern: str):
    """
    Invalidate cache keys matching pattern

    Args:
        key_pattern: Redis key pattern (e.g., "market_data:*")
    """
    redis_client = RedisClient.get_client()
    if redis_client is None:
        return 0

    try:
        keys = redis_client.keys(key_pattern)
        if keys:
            deleted = redis_client.delete(*keys)
            logging.info(f"🗑️ Invalidated {deleted} cache keys: {key_pattern}")
            return deleted
        return 0
    except Exception as e:
        logging.error(f"Cache invalidation error: {e}")
        return 0


# ==================== USER SESSION STATE ====================

class UserSessionState:
    """Manage user-specific state in Redis (replaces global state)"""

    @staticmethod
    def get_scan_state(user_id: str) -> dict:
        """Get user's scan state"""
        redis_client = RedisClient.get_client()
        if redis_client is None:
            return {"in_progress": False, "status": "idle", "results": []}

        try:
            key = f"scan_state:{user_id}"
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logging.error(f"Error getting scan state: {e}")

        return {"in_progress": False, "status": "idle", "results": []}

    @staticmethod
    def set_scan_state(user_id: str, state: dict, ttl: int = 3600):
        """Set user's scan state"""
        redis_client = RedisClient.get_client()
        if redis_client is None:
            return False

        try:
            key = f"scan_state:{user_id}"
            redis_client.setex(key, ttl, json.dumps(state, default=str))
            return True
        except Exception as e:
            logging.error(f"Error setting scan state: {e}")
            return False

    @staticmethod
    def clear_scan_state(user_id: str):
        """Clear user's scan state"""
        redis_client = RedisClient.get_client()
        if redis_client is None:
            return

        try:
            key = f"scan_state:{user_id}"
            redis_client.delete(key)
        except Exception as e:
            logging.error(f"Error clearing scan state: {e}")


# ==================== RATE LIMIT HELPERS ====================

def get_user_identifier() -> str:
    """
    Get user identifier for rate limiting
    Uses user_id if authenticated, IP otherwise
    """
    from flask import session, request

    # Try to get user_id from session
    user_id = session.get('user_id')
    if user_id:
        return f"user:{user_id}"

    # Fallback to IP address
    return f"ip:{request.remote_addr}"


# Rate limit configurations for different endpoints
RATE_LIMITS = {
    "scan": "5 per minute",  # Expensive operations
    "search": "30 per minute",  # Regular searches
    "favorites": "60 per minute",  # User actions
    "news": "20 per minute",  # External API calls
    "discovery": "10 per minute",  # Admin operations
    "default": "100 per minute"  # General endpoints
}
