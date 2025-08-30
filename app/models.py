from pydantic import BaseModel, Field
from typing import List


class RecommendationRequest(BaseModel):
    user_id: str
    num_recommendations: int = Field(default=5, ge=1, le=20)


class Product(BaseModel):
    id: str
    name: str


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Product]
