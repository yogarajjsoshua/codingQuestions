import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_supported_fields(client):
    """Test supported fields endpoint."""
    response = client.get("/api/v1/supported-fields")
    
    assert response.status_code == 200
    data = response.json()
    assert "fields" in data
    assert "descriptions" in data
    assert "population" in data["fields"]
    assert "capital" in data["fields"]


def test_query_endpoint_success(client):
    """Test successful query."""
    mock_result = {
        "question": "What is the population of Germany?",
        "country_name": "Germany",
        "requested_fields": ["population"],
        "extracted_data": {"population": 83491249},
        "final_answer": "Germany has a population of approximately 83.5 million people.",
        "error": None
    }
    
    with patch('app.main.country_info_graph.ainvoke', new_callable=AsyncMock) as mock_graph:
        mock_graph.return_value = mock_result
        
        response = client.post(
            "/api/v1/query",
            json={"question": "What is the population of Germany?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "country" in data
        assert data["country"] == "Germany"
        assert "fields_retrieved" in data


def test_query_endpoint_country_not_found(client):
    """Test query with country not found."""
    mock_result = {
        "question": "What is the population of Atlantis?",
        "country_name": "Atlantis",
        "error": "Country 'Atlantis' not found"
    }
    
    with patch('app.main.country_info_graph.ainvoke', new_callable=AsyncMock) as mock_graph:
        mock_graph.return_value = mock_result
        
        response = client.post(
            "/api/v1/query",
            json={"question": "What is the population of Atlantis?"}
        )
        
        assert response.status_code == 404


def test_query_endpoint_invalid_request(client):
    """Test query with invalid request."""
    response = client.post(
        "/api/v1/query",
        json={"question": ""}
    )
    
    assert response.status_code == 422


def test_query_endpoint_multiple_fields(client):
    """Test query with multiple fields."""
    mock_result = {
        "question": "What is the capital and currency of Japan?",
        "country_name": "Japan",
        "requested_fields": ["capital", "currency"],
        "extracted_data": {
            "capital": "Tokyo",
            "currency": "Japanese yen (¥)"
        },
        "final_answer": "Japan's capital is Tokyo, and its currency is the Japanese yen (¥).",
        "error": None
    }
    
    with patch('app.main.country_info_graph.ainvoke', new_callable=AsyncMock) as mock_graph:
        mock_graph.return_value = mock_result
        
        response = client.post(
            "/api/v1/query",
            json={"question": "What is the capital and currency of Japan?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["fields_retrieved"]) == 2
        assert "capital" in data["fields_retrieved"]
        assert "currency" in data["fields_retrieved"]
