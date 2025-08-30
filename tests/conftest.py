import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.ai_models import (
    AIProvider,
    AIModelConfig, 
    AIProcessingConfig,
    RecommendationConfig,
    AIAnalysisResult
)


@pytest.fixture
def sample_products_df():
    """Sample product data for testing"""
    return pd.DataFrame({
        'id': ['1', '2', '3', '4', '5'],
        'name': [
            'Wireless Headphones',
            'Smart Watch', 
            'Laptop Stand',
            'Coffee Maker',
            'Desk Lamp'
        ],
        'description': [
            'High-quality wireless headphones with noise cancellation',
            'Fitness tracking smartwatch with heart rate monitor',
            'Adjustable aluminum laptop stand for ergonomic working',
            'Programmable coffee maker with timer and auto-brew',
            'LED desk lamp with adjustable brightness and USB charging'
        ],
        'category': [
            'Electronics',
            'Electronics', 
            'Office',
            'Kitchen',
            'Office'
        ],
        'price': [99.99, 199.99, 49.99, 79.99, 39.99],
        'rating': [4.5, 4.2, 4.7, 4.1, 4.3]
    })


@pytest.fixture
def sample_csv_file(sample_products_df):
    """Create a temporary CSV file with sample data"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        sample_products_df.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_ai_config():
    """Mock AI configuration for testing"""
    return AIModelConfig(
        provider=AIProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test-key",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )


@pytest.fixture
def test_ai_processing_config(mock_ai_config):
    """Test AI processing configuration"""
    return AIProcessingConfig(
        enabled=True,
        model_config=mock_ai_config,
        system_prompt="Test system prompt",
        user_prompt_template="Test: {data}",
        output_format="json",
        batch_size=2,
        retry_attempts=2,
        retry_delay=0.1
    )


@pytest.fixture
def test_recommendation_config(test_ai_processing_config):
    """Test recommendation configuration"""
    return RecommendationConfig(
        ai_processing=test_ai_processing_config,
        content_similarity_weight=0.6,
        ai_enhancement_weight=0.4,
        use_ai_for_user_profiling=True,
        use_ai_for_content_analysis=True,
        cache_ai_responses=False,  # Disable caching for tests
        cache_ttl_seconds=0
    )


@pytest.fixture
def disabled_ai_config():
    """Configuration with AI disabled"""
    return RecommendationConfig(
        ai_processing=AIProcessingConfig(
            enabled=False,
            model_config=mock_ai_config(),
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


@pytest.fixture
def mock_ai_analysis_result():
    """Mock AI analysis result"""
    return AIAnalysisResult(
        original_data="Test product data",
        processed_data='{"appeal_score": 0.8, "key_features": ["wireless", "premium"], "target_audience": "tech enthusiasts", "enhanced_description": "Premium wireless device"}',
        analysis="High-quality product with good market appeal",
        confidence_score=0.8,
        processing_time=0.5,
        tokens_used=150
    )


@pytest.fixture
def mock_ai_client(mock_ai_analysis_result):
    """Mock AI client for testing"""
    client = AsyncMock()
    client.process_data.return_value = mock_ai_analysis_result
    client.batch_process.return_value = [mock_ai_analysis_result] * 2
    client.close.return_value = None
    return client


@pytest.fixture
def test_client():
    """FastAPI test client"""
    # Import here to avoid circular imports
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_recommendation_request():
    """Sample recommendation request data"""
    return {
        "user_id": "test_user_123",
        "num_recommendations": 3,
        "user_preferences": "I like electronics and tech gadgets",
        "context": "Looking for productivity tools",
        "ai_processing_enabled": True
    }


@pytest.fixture
def sample_basic_request():
    """Sample basic recommendation request"""
    return {
        "user_id": "test_user_basic",
        "num_recommendations": 5
    }
