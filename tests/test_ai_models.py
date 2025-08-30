import pytest
from app.ai_models import (
    AIProvider,
    AIModelConfig,
    AIProcessingConfig,
    RecommendationConfig,
    AIEnhancedRecommendationRequest,
    EnhancedProduct,
    AIAnalysisResult
)


class TestAIModels:
    """Test AI model classes and validation"""
    
    def test_ai_model_config_creation(self):
        """Test creating AI model configuration"""
        config = AIModelConfig(
            provider=AIProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key",
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
        
        assert config.provider == AIProvider.OPENAI
        assert config.model_name == "gpt-3.5-turbo"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.timeout == 30
    
    def test_ai_model_config_validation(self):
        """Test AI model configuration validation"""
        # Test temperature bounds
        with pytest.raises(ValueError):
            AIModelConfig(
                provider=AIProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=3.0  # Should be <= 2.0
            )
        
        # Test max_tokens bounds
        with pytest.raises(ValueError):
            AIModelConfig(
                provider=AIProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                max_tokens=0  # Should be >= 1
            )
    
    def test_ai_processing_config(self, mock_ai_config):
        """Test AI processing configuration"""
        config = AIProcessingConfig(
            enabled=True,
            ai_model_config=mock_ai_config,
            system_prompt="Test prompt",
            user_prompt_template="Process: {data}",
            batch_size=5
        )
        
        assert config.enabled is True
        assert config.ai_model_config == mock_ai_config
        assert config.system_prompt == "Test prompt"
        assert config.user_prompt_template == "Process: {data}"
        assert config.batch_size == 5
    
    def test_recommendation_config(self, test_ai_processing_config):
        """Test recommendation configuration"""
        config = RecommendationConfig(
            ai_processing=test_ai_processing_config,
            content_similarity_weight=0.6,
            ai_enhancement_weight=0.4
        )
        
        assert config.ai_processing == test_ai_processing_config
        assert config.content_similarity_weight == 0.6
        assert config.ai_enhancement_weight == 0.4
        
        # Test weights sum validation (if implemented)
        assert abs(
            config.content_similarity_weight + 
            config.ai_enhancement_weight - 1.0
        ) < 0.01
    
    def test_ai_enhanced_recommendation_request(self):
        """Test AI enhanced recommendation request model"""
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            num_recommendations=5,
            user_preferences="tech gadgets",
            context="gift shopping",
            ai_processing_enabled=True
        )
        
        assert request.user_id == "test_user"
        assert request.num_recommendations == 5
        assert request.user_preferences == "tech gadgets"
        assert request.context == "gift shopping"
        assert request.ai_processing_enabled is True
    
    def test_enhanced_product_model(self):
        """Test enhanced product model"""
        product = EnhancedProduct(
            id="prod_123",
            name="Test Product",
            description="A test product",
            category="Electronics",
            price=99.99,
            rating=4.5,
            similarity_score=0.8,
            ai_relevance_score=0.7,
            combined_score=0.75
        )
        
        assert product.id == "prod_123"
        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.similarity_score == 0.8
        assert product.ai_relevance_score == 0.7
        assert product.combined_score == 0.75
    
    def test_ai_analysis_result(self):
        """Test AI analysis result model"""
        result = AIAnalysisResult(
            original_data="raw product data",
            processed_data="enhanced data",
            analysis="product analysis",
            confidence_score=0.85,
            processing_time=1.5,
            tokens_used=200
        )
        
        assert result.original_data == "raw product data"
        assert result.processed_data == "enhanced data"
        assert result.analysis == "product analysis"
        assert result.confidence_score == 0.85
        assert result.processing_time == 1.5
        assert result.tokens_used == 200
    
    def test_ai_provider_enum(self):
        """Test AI provider enumeration"""
        assert AIProvider.OPENAI == "openai"
        assert AIProvider.ANTHROPIC == "anthropic"
        assert AIProvider.COHERE == "cohere"
        assert AIProvider.HUGGINGFACE == "huggingface"
        assert AIProvider.OLLAMA == "ollama"
        assert AIProvider.CUSTOM == "custom"
