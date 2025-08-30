import asyncio
import time
from abc import ABC, abstractmethod
from typing import List
import httpx
from app.ai_models import AIModelConfig, AIProvider, AIAnalysisResult


class AIClientError(Exception):
    """Base exception for AI client errors"""
    pass


class AIRateLimitError(AIClientError):
    """Raised when rate limit is exceeded"""
    pass


class AIQuotaExceededError(AIClientError):
    """Raised when quota is exceeded"""
    pass


class BaseAIClient(ABC):
    """Abstract base class for AI clients"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers=config.custom_headers
        )
    
    @abstractmethod
    async def process_data(
        self, 
        data: str, 
        system_prompt: str = None, 
        user_prompt: str = None
    ) -> AIAnalysisResult:
        """Process data using the AI model"""
        pass
    
    @abstractmethod
    async def batch_process(
        self, 
        data_list: List[str], 
        system_prompt: str = None,
        user_prompt_template: str = None
    ) -> List[AIAnalysisResult]:
        """Process multiple data items"""
        pass
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class OpenAIClient(BaseAIClient):
    """OpenAI API client"""
    
    async def process_data(
        self, 
        data: str, 
        system_prompt: str = None, 
        user_prompt: str = None
    ) -> AIAnalysisResult:
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        user_content = user_prompt or data
        messages.append({"role": "user", "content": user_content})
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **self.config.custom_params
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                f"{self.config.base_url or 'https://api.openai.com'}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            processing_time = time.time() - start_time
            
            return AIAnalysisResult(
                original_data=data,
                processed_data=result["choices"][0]["message"]["content"],
                analysis=result["choices"][0]["message"]["content"],
                confidence_score=0.8,  # Could be calculated based on model response
                processing_time=processing_time,
                tokens_used=result.get("usage", {}).get("total_tokens", 0)
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise AIRateLimitError(f"Rate limit exceeded: {e}")
            elif e.response.status_code == 402:
                raise AIQuotaExceededError(f"Quota exceeded: {e}")
            else:
                raise AIClientError(f"OpenAI API error: {e}")
    
    async def batch_process(
        self, 
        data_list: List[str], 
        system_prompt: str = None,
        user_prompt_template: str = None
    ) -> List[AIAnalysisResult]:
        results = []
        for data in data_list:
            user_prompt = None
            if user_prompt_template:
                user_prompt = user_prompt_template.format(data=data)
            
            result = await self.process_data(data, system_prompt, user_prompt)
            results.append(result)
            
            # Add small delay to respect rate limits
            await asyncio.sleep(0.1)
        
        return results


class AnthropicClient(BaseAIClient):
    """Anthropic Claude API client"""
    
    async def process_data(
        self, 
        data: str, 
        system_prompt: str = None, 
        user_prompt: str = None
    ) -> AIAnalysisResult:
        start_time = time.time()
        
        payload = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "user", "content": user_prompt or data}
            ],
            **self.config.custom_params
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                f"{self.config.base_url or 'https://api.anthropic.com'}/v1/messages",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            processing_time = time.time() - start_time
            
            return AIAnalysisResult(
                original_data=data,
                processed_data=result["content"][0]["text"],
                analysis=result["content"][0]["text"],
                confidence_score=0.8,
                processing_time=processing_time,
                tokens_used=result.get("usage", {}).get("input_tokens", 0) + 
                           result.get("usage", {}).get("output_tokens", 0)
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise AIRateLimitError(f"Rate limit exceeded: {e}")
            elif e.response.status_code == 402:
                raise AIQuotaExceededError(f"Quota exceeded: {e}")
            else:
                raise AIClientError(f"Anthropic API error: {e}")
    
    async def batch_process(
        self, 
        data_list: List[str], 
        system_prompt: str = None,
        user_prompt_template: str = None
    ) -> List[AIAnalysisResult]:
        results = []
        for data in data_list:
            user_prompt = None
            if user_prompt_template:
                user_prompt = user_prompt_template.format(data=data)
            
            result = await self.process_data(data, system_prompt, user_prompt)
            results.append(result)
            
            # Add delay for rate limiting
            await asyncio.sleep(0.2)
        
        return results


class OllamaClient(BaseAIClient):
    """Ollama local AI client"""
    
    async def process_data(
        self, 
        data: str, 
        system_prompt: str = None, 
        user_prompt: str = None
    ) -> AIAnalysisResult:
        start_time = time.time()
        
        payload = {
            "model": self.config.model_name,
            "prompt": user_prompt or data,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                **self.config.custom_params
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.config.base_url or 'http://localhost:11434'}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            processing_time = time.time() - start_time
            
            return AIAnalysisResult(
                original_data=data,
                processed_data=result["response"],
                analysis=result["response"],
                confidence_score=0.7,
                processing_time=processing_time,
                tokens_used=result.get("prompt_eval_count", 0) + 
                           result.get("eval_count", 0)
            )
            
        except httpx.HTTPStatusError as e:
            raise AIClientError(f"Ollama API error: {e}")
    
    async def batch_process(
        self, 
        data_list: List[str], 
        system_prompt: str = None,
        user_prompt_template: str = None
    ) -> List[AIAnalysisResult]:
        results = []
        for data in data_list:
            user_prompt = None
            if user_prompt_template:
                user_prompt = user_prompt_template.format(data=data)
            
            result = await self.process_data(data, system_prompt, user_prompt)
            results.append(result)
        
        return results


class CustomAPIClient(BaseAIClient):
    """Generic client for custom AI APIs"""
    
    async def process_data(
        self, 
        data: str, 
        system_prompt: str = None, 
        user_prompt: str = None
    ) -> AIAnalysisResult:
        start_time = time.time()
        
        # This is a template - users can customize based on their API
        payload = {
            "input": user_prompt or data,
            "system": system_prompt,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **self.config.custom_params
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.custom_headers
        }
        
        try:
            response = await self.client.post(
                self.config.base_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            processing_time = time.time() - start_time
            
            # This assumes the API returns a 'response' field
            # Users would need to customize this based on their API structure
            response_text = result.get("response", str(result))
            
            return AIAnalysisResult(
                original_data=data,
                processed_data=response_text,
                analysis=response_text,
                confidence_score=0.7,
                processing_time=processing_time,
                tokens_used=result.get("tokens_used", 0)
            )
            
        except httpx.HTTPStatusError as e:
            raise AIClientError(f"Custom API error: {e}")
    
    async def batch_process(
        self, 
        data_list: List[str], 
        system_prompt: str = None,
        user_prompt_template: str = None
    ) -> List[AIAnalysisResult]:
        results = []
        for data in data_list:
            user_prompt = None
            if user_prompt_template:
                user_prompt = user_prompt_template.format(data=data)
            
            result = await self.process_data(data, system_prompt, user_prompt)
            results.append(result)
        
        return results


def create_ai_client(config: AIModelConfig) -> BaseAIClient:
    """Factory function to create AI clients based on provider"""
    
    if config.provider == AIProvider.OPENAI:
        return OpenAIClient(config)
    elif config.provider == AIProvider.ANTHROPIC:
        return AnthropicClient(config)
    elif config.provider == AIProvider.OLLAMA:
        return OllamaClient(config)
    elif config.provider == AIProvider.CUSTOM:
        return CustomAPIClient(config)
    else:
        raise ValueError(f"Unsupported AI provider: {config.provider}")
