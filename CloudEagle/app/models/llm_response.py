"""Unified LLM response models."""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Unified response from any LLM provider."""
    content: str = Field(description="The response content from the LLM")
    provider: Literal["gemini", "azure_openai", "grok"] = Field(description="Which provider was used")
    model: str = Field(description="The specific model used")
    fallback_used: bool = Field(default=False, description="Whether fallback was triggered")
    fallback_reason: Optional[str] = Field(default=None, description="Reason for fallback if used")
    tokens: TokenUsage = Field(default_factory=TokenUsage, description="Token usage information")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "The capital of France is Paris.",
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "fallback_used": False,
                "tokens": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18
                },
                "estimated_cost_usd": 0.000003
            }
        }
