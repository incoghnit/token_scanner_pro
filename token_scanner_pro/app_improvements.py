"""
CRITICAL IMPROVEMENTS FOR app.py

This file contains the key improvements to integrate into app.py:
1. Rate limiting with Redis
2. Pydantic validation
3. Structured logging
4. Redis cache
5. User-specific state (not global)

INSTRUCTIONS:
Replace the corresponding sections in app.py with these improved versions.
"""

# ==================== IMPORTS TO ADD AT TOP ====================
"""
Add these imports at the top of app.py (after existing imports):
"""

from config import Config, RedisClient, cache, UserSessionState, get_user_identifier, RATE_LIMITS
from logger import logger, LogContext, PerformanceLogger
from validation_models import (
    ScanRequest, TokenSearchRequest, FavoriteRequest,
    AnalyzeTokenRequest, validate_request
)
from pydantic import ValidationError
import time

# ==================== FLASK APP CONFIGURATION (REPLACE LINES 103-132) ====================
"""
Replace the Flask app initialization section with this:
"""

app = Flask(__name__)

# Load configuration from config.py
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Security: Force HTTPS in production
if Config.HTTPS_ONLY:
    @app.before_request
    def enforce_https():
        if not request.is_secure and not app.debug:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

# CORS configuration
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app,
     supports_credentials=True,
     origins=allowed_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# Rate Limiter with Redis storage
limiter = Limiter(
    app=app,
    key_func=get_user_identifier,  # Use user ID or IP
    storage_uri=Config.RATELIMIT_STORAGE_URL,  # Redis
    strategy=Config.RATELIMIT_STRATEGY,
    headers_enabled=Config.RATELIMIT_HEADERS_ENABLED
)

# Initialize Redis client
redis_client = RedisClient.get_client()
if redis_client:
    logger.info("✅ Redis cache enabled")
else:
    logger.warning("⚠️ Redis unavailable - caching disabled")

# ==================== REQUEST/RESPONSE LOGGING MIDDLEWARE ====================
"""
Add this middleware to log all requests/responses:
"""

@app.before_request
def log_request():
    """Log incoming requests"""
    request.start_time = time.time()

    user_id = session.get('user_id')
    LogContext.api_request(
        endpoint=request.endpoint or request.path,
        method=request.method,
        user_id=user_id
    )

@app.after_request
def log_response(response):
    """Log outgoing responses"""
    if hasattr(request, 'start_time'):
        duration_ms = (time.time() - request.start_time) * 1000
        LogContext.api_response(
            endpoint=request.endpoint or request.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
    return response

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler with structured logging"""
    LogContext.error(
        error_type=type(error).__name__,
        message=str(error),
        details={
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path
        }
    )

    # Return user-friendly error
    if isinstance(error, ValidationError):
        return jsonify({
            "success": False,
            "error": "Invalid request data",
            "details": error.errors()
        }), 400

    # Don't expose internal errors in production
    if not app.debug:
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

    return jsonify({
        "success": False,
        "error": str(error)
    }), 500

# ==================== IMPROVED /api/scan/start ENDPOINT ====================
"""
Replace the /api/scan/start endpoint with this improved version:
"""

@app.route('/api/scan/start', methods=['POST'])
@login_required
@limiter.limit(RATE_LIMITS["scan"])  # 5 per minute
def start_scan():
    """
    Start token scan with validation and user-specific state

    IMPROVED:
    - Pydantic validation
    - Rate limiting per user
    - User-specific state (no global state)
    - Structured logging
    - Performance tracking
    """
    try:
        # Get user ID
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        # Validate request with Pydantic
        try:
            validated_data = validate_request(ScanRequest, request.get_json())
        except ValueError as e:
            logger.warning(f"Validation error: {e}", extra={"user_id": user_id})
            return jsonify({"success": False, "error": str(e)}), 400

        # Check if user already has scan in progress
        current_state = UserSessionState.get_scan_state(user_id)
        if current_state.get('in_progress'):
            return jsonify({
                "success": False,
                "error": "Scan already in progress. Please wait."
            }), 429

        # Set scan as in progress
        UserSessionState.set_scan_state(user_id, {
            "in_progress": True,
            "status": "starting",
            "started_at": datetime.now().isoformat()
        })

        # Run scan with performance tracking
        with PerformanceLogger(f"token_scan_user_{user_id}"):
            try:
                results = scanner.scan_tokens_from_profile(
                    str(validated_data.profile_url),
                    validated_data.max_tokens
                )

                # Save results to user state
                UserSessionState.set_scan_state(user_id, {
                    "in_progress": False,
                    "status": "completed",
                    "results": results,
                    "completed_at": datetime.now().isoformat()
                })

                # Log scan completion
                LogContext.scan_event(
                    event="scan_completed",
                    tokens_count=len(results) if results else 0,
                    user_id=user_id
                )

                return jsonify({
                    "success": True,
                    "message": f"Scan completed - {len(results)} token(s) analyzed"
                })

            except Exception as e:
                # Log error and update state
                LogContext.error("scan_error", str(e), {"user_id": user_id})

                UserSessionState.set_scan_state(user_id, {
                    "in_progress": False,
                    "status": "error",
                    "error": str(e)
                })

                return jsonify({
                    "success": False,
                    "error": f"Scan failed: {str(e)}"
                }), 500

    except Exception as e:
        logger.error(f"Unexpected error in start_scan: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@app.route('/api/scan/progress', methods=['GET'])
@login_required
def get_scan_progress():
    """Get scan progress for current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    state = UserSessionState.get_scan_state(user_id)

    return jsonify({
        "success": True,
        "in_progress": state.get('in_progress', False),
        "status": state.get('status', 'idle'),
        "message": state.get('status', 'No scan in progress')
    })


@app.route('/api/scan/results', methods=['GET'])
@login_required
def get_scan_results():
    """Get scan results for current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    state = UserSessionState.get_scan_state(user_id)
    results = state.get('results', [])

    return jsonify({
        "success": True,
        "results": results,
        "count": len(results) if results else 0
    })

# ==================== IMPROVED /api/favorites/add WITH VALIDATION ====================
"""
Replace /api/favorites/add with this improved version:
"""

@app.route('/api/favorites/add', methods=['POST'])
@login_required
@limiter.limit(RATE_LIMITS["favorites"])  # 60 per minute
def add_favorite():
    """Add token to favorites with validation"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        # Validate request
        try:
            validated_data = validate_request(FavoriteRequest, request.get_json())
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        # Add to favorites
        favorite_id = db.add_favorite(
            user_id=user_id,
            token_address=validated_data.token_address,
            chain=validated_data.chain,
            token_data=validated_data.token_data
        )

        if favorite_id:
            logger.info(f"Favorite added: {validated_data.token_address}", extra={"user_id": user_id})
            return jsonify({
                "success": True,
                "message": "Token added to favorites",
                "favorite_id": favorite_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to add favorite"
            }), 500

    except Exception as e:
        LogContext.error("favorite_add_error", str(e), {"user_id": user_id})
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== IMPROVED /api/token/search WITH CACHE ====================
"""
Replace /api/token/search with this cached version:
"""

@app.route('/api/token/search', methods=['GET'])
@limiter.limit(RATE_LIMITS["search"])  # 30 per minute
def search_token():
    """Search tokens with validation and caching"""
    try:
        query = request.args.get('query', '').strip()

        # Validate
        try:
            validated_data = validate_request(TokenSearchRequest, {"query": query})
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        # Try cache first
        cache_key = f"token_search:{validated_data.query.lower()}"
        if redis_client:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                LogContext.cache_event("hit", cache_key, hit=True)
                return jsonify(json.loads(cached_result))

        # Cache miss - call external API
        LogContext.cache_event("miss", cache_key, hit=False)

        with PerformanceLogger(f"token_search_{validated_data.query}"):
            # Call CoinMarketCap or similar API here
            # For now, return placeholder
            tokens = []  # Replace with actual API call

            result = {
                "success": True,
                "tokens": tokens,
                "count": len(tokens)
            }

            # Cache result for 5 minutes
            if redis_client:
                redis_client.setex(
                    cache_key,
                    Config.CACHE_TTL_MEDIUM,
                    json.dumps(result)
                )

            return jsonify(result)

    except Exception as e:
        LogContext.error("token_search_error", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== INSTRUCTIONS ====================
"""
TO APPLY THESE IMPROVEMENTS:

1. Add new imports at top of app.py
2. Replace Flask initialization section (lines ~103-132)
3. Add request/response logging middleware
4. Replace /api/scan/start endpoint
5. Replace /api/favorites/add endpoint
6. Replace /api/token/search endpoint
7. Apply similar patterns to other endpoints

TESTING:
1. Install dependencies: pip install -r requirements.txt
2. Start Redis: docker run -d -p 6379:6379 redis:alpine
3. Test endpoints with validation errors
4. Check logs for JSON formatted output
5. Monitor Redis cache hits in logs

MIGRATION CHECKLIST:
☐ Update all API endpoints with validation
☐ Add rate limits to all sensitive endpoints
☐ Replace global state with UserSessionState
☐ Add caching to external API calls
☐ Test error handling
☐ Monitor logs in production
"""
