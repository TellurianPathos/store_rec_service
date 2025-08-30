"""
Security utilities and middleware for the AI recommendation service.
Production-ready security features including API key authentication and rate limiting.
"""
from fastapi import Security, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import hashlib
import hmac
import time
import os
from datetime import datetime, timedelta
import secrets

from app.logger import get_logger
from app.exceptions import DataValidationError, RateLimitError

logger = get_logger(__name__)

# Security configuration
SECURITY_CONFIG = {
    "api_key_required": os.getenv("REQUIRE_API_KEY", "false").lower() == "true",
    "api_keys": set(os.getenv("API_KEYS", "").split(",")) if os.getenv("API_KEYS") else set(),
    "rate_limit_enabled": os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    "max_requests_per_minute": int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60")),
    "max_requests_per_hour": int(os.getenv("MAX_REQUESTS_PER_HOUR", "1000")),
    "enable_ip_filtering": os.getenv("ENABLE_IP_FILTERING", "false").lower() == "true",
    "allowed_ips": set(os.getenv("ALLOWED_IPS", "").split(",")) if os.getenv("ALLOWED_IPS") else set(),
    "blocked_ips": set(os.getenv("BLOCKED_IPS", "").split(",")) if os.getenv("BLOCKED_IPS") else set(),
}

security = HTTPBearer(auto_error=False)


class RateLimiter:
    """
    Advanced rate limiter with multiple time windows and burst protection.
    In production, use Redis for distributed rate limiting.
    """
    
    def __init__(self):
        self.requests = {}  # {identifier: [timestamps]}
        self.blocked_until = {}  # {identifier: unblock_timestamp}
    
    def _clean_old_requests(self, identifier: str, window_seconds: int):
        """Clean old request timestamps"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        if identifier in self.requests:
            self.requests[identifier] = [
                timestamp for timestamp in self.requests[identifier]
                if timestamp > cutoff_time
            ]
            
            if not self.requests[identifier]:
                del self.requests[identifier]
    
    def is_rate_limited(
        self, 
        identifier: str, 
        max_requests: int, 
        window_seconds: int
    ) -> tuple[bool, dict]:
        """
        Check if identifier is rate limited.
        
        Args:
            identifier: Unique identifier (user ID, IP, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_limited, rate_info)
        """
        current_time = time.time()
        
        # Check if currently blocked
        if identifier in self.blocked_until:
            if current_time < self.blocked_until[identifier]:
                return True, {
                    "blocked_until": self.blocked_until[identifier],
                    "reason": "temporarily_blocked"
                }
            else:
                del self.blocked_until[identifier]
        
        # Clean old requests
        self._clean_old_requests(identifier, window_seconds)
        
        # Count current requests
        request_count = len(self.requests.get(identifier, []))
        
        if request_count >= max_requests:
            # Block for additional time if severely over limit
            if request_count > max_requests * 1.5:
                self.blocked_until[identifier] = current_time + window_seconds * 2
                
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={
                    "identifier": identifier,
                    "request_count": request_count,
                    "limit": max_requests,
                    "window_seconds": window_seconds
                }
            )
            
            return True, {
                "request_count": request_count,
                "limit": max_requests,
                "window_seconds": window_seconds,
                "retry_after": window_seconds
            }
        
        return False, {
            "request_count": request_count,
            "limit": max_requests,
            "remaining": max_requests - request_count
        }
    
    def record_request(self, identifier: str):
        """Record a request for the identifier"""
        current_time = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        self.requests[identifier].append(current_time)


# Global rate limiter instance
rate_limiter = RateLimiter()


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate API key against configured keys.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not SECURITY_CONFIG["api_key_required"]:
            return True
        
        if not api_key:
            return False
        
        # Hash comparison to prevent timing attacks
        expected_keys = SECURITY_CONFIG["api_keys"]
        
        for expected_key in expected_keys:
            if hmac.compare_digest(api_key, expected_key):
                return True
        
        return False
    
    @staticmethod
    def validate_ip_address(ip_address: str) -> bool:
        """
        Validate IP address against allow/block lists.
        
        Args:
            ip_address: Client IP address
            
        Returns:
            True if allowed, False otherwise
        """
        if not SECURITY_CONFIG["enable_ip_filtering"]:
            return True
        
        # Check blocked IPs first
        if ip_address in SECURITY_CONFIG["blocked_ips"]:
            logger.warning(f"Blocked IP attempted access: {ip_address}")
            return False
        
        # Check allowed IPs if configured
        allowed_ips = SECURITY_CONFIG["allowed_ips"]
        if allowed_ips and ip_address not in allowed_ips:
            logger.warning(f"Unauthorized IP attempted access: {ip_address}")
            return False
        
        return True
    
    @staticmethod
    def validate_user_agent(user_agent: str) -> bool:
        """
        Validate user agent for suspicious patterns.
        
        Args:
            user_agent: User agent string
            
        Returns:
            True if valid, False otherwise
        """
        if not user_agent:
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "sqlmap",
            "nikto",
            "nessus",
            "burp",
            "nmap",
            "masscan",
            "python-requests/",  # Unless explicitly allowed
            "curl/",             # Unless explicitly allowed
            "wget/",             # Unless explicitly allowed
        ]
        
        user_agent_lower = user_agent.lower()
        
        # In development, allow common tools
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            allowed_dev_tools = ["python-requests/", "curl/", "wget/", "httpx/"]
            if any(tool in user_agent_lower for tool in allowed_dev_tools):
                return True
        
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower:
                logger.warning(
                    f"Suspicious user agent detected: {user_agent}",
                    extra={"user_agent": user_agent, "pattern": pattern}
                )
                return False
        
        return True


security_validator = SecurityValidator()


async def verify_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """
    Verify API key if required.
    
    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials
        
    Returns:
        API key if valid or None if not required
        
    Raises:
        HTTPException: If API key validation fails
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    if not SECURITY_CONFIG["api_key_required"]:
        return None
    
    if not credentials:
        logger.warning(
            "API key required but not provided",
            extra={"request_id": request_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AuthenticationRequired",
                "message": "API key required for access",
                "request_id": request_id
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = credentials.credentials
    
    if not security_validator.validate_api_key(api_key):
        logger.warning(
            "Invalid API key provided",
            extra={
                "request_id": request_id,
                "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "short_key"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "InvalidApiKey",
                "message": "Invalid API key provided",
                "request_id": request_id
            }
        )
    
    logger.info(
        "API key validated successfully",
        extra={"request_id": request_id}
    )
    
    return api_key


async def check_rate_limits(request: Request) -> None:
    """
    Check rate limits for the request.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not SECURITY_CONFIG["rate_limit_enabled"]:
        return
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    client_ip = request.client.host if request.client else "unknown"
    
    # Check per-minute rate limit
    is_limited_minute, rate_info_minute = rate_limiter.is_rate_limited(
        f"ip:{client_ip}:minute",
        SECURITY_CONFIG["max_requests_per_minute"],
        60
    )
    
    # Check per-hour rate limit
    is_limited_hour, rate_info_hour = rate_limiter.is_rate_limited(
        f"ip:{client_ip}:hour",
        SECURITY_CONFIG["max_requests_per_hour"],
        3600
    )
    
    if is_limited_minute or is_limited_hour:
        rate_info = rate_info_minute if is_limited_minute else rate_info_hour
        
        logger.warning(
            f"Rate limit exceeded for IP {client_ip}",
            extra={
                "request_id": request_id,
                "client_ip": client_ip,
                "rate_info": rate_info
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RateLimitExceeded",
                "message": "Too many requests. Please slow down.",
                "request_id": request_id,
                "retry_after": rate_info.get("retry_after", 60)
            },
            headers={
                "Retry-After": str(rate_info.get("retry_after", 60))
            }
        )
    
    # Record the request
    rate_limiter.record_request(f"ip:{client_ip}:minute")
    rate_limiter.record_request(f"ip:{client_ip}:hour")


async def validate_security(request: Request) -> None:
    """
    Comprehensive security validation for requests.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If security validation fails
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    # Validate IP address
    if not security_validator.validate_ip_address(client_ip):
        logger.warning(
            f"Access denied for IP: {client_ip}",
            extra={"request_id": request_id, "client_ip": client_ip}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "AccessDenied",
                "message": "Access denied from your location",
                "request_id": request_id
            }
        )
    
    # Validate user agent
    if not security_validator.validate_user_agent(user_agent):
        logger.warning(
            f"Suspicious user agent blocked: {user_agent}",
            extra={
                "request_id": request_id,
                "client_ip": client_ip,
                "user_agent": user_agent
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "SuspiciousRequest",
                "message": "Request blocked due to suspicious patterns",
                "request_id": request_id
            }
        )
    
    # Check rate limits
    await check_rate_limits(request)


def generate_secure_token() -> str:
    """Generate a cryptographically secure token"""
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str, salt: str = None) -> str:
    """
    Hash sensitive data with optional salt.
    
    Args:
        data: Data to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        Hashed data
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()


class SecurityHeaders:
    """Security headers for responses"""
    
    @staticmethod
    def get_security_headers(environment: str = "production") -> Dict[str, str]:
        """
        Get security headers based on environment.
        
        Args:
            environment: Environment name
            
        Returns:
            Dictionary of security headers
        """
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        
        if environment == "production":
            headers.update({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self'; "
                    "font-src 'self'; "
                    "object-src 'none'; "
                    "frame-src 'none'; "
                    "base-uri 'self'"
                )
            })
        
        return headers


# Global security headers instance
security_headers = SecurityHeaders()