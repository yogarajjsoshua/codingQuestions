from typing import TypedDict, List, Optional, Dict, Any


class CountryInfoState(TypedDict):
    """State that flows through the LangGraph workflow."""
    
    question: str
    country_name: Optional[str]
    requested_fields: Optional[List[str]]
    query_type: Optional[str]
    api_response: Optional[Dict[str, Any]]
    extracted_data: Optional[Dict[str, Any]]
    final_answer: Optional[str]
    error: Optional[str]
    error_type: Optional[str]
    out_of_scope: Optional[bool]
    
    session_id: Optional[str]
    message_id: Optional[str]
    conversation_context: Optional[str]
    previous_countries: Optional[List[str]]
    
    llm_total_cost: Optional[float]
    llm_providers_used: Optional[List[str]]
