"""
API Request Logging Middleware
Logs all API requests with detailed information
"""
import time
import logging
from pathlib import Path
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
log_dir = Path.home() / ".tmp"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "api_requests.log"

# Create logger
logger = logging.getLogger("api_requests")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# Format: timestamp | method | path | status | duration | user | ip | user_agent
formatter = logging.Formatter(
    '%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests
    """
    
    async def dispatch(self, request: Request, call_next):  # type: ignore
        # Start timer
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get user from token if available
        user = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Extract user from token (if available in request state after auth)
            user = getattr(request.state, "user_email", "authenticated")
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            logger.error(
                f"{method} {path} | 500 | {time.time() - start_time:.3f}s | "
                f"{user} | {ip_address} | {user_agent} | ERROR: {str(e)}"
            )
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the request
        logger.info(
            f"{method} {path} | {status_code} | {duration:.3f}s | "
            f"{user} | {ip_address} | {user_agent}"
        )
        
        return response
