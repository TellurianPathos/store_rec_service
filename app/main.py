from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from typing import Dict
import os
import uuid
import time

from app.logger import setup_logging, get_logger, log_api_request

from app.models import RecommendationRequest, RecommendationResponse
from app.ai_models import (
    AIEnhancedRecommendationRequest, 
    EnhancedRecommendationResponse
)
from app.recommender import ContentRecommender
from app.ai_recommender import AIEnhancedRecommender

# Try to import configuration
try:
    from config import DEFAULT_CONFIG
except ImportError:
    # Fallback to template configuration
    from config_template import MINIMAL_CONFIG as DEFAULT_CONFIG

# Initialize logging based on environment
setup_logging(
    environment=os.getenv('ENVIRONMENT', 'development'),
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_file=os.getenv('LOG_FILE')
)

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="AI-Enhanced Store Recommendation API",
    description="Production-ready API for AI-powered product recommendations",
    version="1.0.0",
    docs_url="/docs" if os.getenv('ENVIRONMENT') != 'production' else None,
    redoc_url="/redoc" if os.getenv('ENVIRONMENT') != 'production' else None,
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv('ALLOWED_HOSTS', '*').split(',') if os.getenv('ALLOWED_HOSTS') != '*' else ['*']
)

# Add CORS middleware for development
if os.getenv('ENVIRONMENT', 'development') == 'development':
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID and logging context to all requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    )
    
    response = await call_next(request)
    
    # Log response
    duration = (time.time() - start_time) * 1000
    logger.info(
        f"Request completed: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "duration": round(duration, 2),
            "status_code": response.status_code
        }
    )
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "message": "An unexpected error occurred. Please try again later."
        }
    )

# Global recommender instances
content_recommender = None
ai_recommender = None

@app.on_event("startup")
async def startup_event():
    """Initialize recommenders on startup"""
    global content_recommender, ai_recommender
    
    logger.info("Starting AI recommendation service initialization")
    
    try:
        # Initialize basic content recommender
        content_recommender = ContentRecommender()
        logger.info("Content recommender initialized successfully")
        
        # Initialize AI-enhanced recommender
        ai_recommender = AIEnhancedRecommender(DEFAULT_CONFIG)
        logger.info(
            "AI recommender created",
            extra={
                "ai_enabled": DEFAULT_CONFIG.ai_processing.enabled,
                "ai_provider": DEFAULT_CONFIG.ai_processing.ai_model_config.provider.value
            }
        )
        
        # Check if data file exists
        data_path = "data/generic_dataset.csv"
        if os.path.exists(data_path):
            await ai_recommender.initialize(data_path)
            logger.info(f"AI recommender initialized with data from {data_path}")
        else:
            logger.warning(
                f"Data file not found: {data_path}. Service will run with limited functionality."
            )
            
        logger.info("AI recommendation service startup completed successfully")
        
    except Exception as e:
        logger.error(
            "Failed to initialize recommendation service",
            extra={"error_type": type(e).__name__},
            exc_info=True
        )
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Starting service shutdown")
    
    try:
        if ai_recommender:
            await ai_recommender.close()
            logger.info("AI recommender closed successfully")
        logger.info("Service shutdown completed successfully")
    except Exception as e:
        logger.error(
            "Error during service shutdown",
            extra={"error_type": type(e).__name__},
            exc_info=True
        )

# Dependency to get the basic recommender
def get_content_recommender() -> ContentRecommender:
    if content_recommender is None:
        raise HTTPException(status_code=500, detail="Recommender not initialized")
    return content_recommender

# Dependency to get the AI-enhanced recommender
def get_ai_recommender() -> AIEnhancedRecommender:
    if ai_recommender is None:
        raise HTTPException(status_code=500, detail="AI Recommender not initialized")
    return ai_recommender

@app.get("/health")
async def health_check(request: Request):
    """
    Comprehensive health check endpoint with detailed system status.
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "request_id": request_id,
        "version": "1.0.0",
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "components": {
            "content_recommender": "healthy" if content_recommender else "unavailable",
            "ai_recommender": "healthy" if ai_recommender else "unavailable",
            "ai_processing": {
                "enabled": DEFAULT_CONFIG.ai_processing.enabled,
                "provider": DEFAULT_CONFIG.ai_processing.ai_model_config.provider.value if DEFAULT_CONFIG.ai_processing.enabled else "none",
                "status": "healthy" if DEFAULT_CONFIG.ai_processing.enabled and ai_recommender else "disabled"
            },
            "data": {
                "products_loaded": len(ai_recommender.products_df) if ai_recommender and hasattr(ai_recommender, 'products_df') and ai_recommender.products_df is not None else 0,
                "model_trained": bool(ai_recommender and hasattr(ai_recommender, 'tfidf_vectorizer') and ai_recommender.tfidf_vectorizer is not None)
            }
        }
    }
    
    # Check if any components are unhealthy
    unhealthy_components = [
        name for name, status in health_status["components"].items() 
        if (isinstance(status, str) and status != "healthy") or 
           (isinstance(status, dict) and status.get("status") not in ["healthy", "disabled"])
    ]
    
    if unhealthy_components:
        health_status["status"] = "degraded"
        health_status["unhealthy_components"] = unhealthy_components
    
    # Log health check
    logger.info(
        "Health check performed",
        extra={
            "request_id": request_id,
            "status": health_status["status"],
            "ai_enabled": DEFAULT_CONFIG.ai_processing.enabled
        }
    )
    
    return health_status

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    recommender: ContentRecommender = Depends(get_content_recommender)
) -> RecommendationResponse:
    """
    Get basic content-based product recommendations.
    This endpoint maintains backward compatibility.
    """
    recommendations = recommender.get_recommendations(
        user_id=request.user_id,
        num_recommendations=request.num_recommendations
    )
    
    return RecommendationResponse(
        user_id=request.user_id,
        recommendations=recommendations
    )

@app.post("/recommend/ai", response_model=EnhancedRecommendationResponse)
async def get_ai_recommendations(
    request: AIEnhancedRecommendationRequest,
    recommender: AIEnhancedRecommender = Depends(get_ai_recommender)
) -> EnhancedRecommendationResponse:
    """
    Get AI-enhanced product recommendations with advanced features.
    """
    try:
        return await recommender.get_recommendations(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

@app.get("/config")
async def get_configuration(request: Request):
    """
    Get current AI configuration (without sensitive data like API keys).
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    config_info = {
        "request_id": request_id,
        "timestamp": time.time(),
        "ai_processing_enabled": DEFAULT_CONFIG.ai_processing.enabled,
        "ai_provider": DEFAULT_CONFIG.ai_processing.ai_model_config.provider.value,
        "model_name": DEFAULT_CONFIG.ai_processing.ai_model_config.model_name,
        "content_similarity_weight": DEFAULT_CONFIG.content_similarity_weight,
        "ai_enhancement_weight": DEFAULT_CONFIG.ai_enhancement_weight,
        "batch_size": DEFAULT_CONFIG.ai_processing.batch_size,
        "cache_enabled": DEFAULT_CONFIG.cache_ai_responses,
        "user_profiling_enabled": DEFAULT_CONFIG.use_ai_for_user_profiling,
        "content_analysis_enabled": DEFAULT_CONFIG.use_ai_for_content_analysis,
        "environment": os.getenv('ENVIRONMENT', 'development')
    }
    
    logger.info(
        "Configuration requested",
        extra={
            "request_id": request_id,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    return config_info
