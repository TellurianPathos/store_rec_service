import joblib
from typing import List, Tuple, Dict, Any
import numpy as np
import os
from pathlib import Path

from app.models import Product


class ContentRecommender:
    """
    A content-based recommendation system that uses pre-trained TF-IDF vectors
    to find similar products.
    """
    
    def __init__(self, model_path: str = "ml_models/content_model.pkl"):
        """
        Initialize the recommender with a trained model.
        
        Args:
            model_path: Path to the saved model file
        """
        self.model_path = model_path
        self.tfidf_matrix = None
        self.product_df = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the trained model from disk."""
        if os.path.exists(self.model_path):
            try:
                self.tfidf_matrix, self.product_df = joblib.load(self.model_path)
                print(f"Model loaded from {self.model_path}")
            except Exception as e:
                print(f"Error loading model: {e}")
                # Initialize with empty model for now
                self.tfidf_matrix = np.array([])
                self.product_df = {}
        else:
            print(f"Model file not found at {self.model_path}. Using empty model.")
            # Initialize with empty model
            self.tfidf_matrix = np.array([])
            self.product_df = {}
    
    def get_recommendations(self, user_id: str, num_recommendations: int = 5) -> List[Product]:
        """
        Get product recommendations for a user.
        
        Args:
            user_id: The ID of the user to get recommendations for
            num_recommendations: Number of recommendations to return
            
        Returns:
            List of recommended Product objects
        """
        # In a real system, we'd use the user_id to fetch user history or preferences
        # For this example, we'll just return random products
        
        if self.product_df is None or len(self.product_df) == 0:
            # Return dummy recommendations if no model is loaded
            return [
                Product(id=f"dummy{i}", name=f"Dummy Product {i}")
                for i in range(min(num_recommendations, 5))
            ]
        
        # In a real implementation, we would:
        # 1. Get user's previous interactions or preferences
        # 2. Find item vectors similar to those items
        # 3. Return the most similar items
        
        # For now, just return some random products from our dataset
        sample_size = min(num_recommendations, len(self.product_df))
        if sample_size == 0:
            return []
            
        # Random sample from product dataframe
        sample_indices = np.random.choice(
            len(self.product_df), 
            size=sample_size, 
            replace=False
        )
        
        recommendations = []
        for idx in sample_indices:
            product = self.product_df.iloc[idx]
            recommendations.append(
                Product(
                    id=str(product.get("id", f"product_{idx}")),
                    name=str(product.get("name", f"Product {idx}"))
                )
            )
            
        return recommendations
