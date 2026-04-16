"""Token counting utilities for managing context window."""
import tiktoken
from typing import Optional
import structlog

logger = structlog.get_logger()


class TokenCounter:
    """Utility class for estimating token counts."""
    
    _encoding = None
    
    @classmethod
    def get_encoding(cls):
        """Get or create the tiktoken encoding."""
        if cls._encoding is None:
            try:
                # Use cl100k_base encoding (used by GPT-3.5/4 and similar to Gemini)
                cls._encoding = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning("tiktoken_encoding_error", error=str(e))
                # Fallback to gpt-3.5-turbo encoding
                cls._encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return cls._encoding
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        try:
            encoding = cls.get_encoding()
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning("token_estimation_error", error=str(e))
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    @classmethod
    def estimate_messages_tokens(cls, messages: list) -> int:
        """
        Estimate total tokens for a list of message dictionaries.
        
        Args:
            messages: List of message dicts with 'question' and 'answer' keys
            
        Returns:
            Total estimated token count
        """
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                for key in ['question', 'answer', 'final_answer']:
                    if key in msg:
                        total += cls.estimate_tokens(str(msg[key]))
            elif isinstance(msg, str):
                total += cls.estimate_tokens(msg)
        return total
    
    @classmethod
    def truncate_to_token_limit(cls, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within a token limit.
        
        Args:
            text: The text to truncate
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            Truncated text
        """
        if not text:
            return text
        
        try:
            encoding = cls.get_encoding()
            tokens = encoding.encode(text)
            
            if len(tokens) <= max_tokens:
                return text
            
            # Truncate and decode
            truncated_tokens = tokens[:max_tokens]
            return encoding.decode(truncated_tokens) + "..."
            
        except Exception as e:
            logger.warning("token_truncation_error", error=str(e))
            # Fallback: character-based truncation
            char_limit = max_tokens * 4
            return text[:char_limit] + "..."


def estimate_tokens(text: str) -> int:
    """Convenience function for token estimation."""
    return TokenCounter.estimate_tokens(text)


def should_summarize(total_tokens: int, max_tokens: int = 5000) -> bool:
    """
    Determine if conversation should be summarized based on token count.
    
    Args:
        total_tokens: Current total token count
        max_tokens: Maximum tokens before summarization
        
    Returns:
        True if summarization is needed
    """
    return total_tokens > max_tokens
