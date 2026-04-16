from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    gemini_api_key: str
    log_level: str = "INFO"
    rate_limit_per_minute: int = 100
    api_timeout_seconds: int = 30
    cache_ttl_hours: int = 24
    
    rest_countries_base_url: str = "https://restcountries.com/v3.1"
    
    mongodb_connection_string: str
    mongodb_database_name: str = "country_agent"
    context_collection_name: str = "conversations"
    cost_collection_name: str = "llm_costs"
    
    max_context_tokens: int = 2000
    recent_messages_count: int = 3
    summary_trigger_count: int = 5
    
    openai_api_4_key: Optional[str] = None
    openai_4_base_url: Optional[str] = None
    openai_api_4_version: Optional[str] = None
    open_api_4_engine: Optional[str] = None
    
    grok_api_key: Optional[str] = None
    grok_base_url: Optional[str] = "https://api.groq.com/openai/v1"
    grok_model: Optional[str] = "llama-3.1-8b-instant"
    
    langchain_tracing_v2: bool = True
    langchain_api_key: Optional[str] = None
    langchain_project: Optional[str] = None
    langchain_endpoint: Optional[str] = None

    

settings = Settings()
