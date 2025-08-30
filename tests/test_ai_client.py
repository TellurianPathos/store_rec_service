import pytest
import asyncio
import httpx
import respx
from unittest.mock import patch, AsyncMock

from app.ai_client import (
    OpenAIClient,
    AnthropicClient, 
    OllamaClient,
    CustomAPIClient,
    create_ai_client,
    AIClientError,
    AIRateLimitError,
    AIQuotaExceededError
)
from app.ai_models import AIProvider, AIModelConfig


class TestAIClients:
    """Test AI client implementations"""
    
    @pytest.mark.asyncio
    async def test_openai_client_success(self, mock_ai_config):
        """Test successful OpenAI API call"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-openai-key"
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Processed product data with AI insights"
                }
            }],
            "usage": {
                "total_tokens": 150
            }
        }
        
        with respx.mock:
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(return_value=httpx.Response(200, json=mock_response))
            
            client = OpenAIClient(mock_ai_config)
            result = await client.process_data(
                "Test product data",
                system_prompt="Test system prompt"
            )
            
            assert result.original_data == "Test product data"
            assert result.processed_data == "Processed product data with AI insights"
            assert result.tokens_used == 150
            assert result.confidence_score > 0
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_openai_client_rate_limit(self, mock_ai_config):
        """Test OpenAI rate limit handling"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-openai-key"
        
        with respx.mock:
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(return_value=httpx.Response(429, json={"error": "Rate limit"}))
            
            client = OpenAIClient(mock_ai_config)
            
            with pytest.raises(AIRateLimitError):
                await client.process_data("Test data")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_anthropic_client_success(self, mock_ai_config):
        """Test successful Anthropic API call"""
        mock_ai_config.provider = AIProvider.ANTHROPIC
        mock_ai_config.api_key = "test-anthropic-key"
        
        mock_response = {
            "content": [{
                "text": "Anthropic processed response"
            }],
            "usage": {
                "input_tokens": 50,
                "output_tokens": 100
            }
        }
        
        with respx.mock:
            respx.post(
                "https://api.anthropic.com/v1/messages"
            ).mock(return_value=httpx.Response(200, json=mock_response))
            
            client = AnthropicClient(mock_ai_config)
            result = await client.process_data(
                "Test product data",
                system_prompt="Test system prompt"
            )
            
            assert result.original_data == "Test product data"
            assert result.processed_data == "Anthropic processed response"
            assert result.tokens_used == 150  # input + output tokens
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_ollama_client_success(self, mock_ai_config):
        """Test successful Ollama API call"""
        mock_ai_config.provider = AIProvider.OLLAMA
        mock_ai_config.base_url = "http://localhost:11434"
        mock_ai_config.model_name = "llama2"
        
        mock_response = {
            "response": "Ollama local model response",
            "prompt_eval_count": 25,
            "eval_count": 75
        }
        
        with respx.mock:
            respx.post(
                "http://localhost:11434/api/generate"
            ).mock(return_value=httpx.Response(200, json=mock_response))
            
            client = OllamaClient(mock_ai_config)
            result = await client.process_data("Test product data")
            
            assert result.original_data == "Test product data"
            assert result.processed_data == "Ollama local model response"
            assert result.tokens_used == 100  # prompt_eval + eval
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_custom_api_client(self, mock_ai_config):
        """Test custom API client"""
        mock_ai_config.provider = AIProvider.CUSTOM
        mock_ai_config.base_url = "https://custom-api.example.com/process"
        mock_ai_config.api_key = "custom-key"
        
        mock_response = {
            "response": "Custom API response",
            "tokens_used": 120
        }
        
        with respx.mock:
            respx.post(
                "https://custom-api.example.com/process"
            ).mock(return_value=httpx.Response(200, json=mock_response))
            
            client = CustomAPIClient(mock_ai_config)
            result = await client.process_data("Test data")
            
            assert result.original_data == "Test data"
            assert result.processed_data == "Custom API response"
            assert result.tokens_used == 120
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_ai_config):
        """Test batch processing functionality"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-key"
        
        mock_response = {
            "choices": [{
                "message": {"content": "Batch processed"}
            }],
            "usage": {"total_tokens": 100}
        }
        
        with respx.mock:
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(return_value=httpx.Response(200, json=mock_response))
            
            client = OpenAIClient(mock_ai_config)
            data_list = ["Product 1", "Product 2", "Product 3"]
            
            results = await client.batch_process(
                data_list,
                system_prompt="Batch process",
                user_prompt_template="Process: {data}"
            )
            
            assert len(results) == 3
            for result in results:
                assert result.processed_data == "Batch processed"
                assert result.tokens_used == 100
            
            await client.close()
    
    def test_create_ai_client_factory(self, mock_ai_config):
        """Test AI client factory function"""
        # Test OpenAI client creation
        mock_ai_config.provider = AIProvider.OPENAI
        client = create_ai_client(mock_ai_config)
        assert isinstance(client, OpenAIClient)
        
        # Test Anthropic client creation
        mock_ai_config.provider = AIProvider.ANTHROPIC
        client = create_ai_client(mock_ai_config)
        assert isinstance(client, AnthropicClient)
        
        # Test Ollama client creation
        mock_ai_config.provider = AIProvider.OLLAMA
        client = create_ai_client(mock_ai_config)
        assert isinstance(client, OllamaClient)
        
        # Test Custom client creation
        mock_ai_config.provider = AIProvider.CUSTOM
        client = create_ai_client(mock_ai_config)
        assert isinstance(client, CustomAPIClient)
        
        # Test unsupported provider
        mock_ai_config.provider = "unsupported"
        with pytest.raises(ValueError):
            create_ai_client(mock_ai_config)
    
    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self, mock_ai_config):
        """Test quota exceeded error handling"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-key"
        
        with respx.mock:
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(return_value=httpx.Response(402, json={"error": "Quota exceeded"}))
            
            client = OpenAIClient(mock_ai_config)
            
            with pytest.raises(AIQuotaExceededError):
                await client.process_data("Test data")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_generic_ai_error(self, mock_ai_config):
        """Test generic AI client error handling"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-key"
        
        with respx.mock:
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(return_value=httpx.Response(500, json={"error": "Server error"}))
            
            client = OpenAIClient(mock_ai_config)
            
            with pytest.raises(AIClientError):
                await client.process_data("Test data")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_client_timeout(self, mock_ai_config):
        """Test client timeout handling"""
        mock_ai_config.provider = AIProvider.OPENAI
        mock_ai_config.api_key = "test-key"
        mock_ai_config.timeout = 0.001  # Very short timeout
        
        with respx.mock:
            # Mock a slow response
            respx.post(
                "https://api.openai.com/v1/chat/completions"
            ).mock(side_effect=httpx.TimeoutException("Request timeout"))
            
            client = OpenAIClient(mock_ai_config)
            
            with pytest.raises(httpx.TimeoutException):
                await client.process_data("Test data")
            
            await client.close()
