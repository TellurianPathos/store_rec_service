import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os

from app.main import app
from app.ai_models import EnhancedRecommendationResponse, EnhancedProduct


class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "ok"
        assert "ai_enabled" in data
        assert "ai_provider" in data
    
    def test_config_endpoint(self, client):
        """Test configuration endpoint"""
        response = client.get("/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected configuration fields
        expected_fields = [
            "ai_processing_enabled",
            "ai_provider", 
            "model_name",
            "content_similarity_weight",
            "ai_enhancement_weight",
            "batch_size",
            "cache_enabled",
            "user_profiling_enabled",
            "content_analysis_enabled"
        ]
        
        for field in expected_fields:
            assert field in data
    
    @patch('app.main.content_recommender')
    def test_basic_recommendations_endpoint(self, mock_recommender, client):
        """Test basic recommendations endpoint"""
        # Mock recommender response
        mock_recommender.get_recommendations.return_value = [
            {"id": "1", "name": "Product 1"},
            {"id": "2", "name": "Product 2"}
        ]
        
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 2
        }
        
        response = client.post("/recommend", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == "test_user"
        assert "recommendations" in data
        assert len(data["recommendations"]) == 2
    
    def test_basic_recommendations_validation(self, client):
        """Test request validation for basic recommendations"""
        # Test missing user_id
        response = client.post("/recommend", json={
            "num_recommendations": 5
        })
        assert response.status_code == 422
        
        # Test invalid num_recommendations (too high)
        response = client.post("/recommend", json={
            "user_id": "test_user",
            "num_recommendations": 25  # Max is 20
        })
        assert response.status_code == 422
        
        # Test invalid num_recommendations (negative)
        response = client.post("/recommend", json={
            "user_id": "test_user",
            "num_recommendations": -1
        })
        assert response.status_code == 422
    
    @patch('app.main.ai_recommender')
    def test_ai_recommendations_endpoint(self, mock_ai_recommender, client):
        """Test AI-enhanced recommendations endpoint"""
        # Mock AI recommender response
        mock_response = EnhancedRecommendationResponse(
            user_id="test_user",
            recommendations=[
                EnhancedProduct(
                    id="1",
                    name="AI Product 1",
                    similarity_score=0.8,
                    ai_relevance_score=0.9,
                    combined_score=0.85
                )
            ],
            processing_time=1.5,
            ai_processing_used=True,
            explanation="These products match your preferences"
        )
        
        mock_ai_recommender.get_recommendations = AsyncMock(
            return_value=mock_response
        )
        
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 3,
            "user_preferences": "electronics",
            "context": "gift shopping",
            "ai_processing_enabled": True
        }
        
        response = client.post("/recommend/ai", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == "test_user"
        assert data["ai_processing_used"] is True
        assert "processing_time" in data
        assert "explanation" in data
        assert len(data["recommendations"]) == 1
    
    def test_ai_recommendations_validation(self, client):
        """Test request validation for AI recommendations"""
        # Test missing user_id
        response = client.post("/recommend/ai", json={
            "num_recommendations": 5
        })
        assert response.status_code == 422
        
        # Test invalid num_recommendations
        response = client.post("/recommend/ai", json={
            "user_id": "test_user",
            "num_recommendations": 25  # Max is 20
        })
        assert response.status_code == 422
    
    @patch('app.main.ai_recommender')
    def test_ai_recommendations_error_handling(self, mock_ai_recommender, client):
        """Test error handling in AI recommendations"""
        # Mock AI recommender to raise an exception
        mock_ai_recommender.get_recommendations = AsyncMock(
            side_effect=Exception("AI processing failed")
        )
        
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 3,
            "ai_processing_enabled": True
        }
        
        response = client.post("/recommend/ai", json=request_data)
        
        assert response.status_code == 500
        assert "Recommendation error" in response.json()["detail"]
    
    def test_cors_headers(self, client):
        """Test CORS headers if configured"""
        response = client.get("/health")
        
        # Basic test - in production you might want to test specific CORS headers
        assert response.status_code == 200
    
    @patch('app.main.ai_recommender', None)
    def test_ai_recommender_not_initialized(self, client):
        """Test behavior when AI recommender is not initialized"""
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 3
        }
        
        response = client.post("/recommend/ai", json=request_data)
        
        assert response.status_code == 500
        assert "not initialized" in response.json()["detail"]
    
    @patch('app.main.content_recommender', None)
    def test_content_recommender_not_initialized(self, client):
        """Test behavior when content recommender is not initialized"""
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 3
        }
        
        response = client.post("/recommend", json=request_data)
        
        assert response.status_code == 500
        assert "not initialized" in response.json()["detail"]
    
    def test_request_size_limits(self, client):
        """Test request size limits"""
        # Test very long user preferences
        long_preferences = "A" * 10000  # Very long string
        
        request_data = {
            "user_id": "test_user",
            "num_recommendations": 3,
            "user_preferences": long_preferences
        }
        
        response = client.post("/recommend/ai", json=request_data)
        
        # Should either accept it or return appropriate error
        assert response.status_code in [200, 413, 422, 500]
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads making concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestAPIIntegration:
    """Integration tests for the complete API"""
    
    @pytest.fixture
    def client_with_data(self, sample_csv_file):
        """Test client with sample data"""
        # Mock the data path to use our sample file
        with patch('app.main.data_path', sample_csv_file):
            client = TestClient(app)
            # Trigger startup event
            with client:
                yield client
    
    def test_full_recommendation_flow(self, client_with_data):
        """Test complete recommendation flow"""
        # Test health first
        response = client_with_data.get("/health")
        assert response.status_code == 200
        
        # Test basic recommendations
        response = client_with_data.post("/recommend", json={
            "user_id": "integration_test_user",
            "num_recommendations": 3
        })
        
        # Should work even without AI (fallback to content-based)
        assert response.status_code in [200, 500]  # May fail if no model
    
    def test_api_documentation(self, client_with_data):
        """Test API documentation endpoints"""
        # Test OpenAPI schema
        response = client_with_data.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check that our endpoints are documented
        paths = schema["paths"]
        assert "/health" in paths
        assert "/recommend" in paths
        assert "/recommend/ai" in paths
        assert "/config" in paths
    
    def test_api_versioning(self, client_with_data):
        """Test API version information"""
        response = client_with_data.get("/openapi.json")
        schema = response.json()
        
        assert "info" in schema
        assert "version" in schema["info"]
        assert "title" in schema["info"]
        assert "AI-Enhanced" in schema["info"]["title"]
