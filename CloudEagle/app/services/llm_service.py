"""LLM Service with automatic fallback from Grok to Gemini to Azure OpenAI."""
from typing import List, Union, Optional
from datetime import datetime, timezone
import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from openai import AzureOpenAI
import tiktoken
from langsmith import traceable

from app.config import settings
from app.models.llm_response import LLMResponse, TokenUsage
from app.services.cost_calculator import cost_calculator
from app.database import MongoDB

logger = structlog.get_logger()


class LLMService:
    """Unified LLM service with automatic fallback support across multiple providers.
    
    Supports three-tier fallback: Grok → Gemini → Azure OpenAI
    """
    
    def __init__(self):
        """Initialize the LLM service."""
        self.gemini_model = "gemini-2.5-flash"
        self.azure_model = settings.open_api_4_engine or "gpt-4o"
        
        # Initialize Azure client if configured
        self.azure_client = None
        if self._is_azure_configured():
            try:
                self.azure_client = AzureOpenAI(
                    api_key=settings.openai_api_4_key,
                    api_version=settings.openai_api_4_version,
                    azure_endpoint=settings.openai_4_base_url
                )
                logger.info("azure_openai_initialized", model=self.azure_model)
            except Exception as e:
                logger.warning("azure_openai_init_failed", error=str(e))
        
        # Initialize Grok client if configured
        self.grok_client = None
        self.grok_model = settings.grok_model or "grok-beta"
        if self._is_grok_configured():
            try:
                from openai import OpenAI
                self.grok_client = OpenAI(
                    api_key=settings.grok_api_key,
                    base_url=settings.grok_base_url
                )
                logger.info("grok_initialized", model=self.grok_model)
            except Exception as e:
                logger.warning("grok_init_failed", error=str(e))
        
        # Initialize tokenizer for Azure
        self.tokenizer = None
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("tokenizer_init_failed", error=str(e))
    
    def _is_azure_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return all([
            settings.openai_api_4_key,
            settings.openai_4_base_url,
            settings.openai_api_4_version,
            settings.open_api_4_engine
        ])
    
    def _is_grok_configured(self) -> bool:
        """Check if Grok is properly configured."""
        return all([
            settings.grok_api_key,
            settings.grok_base_url,
            settings.grok_model
        ])
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if error is a rate limit/quota error from Gemini.
        
        Args:
            error: Exception to check
            
        Returns:
            True if this is a rate limit error
        """
        error_str = str(error).lower()
        error_indicators = [
            "429",
            "rate limit",
            "quota",
            "resource_exhausted",
            "resourceexhausted",
            "too many requests",
            "quota exceeded"
        ]
        return any(indicator in error_str for indicator in error_indicators)
    
    def _convert_messages_to_openai_format(
        self, 
        messages: List[BaseMessage]
    ) -> List[dict]:
        """
        Convert LangChain messages to OpenAI format.
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            List of OpenAI-formatted messages
        """
        openai_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append({
                    "role": "system",
                    "content": msg.content
                })
            elif isinstance(msg, HumanMessage):
                openai_messages.append({
                    "role": "user",
                    "content": msg.content
                })
            else:
                # Fallback for other message types
                openai_messages.append({
                    "role": "user",
                    "content": str(msg.content)
                })
        return openai_messages
    
    def _estimate_tokens_for_messages(self, messages: List[BaseMessage]) -> int:
        """
        Estimate token count for messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count
        """
        try:
            if self.tokenizer:
                text = " ".join([msg.content for msg in messages])
                return len(self.tokenizer.encode(text))
            else:
                # Fallback: rough estimate (4 chars = 1 token)
                text = " ".join([msg.content for msg in messages])
                return len(text) // 4
        except Exception:
            # Fallback
            text = " ".join([msg.content for msg in messages])
            return len(text) // 4
    
    @traceable(name="gemini_call", run_type="llm")
    async def _invoke_gemini(
        self,
        messages: List[BaseMessage],
        temperature: float
    ) -> LLMResponse:
        """
        Invoke Gemini API.
        
        Args:
            messages: List of messages
            temperature: Temperature setting
            
        Returns:
            LLMResponse object
        """
        llm = ChatGoogleGenerativeAI(
            model=self.gemini_model,
            temperature=temperature,
            google_api_key=settings.gemini_api_key
        )
        
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Estimate tokens (Gemini doesn't always provide usage info)
        prompt_tokens = self._estimate_tokens_for_messages(messages)
        completion_tokens = self._estimate_tokens_for_messages([HumanMessage(content=content)])
        
        # Calculate cost
        cost = cost_calculator.calculate_cost(
            model=self.gemini_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        return LLMResponse(
            content=content,
            provider="gemini",
            model=self.gemini_model,
            fallback_used=False,
            tokens=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            ),
            estimated_cost_usd=cost
        )
    
    @traceable(name="azure_openai_call", run_type="llm")
    async def _invoke_azure(
        self,
        messages: List[BaseMessage],
        temperature: float
    ) -> LLMResponse:
        """
        Invoke Azure OpenAI API.
        
        Args:
            messages: List of messages
            temperature: Temperature setting
            
        Returns:
            LLMResponse object
        """
        if not self.azure_client:
            raise Exception("Azure OpenAI is not configured")
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)
        
        # Call Azure OpenAI
        response = self.azure_client.chat.completions.create(
            model=self.azure_model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        
        # Get token usage from response
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        # Calculate cost
        cost = cost_calculator.calculate_cost(
            model="gpt-4o",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        return LLMResponse(
            content=content,
            provider="azure_openai",
            model=self.azure_model,
            fallback_used=False,
            tokens=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            ),
            estimated_cost_usd=cost
        )
    
    @traceable(name="grok_call", run_type="llm")
    async def _invoke_grok(
        self,
        messages: List[BaseMessage],
        temperature: float
    ) -> LLMResponse:
        """
        Invoke Grok API.
        
        Args:
            messages: List of messages
            temperature: Temperature setting
            
        Returns:
            LLMResponse object
        """
        if not self.grok_client:
            raise Exception("Grok is not configured")
        
        # Convert messages to OpenAI format (Grok uses OpenAI-compatible API)
        openai_messages = self._convert_messages_to_openai_format(messages)
        
        # Call Grok API
        response = self.grok_client.chat.completions.create(
            model=self.grok_model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        
        # Get token usage from response
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        # Calculate cost
        cost = cost_calculator.calculate_cost(
            model=self.grok_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        return LLMResponse(
            content=content,
            provider="grok",
            model=self.grok_model,
            fallback_used=False,
            tokens=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            ),
            estimated_cost_usd=cost
        )
    
    @traceable(
        name="llm_invoke",
        run_type="llm",
        tags=["llm", "multi-provider"]
    )
    async def invoke(
        self,
        messages: List[BaseMessage],
        temperature: float,
        operation: str = "general",
        session_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Invoke LLM with automatic fallback.
        
        Uses the preferred provider determined at startup. If the primary provider
        encounters rate limits or errors at runtime, automatically falls back through
        the available providers in order: Grok → Gemini → Azure OpenAI.
        
        Args:
            messages: List of LangChain messages
            temperature: Temperature setting (0.0 to 1.0)
            operation: Operation type for cost tracking
            session_id: Optional session ID for cost tracking
            
        Returns:
            LLMResponse with content and metadata
        """
        logger.info("llm_invoke_start", operation=operation, temperature=temperature)
        
        # Import health checker
        try:
            from app.services.llm_health_checker import llm_health_checker
            preferred_provider = llm_health_checker.get_preferred_provider() if llm_health_checker.health_check_completed else "grok"
        except Exception:
            # Fallback to default behavior if health checker not available
            preferred_provider = "grok"
        
        # If Grok was determined as preferred at startup, use it directly
        if preferred_provider == "grok":
            logger.info("using_grok_as_primary", reason="startup_health_check")
            try:
                response = await self._invoke_grok(messages, temperature)
                logger.info(
                    "llm_invoke_success",
                    provider="grok",
                    operation=operation,
                    tokens=response.tokens.total_tokens,
                    cost=response.estimated_cost_usd
                )
                await self._save_cost_data(response, operation, session_id)
                return response
            except Exception as grok_error:
                logger.error("grok_primary_failed", error=str(grok_error), operation=operation)
                
                # Try Gemini as fallback
                try:
                    response = await self._invoke_gemini(messages, temperature)
                    response.fallback_used = True
                    response.fallback_reason = f"Grok failed: {str(grok_error)}"
                    
                    logger.info(
                        "llm_gemini_fallback_success",
                        provider="gemini",
                        operation=operation,
                        tokens=response.tokens.total_tokens,
                        cost=response.estimated_cost_usd
                    )
                    
                    await self._save_cost_data(response, operation, session_id)
                    return response
                    
                except Exception as gemini_error:
                    logger.error("gemini_fallback_failed", error=str(gemini_error), operation=operation)
                    
                    # Try Azure as final fallback
                    if self.azure_client:
                        try:
                            response = await self._invoke_azure(messages, temperature)
                            response.fallback_used = True
                            response.fallback_reason = (
                                f"Grok failed: {str(grok_error)}, "
                                f"Gemini failed: {str(gemini_error)}"
                            )
                            
                            logger.info(
                                "llm_azure_fallback_success",
                                provider="azure_openai",
                                operation=operation,
                                tokens=response.tokens.total_tokens,
                                cost=response.estimated_cost_usd
                            )
                            
                            await self._save_cost_data(response, operation, session_id)
                            return response
                            
                        except Exception as azure_error:
                            logger.error(
                                "all_llm_providers_failed",
                                grok_error=str(grok_error),
                                gemini_error=str(gemini_error),
                                azure_error=str(azure_error),
                                operation=operation
                            )
                            raise Exception(
                                f"All LLM providers failed. "
                                f"Grok: {str(grok_error)}, "
                                f"Gemini: {str(gemini_error)}, "
                                f"Azure: {str(azure_error)}"
                            )
                    else:
                        raise Exception(
                            f"Grok and Gemini failed, Azure not configured. "
                            f"Grok: {str(grok_error)}, "
                            f"Gemini: {str(gemini_error)}"
                        )
        
        # If Gemini was determined as preferred at startup, use it directly
        if preferred_provider == "gemini":
            logger.info("using_gemini_as_primary", reason="startup_health_check")
            try:
                response = await self._invoke_gemini(messages, temperature)
                logger.info(
                    "llm_invoke_success",
                    provider="gemini",
                    operation=operation,
                    tokens=response.tokens.total_tokens,
                    cost=response.estimated_cost_usd
                )
                await self._save_cost_data(response, operation, session_id)
                return response
            except Exception as gemini_error:
                logger.error("gemini_primary_failed", error=str(gemini_error), operation=operation)
                
                # Try Azure as fallback
                if self.azure_client:
                    try:
                        response = await self._invoke_azure(messages, temperature)
                        response.fallback_used = True
                        response.fallback_reason = f"Gemini failed: {str(gemini_error)}"
                        
                        logger.info(
                            "llm_azure_fallback_success",
                            provider="azure_openai",
                            operation=operation,
                            tokens=response.tokens.total_tokens,
                            cost=response.estimated_cost_usd
                        )
                        
                        await self._save_cost_data(response, operation, session_id)
                        return response
                        
                    except Exception as azure_error:
                        logger.error(
                            "all_llm_providers_failed",
                            gemini_error=str(gemini_error),
                            azure_error=str(azure_error),
                            operation=operation
                        )
                        raise Exception(
                            f"Both Gemini and Azure failed. "
                            f"Gemini: {str(gemini_error)}, "
                            f"Azure: {str(azure_error)}"
                        )
                else:
                    raise
        
        # If Azure was determined as preferred at startup, use it directly
        if preferred_provider == "azure":
            logger.info("using_azure_as_primary", reason="startup_health_check")
            try:
                response = await self._invoke_azure(messages, temperature)
                logger.info(
                    "llm_invoke_success",
                    provider="azure_openai",
                    operation=operation,
                    tokens=response.tokens.total_tokens,
                    cost=response.estimated_cost_usd
                )
                await self._save_cost_data(response, operation, session_id)
                return response
            except Exception as azure_error:
                logger.error("azure_primary_failed", error=str(azure_error), operation=operation)
                raise
        
        # Fallback default behavior (should not reach here if health check completed)
        try:
            response = await self._invoke_grok(messages, temperature)
            
            logger.info(
                "llm_invoke_success",
                provider="grok",
                operation=operation,
                tokens=response.tokens.total_tokens,
                cost=response.estimated_cost_usd
            )
            
            await self._save_cost_data(response, operation, session_id)
            
            return response
            
        except Exception as grok_error:
            logger.error("grok_default_failed", error=str(grok_error), operation=operation)
            
            # Try Gemini fallback
            try:
                response = await self._invoke_gemini(messages, temperature)
                response.fallback_used = True
                response.fallback_reason = f"Grok failed: {str(grok_error)}"
                
                logger.info(
                    "llm_fallback_success",
                    provider="gemini",
                    operation=operation,
                    tokens=response.tokens.total_tokens,
                    cost=response.estimated_cost_usd
                )
                
                await self._save_cost_data(response, operation, session_id)
                
                return response
                
            except Exception as gemini_error:
                logger.error(
                    "gemini_fallback_failed",
                    grok_error=str(grok_error),
                    gemini_error=str(gemini_error),
                    operation=operation
                )
                
                # Try Azure as final fallback
                if self.azure_client:
                    try:
                        response = await self._invoke_azure(messages, temperature)
                        response.fallback_used = True
                        response.fallback_reason = (
                            f"Grok failed: {str(grok_error)}, "
                            f"Gemini failed: {str(gemini_error)}"
                        )
                        
                        logger.info(
                            "llm_final_fallback_success",
                            provider="azure_openai",
                            operation=operation,
                            tokens=response.tokens.total_tokens,
                            cost=response.estimated_cost_usd
                        )
                        
                        await self._save_cost_data(response, operation, session_id)
                        
                        return response
                        
                    except Exception as azure_error:
                        logger.error(
                            "all_llm_providers_failed",
                            grok_error=str(grok_error),
                            gemini_error=str(gemini_error),
                            azure_error=str(azure_error),
                            operation=operation
                        )
                        raise Exception(
                            f"All LLM providers failed. "
                            f"Grok: {str(grok_error)}, "
                            f"Gemini: {str(gemini_error)}, "
                            f"Azure: {str(azure_error)}"
                        )
                else:
                    raise Exception(
                        f"Grok and Gemini failed, Azure not configured. "
                        f"Grok: {str(grok_error)}, "
                        f"Gemini: {str(gemini_error)}"
                    )
    
    async def _save_cost_data(
        self,
        response: LLMResponse,
        operation: str,
        session_id: Optional[str]
    ):
        """
        Save cost tracking data to MongoDB.
        
        Args:
            response: LLM response with cost data
            operation: Operation type
            session_id: Optional session ID
        """
        try:
            collection = MongoDB.get_collection(settings.cost_collection_name)
            
            cost_record = {
                "timestamp": datetime.now(timezone.utc),
                "session_id": session_id,
                "provider": response.provider,
                "model": response.model,
                "operation": operation,
                "prompt_tokens": response.tokens.prompt_tokens,
                "completion_tokens": response.tokens.completion_tokens,
                "total_tokens": response.tokens.total_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
                "fallback_used": response.fallback_used,
                "fallback_reason": response.fallback_reason
            }
            
            await collection.insert_one(cost_record)
            
            logger.debug("cost_data_saved", operation=operation, cost=response.estimated_cost_usd)
            
        except Exception as e:
            # Don't fail the request if cost tracking fails
            logger.error("cost_tracking_error", error=str(e), operation=operation)


# Global instance
llm_service = LLMService()
