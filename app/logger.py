"""
Logging configuration for the AI recommendation service.
Production-ready logging with structured output and performance monitoring.
"""
import logging
import logging.config
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import time


class ProductionFormatter(logging.Formatter):
    """Custom formatter for production logs with JSON structure"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        if hasattr(record, 'ai_provider'):
            log_entry['ai_provider'] = record.ai_provider
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_entry)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development"""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding for different levels
        colors = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Green
            'WARNING': '\033[33m',    # Yellow
            'ERROR': '\033[31m',      # Red
            'CRITICAL': '\033[35m'    # Magenta
        }
        reset_color = '\033[0m'
        
        color = colors.get(record.levelname, '')
        
        base_msg = f"{timestamp} {color}{record.levelname:8}{reset_color} {record.name:25} {record.getMessage()}"
        
        # Add context information if available
        context_info = []
        if hasattr(record, 'user_id'):
            context_info.append(f"user={record.user_id}")
        if hasattr(record, 'duration'):
            context_info.append(f"duration={record.duration}ms")
        if hasattr(record, 'ai_provider'):
            context_info.append(f"provider={record.ai_provider}")
            
        if context_info:
            base_msg += f" [{', '.join(context_info)}]"
            
        return base_msg


def setup_logging(
    environment: str = None,
    log_level: str = None,
    log_file: str = None
) -> None:
    """
    Configure logging based on environment.
    
    Args:
        environment: 'development', 'production', or 'testing'
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (production only)
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO' if environment == 'production' else 'DEBUG')
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Configure based on environment
    if environment == 'production':
        # Production: JSON formatted logs
        formatter = ProductionFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
    elif environment == 'testing':
        # Testing: Minimal logging to avoid noise
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        root_logger.addHandler(handler)
        log_level = 'WARNING'  # Reduce noise in tests
        
    else:
        # Development: Human-readable format
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(DevelopmentFormatter())
        root_logger.addHandler(handler)
    
    # Set log level
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Set levels for specific loggers to reduce noise
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_performance(logger: Optional[logging.Logger] = None):
    """Decorator to log function performance"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Function completed: {func_name}",
                    extra={"duration": round(duration, 2), "function": func_name}
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Function failed: {func_name} - {str(e)}",
                    extra={
                        "duration": round(duration, 2),
                        "function": func_name,
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(
                    f"Function completed: {func_name}",
                    extra={"duration": round(duration, 2), "function": func_name}
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Function failed: {func_name} - {str(e)}",
                    extra={
                        "duration": round(duration, 2),
                        "function": func_name,
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def log_api_request(logger: Optional[logging.Logger] = None):
    """Decorator to log API requests and responses"""
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = get_logger('api')
            
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            start_time = time.time()
            request_id = getattr(request.state, 'request_id', 'unknown')
            
            # Log request
            logger.info(
                f"API Request: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params)
                }
            )
            
            try:
                response = await func(request, *args, **kwargs)
                duration = (time.time() - start_time) * 1000
                
                logger.info(
                    f"API Response: {request.method} {request.url.path}",
                    extra={
                        "request_id": request_id,
                        "duration": round(duration, 2),
                        "status": "success"
                    }
                )
                return response
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"API Error: {request.method} {request.url.path} - {str(e)}",
                    extra={
                        "request_id": request_id,
                        "duration": round(duration, 2),
                        "status": "error",
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator


# Initialize logging on module import
import asyncio
setup_logging()