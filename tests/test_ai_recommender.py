import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock

from app.ai_recommender import AIEnhancedRecommender
from app.ai_models import (
    AIEnhancedRecommendationRequest,
    EnhancedRecommendationResponse,
    EnhancedProduct
)


class TestAIEnhancedRecommender:
    """Test the AI-enhanced recommendation engine"""
    
    @pytest.mark.asyncio
    async def test_recommender_initialization(self, test_recommendation_config):
        """Test AI recommender initialization"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        assert recommender.config == test_recommendation_config
        assert recommender.ai_client is not None
        assert recommender.tfidf_vectorizer is None
        assert recommender.products_df is None
    
    @pytest.mark.asyncio
    async def test_initialize_with_data(
        self, 
        test_recommendation_config, 
        sample_csv_file,
        mock_ai_client
    ):
        """Test initialization with product data"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        # Mock the AI client
        with patch('app.ai_recommender.create_ai_client', return_value=mock_ai_client):
            await recommender.initialize(sample_csv_file)
        
        assert recommender.products_df is not None
        assert len(recommender.products_df) > 0
        assert recommender.tfidf_vectorizer is not None
        assert recommender.product_features is not None
    
    @pytest.mark.asyncio
    async def test_ai_enhance_products(
        self, 
        test_recommendation_config,
        sample_products_df,
        mock_ai_client
    ):
        """Test AI enhancement of product data"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.products_df = sample_products_df
        recommender.ai_client = mock_ai_client
        
        await recommender._ai_enhance_products()
        
        # Verify AI client was called
        assert mock_ai_client.batch_process.called
        
        # Verify products dataframe has AI analysis column
        assert 'ai_analysis' in recommender.products_df.columns
    
    @pytest.mark.asyncio
    async def test_get_recommendations_basic(
        self,
        test_recommendation_config,
        sample_csv_file,
        mock_ai_client
    ):
        """Test basic recommendation functionality"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        with patch('app.ai_recommender.create_ai_client', return_value=mock_ai_client):
            await recommender.initialize(sample_csv_file)
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            num_recommendations=3,
            user_preferences="electronics",
            ai_processing_enabled=True
        )
        
        response = await recommender.get_recommendations(request)
        
        assert isinstance(response, EnhancedRecommendationResponse)
        assert response.user_id == "test_user"
        assert len(response.recommendations) <= 3
        assert response.ai_processing_used is True
        assert response.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_get_recommendations_ai_disabled(
        self,
        disabled_ai_config,
        sample_csv_file
    ):
        """Test recommendations with AI disabled"""
        recommender = AIEnhancedRecommender(disabled_ai_config)
        await recommender.initialize(sample_csv_file)
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            num_recommendations=3,
            ai_processing_enabled=False
        )
        
        response = await recommender.get_recommendations(request)
        
        assert isinstance(response, EnhancedRecommendationResponse)
        assert response.ai_processing_used is False
        assert response.explanation is None
    
    @pytest.mark.asyncio
    async def test_generate_user_profile(
        self,
        test_recommendation_config,
        mock_ai_client
    ):
        """Test user profile generation"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.ai_client = mock_ai_client
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            user_preferences="I love tech gadgets",
            context="Looking for birthday gifts"
        )
        
        profile = await recommender._generate_user_profile(request)
        
        assert profile is not None
        mock_ai_client.process_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_user_profile_no_data(
        self,
        test_recommendation_config,
        mock_ai_client
    ):
        """Test user profile generation with no preferences"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.ai_client = mock_ai_client
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user"
        )
        
        profile = await recommender._generate_user_profile(request)
        
        assert profile is None
        mock_ai_client.process_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_content_recommendations(
        self,
        test_recommendation_config,
        sample_csv_file,
        mock_ai_client
    ):
        """Test content-based recommendation generation"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        with patch('app.ai_recommender.create_ai_client', return_value=mock_ai_client):
            await recommender.initialize(sample_csv_file)
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            num_recommendations=3,
            user_preferences="electronics and gadgets"
        )
        
        recommendations = recommender._get_content_recommendations(request)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(prod, EnhancedProduct) for prod in recommendations)
    
    @pytest.mark.asyncio
    async def test_ai_score_recommendations(
        self,
        test_recommendation_config,
        mock_ai_client
    ):
        """Test AI scoring of recommendations"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.ai_client = mock_ai_client
        
        # Mock AI response with scores
        mock_ai_client.process_data.return_value.processed_data = '[0.8, 0.6, 0.9]'
        
        recommendations = [
            EnhancedProduct(id="1", name="Product 1"),
            EnhancedProduct(id="2", name="Product 2"),
            EnhancedProduct(id="3", name="Product 3")
        ]
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            user_preferences="tech gadgets"
        )
        
        scored_recs = await recommender._ai_score_recommendations(
            recommendations, request, "user profile"
        )
        
        assert len(scored_recs) == 3
        assert scored_recs[0].ai_relevance_score == 0.8
        assert scored_recs[1].ai_relevance_score == 0.6
        assert scored_recs[2].ai_relevance_score == 0.9
        
        # Should be sorted by combined score (highest first)
        assert scored_recs[0].combined_score >= scored_recs[1].combined_score
    
    @pytest.mark.asyncio
    async def test_generate_explanation(
        self,
        test_recommendation_config,
        mock_ai_client
    ):
        """Test explanation generation"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.ai_client = mock_ai_client
        
        recommendations = [
            EnhancedProduct(
                id="1", 
                name="Laptop", 
                description="High-performance laptop"
            ),
            EnhancedProduct(
                id="2", 
                name="Mouse", 
                description="Wireless gaming mouse"
            )
        ]
        
        request = AIEnhancedRecommendationRequest(
            user_id="test_user",
            user_preferences="gaming setup"
        )
        
        explanation = await recommender._generate_explanation(
            recommendations, request
        )
        
        assert explanation is not None
        mock_ai_client.process_data.assert_called()
    
    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        test_recommendation_config,
        sample_csv_file
    ):
        """Test error handling in AI operations"""
        # Mock AI client that raises errors
        error_client = AsyncMock()
        error_client.process_data.side_effect = Exception("AI Error")
        error_client.batch_process.side_effect = Exception("Batch Error")
        
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        with patch('app.ai_recommender.create_ai_client', return_value=error_client):
            # Should not crash even with AI errors
            await recommender.initialize(sample_csv_file)
            
            request = AIEnhancedRecommendationRequest(
                user_id="test_user",
                num_recommendations=3,
                ai_processing_enabled=True
            )
            
            response = await recommender.get_recommendations(request)
            
            # Should still return a response
            assert isinstance(response, EnhancedRecommendationResponse)
            assert len(response.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_cleanup(self, test_recommendation_config, mock_ai_client):
        """Test resource cleanup"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        recommender.ai_client = mock_ai_client
        
        await recommender.close()
        
        mock_ai_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_caching_disabled(
        self,
        test_recommendation_config,
        sample_csv_file,
        mock_ai_client
    ):
        """Test behavior when caching is disabled"""
        # Ensure caching is disabled in config
        test_recommendation_config.cache_ai_responses = False
        
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        with patch('app.ai_recommender.create_ai_client', return_value=mock_ai_client):
            await recommender.initialize(sample_csv_file)
        
        # Verify cache is empty
        assert len(recommender.cache) == 0
    
    @pytest.mark.asyncio 
    async def test_different_request_scenarios(
        self,
        test_recommendation_config,
        sample_csv_file,
        mock_ai_client
    ):
        """Test different types of recommendation requests"""
        recommender = AIEnhancedRecommender(test_recommendation_config)
        
        with patch('app.ai_recommender.create_ai_client', return_value=mock_ai_client):
            await recommender.initialize(sample_csv_file)
        
        # Test scenarios
        scenarios = [
            {
                "user_id": "tech_user",
                "user_preferences": "gaming equipment",
                "context": "competitive gaming setup"
            },
            {
                "user_id": "office_user", 
                "user_preferences": "productivity tools",
                "context": "home office setup"
            },
            {
                "user_id": "minimal_user",
                "num_recommendations": 1
            }
        ]
        
        for scenario in scenarios:
            request = AIEnhancedRecommendationRequest(**scenario)
            response = await recommender.get_recommendations(request)
            
            assert isinstance(response, EnhancedRecommendationResponse)
            assert response.user_id == scenario["user_id"]
            assert len(response.recommendations) > 0
