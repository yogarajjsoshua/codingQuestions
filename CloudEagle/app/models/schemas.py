from pydantic import BaseModel, Field
from typing import List, Optional


class QueryRequest(BaseModel):
    """Request model for country information query."""
    
    question: str = Field(..., description="The user's question about a country", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID for maintaining conversation context")


class QueryResponse(BaseModel):
    """Response model for country information query."""
    
    answer: str = Field(..., description="Natural language answer to the question")
    country: Optional[str] = Field(None, description="The country that was queried")
    fields_retrieved: List[str] = Field(default_factory=list, description="List of fields that were retrieved")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    session_id: str = Field(..., description="Session ID for maintaining conversation context across requests")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class SupportedFieldsResponse(BaseModel):
    """Response model for supported fields endpoint."""
    
    fields: List[str] = Field(..., description="List of supported queryable fields")
    descriptions: dict = Field(..., description="Field descriptions")


class IntentExtractionResult(BaseModel):
    """Result of intent extraction from LLM."""
    
    country_name: str = Field(..., description="Extracted country name")
    requested_fields: List[str] = Field(..., description="List of requested fields")
    query_type: str = Field(..., description="Type of query: single_field, multiple_fields, or general")
