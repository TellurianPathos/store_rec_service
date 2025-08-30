import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.recommender import ContentRecommender
from app.models import Product


class TestContentRecommender:
    """Test the basic content recommendation engine"""
    
    def test_recommender_initialization(self):
        """Test recommender initialization"""
        recommender = ContentRecommender()
        assert recommender is not None
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists')
    def test_load_existing_model(self, mock_exists, mock_load):
        """Test loading existing model"""
        # Mock that model file exists
        mock_exists.return_value = True
        
        # Mock loaded model data
        mock_model_data = {
            'vectorizer': MagicMock(),
            'features': MagicMock(),
            'products': pd.DataFrame({
                'id': ['1', '2'],
                'name': ['Product 1', 'Product 2']
            })
        }
        mock_load.return_value = mock_model_data
        
        recommender = ContentRecommender()
        
        # Verify model was loaded
        mock_load.assert_called_once_with("ml_models/content_model.pkl")
        assert recommender.tfidf_vectorizer is not None
        assert recommender.product_features is not None
        assert recommender.products_df is not None
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists')
    def test_model_not_found(self, mock_exists, mock_load):
        """Test behavior when model file doesn't exist"""
        mock_exists.return_value = False
        
        recommender = ContentRecommender()
        
        # Model loading should not be called
        mock_load.assert_not_called()
        assert recommender.tfidf_vectorizer is None
        assert recommender.product_features is None
        assert recommender.products_df is None
    
    def test_get_recommendations_no_model(self):
        """Test getting recommendations when no model is loaded"""
        recommender = ContentRecommender()
        
        # Should return empty list when no model
        recommendations = recommender.get_recommendations("user123", 5)
        assert recommendations == []
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists')
    def test_get_recommendations_with_model(self, mock_exists, mock_load):
        """Test getting recommendations with loaded model"""
        mock_exists.return_value = True
        
        # Create sample products dataframe
        products_df = pd.DataFrame({
            'id': ['1', '2', '3'],
            'name': ['Laptop', 'Mouse', 'Keyboard'],
            'description': [
                'High-performance laptop',
                'Wireless mouse',
                'Mechanical keyboard'
            ]
        })
        
        mock_model_data = {
            'vectorizer': MagicMock(),
            'features': MagicMock(),
            'products': products_df
        }
        mock_load.return_value = mock_model_data
        
        recommender = ContentRecommender()
        
        # Mock the sample method to return specific products
        with patch.object(products_df, 'sample') as mock_sample:
            mock_sample.return_value = products_df.head(2)
            
            recommendations = recommender.get_recommendations("user123", 2)
            
            assert len(recommendations) == 2
            assert all(isinstance(product, Product) for product in recommendations)
            assert recommendations[0].name == 'Laptop'
            assert recommendations[1].name == 'Mouse'
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists') 
    def test_recommendations_limit(self, mock_exists, mock_load):
        """Test that recommendation count is properly limited"""
        mock_exists.return_value = True
        
        # Create sample with many products
        products_df = pd.DataFrame({
            'id': [str(i) for i in range(10)],
            'name': [f'Product {i}' for i in range(10)],
            'description': [f'Description {i}' for i in range(10)]
        })
        
        mock_model_data = {
            'vectorizer': MagicMock(),
            'features': MagicMock(),
            'products': products_df
        }
        mock_load.return_value = mock_model_data
        
        recommender = ContentRecommender()
        
        # Test different recommendation counts
        for num_recs in [1, 3, 5, 10]:
            with patch.object(products_df, 'sample') as mock_sample:
                mock_sample.return_value = products_df.head(num_recs)
                
                recommendations = recommender.get_recommendations(
                    "user123", 
                    num_recs
                )
                
                assert len(recommendations) == num_recs
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists')
    def test_product_conversion(self, mock_exists, mock_load):
        """Test conversion of DataFrame rows to Product objects"""
        mock_exists.return_value = True
        
        products_df = pd.DataFrame({
            'id': ['prod_1'],
            'name': ['Test Product'],
            'description': ['A test product'],
            'category': ['Electronics'],
            'price': [99.99]
        })
        
        mock_model_data = {
            'vectorizer': MagicMock(),
            'features': MagicMock(),
            'products': products_df
        }
        mock_load.return_value = mock_model_data
        
        recommender = ContentRecommender()
        
        with patch.object(products_df, 'sample') as mock_sample:
            mock_sample.return_value = products_df
            
            recommendations = recommender.get_recommendations("user123", 1)
            
            assert len(recommendations) == 1
            product = recommendations[0]
            
            assert isinstance(product, Product)
            assert product.id == 'prod_1'
            assert product.name == 'Test Product'
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        recommender = ContentRecommender()
        
        # Test with zero recommendations
        recommendations = recommender.get_recommendations("user123", 0)
        assert recommendations == []
        
        # Test with negative recommendations
        recommendations = recommender.get_recommendations("user123", -1)
        assert recommendations == []
        
        # Test with empty user_id
        recommendations = recommender.get_recommendations("", 5)
        assert recommendations == []
    
    @patch('app.recommender.joblib.load')
    @patch('app.recommender.os.path.exists')
    def test_model_loading_error(self, mock_exists, mock_load):
        """Test handling of model loading errors"""
        mock_exists.return_value = True
        mock_load.side_effect = Exception("Model loading failed")
        
        # Should handle the exception gracefully
        recommender = ContentRecommender()
        
        # Should still be able to call get_recommendations without crashing
        recommendations = recommender.get_recommendations("user123", 5)
        assert recommendations == []
