from fastapi import FastAPI, Depends, HTTPException
from typing import Dict
import os

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

# Create FastAPI application
app = FastAPI(
    title="AI-Enhanced Store Recommendation API",
    description="API for AI-powered product recommendations",
    version="1.0.0",
)

# Global recommender instances
content_recommender = None
ai_recommender = None

@app.on_event("startup")
async def startup_event():
    """Initialize recommenders on startup"""
    global content_recommender, ai_recommender
    
    # Initialize basic content recommender
    content_recommender = ContentRecommender()
    
    # Initialize AI-enhanced recommender
    ai_recommender = AIEnhancedRecommender(DEFAULT_CONFIG)
    
    # Check if data file exists
    data_path = "data/generic_dataset.csv"
    if os.path.exists(data_path):
        await ai_recommender.initialize(data_path)
    else:
        print(f"Warning: Data file {data_path} not found. Please add your data.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    if ai_recommender:
        await ai_recommender.close()

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
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "status": "ok",
        "ai_enabled": DEFAULT_CONFIG.ai_processing.enabled,
        "ai_provider": DEFAULT_CONFIG.ai_processing.ai_model_config.provider.value if DEFAULT_CONFIG.ai_processing.enabled else "none"
    }

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
async def get_configuration() -> Dict[str, any]:
    """
    Get current AI configuration (without sensitive data like API keys).
    """
    config_info = {
        "ai_processing_enabled": DEFAULT_CONFIG.ai_processing.enabled,
        "ai_provider": DEFAULT_CONFIG.ai_processing.ai_model_config.provider.value,
        "model_name": DEFAULT_CONFIG.ai_processing.ai_model_config.model_name,
        "content_similarity_weight": DEFAULT_CONFIG.content_similarity_weight,
        "ai_enhancement_weight": DEFAULT_CONFIG.ai_enhancement_weight,
        "batch_size": DEFAULT_CONFIG.ai_processing.batch_size,
        "cache_enabled": DEFAULT_CONFIG.cache_ai_responses,
        "user_profiling_enabled": DEFAULT_CONFIG.use_ai_for_user_profiling,
        "content_analysis_enabled": DEFAULT_CONFIG.use_ai_for_content_analysis
    }
    
    return config_info
