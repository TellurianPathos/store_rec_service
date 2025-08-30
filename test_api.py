#!/usr/bin/env python3
"""
Example usage of the AI-Enhanced Recommendation API
"""

import asyncio
import httpx
import json


async def test_api():
    """Test the recommendation API endpoints"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        # Test health endpoint
        print("🔍 Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"Health Status: {response.json()}")
        print()
        
        # Test configuration endpoint
        print("⚙️  Testing configuration endpoint...")
        response = await client.get(f"{base_url}/config")
        config = response.json()
        print(f"AI Enabled: {config['ai_processing_enabled']}")
        print(f"AI Provider: {config['ai_provider']}")
        print(f"Model: {config['model_name']}")
        print()
        
        # Test basic recommendations
        print("🛍️  Testing basic recommendations...")
        basic_request = {
            "user_id": "user123",
            "num_recommendations": 5
        }
        
        response = await client.post(
            f"{base_url}/recommend",
            json=basic_request
        )
        
        if response.status_code == 200:
            recommendations = response.json()
            print(f"Basic recommendations for {recommendations['user_id']}:")
            for i, product in enumerate(recommendations['recommendations'], 1):
                print(f"  {i}. {product['name']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        print()
        
        # Test AI-enhanced recommendations (if AI is enabled)
        if config['ai_processing_enabled']:
            print("🤖 Testing AI-enhanced recommendations...")
            ai_request = {
                "user_id": "user123",
                "num_recommendations": 3,
                "user_preferences": "I like electronics and gadgets, preferably affordable options",
                "context": "Looking for birthday gifts",
                "ai_processing_enabled": True
            }
            
            response = await client.post(
                f"{base_url}/recommend/ai",
                json=ai_request
            )
            
            if response.status_code == 200:
                ai_recommendations = response.json()
                print(f"AI recommendations for {ai_recommendations['user_id']}:")
                print(f"Processing time: {ai_recommendations['processing_time']:.2f}s")
                print(f"AI processing used: {ai_recommendations['ai_processing_used']}")
                
                for i, product in enumerate(ai_recommendations['recommendations'], 1):
                    print(f"  {i}. {product['name']}")
                    if product.get('similarity_score'):
                        print(f"     Similarity: {product['similarity_score']:.2f}")
                    if product.get('ai_relevance_score'):
                        print(f"     AI Relevance: {product['ai_relevance_score']:.2f}")
                    if product.get('combined_score'):
                        print(f"     Combined Score: {product['combined_score']:.2f}")
                
                if ai_recommendations.get('explanation'):
                    print(f"\nExplanation: {ai_recommendations['explanation']}")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        else:
            print("🤖 AI features are disabled in the current configuration")


async def test_different_scenarios():
    """Test different recommendation scenarios"""
    
    base_url = "http://localhost:8000"
    
    scenarios = [
        {
            "name": "Tech Enthusiast",
            "user_id": "tech_user",
            "preferences": "I love cutting-edge technology, smart devices, and premium electronics",
            "context": "Looking to upgrade my home setup"
        },
        {
            "name": "Budget Shopper",
            "user_id": "budget_user", 
            "preferences": "I need practical items at affordable prices, value for money is important",
            "context": "Shopping for everyday essentials"
        },
        {
            "name": "Gift Buyer",
            "user_id": "gift_user",
            "preferences": "Looking for popular items that make good gifts",
            "context": "Holiday shopping for family members"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        
        for scenario in scenarios:
            print(f"\n🎯 Testing scenario: {scenario['name']}")
            print("-" * 50)
            
            ai_request = {
                "user_id": scenario["user_id"],
                "num_recommendations": 3,
                "user_preferences": scenario["preferences"],
                "context": scenario["context"],
                "ai_processing_enabled": True
            }
            
            try:
                response = await client.post(
                    f"{base_url}/recommend/ai",
                    json=ai_request,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Recommendations for {scenario['name']}:")
                    
                    for i, product in enumerate(result['recommendations'], 1):
                        print(f"  {i}. {product['name']}")
                        if product.get('description'):
                            print(f"     {product['description'][:100]}...")
                    
                    if result.get('explanation'):
                        print(f"\nWhy these were recommended:")
                        print(f"  {result['explanation']}")
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"Request failed: {e}")


def main():
    """Main function to run API tests"""
    
    print("🚀 AI-Enhanced Recommendation API Test Suite")
    print("=" * 60)
    
    print("\nMake sure the API server is running:")
    print("  uvicorn app.main:app --reload")
    print()
    
    choice = input("Choose test mode:\n1. Basic API test\n2. Scenario testing\n3. Both\nEnter choice (1-3): ")
    
    if choice == '1':
        asyncio.run(test_api())
    elif choice == '2':
        asyncio.run(test_different_scenarios())
    elif choice == '3':
        asyncio.run(test_api())
        asyncio.run(test_different_scenarios())
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
