import structlog
from langchain_core.messages import HumanMessage
from app.agent.prompts import ERROR_HUMANIZATION_PROMPT
from app.services.llm_service import llm_service

logger = structlog.get_logger()


async def generate_human_friendly_error(
    error_message: str,
    question: str,
    session_id: str = None,
    error_type: str = "general"
) -> str:
    """
    Generate a human-friendly error message using LLM.
    Falls back to generic message if LLM fails.
    
    Args:
        error_message: The technical error message
        question: The user's original question
        session_id: Session ID for cost tracking
        error_type: Type of error (e.g., "missing_country", "api_error", "general")
        
    Returns:
        Human-friendly error message
    """
    try:
        prompt = ERROR_HUMANIZATION_PROMPT.format(
            error_type=error_type,
            error_message=error_message,
            question=question
        )
        
        messages = [HumanMessage(content=prompt)]
        
        llm_response = await llm_service.invoke(
            messages=messages,
            temperature=0.7,
            operation="error_humanization",
            session_id=session_id
        )
        
        response = llm_response.content.strip()
        logger.info("error_humanization_success", original_error=error_message[:50])
        return response
        
    except Exception as e:
        logger.error("error_humanization_failed", error=str(e))
        # Fallback to generic message
        return "Sorry, I am not able to assist you with that query. Could you please try rephrasing your question?"
