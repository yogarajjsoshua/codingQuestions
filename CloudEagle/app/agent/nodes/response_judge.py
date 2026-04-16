"""Response Judge Node - Evaluates and improves out-of-scope responses."""
import json
import structlog
from langchain_core.messages import HumanMessage
from langsmith import traceable

from app.models.graph_state import CountryInfoState
from app.agent.prompts import JUDGE_EVALUATION_PROMPT
from app.services.llm_service import llm_service

logger = structlog.get_logger()


@traceable(
    name="response_judge",
    run_type="chain",
    tags=["agent", "judge", "quality"]
)
async def response_judge_node(state: CountryInfoState) -> CountryInfoState:
    """
    Response Judge Node: Evaluate out-of-scope responses for quality.
    
    This node only processes out-of-scope queries. It evaluates if the response is:
    - Polite and respectful
    - Clear about limitations
    - Natural and conversational
    - Not overly apologetic
    
    If the response is inadequate, it generates an improved version.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with potentially improved response
    """
    # Only judge out-of-scope responses
    if not state.get("out_of_scope", False):
        logger.debug("judge_skipped", reason="not_out_of_scope")
        return state
    
    # Skip if there's an error
    if state.get("error"):
        logger.debug("judge_skipped", reason="error_present")
        return state
    
    question = state["question"]
    current_response = state.get("final_answer", "")
    session_id = state.get("session_id")
    
    # Initialize cost tracking if not present
    if "llm_total_cost" not in state or state["llm_total_cost"] is None:
        state["llm_total_cost"] = 0.0
    if "llm_providers_used" not in state or state["llm_providers_used"] is None:
        state["llm_providers_used"] = []
    
    if not current_response:
        logger.warning("judge_skipped", reason="no_response_to_judge")
        return state
    
    logger.info("response_judge_start", question=question[:50])
    
    try:
        # Build judge prompt
        judge_prompt = JUDGE_EVALUATION_PROMPT.format(
            question=question,
            response=current_response
        )
        
        messages = [HumanMessage(content=judge_prompt)]
        
        # Use LLM service to evaluate
        llm_response = await llm_service.invoke(
            messages=messages,
            temperature=0,
            operation="response_judging",
            session_id=session_id
        )
        
        response_text = llm_response.content.strip()
        
        # Track cost
        state["llm_total_cost"] += llm_response.estimated_cost_usd
        if llm_response.provider not in state["llm_providers_used"]:
            state["llm_providers_used"].append(llm_response.provider)
        
        # Parse judge response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text
        
        judge_result = json.loads(json_str)
        
        is_adequate = judge_result.get("is_adequate", True)
        issues = judge_result.get("issues", [])
        improved_response = judge_result.get("improved_response")
        
        if not is_adequate and improved_response:
            logger.info(
                "response_improved_by_judge",
                issues=issues,
                original_response=current_response[:100],
                improved_response=improved_response[:100]
            )
            state["final_answer"] = improved_response
        else:
            logger.info("response_approved_by_judge", response=current_response[:100])
        
    except json.JSONDecodeError as e:
        logger.error("judge_json_parse_error", error=str(e), response=response_text[:200])
        # Keep original response if judge fails
    except Exception as e:
        logger.error("response_judge_error", error=str(e))
        # Keep original response if judge fails
    
    return state
