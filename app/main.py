from fastapi import FastAPI, Depends
from typing import Dict

from app.models import RecommendationRequest, RecommendationResponse
from app.recommender import ContentRecommender

# Create FastAPI application
app = FastAPI(
    title="Store Recommendation API",
    description="API for product recommendations",
    version="0.1.0",
)

# Dependency to get the recommender
def get_recommender() -> ContentRecommender:
    return ContentRecommender()

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    recommender: ContentRecommender = Depends(get_recommender)
) -> RecommendationResponse:
    """
    Get product recommendations for a user.
    """
    recommendations = recommender.get_recommendations(
        user_id=request.user_id,
        num_recommendations=request.num_recommendations
    )
    
    return RecommendationResponse(
        user_id=request.user_id,
        recommendations=recommendations
    )
