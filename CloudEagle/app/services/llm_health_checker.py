"""LLM Health Checker Service for startup validation."""
import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from openai import AzureOpenAI
from langsmith import traceable

from app.config import settings

logger = structlog.get_logger()


class LLMHealthChecker:
    """Check LLM provider availability at startup."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.gemini_available = False
        self.azure_available = False
        self.grok_available = False
        self.preferred_provider = None
        self.health_check_completed = False
    
    async def check_providers_health(self):
        """
        Check all LLM providers at startup.
        
        Sets the preferred provider based on availability:
        1. Grok (if available)
        2. Gemini (if Grok unavailable but Gemini configured)
        3. Azure OpenAI (if both Grok and Gemini unavailable but Azure configured)
        
        Raises:
            Exception: If no providers are available
        """
        logger.info("llm_health_check_started")
        
        # Check Grok
        self.grok_available = await self._test_grok()
        
        # Check Gemini
        self.gemini_available = await self._test_gemini()
        
        # Check Azure OpenAI
        self.azure_available = await self._test_azure()
        
        # Determine preferred provider (priority: Grok > Gemini > Azure)
        if self.grok_available:
            self.preferred_provider = "grok"
            logger.info(
                "llm_health_check_complete", 
                preferred="grok", 
                gemini_fallback_available=self.gemini_available,
                azure_fallback_available=self.azure_available
            )
        elif self.gemini_available:
            self.preferred_provider = "gemini"
            logger.warning(
                "llm_health_check_complete", 
                preferred="gemini", 
                reason="grok_unavailable",
                azure_fallback_available=self.azure_available
            )
        elif self.azure_available:
            self.preferred_provider = "azure"
            logger.warning(
                "llm_health_check_complete", 
                preferred="azure", 
                reason="grok_and_gemini_unavailable"
            )
        else:
            error_msg = "No LLM providers available. Please check your API keys and configuration."
            logger.error("llm_health_check_failed", error=error_msg)
            raise Exception(error_msg)
        
        self.health_check_completed = True
    
    async def test_langsmith_tracing(self) -> bool:
        """
        Test LangSmith tracing with available LLM providers.
        
        Makes a traced call to verify that LangSmith tracing is working.
        Tests the preferred provider first, then fallback providers if the preferred fails.
        
        Returns:
            True if tracing test succeeded with any provider, False otherwise
        """
        if not self.health_check_completed:
            logger.warning("langsmith_test_skipped", reason="health_check_not_completed")
            return False
        
        if not settings.langchain_tracing_v2:
            logger.info("langsmith_tracing_disabled", reason="langchain_tracing_v2_is_false")
            return False
        
        if not settings.langchain_api_key:
            logger.warning("langsmith_not_configured", reason="missing_api_key")
            return False
        
        logger.info(
            "langsmith_tracing_test_started", 
            provider=self.preferred_provider,
            project=settings.langchain_project or "default"
        )
        
        # Create ordered list of providers to try
        providers_to_test = []
        
        # Start with preferred provider
        if self.preferred_provider == "grok" and self.grok_available:
            providers_to_test.append(("grok", self._test_grok_tracing))
        elif self.preferred_provider == "gemini" and self.gemini_available:
            providers_to_test.append(("gemini", self._test_gemini_tracing))
        elif self.preferred_provider == "azure" and self.azure_available:
            providers_to_test.append(("azure", self._test_azure_tracing))
        
        # Add fallback providers (priority: Grok > Gemini > Azure)
        if self.grok_available and ("grok", self._test_grok_tracing) not in providers_to_test:
            providers_to_test.append(("grok", self._test_grok_tracing))
        if self.gemini_available and ("gemini", self._test_gemini_tracing) not in providers_to_test:
            providers_to_test.append(("gemini", self._test_gemini_tracing))
        if self.azure_available and ("azure", self._test_azure_tracing) not in providers_to_test:
            providers_to_test.append(("azure", self._test_azure_tracing))
        
        # Try each provider until one succeeds
        for provider_name, test_func in providers_to_test:
            try:
                logger.info(
                    "langsmith_testing_provider",
                    provider=provider_name,
                    is_preferred=provider_name == self.preferred_provider
                )
                
                success = await test_func()
                
                if success:
                    logger.info(
                        "langsmith_tracing_verified",
                        status="✓ WORKING",
                        provider=provider_name,
                        preferred_provider=self.preferred_provider,
                        project=settings.langchain_project or "default",
                        message=f"LangSmith tracing is active with {provider_name} and will populate your dashboard"
                    )
                    return True
                else:
                    logger.warning(
                        "langsmith_provider_test_failed",
                        provider=provider_name,
                        message=f"LangSmith tracing test failed with {provider_name}, trying next provider..."
                    )
                    
            except Exception as e:
                logger.warning(
                    "langsmith_provider_test_error",
                    provider=provider_name,
                    error=str(e),
                    message=f"Error testing {provider_name}, trying next provider..."
                )
        
        # All providers failed
        logger.warning(
            "langsmith_tracing_test_failed",
            status="✗ FAILED",
            preferred_provider=self.preferred_provider,
            tested_providers=[p[0] for p in providers_to_test],
            message="LangSmith tracing test failed with all available providers - check your configuration"
        )
        return False
    
    @traceable(
        name="startup_gemini_tracing_test",
        run_type="llm",
        tags=["startup", "health-check", "langsmith-test"]
    )
    async def _test_gemini_tracing(self) -> bool:
        """Test Gemini with LangSmith tracing."""
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=settings.gemini_api_key,
                timeout=10
            )
            
            test_message = [HumanMessage(content="Hello, this is a LangSmith tracing test at startup.")]
            response = await llm.ainvoke(test_message)
            
            return bool(response and response.content)
        except Exception as e:
            logger.error("gemini_tracing_test_failed", error=str(e))
            return False
    
    @traceable(
        name="startup_azure_tracing_test",
        run_type="llm",
        tags=["startup", "health-check", "langsmith-test"]
    )
    async def _test_azure_tracing(self) -> bool:
        """Test Azure OpenAI with LangSmith tracing."""
        try:
            client = AzureOpenAI(
                api_key=settings.openai_api_4_key,
                api_version=settings.openai_api_4_version,
                azure_endpoint=settings.openai_4_base_url,
                timeout=10
            )
            
            response = client.chat.completions.create(
                model=settings.open_api_4_engine,
                messages=[{"role": "user", "content": "Hello, this is a LangSmith tracing test at startup."}],
                max_tokens=10
            )
            
            return bool(response and response.choices)
        except Exception as e:
            logger.error("azure_tracing_test_failed", error=str(e))
            return False
    
    @traceable(
        name="startup_grok_tracing_test",
        run_type="llm",
        tags=["startup", "health-check", "langsmith-test"]
    )
    async def _test_grok_tracing(self) -> bool:
        """Test Grok with LangSmith tracing."""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=settings.grok_api_key,
                base_url=settings.grok_base_url,
                timeout=10
            )
            
            response = client.chat.completions.create(
                model=settings.grok_model,
                messages=[{"role": "user", "content": "Hello, this is a LangSmith tracing test at startup."}],
                max_tokens=10
            )
            
            return bool(response and response.choices)
        except Exception as e:
            logger.error("grok_tracing_test_failed", error=str(e))
            return False
    
    async def _test_gemini(self) -> bool:
        """
        Test Gemini API availability with a minimal request.
        
        Returns:
            True if Gemini is available, False otherwise
        """
        if not settings.gemini_api_key:
            logger.info("gemini_not_configured")
            return False
        
        try:
            logger.info("testing_gemini_availability")
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=settings.gemini_api_key,
                timeout=10
            )
            
            # Send a minimal test message
            test_message = [HumanMessage(content="test")]
            response = await llm.ainvoke(test_message)
            
            if response and response.content:
                logger.info("gemini_available", status="healthy")
                return True
            else:
                logger.warning("gemini_test_failed", reason="no_response")
                return False
                
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
                logger.warning("gemini_rate_limited", error=str(e))
            else:
                logger.warning("gemini_unavailable", error=str(e))
            return False
    
    async def _test_azure(self) -> bool:
        """
        Test Azure OpenAI API availability.
        
        Returns:
            True if Azure is available, False otherwise
        """
        # Check if Azure is configured
        if not all([
            settings.openai_api_4_key,
            settings.openai_4_base_url,
            settings.openai_api_4_version,
            settings.open_api_4_engine
        ]):
            logger.info("azure_not_configured")
            return False
        
        try:
            logger.info("testing_azure_availability")
            client = AzureOpenAI(
                api_key=settings.openai_api_4_key,
                api_version=settings.openai_api_4_version,
                azure_endpoint=settings.openai_4_base_url,
                timeout=10
            )
            
            # Send a minimal test request
            response = client.chat.completions.create(
                model=settings.open_api_4_engine,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                logger.info("azure_available", status="healthy")
                return True
            else:
                logger.warning("azure_test_failed", reason="no_response")
                return False
                
        except Exception as e:
            logger.warning("azure_unavailable", error=str(e))
            return False
    
    async def _test_grok(self) -> bool:
        """
        Test Grok API availability.
        
        Returns:
            True if Grok is available, False otherwise
        """
        # Check if Grok is configured
        if not all([
            settings.grok_api_key,
            settings.grok_base_url,
            settings.grok_model
        ]):
            logger.info("grok_not_configured")
            return False
        
        try:
            logger.info("testing_grok_availability")
            from openai import OpenAI
            
            client = OpenAI(
                api_key=settings.grok_api_key,
                base_url=settings.grok_base_url,
                timeout=10
            )
            
            # Send a minimal test request
            response = client.chat.completions.create(
                model=settings.grok_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                logger.info("grok_available", status="healthy")
                return True
            else:
                logger.warning("grok_test_failed", reason="no_response")
                return False
                
        except Exception as e:
            logger.warning("grok_unavailable", error=str(e))
            return False
    
    def get_preferred_provider(self) -> str:
        """
        Get the preferred LLM provider.
        
        Returns:
            "grok", "gemini", or "azure"
        
        Raises:
            RuntimeError: If health check hasn't been completed
        """
        if not self.health_check_completed:
            raise RuntimeError("Health check not completed. Call check_providers_health() first.")
        return self.preferred_provider
    
    def is_provider_available(self, provider: str) -> bool:
        """
        Check if a specific provider is available.
        
        Args:
            provider: "gemini", "azure", or "grok"
            
        Returns:
            True if the provider is available
        """
        if provider == "gemini":
            return self.gemini_available
        elif provider in ["azure", "azure_openai"]:
            return self.azure_available
        elif provider == "grok":
            return self.grok_available
        return False


# Global instance
llm_health_checker = LLMHealthChecker()
