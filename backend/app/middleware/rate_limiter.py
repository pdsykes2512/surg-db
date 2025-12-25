"""
Rate Limiting Middleware
Implements request rate limiting using slowapi
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # Default rate limit
    storage_uri="memory://",  # Use in-memory storage (consider Redis for production)
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "error": "too_many_requests"
        }
    )


# Rate limit configurations for different endpoint types
AUTH_LIMIT = "5/minute"  # Strict limit for auth endpoints
DATA_READ_LIMIT = "100/minute"  # Moderate limit for read operations
DATA_WRITE_LIMIT = "50/minute"  # Stricter limit for write operations
EXPORT_LIMIT = "10/minute"  # Limited for resource-intensive operations
