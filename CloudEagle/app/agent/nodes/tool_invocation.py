import structlog
from langsmith import traceable
from app.models.graph_state import CountryInfoState
from app.tools.rest_countries import rest_countries_client, CountryNotFoundError, RestCountriesAPIError
from app.context_manager import context_manager

logger = structlog.get_logger()


@traceable(
    name="tool_invocation",
    run_type="tool",
    tags=["agent", "api", "rest-countries"]
)
async def tool_invocation_node(state: CountryInfoState) -> CountryInfoState:
    """
    Tool Invocation Node: Call the REST Countries API and extract requested fields.
    Now with session-based caching to avoid redundant API calls.
    """
    # Skip if out of scope or has error
    if state.get("out_of_scope", False) or state.get("error"):
        return state
    
    country_name = state.get("country_name")
    requested_fields = state.get("requested_fields", [])
    session_id = state.get("session_id")
    
    if not country_name:
        logger.error("missing_country_name")
        state["error"] = "Country name not identified"
        state["error_type"] = "missing_country"
        return state
    
    logger.info("tool_invocation_start", country=country_name, fields=requested_fields)
    
    try:
        # First, check if this country data exists in the session cache
        country_data = None
        if session_id:
            country_data = await context_manager.get_country_from_session(session_id, country_name)
        
        # If not in session cache, fetch from API
        if country_data is None:
            logger.info("fetching_country_from_api", country=country_name)
            country_data = await rest_countries_client.get_country_by_name(country_name)
            
            # Save to session cache for future queries in this session
            if session_id:
                await context_manager.save_country_to_session(session_id, country_name, country_data)
        else:
            logger.info("using_session_cached_country", country=country_name, session_id=session_id)
        
        state["api_response"] = country_data
        
        extracted_data = rest_countries_client.extract_fields(country_data, requested_fields)
        state["extracted_data"] = extracted_data
        
        logger.info(
            "tool_invocation_success",
            country=country_name,
            fields_extracted=list(extracted_data.keys())
        )
        
    except CountryNotFoundError as e:
        logger.warning("country_not_found", country=country_name)
        state["error"] = str(e)
        state["error_type"] = "country_not_found"
    except RestCountriesAPIError as e:
        logger.error("api_error", country=country_name, error=str(e))
        state["error"] = str(e)
        state["error_type"] = "api_error"
    except Exception as e:
        logger.error("unexpected_error", country=country_name, error=str(e))
        state["error"] = f"Unexpected error while fetching data: {str(e)}"
        state["error_type"] = "unexpected"
    
    return state
