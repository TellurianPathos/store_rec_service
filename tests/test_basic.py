import pytest


def test_basic_functionality():
    """Test basic Python functionality"""
    assert 1 + 1 == 2
    assert "hello" == "hello"


def test_imports():
    """Test that we can import our modules"""
    from app.models import RecommendationRequest, Product
    from app.ai_models import AIProvider
    
    # Test basic model creation
    request = RecommendationRequest(user_id="test", num_recommendations=5)
    assert request.user_id == "test"
    assert request.num_recommendations == 5
    
    product = Product(id="1", name="Test Product")
    assert product.id == "1"
    assert product.name == "Test Product"
    
    # Test enum
    assert AIProvider.OPENAI == "openai"


@pytest.mark.asyncio
async def test_async_functionality():
    """Test async functionality works"""
    import asyncio
    
    async def async_add(a, b):
        await asyncio.sleep(0.01)  # Simulate async work
        return a + b
    
    result = await async_add(2, 3)
    assert result == 5


class TestBasicModels:
    """Test basic model functionality"""
    
    def test_recommendation_request_validation(self):
        """Test request validation"""
        from app.models import RecommendationRequest
        
        # Valid request
        request = RecommendationRequest(user_id="user123", num_recommendations=3)
        assert request.user_id == "user123"
        assert request.num_recommendations == 3
        
        # Test default value
        request = RecommendationRequest(user_id="user123")
        assert request.num_recommendations == 5  # default value
    
    def test_product_model(self):
        """Test product model"""
        from app.models import Product
        
        product = Product(id="prod_1", name="Test Product")
        assert product.id == "prod_1"
        assert product.name == "Test Product"
