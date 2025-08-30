#!/usr/bin/env python3
"""
Integration test script for the AI-Enhanced Recommendation System
Tests the complete system end-to-end
"""

import asyncio
import httpx
import json
import time
import sys
from pathlib import Path


class IntegrationTestRunner:
    """Run integration tests against the API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Starting Integration Tests")
        print("=" * 50)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Test basic connectivity
            await self.test_health_check(client)
            
            # Test configuration
            await self.test_configuration(client)
            
            # Test basic recommendations
            await self.test_basic_recommendations(client)
            
            # Test AI recommendations (if enabled)
            await self.test_ai_recommendations(client)
            
            # Test error handling
            await self.test_error_handling(client)
            
            # Test API documentation
            await self.test_api_documentation(client)
        
        # Print summary
        self.print_summary()
    
    async def test_health_check(self, client):
        """Test health endpoint"""
        test_name = "Health Check"
        try:
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "ok":
                    self.log_test(test_name, True, "Health check passed")
                else:
                    self.log_test(test_name, False, "Invalid health response")
            else:
                self.log_test(test_name, False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    async def test_configuration(self, client):
        """Test configuration endpoint"""
        test_name = "Configuration"
        try:
            response = await client.get(f"{self.base_url}/config")
            
            if response.status_code == 200:
                config = response.json()
                required_fields = [
                    "ai_processing_enabled", 
                    "ai_provider", 
                    "content_similarity_weight"
                ]
                
                missing_fields = [f for f in required_fields if f not in config]
                if not missing_fields:
                    self.log_test(test_name, True, "All config fields present")
                else:
                    self.log_test(test_name, False, f"Missing: {missing_fields}")
            else:
                self.log_test(test_name, False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    async def test_basic_recommendations(self, client):
        """Test basic recommendation endpoint"""
        test_name = "Basic Recommendations"
        try:
            request_data = {
                "user_id": "integration_test_user",
                "num_recommendations": 3
            }
            
            response = await client.post(
                f"{self.base_url}/recommend",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if ("user_id" in data and 
                    "recommendations" in data and 
                    data["user_id"] == "integration_test_user"):
                    self.log_test(test_name, True, 
                                f"Got {len(data['recommendations'])} recommendations")
                else:
                    self.log_test(test_name, False, "Invalid response format")
            else:
                self.log_test(test_name, False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    async def test_ai_recommendations(self, client):
        """Test AI recommendation endpoint"""
        test_name = "AI Recommendations"
        try:
            request_data = {
                "user_id": "ai_test_user",
                "num_recommendations": 2,
                "user_preferences": "technology and gadgets",
                "context": "looking for productivity tools",
                "ai_processing_enabled": True
            }
            
            response = await client.post(
                f"{self.base_url}/recommend/ai",
                json=request_data,
                timeout=60.0  # AI processing may take longer
            )
            
            if response.status_code == 200:
                data = response.json()
                if ("user_id" in data and 
                    "recommendations" in data and
                    "ai_processing_used" in data):
                    self.log_test(test_name, True, 
                                f"AI processing: {data['ai_processing_used']}")
                else:
                    self.log_test(test_name, False, "Invalid AI response format")
            else:
                self.log_test(test_name, False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    async def test_error_handling(self, client):
        """Test error handling"""
        test_name = "Error Handling"
        try:
            # Test invalid request
            response = await client.post(
                f"{self.base_url}/recommend",
                json={"invalid": "data"}
            )
            
            if response.status_code == 422:  # Validation error
                self.log_test(test_name, True, "Validation errors handled correctly")
            else:
                self.log_test(test_name, False, 
                            f"Expected 422, got {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    async def test_api_documentation(self, client):
        """Test API documentation"""
        test_name = "API Documentation"
        try:
            response = await client.get(f"{self.base_url}/openapi.json")
            
            if response.status_code == 200:
                schema = response.json()
                if "openapi" in schema and "paths" in schema:
                    endpoints = len(schema["paths"])
                    self.log_test(test_name, True, f"OpenAPI schema with {endpoints} endpoints")
                else:
                    self.log_test(test_name, False, "Invalid OpenAPI schema")
            else:
                self.log_test(test_name, False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test(test_name, False, f"Exception: {e}")
    
    def log_test(self, test_name, passed, message):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append((test_name, passed, message))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 Integration Test Summary")
        print("=" * 50)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All integration tests passed!")
            return True
        else:
            print("\n❌ Some integration tests failed.")
            print("\nFailed tests:")
            for name, success, message in self.test_results:
                if not success:
                    print(f"  - {name}: {message}")
            return False


async def main():
    """Main function"""
    print("🚀 AI-Enhanced Recommendation System Integration Tests")
    
    # Check if server is specified
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing server: {base_url}")
    print("Make sure the server is running before starting tests!")
    
    # Wait a moment for user to read
    await asyncio.sleep(2)
    
    # Run tests
    runner = IntegrationTestRunner(base_url)
    success = await runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
