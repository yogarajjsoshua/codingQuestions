# Country Information AI Agent

A production-ready AI agent built with LangGraph that answers natural language questions about countries using the REST Countries API.

## Features

- **Three-Step LangGraph Workflow**:
  1. **Intent Identification**: Uses OpenAI function calling to extract country name and requested fields
  2. **Tool Invocation**: Fetches data from REST Countries API with retry logic and caching
  3. **Answer Synthesis**: Generates natural language responses using LLM

- **Production-Ready**:
  - Robust error handling with retries and exponential backoff
  - In-memory caching (24-hour TTL)
  - Rate limiting (100 requests/minute per IP)
  - Structured logging with JSON output
  - Comprehensive test coverage

- **FastAPI REST API**:
  - Async/await for concurrent request handling
  - OpenAPI documentation (Swagger UI)
  - CORS support
  - Health check endpoint

## Architecture

```
┌─────────────┐
│   User      │
│  Question   │
└──────┬──────┘
       │
       v
┌──────────────────┐
│ Intent Identifier│ ← LLM extracts country & fields
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ Tool Invocation  │ ← Calls REST Countries API
└────────┬─────────┘
         │
         v
┌──────────────────┐
│Answer Synthesis  │ ← LLM formats natural response
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ Final Answer     │
└──────────────────┘
```

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
cd CloudEagle
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=100
API_TIMEOUT_SECONDS=30
CACHE_TTL_HOURS=24
```

## Running the Application

### Start the API Server

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. Query Country Information

**Endpoint**: `POST /api/v1/query`

**Request**:
```json
{
  "question": "What is the population of Germany?"
}
```

**Response**:
```json
{
  "answer": "Germany has a population of approximately 83.5 million people.",
  "country": "Germany",
  "fields_retrieved": ["population"],
  "execution_time_ms": 1250
}
```

**Example Questions**:
- "What is the population of Germany?"
- "What currency does Japan use?"
- "What is the capital and population of Brazil?"
- "Tell me about France's languages and region"
- "What is the area of Canada?"
- "What are the bordering countries of Switzerland?"

### 2. Health Check

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "service": "country-info-agent"
}
```

### 3. Supported Fields

**Endpoint**: `GET /api/v1/supported-fields`

**Response**:
```json
{
  "fields": ["population", "capital", "currency", "..."],
  "descriptions": {
    "population": "Total population count",
    "capital": "Capital city",
    "currency": "Currency information with name and symbol",
    "..."
  }
}
```

## Supported Fields

The agent can answer questions about the following country attributes:

| Field | Description | Example Query |
|-------|-------------|---------------|
| `population` | Total population count | "What is the population of India?" |
| `capital` | Capital city | "What is the capital of France?" |
| `currency` | Currency with symbol | "What currency does Japan use?" |
| `languages` | Spoken languages | "What languages are spoken in Switzerland?" |
| `region` | Geographic region | "What region is Brazil in?" |
| `subregion` | Geographic subregion | "What subregion is Thailand in?" |
| `area` | Land area (km²) | "How big is Russia?" |
| `borders` | Bordering countries | "What countries border Germany?" |
| `timezones` | Time zones | "What timezone is Australia in?" |
| `continents` | Continents | "What continent is Egypt on?" |
| `landlocked` | Landlocked status | "Is Switzerland landlocked?" |
| `independent` | Independence status | "Is Puerto Rico independent?" |
| `un_member` | UN membership | "Is Taiwan a UN member?" |

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test Files

```bash
pytest tests/test_tools.py
pytest tests/test_agent.py
pytest tests/test_api.py
```

## Example Usage with cURL

### Basic Query

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the population of Germany?"}'
```

### Multiple Fields

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital and currency of Japan?"}'
```

### General Information

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about Brazil"}'
```

## Example Usage with Python

```python
import requests

url = "http://localhost:8000/api/v1/query"
payload = {
    "question": "What is the population of Germany?"
}

response = requests.post(url, json=payload)
data = response.json()

print(data["answer"])
# Output: "Germany has a population of approximately 83.5 million people."
```

## Project Structure

```
CloudEagle/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration settings
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── graph_state.py         # LangGraph state
│   ├── agent/
│   │   ├── graph.py               # LangGraph workflow
│   │   ├── prompts.py             # LLM prompts
│   │   └── nodes/
│   │       ├── intent_identifier.py
│   │       ├── tool_invocation.py
│   │       └── answer_synthesis.py
│   └── tools/
│       └── rest_countries.py      # REST Countries API client
├── tests/
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_api.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Invalid request (e.g., empty question)
- `404`: Country not found
- `429`: Rate limit exceeded
- `500`: Internal server error
- `503`: External API unavailable

**Error Response Format**:
```json
{
  "detail": "Country 'Atlantis' not found"
}
```

## Performance

- **Caching**: Country data is cached for 24 hours to reduce API calls
- **Async Processing**: Non-blocking I/O for concurrent requests
- **Rate Limiting**: 100 requests per minute per IP address
- **Timeout**: 30-second timeout for external API calls
- **Retries**: 3 automatic retries with exponential backoff

## Monitoring and Logging

All logs are structured in JSON format for easy parsing:

```json
{
  "event": "query_received",
  "question": "What is the population of Germany?",
  "timestamp": "2026-04-11T10:30:00Z",
  "level": "info"
}
```

Key events logged:
- `query_received`: New query received
- `intent_extracted`: Intent successfully extracted
- `api_request`: External API call made
- `cache_hit`: Data served from cache
- `query_success`: Query completed successfully
- `query_error`: Query failed

## Design Decisions

1. **LangGraph over Simple Prompting**: Provides clear separation of concerns, making the system easier to debug, test, and extend with additional steps.

2. **OpenAI Function Calling**: Ensures reliable extraction of structured data (country name and fields) instead of parsing unstructured text.

3. **Async Architecture**: FastAPI with httpx enables efficient handling of concurrent requests without blocking.

4. **In-Memory Caching**: Country data changes infrequently, so 24-hour caching significantly reduces API calls and improves response times.

5. **Retry Logic**: Network issues are common; tenacity library provides robust retry with exponential backoff.

6. **Stateless Design**: Each request is independent, making the service horizontally scalable.

## Limitations

- No persistent storage (all caching is in-memory)
- Single LLM provider (OpenAI) - could be extended to support multiple
- No user authentication/authorization
- Rate limiting is per-instance (not distributed)
- No comparison queries between countries (e.g., "Which is bigger, France or Germany?")

## Future Enhancements

- Add support for multi-country queries
- Implement distributed caching (Redis)
- Add more LLM providers (Anthropic, local models)
- Support for historical data queries
- WebSocket support for streaming responses
- Prometheus metrics integration
- Docker containerization

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
