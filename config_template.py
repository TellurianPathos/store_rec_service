# AI-Enhanced Recommendation System Configuration
# Copy this file to config.py and customize for your needs

from app.ai_models import (
    AIProvider, 
    AIModelConfig, 
    AIProcessingConfig, 
    RecommendationConfig
)

# Example configurations for different AI providers

# OpenAI Configuration
OPENAI_CONFIG = AIModelConfig(
    provider=AIProvider.OPENAI,
    model_name="gpt-3.5-turbo",  # or "gpt-4" for better quality
    api_key="your-openai-api-key-here",
    base_url=None,  # Uses default OpenAI endpoint
    temperature=0.7,
    max_tokens=1000,
    timeout=30,
    custom_headers={},
    custom_params={}
)

# Anthropic Claude Configuration
ANTHROPIC_CONFIG = AIModelConfig(
    provider=AIProvider.ANTHROPIC,
    model_name="claude-3-sonnet-20240229",
    api_key="your-anthropic-api-key-here",
    base_url=None,  # Uses default Anthropic endpoint
    temperature=0.7,
    max_tokens=1000,
    timeout=30,
    custom_headers={},
    custom_params={}
)

# Ollama Local Configuration
OLLAMA_CONFIG = AIModelConfig(
    provider=AIProvider.OLLAMA,
    model_name="llama2",  # or "mistral", "codellama", etc.
    api_key=None,  # Not needed for local Ollama
    base_url="http://localhost:11434",  # Default Ollama endpoint
    temperature=0.7,
    max_tokens=1000,
    timeout=60,  # Longer timeout for local processing
    custom_headers={},
    custom_params={}
)

# Custom API Configuration Template
CUSTOM_API_CONFIG = AIModelConfig(
    provider=AIProvider.CUSTOM,
    model_name="your-model-name",
    api_key="your-api-key",
    base_url="https://your-api-endpoint.com/v1/chat",
    temperature=0.7,
    max_tokens=1000,
    timeout=30,
    custom_headers={
        "X-Custom-Header": "value",
        "User-Agent": "RecommendationSystem/1.0"
    },
    custom_params={
        "custom_param": "value"
    }
)

# AI Processing Configuration
AI_PROCESSING_CONFIG = AIProcessingConfig(
    enabled=True,  # Set to False to disable AI features
    ai_model_config=OPENAI_CONFIG,  # Change this to your preferred provider
    system_prompt=(
        "You are a helpful assistant that processes product data "
        "for recommendations."
    ),
    user_prompt_template="Process this product data: {data}",
    output_format="json",
    batch_size=10,  # Process products in batches
    retry_attempts=3,
    retry_delay=1.0
)

# Main Recommendation Configuration
RECOMMENDATION_CONFIG = RecommendationConfig(
    ai_processing=AI_PROCESSING_CONFIG,
    content_similarity_weight=0.6,  # Weight for content-based recommendations
    ai_enhancement_weight=0.4,      # Weight for AI-enhanced scores
    use_ai_for_user_profiling=True,
    use_ai_for_content_analysis=True,
    cache_ai_responses=True,
    cache_ttl_seconds=3600  # Cache responses for 1 hour
)

# Environment-specific configurations

# Development Configuration (uses Ollama for free local processing)
DEV_CONFIG = RecommendationConfig(
    ai_processing=AIProcessingConfig(
        enabled=True,
        ai_model_config=OLLAMA_CONFIG,
        system_prompt=(
            "You are a helpful assistant that processes product data "
            "for recommendations."
        ),
        user_prompt_template="Analyze this product: {data}",
        output_format="json",
        batch_size=5,  # Smaller batches for local processing
        retry_attempts=2,
        retry_delay=2.0
    ),
    content_similarity_weight=0.7,
    ai_enhancement_weight=0.3,
    use_ai_for_user_profiling=True,
    use_ai_for_content_analysis=True,
    cache_ai_responses=True,
    cache_ttl_seconds=7200
)

# Production Configuration (uses OpenAI for reliability)
PROD_CONFIG = RecommendationConfig(
    ai_processing=AIProcessingConfig(
        enabled=True,
        ai_model_config=OPENAI_CONFIG,
        system_prompt=(
            "You are an expert product analyst. Analyze products for "
            "customer recommendations with high accuracy."
        ),
        user_prompt_template="Analyze this product for recommendations: {data}",
        output_format="json",
        batch_size=20,  # Larger batches for efficiency
        retry_attempts=3,
        retry_delay=1.0
    ),
    content_similarity_weight=0.5,
    ai_enhancement_weight=0.5,
    use_ai_for_user_profiling=True,
    use_ai_for_content_analysis=True,
    cache_ai_responses=True,
    cache_ttl_seconds=3600
)

# Minimal Configuration (AI disabled for basic content-based recommendations)
MINIMAL_CONFIG = RecommendationConfig(
    ai_processing=AIProcessingConfig(
        enabled=False,
        model_config=OPENAI_CONFIG,  # Not used when disabled
        system_prompt="",
        user_prompt_template="",
        output_format="text",
        batch_size=1,
        retry_attempts=1,
        retry_delay=1.0
    ),
    content_similarity_weight=1.0,
    ai_enhancement_weight=0.0,
    use_ai_for_user_profiling=False,
    use_ai_for_content_analysis=False,
    cache_ai_responses=False,
    cache_ttl_seconds=0
)

# Configuration selector based on environment
import os

def get_config():
    """Get configuration based on environment variable"""
    env = os.getenv("RECOMMENDATION_ENV", "dev").lower()
    
    if env == "prod":
        return PROD_CONFIG
    elif env == "minimal":
        return MINIMAL_CONFIG
    else:
        return DEV_CONFIG

# Default configuration
DEFAULT_CONFIG = get_config()
