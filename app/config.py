"""
Production-ready configuration management for the AI recommendation service.
Centralized configuration with environment-based settings and validation.
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, validator, Field
from enum import Enum
import logging

from app.logger import get_logger

logger = get_logger(__name__)


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing" 
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="recommendations")
    user: str = Field(default="postgres")
    password: str = Field(default="")
    ssl_mode: str = Field(default="prefer")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    
    class Config:
        env_prefix = "DB_"


class RedisConfig(BaseModel):
    """Redis configuration for caching and rate limiting"""
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = Field(default=5.0, ge=0.1, le=60.0)
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    
    class Config:
        env_prefix = "REDIS_"


class SecurityConfig(BaseModel):
    """Security configuration"""
    require_api_key: bool = Field(default=False)
    api_keys: List[str] = Field(default_factory=list)
    rate_limit_enabled: bool = Field(default=True)
    max_requests_per_minute: int = Field(default=60, ge=1, le=10000)
    max_requests_per_hour: int = Field(default=1000, ge=1, le=100000)
    enable_ip_filtering: bool = Field(default=False)
    allowed_ips: List[str] = Field(default_factory=list)
    blocked_ips: List[str] = Field(default_factory=list)
    cors_origins: List[str] = Field(default_factory=list)
    trusted_hosts: List[str] = Field(default_factory=list)
    
    @validator('api_keys', pre=True)
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            return [key.strip() for key in v.split(',') if key.strip()]
        return v
    
    @validator('allowed_ips', pre=True)
    def parse_allowed_ips(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(',') if ip.strip()]
        return v
    
    @validator('blocked_ips', pre=True)
    def parse_blocked_ips(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(',') if ip.strip()]
        return v
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @validator('trusted_hosts', pre=True)
    def parse_trusted_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',') if host.strip()]
        return v
    
    class Config:
        env_prefix = "SECURITY_"


class AIConfig(BaseModel):
    """AI service configuration"""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = Field(default="http://localhost:11434")
    default_provider: str = Field(default="openai")
    default_model: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0)
    
    class Config:
        env_prefix = "AI_"


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration"""
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)
    enable_health_checks: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1, le=65535)
    health_check_interval: int = Field(default=30, ge=5, le=300)
    trace_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    
    class Config:
        env_prefix = "MONITORING_"


class ApplicationConfig(BaseModel):
    """Main application configuration"""
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_file: Optional[str] = None
    
    # Server configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=32)
    
    # Data configuration
    data_path: str = Field(default="data/generic_dataset.csv")
    model_path: str = Field(default="ml_models")
    
    # Feature flags
    enable_ai_processing: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_user_profiling: bool = Field(default=True)
    enable_content_analysis: bool = Field(default=True)
    
    # Performance settings
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    batch_size: int = Field(default=10, ge=1, le=100)
    max_concurrent_requests: int = Field(default=100, ge=1, le=1000)
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    @validator('environment', pre=True)
    def parse_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @validator('log_level', pre=True)
    def parse_log_level(cls, v):
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v
    
    @validator('debug')
    def set_debug_from_environment(cls, v, values):
        environment = values.get('environment')
        if environment == Environment.DEVELOPMENT:
            return True
        elif environment == Environment.PRODUCTION:
            return False
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ConfigManager:
    """Configuration manager with environment-specific settings"""
    
    def __init__(self):
        self._config: Optional[ApplicationConfig] = None
        self._loaded = False
    
    def load_config(self, config_file: Optional[str] = None) -> ApplicationConfig:
        """
        Load configuration from environment and files.
        
        Args:
            config_file: Optional config file path
            
        Returns:
            Loaded configuration
        """
        if self._loaded and self._config:
            return self._config
        
        try:
            # Load from environment variables
            env_config = {}
            
            # Parse environment variables with proper prefixes
            for key, value in os.environ.items():
                if key.startswith(('DB_', 'REDIS_', 'SECURITY_', 'AI_', 'MONITORING_')):
                    # Convert to nested structure
                    prefix = key.split('_')[0].lower()
                    field = '_'.join(key.split('_')[1:]).lower()
                    
                    if prefix not in env_config:
                        env_config[prefix] = {}
                    env_config[prefix][field] = value
                else:
                    # Direct application config
                    env_config[key.lower()] = value
            
            # Create configuration
            self._config = ApplicationConfig(**env_config)
            
            # Environment-specific adjustments
            self._apply_environment_defaults()
            
            # Validate configuration
            self._validate_config()
            
            self._loaded = True
            
            logger.info(
                "Configuration loaded successfully",
                extra={
                    "environment": self._config.environment.value,
                    "debug": self._config.debug,
                    "ai_enabled": self._config.enable_ai_processing
                }
            )
            
            return self._config
            
        except Exception as e:
            logger.error(
                "Failed to load configuration",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
    
    def _apply_environment_defaults(self):
        """Apply environment-specific defaults"""
        if not self._config:
            return
        
        if self._config.environment == Environment.PRODUCTION:
            # Production defaults
            self._config.debug = False
            self._config.log_level = LogLevel.INFO
            self._config.security.require_api_key = True
            self._config.monitoring.enable_metrics = True
            self._config.monitoring.enable_tracing = True
            
        elif self._config.environment == Environment.DEVELOPMENT:
            # Development defaults
            self._config.debug = True
            self._config.log_level = LogLevel.DEBUG
            self._config.security.require_api_key = False
            self._config.security.cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
            
        elif self._config.environment == Environment.TESTING:
            # Testing defaults
            self._config.debug = False
            self._config.log_level = LogLevel.WARNING
            self._config.enable_ai_processing = False
            self._config.security.rate_limit_enabled = False
    
    def _validate_config(self):
        """Validate configuration for consistency and requirements"""
        if not self._config:
            return
        
        # Production validations
        if self._config.environment == Environment.PRODUCTION:
            if self._config.security.require_api_key and not self._config.security.api_keys:
                raise ValueError("API keys required in production but none configured")
            
            if not self._config.ai.openai_api_key and not self._config.ai.anthropic_api_key:
                logger.warning("No AI provider API keys configured - AI features will be disabled")
        
        # AI configuration validation
        if self._config.enable_ai_processing:
            providers = []
            if self._config.ai.openai_api_key:
                providers.append("openai")
            if self._config.ai.anthropic_api_key:
                providers.append("anthropic")
            if self._config.ai.ollama_base_url:
                providers.append("ollama")
            
            if not providers and self._config.environment != Environment.TESTING:
                logger.warning("AI processing enabled but no providers configured")
    
    @property
    def config(self) -> ApplicationConfig:
        """Get current configuration"""
        if not self._loaded:
            return self.load_config()
        return self._config
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        db_config = self.config.database
        return (
            f"postgresql://{db_config.user}:{db_config.password}@"
            f"{db_config.host}:{db_config.port}/{db_config.name}"
        )
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        redis_config = self.config.redis
        password_part = f":{redis_config.password}@" if redis_config.password else ""
        scheme = "rediss" if redis_config.ssl else "redis"
        return f"{scheme}://{password_part}{redis_config.host}:{redis_config.port}/{redis_config.db}"
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.config.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.config.environment == Environment.DEVELOPMENT


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> ApplicationConfig:
    """Get the global application configuration"""
    return config_manager.config


def get_database_url() -> str:
    """Get database connection URL"""
    return config_manager.get_database_url()


def get_redis_url() -> str:
    """Get Redis connection URL"""
    return config_manager.get_redis_url()