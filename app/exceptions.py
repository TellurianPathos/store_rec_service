"""
Custom exceptions and error handling for the AI recommendation service.
Production-ready error handling with proper HTTP status codes and logging.
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import traceback


class RecommendationServiceError(Exception):
    """Base exception for recommendation service errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class DataValidationError(RecommendationServiceError):
    """Raised when input data validation fails"""
    pass


class ConfigurationError(RecommendationServiceError):
    """Raised when configuration is invalid or missing"""
    pass


class AIServiceError(RecommendationServiceError):
    """Raised when AI service operations fail"""
    pass


class DataLoadingError(RecommendationServiceError):
    """Raised when data loading fails"""
    pass


class ModelNotInitializedError(RecommendationServiceError):
    """Raised when attempting to use uninitialized models"""
    pass


class RateLimitError(RecommendationServiceError):
    """Raised when rate limits are exceeded"""
    pass


class ServiceUnavailableError(RecommendationServiceError):
    """Raised when service is temporarily unavailable"""
    pass


def create_http_exception(
    error: RecommendationServiceError,
    request_id: str = "unknown"
) -> HTTPException:
    """
    Convert service exceptions to appropriate HTTP exceptions.
    
    Args:
        error: The service exception
        request_id: The request ID for tracking
        
    Returns:
        HTTPException with appropriate status code and details
    """
    error_response = {
        "error": error.error_code,
        "message": error.message,
        "request_id": request_id,
    }
    
    # Add details if present (but sanitize sensitive information)
    if error.details:
        safe_details = {}
        for key, value in error.details.items():
            # Don't expose sensitive information in API responses
            if key.lower() not in ['api_key', 'password', 'secret', 'token']:
                safe_details[key] = value
        if safe_details:
            error_response["details"] = safe_details
    
    # Map service exceptions to HTTP status codes
    status_code_mapping = {
        DataValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AIServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
        DataLoadingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ModelNotInitializedError: status.HTTP_503_SERVICE_UNAVAILABLE,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    status_code = status_code_mapping.get(type(error), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail=error_response
    )


def handle_unexpected_error(
    error: Exception,
    request_id: str = "unknown",
    context: str = "operation"
) -> HTTPException:
    """
    Handle unexpected errors by wrapping them in a generic HTTP exception.
    
    Args:
        error: The unexpected exception
        request_id: The request ID for tracking
        context: Context where the error occurred
        
    Returns:
        HTTPException with generic error message
    """
    # Create a generic error response that doesn't expose internal details
    error_response = {
        "error": "InternalServerError",
        "message": f"An unexpected error occurred during {context}",
        "request_id": request_id,
    }
    
    # In development, include more details
    import os
    if os.getenv('ENVIRONMENT', 'development') == 'development':
        error_response["debug_info"] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        }
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response
    )


class CircuitBreaker:
    """
    Simple circuit breaker pattern for AI service calls.
    Helps prevent cascade failures when AI services are down.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_available(self) -> bool:
        """Check if the service is available based on circuit breaker state"""
        import time
        
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record a failed operation"""
        import time
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> str:
        """Get current circuit breaker state"""
        return self.state


# Global circuit breaker instance for AI services
ai_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """
    Decorator to add circuit breaker protection to functions.
    
    Args:
        circuit_breaker: The circuit breaker instance to use
    """
    def decorator(func):
        from functools import wraps
        import asyncio
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not circuit_breaker.is_available():
                raise ServiceUnavailableError(
                    "Service temporarily unavailable due to repeated failures",
                    error_code="SERVICE_CIRCUIT_OPEN",
                    details={"circuit_breaker_state": circuit_breaker.get_state()}
                )
            
            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not circuit_breaker.is_available():
                raise ServiceUnavailableError(
                    "Service temporarily unavailable due to repeated failures",
                    error_code="SERVICE_CIRCUIT_OPEN",
                    details={"circuit_breaker_state": circuit_breaker.get_state()}
                )
            
            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class RetryHandler:
    """
    Retry handler with exponential backoff for transient failures.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute function with retry logic.
        
        Args:
            func: The function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        import asyncio
        import random
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )
                # Add jitter to prevent thundering herd
                delay += random.uniform(0, delay * 0.1)
                
                await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        raise last_exception


# Global retry handler instance
default_retry_handler = RetryHandler(max_retries=3, base_delay=1.0)