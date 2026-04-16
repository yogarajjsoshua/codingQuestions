"""Cost calculation utilities for LLM usage tracking."""
from typing import Dict, Literal
import structlog

logger = structlog.get_logger()

# Pricing per 1M tokens (as of 2026)
PRICING = {
    "gemini-2.5-flash": {
        "input": 0.075,   # $0.075 per 1M input tokens
        "output": 0.30,    # $0.30 per 1M output tokens
    },
    "gpt-4o": {
        "input": 2.50,     # $2.50 per 1M input tokens
        "output": 10.00,   # $10.00 per 1M output tokens
    },
    "grok-beta": {
        "input": 5.00,     # $5.00 per 1M input tokens (estimated)
        "output": 15.00,   # $15.00 per 1M output tokens (estimated)
    },
}


class CostCalculator:
    """Calculate costs for LLM API usage."""
    
    @staticmethod
    def calculate_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Calculate the cost of an LLM API call.
        
        Args:
            model: Model name (e.g., "gemini-2.5-flash", "gpt-4o")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        try:
            if model not in PRICING:
                logger.warning("unknown_model_for_pricing", model=model)
                return 0.0
            
            pricing = PRICING[model]
            
            # Calculate costs
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]
            total_cost = input_cost + output_cost
            
            logger.debug(
                "cost_calculated",
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost
            )
            
            return round(total_cost, 6)  # Round to 6 decimal places
            
        except Exception as e:
            logger.error("cost_calculation_error", error=str(e), model=model)
            return 0.0
    
    @staticmethod
    def get_model_pricing(model: str) -> Dict[str, float]:
        """
        Get pricing information for a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with input and output pricing
        """
        return PRICING.get(model, {"input": 0.0, "output": 0.0})
    
    @staticmethod
    def get_all_pricing() -> Dict[str, Dict[str, float]]:
        """
        Get pricing information for all models.
        
        Returns:
            Dictionary of all model pricing
        """
        return PRICING.copy()


# Global instance
cost_calculator = CostCalculator()
