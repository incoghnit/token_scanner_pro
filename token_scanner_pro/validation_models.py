"""
Pydantic Models for API Request Validation
Provides strict type checking and validation for all API endpoints
"""

from pydantic import BaseModel, Field, HttpUrl, validator, field_validator
from typing import Optional, Literal
from datetime import datetime


class ScanRequest(BaseModel):
    """Request model for /api/scan/start"""
    profile_url: HttpUrl = Field(..., description="DexScreener profile URL")
    max_tokens: int = Field(default=1, ge=1, le=50, description="Maximum tokens to scan (1-50)")
    nitter_url: Optional[HttpUrl] = Field(default=None, description="Custom Nitter instance URL")

    @field_validator('profile_url')
    @classmethod
    def validate_dexscreener_url(cls, v):
        """Ensure URL is from DexScreener"""
        if 'dexscreener.com' not in str(v):
            raise ValueError('URL must be from dexscreener.com')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "profile_url": "https://dexscreener.com/solana/ABC123",
                "max_tokens": 1
            }
        }


class TokenSearchRequest(BaseModel):
    """Request model for /api/token/search"""
    query: str = Field(..., min_length=2, max_length=100, description="Token symbol or name")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Sanitize search query"""
        # Remove special characters except alphanumeric and spaces
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', v)
        if not sanitized:
            raise ValueError('Query must contain alphanumeric characters')
        return sanitized.strip()


class FavoriteRequest(BaseModel):
    """Request model for /api/favorites/add"""
    token_address: str = Field(..., min_length=32, max_length=128, description="Token contract address")
    chain: Literal['solana', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'base'] = Field(..., description="Blockchain network")
    token_data: Optional[dict] = Field(default=None, description="Optional token metadata")

    @field_validator('token_address')
    @classmethod
    def validate_address(cls, v):
        """Validate token address format"""
        import re
        # Basic validation: alphanumeric
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Invalid token address format')
        return v


class AnalyzeTokenRequest(BaseModel):
    """Request model for /api/analyze-token"""
    address: str = Field(..., min_length=32, max_length=128)
    chain: Literal['solana', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'base']
    token_data: Optional[dict] = Field(default=None)

    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        """Validate address format"""
        import re
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Invalid address format')
        return v


class PriceRequest(BaseModel):
    """Request model for /api/token/price"""
    address: str = Field(..., min_length=32, max_length=128)
    chain: Literal['solana', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'base']

    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        """Validate address"""
        import re
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('Invalid address format')
        return v


class AutoDiscoveryRequest(BaseModel):
    """Request model for /api/discovery/auto/start"""
    interval_seconds: int = Field(default=300, ge=60, le=3600, description="Scan interval in seconds (60-3600)")
    max_tokens: int = Field(default=20, ge=5, le=50, description="Tokens per scan (5-50)")

    @field_validator('interval_seconds')
    @classmethod
    def validate_interval(cls, v):
        """Ensure interval is reasonable"""
        if v < 60:
            raise ValueError('Interval must be at least 60 seconds to avoid API rate limits')
        return v


class NewsRequest(BaseModel):
    """Request model for /api/news/crypto"""
    limit: int = Field(default=10, ge=1, le=50)
    force_refresh: bool = Field(default=False)


class DiscoveryRecentRequest(BaseModel):
    """Request model for /api/discovery/recent"""
    limit: int = Field(default=50, ge=1, le=200)
    chain: Optional[Literal['solana', 'ethereum', 'bsc', 'polygon', 'arbitrum', 'base']] = None


# Helper function to validate and parse request
def validate_request(model_class: type[BaseModel], data: dict) -> BaseModel:
    """
    Validate request data against Pydantic model

    Args:
        model_class: Pydantic model class
        data: Request data dictionary

    Returns:
        Validated model instance

    Raises:
        ValueError: If validation fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Validation error: {str(e)}")
