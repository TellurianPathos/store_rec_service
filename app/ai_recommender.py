import asyncio
import json
import time
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import os

from app.ai_models import (
    AIProcessingConfig, 
    RecommendationConfig,
    AIEnhancedRecommendationRequest,
    EnhancedRecommendationResponse,
    EnhancedProduct,
    AIAnalysisResult
)
from app.ai_client import create_ai_client, BaseAIClient, AIClientError


class AIEnhancedRecommender:
    """Enhanced recommendation engine with AI integration"""
    
    def __init__(self, config: RecommendationConfig):
        self.config = config
        self.ai_client: Optional[BaseAIClient] = None
        self.tfidf_vectorizer = None
        self.product_features = None
        self.products_df = None
        self.cache: Dict[str, Any] = {}
        
        # Initialize AI client if enabled
        if config.ai_processing.enabled:
            self.ai_client = create_ai_client(config.ai_processing.model_config)
    
    async def initialize(self, data_path: str = "data/generic_dataset.csv"):
        """Initialize the recommender with data"""
        # Load product data
        self.products_df = pd.read_csv(data_path)
        
        # Process products with AI if enabled
        if self.config.ai_processing.enabled and self.ai_client:
            await self._ai_enhance_products()
        
        # Train content-based model
        self._train_content_model()
    
    async def _ai_enhance_products(self):
        """Enhance product data using AI"""
        print("Enhancing products with AI...")
        
        # Prepare data for AI processing
        product_texts = []
        for _, product in self.products_df.iterrows():
            text = f"Product: {product.get('name', '')} "
            if 'description' in product and pd.notna(product['description']):
                text += f"Description: {product['description']} "
            if 'category' in product and pd.notna(product['category']):
                text += f"Category: {product['category']}"
            product_texts.append(text.strip())
        
        # Process in batches
        batch_size = self.config.ai_processing.batch_size
        enhanced_data = []
        
        for i in range(0, len(product_texts), batch_size):
            batch = product_texts[i:i + batch_size]
            
            try:
                # Create AI prompt for product analysis
                system_prompt = (
                    "You are an expert product analyst. Analyze the given "
                    "product information and provide insights about customer "
                    "appeal, key features, and target audience. Return your "
                    "analysis as a JSON object with fields: 'appeal_score' "
                    "(0-1), 'key_features' (list), 'target_audience' (string), "
                    "'enhanced_description' (string)."
                )
                
                user_prompt_template = (
                    "Analyze this product for recommendation purposes: {data}"
                )
                
                # Process batch
                results = await self.ai_client.batch_process(
                    batch,
                    system_prompt=system_prompt,
                    user_prompt_template=user_prompt_template
                )
                
                enhanced_data.extend(results)
                
            except AIClientError as e:
                print(f"AI processing error for batch {i}: {e}")
                # Create dummy results for failed batch
                for _ in batch:
                    enhanced_data.append(AIAnalysisResult(
                        original_data="",
                        processed_data="",
                        analysis="",
                        confidence_score=0.0,
                        processing_time=0.0,
                        tokens_used=0
                    ))
        
        # Add AI analysis to products dataframe
        self.products_df['ai_analysis'] = enhanced_data
    
    def _train_content_model(self):
        """Train the content-based recommendation model"""
        # Prepare text features
        text_features = []
        for _, product in self.products_df.iterrows():
            features = []
            
            # Basic product info
            if pd.notna(product.get('name')):
                features.append(product['name'])
            if pd.notna(product.get('description')):
                features.append(product['description'])
            if pd.notna(product.get('category')):
                features.append(product['category'])
            
            # Add AI-enhanced features if available
            if 'ai_analysis' in product and hasattr(product['ai_analysis'], 'processed_data'):
                try:
                    ai_data = json.loads(product['ai_analysis'].processed_data)
                    if 'enhanced_description' in ai_data:
                        features.append(ai_data['enhanced_description'])
                    if 'key_features' in ai_data:
                        features.extend(ai_data['key_features'])
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            text_features.append(" ".join(features))
        
        # Create TF-IDF vectors
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        self.product_features = self.tfidf_vectorizer.fit_transform(text_features)
        
        # Save model
        os.makedirs("ml_models", exist_ok=True)
        joblib.dump({
            'vectorizer': self.tfidf_vectorizer,
            'features': self.product_features,
            'products': self.products_df
        }, "ml_models/ai_enhanced_model.pkl")
    
    async def get_recommendations(
        self, 
        request: AIEnhancedRecommendationRequest
    ) -> EnhancedRecommendationResponse:
        """Get AI-enhanced recommendations"""
        start_time = time.time()
        
        # Generate user profile with AI if enabled
        user_profile = None
        if (request.ai_processing_enabled and 
            self.config.ai_processing.enabled and 
            self.ai_client):
            user_profile = await self._generate_user_profile(request)
        
        # Get content-based recommendations
        content_recommendations = self._get_content_recommendations(
            request, user_profile
        )
        
        # Enhance recommendations with AI scoring
        if (request.ai_processing_enabled and 
            self.config.ai_processing.enabled and 
            self.ai_client):
            enhanced_recommendations = await self._ai_score_recommendations(
                content_recommendations, request, user_profile
            )
        else:
            enhanced_recommendations = content_recommendations
        
        # Generate explanation
        explanation = None
        if (request.ai_processing_enabled and 
            self.config.ai_processing.enabled and 
            self.ai_client):
            explanation = await self._generate_explanation(
                enhanced_recommendations, request
            )
        
        processing_time = time.time() - start_time
        
        return EnhancedRecommendationResponse(
            user_id=request.user_id,
            recommendations=enhanced_recommendations[:request.num_recommendations],
            processing_time=processing_time,
            ai_processing_used=request.ai_processing_enabled and self.config.ai_processing.enabled,
            explanation=explanation
        )
    
    async def _generate_user_profile(
        self, 
        request: AIEnhancedRecommendationRequest
    ) -> Optional[str]:
        """Generate user profile using AI"""
        if not request.user_preferences and not request.context:
            return None
        
        profile_data = f"User preferences: {request.user_preferences or 'None'} "
        profile_data += f"Context: {request.context or 'None'}"
        
        system_prompt = (
            "You are a user profiling expert. Based on the given user "
            "preferences and context, create a detailed user profile for "
            "product recommendations. Include interests, style preferences, "
            "budget considerations, and shopping behavior patterns."
        )
        
        try:
            result = await self.ai_client.process_data(
                profile_data,
                system_prompt=system_prompt
            )
            return result.processed_data
        except AIClientError as e:
            print(f"Error generating user profile: {e}")
            return None
    
    def _get_content_recommendations(
        self, 
        request: AIEnhancedRecommendationRequest,
        user_profile: Optional[str] = None
    ) -> List[EnhancedProduct]:
        """Get content-based recommendations"""
        # Create query vector
        query_features = []
        if request.user_preferences:
            query_features.append(request.user_preferences)
        if request.context:
            query_features.append(request.context)
        if user_profile:
            query_features.append(user_profile)
        
        if not query_features:
            # Return random products if no preferences
            sample_products = self.products_df.sample(
                min(request.num_recommendations * 3, len(self.products_df))
            )
        else:
            query_text = " ".join(query_features)
            query_vector = self.tfidf_vectorizer.transform([query_text])
            
            # Calculate similarities
            similarities = cosine_similarity(
                query_vector, 
                self.product_features
            ).flatten()
            
            # Get top products
            top_indices = similarities.argsort()[-request.num_recommendations * 3:][::-1]
            sample_products = self.products_df.iloc[top_indices]
        
        # Convert to EnhancedProduct objects
        recommendations = []
        for _, product in sample_products.iterrows():
            enhanced_product = EnhancedProduct(
                id=str(product.get('id', product.name)),
                name=product.get('name', 'Unknown Product'),
                description=product.get('description'),
                category=product.get('category'),
                price=product.get('price'),
                rating=product.get('rating'),
                similarity_score=0.0,  # Will be set later
                ai_relevance_score=0.0,  # Will be set later
                combined_score=0.0  # Will be set later
            )
            recommendations.append(enhanced_product)
        
        return recommendations
    
    async def _ai_score_recommendations(
        self,
        recommendations: List[EnhancedProduct],
        request: AIEnhancedRecommendationRequest,
        user_profile: Optional[str] = None
    ) -> List[EnhancedProduct]:
        """Score recommendations using AI"""
        scoring_prompt = (
            f"User ID: {request.user_id}\n"
            f"User Preferences: {request.user_preferences or 'None'}\n"
            f"Context: {request.context or 'None'}\n"
            f"User Profile: {user_profile or 'None'}\n\n"
            "Rate how relevant each product is for this user on a scale "
            "of 0.0 to 1.0. Consider user preferences, context, and the "
            "product characteristics. Return only a JSON array of scores."
        )
        
        products_text = "\n".join([
            f"{i+1}. {prod.name} - {prod.description or 'No description'} "
            f"(Category: {prod.category or 'Unknown'})"
            for i, prod in enumerate(recommendations)
        ])
        
        try:
            result = await self.ai_client.process_data(
                products_text,
                system_prompt=scoring_prompt
            )
            
            # Parse AI scores
            try:
                scores = json.loads(result.processed_data)
                if isinstance(scores, list) and len(scores) == len(recommendations):
                    for i, score in enumerate(scores):
                        recommendations[i].ai_relevance_score = float(score)
                        # Combine content similarity and AI relevance
                        recommendations[i].combined_score = (
                            self.config.content_similarity_weight * recommendations[i].similarity_score +
                            self.config.ai_enhancement_weight * recommendations[i].ai_relevance_score
                        )
            except (json.JSONDecodeError, ValueError, IndexError):
                print("Error parsing AI scores, using default scores")
                
        except AIClientError as e:
            print(f"Error scoring recommendations: {e}")
        
        # Sort by combined score
        recommendations.sort(key=lambda x: x.combined_score, reverse=True)
        
        return recommendations
    
    async def _generate_explanation(
        self,
        recommendations: List[EnhancedProduct],
        request: AIEnhancedRecommendationRequest
    ) -> Optional[str]:
        """Generate explanation for recommendations"""
        top_products = recommendations[:3]  # Explain top 3
        
        products_text = "\n".join([
            f"- {prod.name}: {prod.description or 'No description'}"
            for prod in top_products
        ])
        
        explanation_prompt = (
            f"Explain why these products were recommended for user "
            f"{request.user_id} based on their preferences: "
            f"{request.user_preferences or 'general interests'} and context: "
            f"{request.context or 'general shopping'}. Keep it concise and helpful."
        )
        
        try:
            result = await self.ai_client.process_data(
                products_text,
                system_prompt=explanation_prompt
            )
            return result.processed_data
        except AIClientError as e:
            print(f"Error generating explanation: {e}")
            return None
    
    async def close(self):
        """Clean up resources"""
        if self.ai_client:
            await self.ai_client.close()
