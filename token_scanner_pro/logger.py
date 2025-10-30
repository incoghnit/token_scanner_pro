"""
Structured Logging Configuration
Provides JSON-formatted logging with different levels and contexts
"""

import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime
from typing import Optional


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add level name
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

        # Add logger name
        log_record['logger'] = record.name

        # Add module info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


def setup_logger(name: str = "token_scanner", level: str = "INFO") -> logging.Logger:
    """
    Setup structured JSON logger

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(logger)s %(module)s %(function)s %(message)s'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Create default logger
logger = setup_logger()


# ==================== CONTEXT LOGGERS ====================

class LogContext:
    """Add context to logs (e.g., request_id, user_id)"""

    @staticmethod
    def api_request(endpoint: str, method: str, user_id: Optional[str] = None):
        """Log API request"""
        logger.info(
            "API request received",
            extra={
                "endpoint": endpoint,
                "method": method,
                "user_id": user_id,
                "type": "api_request"
            }
        )

    @staticmethod
    def api_response(endpoint: str, status_code: int, duration_ms: float):
        """Log API response"""
        logger.info(
            "API response sent",
            extra={
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "type": "api_response"
            }
        )

    @staticmethod
    def external_api_call(api_name: str, endpoint: str, duration_ms: float, success: bool):
        """Log external API call"""
        logger.info(
            f"External API call: {api_name}",
            extra={
                "api_name": api_name,
                "endpoint": endpoint,
                "duration_ms": round(duration_ms, 2),
                "success": success,
                "type": "external_api"
            }
        )

    @staticmethod
    def cache_event(event_type: str, key: str, hit: Optional[bool] = None):
        """Log cache event"""
        logger.debug(
            f"Cache {event_type}",
            extra={
                "event": event_type,
                "key": key,
                "hit": hit,
                "type": "cache"
            }
        )

    @staticmethod
    def database_query(collection: str, operation: str, duration_ms: float, count: Optional[int] = None):
        """Log database query"""
        logger.debug(
            f"Database {operation}",
            extra={
                "collection": collection,
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "count": count,
                "type": "database"
            }
        )

    @staticmethod
    def scan_event(event: str, tokens_count: int, duration_s: Optional[float] = None, user_id: Optional[str] = None):
        """Log token scan event"""
        logger.info(
            f"Token scan: {event}",
            extra={
                "event": event,
                "tokens_count": tokens_count,
                "duration_s": round(duration_s, 2) if duration_s else None,
                "user_id": user_id,
                "type": "scan"
            }
        )

    @staticmethod
    def security_event(event_type: str, user_id: Optional[str], details: dict):
        """Log security event"""
        logger.warning(
            f"Security event: {event_type}",
            extra={
                "event_type": event_type,
                "user_id": user_id,
                "details": details,
                "type": "security"
            }
        )

    @staticmethod
    def error(error_type: str, message: str, details: Optional[dict] = None):
        """Log error with context"""
        logger.error(
            message,
            extra={
                "error_type": error_type,
                "details": details or {},
                "type": "error"
            },
            exc_info=True
        )


# ==================== PERFORMANCE MONITORING ====================

class PerformanceLogger:
    """Performance monitoring helper"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
            if exc_type:
                logger.error(
                    f"Operation failed: {self.operation_name}",
                    extra={
                        "operation": self.operation_name,
                        "duration_ms": round(duration_ms, 2),
                        "error": str(exc_val),
                        "type": "performance"
                    }
                )
            else:
                logger.info(
                    f"Operation completed: {self.operation_name}",
                    extra={
                        "operation": self.operation_name,
                        "duration_ms": round(duration_ms, 2),
                        "type": "performance"
                    }
                )


# Usage example:
# with PerformanceLogger("token_scan"):
#     result = expensive_operation()
