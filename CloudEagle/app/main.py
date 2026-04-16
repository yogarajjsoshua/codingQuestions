import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    ErrorResponse,
    SupportedFieldsResponse
)
from app.agent.graph import country_info_graph
from app.config import settings
from app.database import MongoDB
from app.context_manager import context_manager

os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
if settings.langchain_api_key:
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
if settings.langchain_project:
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
if settings.langchain_endpoint:
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="1.0.0")
    
    # Connect to MongoDB
    try:
        await MongoDB.connect()
        logger.info("mongodb_initialized")
    except Exception as e:
        logger.error("mongodb_initialization_failed", error=str(e))
        raise
    
    # Check LLM provider health at startup
    try:
        from app.services.llm_health_checker import llm_health_checker
        await llm_health_checker.check_providers_health()
        logger.info(
            "llm_providers_initialized",
            preferred=llm_health_checker.preferred_provider,
            gemini_available=llm_health_checker.gemini_available,
            azure_available=llm_health_checker.azure_available
        )
        
        # Test LangSmith tracing with the chosen provider
        tracing_status = await llm_health_checker.test_langsmith_tracing()
        if tracing_status:
            logger.info(
                "langsmith_integration_ready",
                status="operational",
                message="✓ LangSmith tracing is configured and working with the chosen LLM provider"
            )
        else:
            logger.warning(
                "langsmith_integration_warning",
                status="not_operational",
                message="⚠ LangSmith tracing test failed - traces may not appear in dashboard"
            )
    except Exception as e:
        logger.error("llm_health_check_failed", error=str(e))
        raise
    
    yield
    
    # Close MongoDB connection
    await MongoDB.close()
    logger.info("application_shutdown")


app = FastAPI(
    title="Country Information AI Agent",
    description="AI-powered API for answering questions about countries using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "country-info-agent"}


@app.get("/api/v1/health/providers")
async def check_providers():
    """
    Check LLM provider configuration and availability.
    
    Returns information about which providers are configured and their status.
    """
    gemini_configured = bool(settings.gemini_api_key)
    azure_configured = all([
        settings.openai_api_4_key,
        settings.openai_4_base_url,
        settings.openai_api_4_version,
        settings.open_api_4_engine
    ])
    
    return {
        "gemini": {
            "configured": gemini_configured,
            "status": "available" if gemini_configured else "not_configured",
            "is_default": True
        },
        "azure_openai": {
            "configured": azure_configured,
            "status": "available" if azure_configured else "not_configured",
            "is_fallback": True,
            "model": settings.open_api_4_engine if azure_configured else None
        }
    }


@app.get("/api/v1/analytics/costs")
async def get_cost_analytics(
    session_id: Optional[str] = None,
    hours: Optional[int] = 24
):
    """
    Get cost analytics for LLM usage.
    
    Args:
        session_id: Optional session ID to filter by
        hours: Number of hours to look back (default: 24)
    
    Returns:
        Cost analytics including total costs, provider breakdown, and operation breakdown
    """
    try:
        collection = MongoDB.get_collection(settings.cost_collection_name)
        
        # Build query
        query = {}
        if session_id:
            query["session_id"] = session_id
        
        # Time filter
        time_filter = datetime.utcnow() - timedelta(hours=hours)
        query["timestamp"] = {"$gte": time_filter}
        
        # Aggregate costs
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": None,
                    "total_cost": {"$sum": "$estimated_cost_usd"},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "total_requests": {"$sum": 1},
                    "gemini_requests": {
                        "$sum": {"$cond": [{"$eq": ["$provider", "gemini"]}, 1, 0]}
                    },
                    "azure_requests": {
                        "$sum": {"$cond": [{"$eq": ["$provider", "azure_openai"]}, 1, 0]}
                    },
                    "fallback_count": {
                        "$sum": {"$cond": ["$fallback_used", 1, 0]}
                    },
                    "gemini_cost": {
                        "$sum": {"$cond": [{"$eq": ["$provider", "gemini"]}, "$estimated_cost_usd", 0]}
                    },
                    "azure_cost": {
                        "$sum": {"$cond": [{"$eq": ["$provider", "azure_openai"]}, "$estimated_cost_usd", 0]}
                    }
                }
            }
        ]
        
        result = await collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            data = result[0]
            return {
                "period_hours": hours,
                "session_id": session_id,
                "total_cost_usd": round(data["total_cost"], 6),
                "total_tokens": data["total_tokens"],
                "total_requests": data["total_requests"],
                "provider_breakdown": {
                    "gemini": {
                        "requests": data["gemini_requests"],
                        "cost_usd": round(data["gemini_cost"], 6)
                    },
                    "azure_openai": {
                        "requests": data["azure_requests"],
                        "cost_usd": round(data["azure_cost"], 6)
                    }
                },
                "fallback_stats": {
                    "fallback_count": data["fallback_count"],
                    "fallback_rate": round(data["fallback_count"] / data["total_requests"] * 100, 2) if data["total_requests"] > 0 else 0
                }
            }
        else:
            return {
                "period_hours": hours,
                "session_id": session_id,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "total_requests": 0,
                "provider_breakdown": {
                    "gemini": {"requests": 0, "cost_usd": 0.0},
                    "azure_openai": {"requests": 0, "cost_usd": 0.0}
                },
                "fallback_stats": {
                    "fallback_count": 0,
                    "fallback_rate": 0.0
                }
            }
    except Exception as e:
        logger.error("cost_analytics_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error retrieving cost analytics: {str(e)}")


@app.get("/api/v1/analytics/sessions/{session_id}")
async def get_session_analytics(session_id: str):
    """
    Get analytics for a specific session.
    
    Args:
        session_id: Session ID to get analytics for
        
    Returns:
        Session analytics including conversation count, total cost, and provider usage
    """
    try:
        # Get session info from conversations collection
        conversations_collection = MongoDB.get_collection(settings.context_collection_name)
        session = await conversations_collection.find_one({"session_id": session_id})
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        metadata = session.get("metadata", {})
        
        return {
            "session_id": session_id,
            "created_at": session.get("created_at"),
            "last_accessed": session.get("last_accessed"),
            "total_messages": metadata.get("total_messages", 0),
            "total_cost_usd": round(metadata.get("total_cost_usd", 0.0), 6),
            "total_tokens": metadata.get("total_tokens_used", 0),
            "provider_usage": metadata.get("provider_usage", {
                "gemini_calls": 0,
                "azure_openai_calls": 0
            })
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("session_analytics_error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving session analytics: {str(e)}")


@app.get("/api/v1/supported-fields", response_model=SupportedFieldsResponse)
async def get_supported_fields():
    """Get list of supported queryable fields."""
    fields = [
        "population",
        "capital",
        "currency",
        "currencies",
        "language",
        "languages",
        "region",
        "subregion",
        "area",
        "borders",
        "timezones",
        "continents",
        "flag",
        "maps",
        "landlocked",
        "independent",
        "un_member",
        "tld",
        "official_name",
        "common_name"
    ]
    
    descriptions = {
        "population": "Total population count",
        "capital": "Capital city",
        "currency": "Currency information with name and symbol",
        "currencies": "Same as currency",
        "language": "Spoken languages",
        "languages": "Same as language",
        "region": "Geographic region (e.g., Europe, Asia)",
        "subregion": "Geographic subregion",
        "area": "Land area in square kilometers",
        "borders": "List of bordering country codes",
        "timezones": "List of time zones",
        "continents": "Continents the country is located on",
        "flag": "Flag emoji",
        "maps": "Links to maps (Google Maps, OpenStreetMap)",
        "landlocked": "Whether the country is landlocked",
        "independent": "Independence status",
        "un_member": "UN membership status",
        "tld": "Top-level domain",
        "official_name": "Official country name",
        "common_name": "Common country name"
    }
    
    return SupportedFieldsResponse(fields=fields, descriptions=descriptions)


@app.post("/api/v1/query", response_model=QueryResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def query_country_info(request: Request, query: QueryRequest, background_tasks: BackgroundTasks):
    """
    Query country information using natural language.
    
    Supports conversation context - provide session_id to maintain context across requests.
    
    Examples:
    - "What is the population of Germany?"
    - "What currency does Japan use?"
    - "What is the capital and population of Brazil?"
    - "What about France?" (with context from previous question)
    """
    start_time = time.time()
    
    # Generate or use provided session_id
    session_id = query.session_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    logger.info(
        "query_received",
        question=query.question,
        session_id=session_id,
        message_id=message_id
    )
    
    try:
        # Retrieve conversation context (async, but fast)
        conversation_context = await context_manager.get_context(session_id)
        
        initial_state = {
            "question": query.question,
            "country_name": None,
            "requested_fields": None,
            "query_type": None,
            "api_response": None,
            "extracted_data": None,
            "final_answer": None,
            "error": None,
            "out_of_scope": False,
            "session_id": session_id,
            "message_id": message_id,
            "conversation_context": conversation_context,
            "previous_countries": None
        }
        
        result = await country_info_graph.ainvoke(initial_state)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        if result.get("error"):
            logger.warning(
                "query_error",
                question=query.question,
                session_id=session_id,
                error=result["error"],
                error_type=result.get("error_type", "unknown"),
                execution_time_ms=execution_time_ms
            )
            
            # Return the human-friendly error message from final_answer
            # instead of raising an HTTPException
            response = QueryResponse(
                answer=result.get("final_answer", "Sorry, I am not able to assist you with that query."),
                country=result.get("country_name"),
                fields_retrieved=[],
                execution_time_ms=execution_time_ms,
                session_id=session_id
            )
            
            # Still save the conversation for tracking
            background_tasks.add_task(
                save_conversation_async,
                session_id,
                message_id,
                query.question,
                result
            )
            
            return response
        
        # Handle extracted_data safely - it could be None or a dict
        extracted_data = result.get("extracted_data")
        fields_retrieved = list(extracted_data.keys()) if extracted_data else []
        
        response = QueryResponse(
            answer=result.get("final_answer", "No answer generated"),
            country=result.get("country_name"),
            fields_retrieved=fields_retrieved,
            execution_time_ms=execution_time_ms,
            session_id=session_id
        )
        
        # Schedule async background task to save conversation
        background_tasks.add_task(
            save_conversation_async,
            session_id,
            message_id,
            query.question,
            result
        )
        
        logger.info(
            "query_success",
            question=query.question,
            session_id=session_id,
            country=response.country,
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "query_exception",
            question=query.question,
            session_id=session_id,
            error=str(e),
            execution_time_ms=execution_time_ms
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def save_conversation_async(
    session_id: str,
    message_id: str,
    question: str,
    result: dict
):
    """
    Background task to save conversation to MongoDB.
    This runs asynchronously after the response is sent to the user.
    
    Args:
        session_id: Unique session identifier
        message_id: Unique message identifier
        question: User's question
        result: LangGraph execution result
    """
    try:
        # Extract cost and provider info from result
        llm_cost = result.get("llm_total_cost", 0.0)
        llm_providers = result.get("llm_providers_used", [])
        primary_provider = llm_providers[0] if llm_providers else "gemini"
        
        await context_manager.save_conversation(
            session_id=session_id,
            message_id=message_id,
            question=question,
            result=result,
            llm_cost=llm_cost,
            llm_provider=primary_provider
        )
    except Exception as e:
        logger.error(
            "background_save_failed",
            session_id=session_id,
            message_id=message_id,
            error=str(e)
        )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "detail": str(exc.detail)}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 handler."""
    logger.error("internal_server_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
