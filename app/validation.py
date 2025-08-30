"""
Input validation and sanitization for the AI recommendation service.
Production-ready validation with comprehensive security checks.
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
import re
import html
from datetime import datetime

from app.exceptions import DataValidationError
from app.logger import get_logger

logger = get_logger(__name__)


class ValidationMixin:
    """Mixin class for common validation methods"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input to prevent XSS and injection attacks.
        
        Args:
            value: The string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            DataValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise DataValidationError(
                "Value must be a string",
                error_code="INVALID_TYPE",
                details={"expected": "string", "received": type(value).__name__}
            )
        
        # Remove null bytes and control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        # HTML escape to prevent XSS
        value = html.escape(value, quote=True)
        
        # Limit length
        if len(value) > max_length:
            logger.warning(
                f"String truncated from {len(value)} to {max_length} characters",
                extra={"original_length": len(value), "max_length": max_length}
            )
            value = value[:max_length]
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                 # Event handlers
            r'expression\s*\(',           # CSS expressions
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                raise DataValidationError(
                    "Input contains potentially dangerous content",
                    error_code="DANGEROUS_CONTENT",
                    details={"pattern": pattern}
                )
        
        return value.strip()
    
    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """
        Validate user ID format and content.
        
        Args:
            user_id: The user ID to validate
            
        Returns:
            Validated user ID
            
        Raises:
            DataValidationError: If validation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise DataValidationError(
                "User ID is required and must be a string",
                error_code="INVALID_USER_ID"
            )
        
        user_id = user_id.strip()
        
        if not user_id:
            raise DataValidationError(
                "User ID cannot be empty",
                error_code="EMPTY_USER_ID"
            )
        
        if len(user_id) > 255:
            raise DataValidationError(
                "User ID too long (maximum 255 characters)",
                error_code="USER_ID_TOO_LONG",
                details={"length": len(user_id), "max_length": 255}
            )
        
        # Allow alphanumeric, hyphens, underscores, dots, and @ symbols
        if not re.match(r'^[a-zA-Z0-9._@-]+$', user_id):
            raise DataValidationError(
                "User ID contains invalid characters",
                error_code="INVALID_USER_ID_FORMAT",
                details={"allowed_pattern": "alphanumeric, dots, hyphens, underscores, @ symbols"}
            )
        
        return user_id
    
    @staticmethod
    def validate_recommendation_count(count: int) -> int:
        """
        Validate number of recommendations requested.
        
        Args:
            count: Number of recommendations
            
        Returns:
            Validated count
            
        Raises:
            DataValidationError: If validation fails
        """
        if not isinstance(count, int):
            raise DataValidationError(
                "Recommendation count must be an integer",
                error_code="INVALID_TYPE",
                details={"expected": "integer", "received": type(count).__name__}
            )
        
        if count < 1:
            raise DataValidationError(
                "Recommendation count must be at least 1",
                error_code="INVALID_COUNT",
                details={"minimum": 1, "received": count}
            )
        
        if count > 100:
            raise DataValidationError(
                "Recommendation count cannot exceed 100",
                error_code="COUNT_TOO_HIGH",
                details={"maximum": 100, "received": count}
            )
        
        return count


class ValidatedRecommendationRequest(BaseModel, ValidationMixin):
    """Enhanced recommendation request with validation"""
    
    user_id: str = Field(
        ...,
        description="Unique identifier for the user requesting recommendations",
        example="user123"
    )
    num_recommendations: int = Field(
        default=5,
        description="Number of recommendations to return (1-100)",
        example=5,
        ge=1,
        le=100
    )
    context: Optional[str] = Field(
        None,
        description="Context for the recommendation request",
        example="shopping for birthday gift",
        max_length=500
    )
    
    @validator('user_id', pre=True)
    def validate_user_id_field(cls, v):
        """Validate user ID field"""
        return cls.validate_user_id(v)
    
    @validator('num_recommendations', pre=True)
    def validate_count_field(cls, v):
        """Validate recommendation count field"""
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        return cls.validate_recommendation_count(v)
    
    @validator('context', pre=True)
    def validate_context_field(cls, v):
        """Validate context field"""
        if v is not None:
            return cls.sanitize_string(v, max_length=500)
        return v


class ValidatedAIRecommendationRequest(BaseModel, ValidationMixin):
    """Enhanced AI recommendation request with comprehensive validation"""
    
    user_id: str = Field(
        ...,
        description="Unique identifier for the user requesting recommendations",
        example="user123"
    )
    num_recommendations: int = Field(
        default=5,
        description="Number of recommendations to return (1-100)",
        example=5,
        ge=1,
        le=100
    )
    user_preferences: Optional[str] = Field(
        None,
        description="User's preferences or interests",
        example="likes technology, outdoor activities",
        max_length=1000
    )
    context: Optional[str] = Field(
        None,
        description="Context for the recommendation request",
        example="shopping for birthday gift",
        max_length=500
    )
    ai_processing_enabled: bool = Field(
        default=True,
        description="Whether to enable AI-enhanced processing"
    )
    include_explanation: bool = Field(
        default=False,
        description="Whether to include explanation for recommendations"
    )
    
    @validator('user_id', pre=True)
    def validate_user_id_field(cls, v):
        """Validate user ID field"""
        return cls.validate_user_id(v)
    
    @validator('num_recommendations', pre=True)
    def validate_count_field(cls, v):
        """Validate recommendation count field"""
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        return cls.validate_recommendation_count(v)
    
    @validator('user_preferences', pre=True)
    def validate_preferences_field(cls, v):
        """Validate user preferences field"""
        if v is not None:
            return cls.sanitize_string(v, max_length=1000)
        return v
    
    @validator('context', pre=True)
    def validate_context_field(cls, v):
        """Validate context field"""
        if v is not None:
            return cls.sanitize_string(v, max_length=500)
        return v


class RequestValidationMiddleware:
    """Middleware for additional request validation beyond Pydantic"""
    
    def __init__(self):
        self.request_counts = {}  # Simple in-memory rate limiting
        self.max_requests_per_minute = 60
    
    def validate_rate_limit(self, user_id: str, client_ip: str) -> None:
        """
        Simple rate limiting validation.
        In production, use Redis or similar for distributed rate limiting.
        
        Args:
            user_id: User identifier
            client_ip: Client IP address
            
        Raises:
            DataValidationError: If rate limit exceeded
        """
        import time
        
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean old entries
        keys_to_remove = []
        for key, timestamps in self.request_counts.items():
            timestamps[:] = [ts for ts in timestamps if ts > minute_ago]
            if not timestamps:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.request_counts[key]
        
        # Check rate limit for user and IP
        for identifier in [f"user:{user_id}", f"ip:{client_ip}"]:
            if identifier not in self.request_counts:
                self.request_counts[identifier] = []
            
            timestamps = self.request_counts[identifier]
            recent_requests = [ts for ts in timestamps if ts > minute_ago]
            
            if len(recent_requests) >= self.max_requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded for {identifier}",
                    extra={
                        "identifier": identifier,
                        "requests_in_minute": len(recent_requests),
                        "limit": self.max_requests_per_minute
                    }
                )
                raise DataValidationError(
                    "Rate limit exceeded. Please slow down your requests.",
                    error_code="RATE_LIMIT_EXCEEDED",
                    details={
                        "requests_in_minute": len(recent_requests),
                        "limit": self.max_requests_per_minute
                    }
                )
            
            # Add current request
            timestamps.append(current_time)
    
    def validate_request_size(self, request_data: Dict[str, Any]) -> None:
        """
        Validate overall request size to prevent DoS attacks.
        
        Args:
            request_data: Request data dictionary
            
        Raises:
            DataValidationError: If request too large
        """
        import json
        
        try:
            request_size = len(json.dumps(request_data))
            max_size = 10 * 1024  # 10KB limit
            
            if request_size > max_size:
                logger.warning(
                    f"Request size too large: {request_size} bytes",
                    extra={"size": request_size, "limit": max_size}
                )
                raise DataValidationError(
                    "Request payload too large",
                    error_code="PAYLOAD_TOO_LARGE",
                    details={"size": request_size, "limit": max_size}
                )
        except (TypeError, ValueError) as e:
            raise DataValidationError(
                "Invalid request format",
                error_code="INVALID_JSON",
                details={"error": str(e)}
            )


# Global validation middleware instance
request_validator = RequestValidationMiddleware()