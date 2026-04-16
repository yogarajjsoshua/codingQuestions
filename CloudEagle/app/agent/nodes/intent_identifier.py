import json
import structlog
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from app.models.graph_state import CountryInfoState
from app.agent.prompts import INTENT_IDENTIFIER_SYSTEM_PROMPT, OUT_OF_SCOPE_RESPONSE_PROMPT
from app.services.llm_service import llm_service

logger = structlog.get_logger()


class IntentExtraction(BaseModel):
    """Schema for extracting intent from user questions."""
    country_name: str = Field(description="The name of the country the user is asking about")
    requested_fields: List[str] = Field(description="List of fields the user wants to know about the country")
    query_type: Literal["single_field", "multiple_fields", "general"] = Field(
        description="Type of query based on the number of fields requested"
    )


async def _generate_polite_out_of_scope_response(question: str, session_id: str) -> str:
    """
    Generate a polite, context-aware response for out-of-scope queries.
    
    Args:
        question: User's out-of-scope question
        session_id: Session ID for cost tracking
        
    Returns:
        Polite response string
    """
    try:
        prompt = OUT_OF_SCOPE_RESPONSE_PROMPT.format(question=question)
        messages = [HumanMessage(content=prompt)]
        
        llm_response = await llm_service.invoke(
            messages=messages,
            temperature=0.7,
            operation="out_of_scope_response",
            session_id=session_id
        )
        
        response = llm_response.content.strip()
        logger.info("out_of_scope_response_generated", question=question[:50])
        return response
        
    except Exception as e:
        logger.error("out_of_scope_response_generation_failed", error=str(e))
        # Fallback to a default polite message
        return "I specialize in providing information about countries, such as their populations, capitals, currencies, languages, and geography. Is there a country you'd like to learn about?"


@traceable(
    name="intent_identification",
    run_type="chain",
    tags=["agent", "intent", "nlu"]
)
async def intent_identifier_node(state: CountryInfoState) -> CountryInfoState:
    """
    Intent Identifier Node: Extract country name and requested fields from the user's question.
    
    Uses LLM to extract structured information via JSON parsing.
    Handles out-of-scope queries with dynamically generated polite responses.
    Now includes conversation context for continuity.
    """
    question = state["question"]
    context = state.get("conversation_context", "")
    session_id = state.get("session_id")
    
    # Initialize cost tracking
    if "llm_total_cost" not in state or state["llm_total_cost"] is None:
        state["llm_total_cost"] = 0.0
    if "llm_providers_used" not in state or state["llm_providers_used"] is None:
        state["llm_providers_used"] = []
    
    logger.info("intent_identifier_start", question=question, has_context=bool(context))
    
    try:
        # Build enhanced prompt with context
        context_section = ""
        if context:
            context_section = f"""
--- CONVERSATION CONTEXT ---
{context}

Use this context to better understand the user's current question. 
If they refer to "it", "that country", or use pronouns, use the context to resolve what they mean.
--- END CONTEXT ---

"""
        
        # Create a prompt that requests JSON output
        enhanced_prompt = f"""{INTENT_IDENTIFIER_SYSTEM_PROMPT}

{context_section}
You MUST respond with a valid JSON object with this exact structure:
{{
    "out_of_scope": true | false,
    "country_name": "the country name" (can be null if out_of_scope is true),
    "requested_fields": ["field1", "field2"] (can be empty array if out_of_scope is true),
    "query_type": "single_field" | "multiple_fields" | "general" (can be null if out_of_scope is true)
}}

User question: {question}

Respond ONLY with the JSON object, no other text."""
        
        messages = [HumanMessage(content=enhanced_prompt)]
        
        # Use LLM service with fallback support
        llm_response = await llm_service.invoke(
            messages=messages,
            temperature=0,
            operation="intent_identification",
            session_id=session_id
        )
        
        response_text = llm_response.content.strip()
        
        # Log provider and cost
        logger.info(
            "llm_usage",
            provider=llm_response.provider,
            fallback_used=llm_response.fallback_used,
            cost=llm_response.estimated_cost_usd
        )
        
        # Track cost in state
        state["llm_total_cost"] += llm_response.estimated_cost_usd
        if llm_response.provider not in state["llm_providers_used"]:
            state["llm_providers_used"].append(llm_response.provider)
        
        # Extract JSON from response (handle markdown code blocks if present)
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text
        
        # Parse JSON
        intent_data = json.loads(json_str)
        
        # Check if query is out of scope
        if intent_data.get("out_of_scope", False):
            state["out_of_scope"] = True
            state["country_name"] = None
            state["requested_fields"] = []
            state["query_type"] = None
            state["extracted_data"] = {}
            
            # Generate dynamic polite response
            polite_response = await _generate_polite_out_of_scope_response(question, session_id)
            state["final_answer"] = polite_response
            
            # Track additional cost
            logger.info("intent_out_of_scope", question=question)
        else:
            # Validate and assign
            state["out_of_scope"] = False
            state["country_name"] = intent_data.get("country_name")
            state["requested_fields"] = intent_data.get("requested_fields", [])
            state["query_type"] = intent_data.get("query_type")
            
            logger.info(
                "intent_extracted",
                country=state["country_name"],
                fields=state["requested_fields"],
                query_type=state["query_type"]
            )
        
    except Exception as e:
        import traceback
        error_message = str(e) if str(e) else repr(e)
        error_traceback = traceback.format_exc()
        logger.error(
            "intent_identifier_error", 
            error=error_message, 
            error_type=type(e).__name__,
            traceback=error_traceback
        )
        state["error"] = f"Error extracting intent: {error_message}"
        state["error_type"] = "intent_extraction"
    
    return state
