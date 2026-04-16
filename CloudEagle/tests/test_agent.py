import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.nodes.intent_identifier import intent_identifier_node
from app.agent.nodes.tool_invocation import tool_invocation_node
from app.agent.nodes.answer_synthesis import answer_synthesis_node
from app.models.llm_response import LLMResponse, TokenUsage


@pytest.fixture
def sample_state():
    """Create a sample state dictionary."""
    return {
        "question": "What is the population of Germany?",
        "country_name": None,
        "requested_fields": None,
        "query_type": None,
        "api_response": None,
        "extracted_data": None,
        "final_answer": None,
        "error": None,
        "session_id": "test-session",
        "llm_total_cost": 0.0,
        "llm_providers_used": []
    }


@pytest.fixture
def sample_country_data():
    """Sample country data."""
    return {
        "name": {"common": "Germany"},
        "population": 83491249,
        "capital": ["Berlin"],
        "currencies": {"EUR": {"name": "euro", "symbol": "€"}},
        "languages": {"deu": "German"}
    }


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    def _create_response(content: str, provider: str = "gemini"):
        return LLMResponse(
            content=content,
            provider=provider,
            model="gemini-2.5-flash" if provider == "gemini" else "gpt-4o",
            fallback_used=False,
            tokens=TokenUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            ),
            estimated_cost_usd=0.000001
        )
    return _create_response


@pytest.mark.asyncio
async def test_intent_identifier_node_single_field(sample_state, mock_llm_response):
    """Test intent identifier with single field question."""
    json_response = '{"out_of_scope": false, "country_name": "Germany", "requested_fields": ["population"], "query_type": "single_field"}'
    
    with patch('app.agent.nodes.intent_identifier.llm_service') as mock_service:
        mock_service.invoke = AsyncMock(return_value=mock_llm_response(json_response))
        
        result = await intent_identifier_node(sample_state)
        
        assert result["country_name"] == "Germany"
        assert result["requested_fields"] == ["population"]
        assert result["query_type"] == "single_field"
        assert result["error"] is None
        assert result["llm_total_cost"] > 0


@pytest.mark.asyncio
async def test_intent_identifier_node_multiple_fields(sample_state, mock_llm_response):
    """Test intent identifier with multiple field question."""
    sample_state["question"] = "What is the capital and currency of Japan?"
    json_response = '{"out_of_scope": false, "country_name": "Japan", "requested_fields": ["capital", "currency"], "query_type": "multiple_fields"}'
    
    with patch('app.agent.nodes.intent_identifier.llm_service') as mock_service:
        mock_service.invoke = AsyncMock(return_value=mock_llm_response(json_response))
        
        result = await intent_identifier_node(sample_state)
        
        assert result["country_name"] == "Japan"
        assert len(result["requested_fields"]) == 2
        assert "capital" in result["requested_fields"]
        assert "currency" in result["requested_fields"]


@pytest.mark.asyncio
async def test_intent_identifier_node_out_of_scope(sample_state, mock_llm_response):
    """Test intent identifier with out of scope question."""
    sample_state["question"] = "What is the meaning of life?"
    json_response = '{"out_of_scope": true, "country_name": null, "requested_fields": [], "query_type": null}'
    
    with patch('app.agent.nodes.intent_identifier.llm_service') as mock_service:
        mock_service.invoke = AsyncMock(return_value=mock_llm_response(json_response))
        
        result = await intent_identifier_node(sample_state)
        
        assert result["out_of_scope"] is True
        assert result["country_name"] is None


@pytest.mark.asyncio
async def test_tool_invocation_node_success(sample_state, sample_country_data):
    """Test successful tool invocation."""
    sample_state["country_name"] = "Germany"
    sample_state["requested_fields"] = ["population"]
    
    with patch('app.agent.nodes.tool_invocation.rest_countries_client') as mock_client:
        mock_client.get_country_by_name = AsyncMock(return_value=sample_country_data)
        mock_client.extract_fields.return_value = {"population": 83491249}
        
        result = await tool_invocation_node(sample_state)
        
        assert result["api_response"] is not None
        assert result["extracted_data"]["population"] == 83491249
        assert result["error"] is None


@pytest.mark.asyncio
async def test_tool_invocation_node_missing_country(sample_state):
    """Test tool invocation without country name."""
    result = await tool_invocation_node(sample_state)
    
    assert result["error"] is not None
    assert "Country name not identified" in result["error"]


@pytest.mark.asyncio
async def test_answer_synthesis_node_success(sample_state, mock_llm_response):
    """Test successful answer synthesis."""
    sample_state["question"] = "What is the population of Germany?"
    sample_state["extracted_data"] = {"population": 83491249}
    
    with patch('app.agent.nodes.answer_synthesis.llm_service') as mock_service:
        response_content = "Germany has a population of approximately 83.5 million people."
        mock_service.invoke = AsyncMock(return_value=mock_llm_response(response_content))
        
        result = await answer_synthesis_node(sample_state)
        
        assert result["final_answer"] is not None
        assert "Germany" in result["final_answer"]
        assert "population" in result["final_answer"].lower()
        assert result["llm_total_cost"] > 0


@pytest.mark.asyncio
async def test_answer_synthesis_node_with_error(sample_state):
    """Test answer synthesis with error state."""
    sample_state["error"] = "Country not found"
    
    result = await answer_synthesis_node(sample_state)
    
    assert "error" in result["final_answer"].lower()
    assert "Country not found" in result["final_answer"]


@pytest.mark.asyncio
async def test_answer_synthesis_node_no_data(sample_state):
    """Test answer synthesis with no extracted data."""
    sample_state["country_name"] = "Germany"
    sample_state["extracted_data"] = {}
    
    result = await answer_synthesis_node(sample_state)
    
    assert "couldn't find" in result["final_answer"].lower()
