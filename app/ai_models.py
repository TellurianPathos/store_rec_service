from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class AIModelConfig(BaseModel):
    provider: AIProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8000)
    timeout: int = Field(default=30, ge=5, le=300)
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class AIProcessingConfig(BaseModel):
    """Configuration for AI-powered data processing"""
    enabled: bool = True
    ai_model_config: AIModelConfig
    system_prompt: str = (
        "You are a helpful assistant that processes product data "
        "for recommendations."
    )
    user_prompt_template: str = "Process this product data: {data}"
    output_format: str = "json"  # json, text, structured
    batch_size: int = Field(default=10, ge=1, le=100)
    retry_attempts: int = Field(default=3, ge=1, le=5)
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)


class RecommendationConfig(BaseModel):
    """Main configuration for the recommendation system"""
    ai_processing: AIProcessingConfig
    content_similarity_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    ai_enhancement_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    use_ai_for_user_profiling: bool = True
    use_ai_for_content_analysis: bool = True
    cache_ai_responses: bool = True
    cache_ttl_seconds: int = Field(default=3600, ge=300, le=86400)


class AIEnhancedRecommendationRequest(BaseModel):
    user_id: str
    num_recommendations: int = Field(default=5, ge=1, le=20)
    user_preferences: Optional[str] = None
    context: Optional[str] = None
    ai_processing_enabled: bool = True
    custom_prompt: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class AIAnalysisResult(BaseModel):
    original_data: str
    processed_data: str
    analysis: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time: float
    tokens_used: int


class EnhancedProduct(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    ai_analysis: Optional[AIAnalysisResult] = None
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    combined_score: float = Field(default=0.0, ge=0.0, le=1.0)


class EnhancedRecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[EnhancedProduct]
    processing_time: float
    ai_processing_used: bool
    explanation: Optional[str] = None
