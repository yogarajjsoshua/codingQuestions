import structlog
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from app.models.graph_state import CountryInfoState
from app.agent.prompts import ANSWER_SYNTHESIS_SYSTEM_PROMPT, create_answer_synthesis_prompt
from app.services.llm_service import llm_service
from app.agent.utils.error_handler import generate_human_friendly_error

logger = structlog.get_logger()


@traceable(
    name="answer_synthesis",
    run_type="chain",
    tags=["agent", "synthesis", "nlg"]
)
async def answer_synthesis_node(state: CountryInfoState) -> CountryInfoState:
    """
    Answer Synthesis Node: Convert extracted data into a natural language answer.
    """
    # Initialize cost tracking if not present
    if "llm_total_cost" not in state or state["llm_total_cost"] is None:
        state["llm_total_cost"] = 0.0
    if "llm_providers_used" not in state or state["llm_providers_used"] is None:
        state["llm_providers_used"] = []
    
    # If out of scope, final_answer is already set
    if state.get("out_of_scope", False):
        return state
    
    if state.get("error"):
        # Try to generate human-friendly error response
        error_message = state["error"]
        error_type = state.get("error_type", "general")
        question = state["question"]
        session_id = state.get("session_id")
        
        logger.info("generating_human_friendly_error", error_type=error_type)
        
        try:
            human_error = await generate_human_friendly_error(
                error_message=error_message,
                question=question,
                session_id=session_id,
                error_type=error_type
            )
            state["final_answer"] = human_error
            
            # Log the LLM usage for error humanization if it was successful
            logger.info("error_humanization_applied", error_type=error_type)
        except Exception as e:
            # Ultimate fallback if everything fails
            logger.error("error_humanization_catastrophic_failure", error=str(e))
            state["final_answer"] = "Sorry, I am not able to assist you with that query."
        
        return state
    
    question = state["question"]
    extracted_data = state.get("extracted_data", {})
    session_id = state.get("session_id")
    
    if not extracted_data:
        logger.warning("no_data_extracted")
        state["final_answer"] = f"I couldn't find information about {state.get('country_name', 'the requested country')}."
        return state
    
    logger.info("answer_synthesis_start", fields=list(extracted_data.keys()))
    
    try:
        prompt = create_answer_synthesis_prompt(question, extracted_data)
        
        messages = [
            SystemMessage(content=ANSWER_SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        # Use LLM service with fallback support
        llm_response = await llm_service.invoke(
            messages=messages,
            temperature=0.7,
            operation="answer_synthesis",
            session_id=session_id
        )
        
        state["final_answer"] = llm_response.content
        
        # Log provider and cost
        logger.info(
            "answer_synthesis_success",
            provider=llm_response.provider,
            fallback_used=llm_response.fallback_used,
            cost=llm_response.estimated_cost_usd
        )
        
        # Track cost in state
        state["llm_total_cost"] += llm_response.estimated_cost_usd
        if llm_response.provider not in state["llm_providers_used"]:
            state["llm_providers_used"].append(llm_response.provider)
        
    except Exception as e:
        logger.error("answer_synthesis_error", error=str(e))
        state["final_answer"] = f"I found the information but had trouble formatting the answer: {extracted_data}"
    
    return state
