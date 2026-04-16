# Country Information AI Agent - UI Deployment Guide

This guide explains how to deploy and interact with the Country Information AI Agent using the web UI.

## Architecture

```
┌─────────────┐      HTTP      ┌──────────────┐    LangGraph    ┌────────────────┐
│  Streamlit  │  ────────────>  │   FastAPI    │  ────────────>  │ REST Countries │
│     UI      │  <────────────  │   Backend    │  <────────────  │      API       │
└─────────────┘                 └──────────────┘                 └────────────────┘
  Port: 8501                       Port: 8000
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
RATE_LIMIT_PER_MINUTE=60
REST_COUNTRIES_BASE_URL=https://restcountries.com/v3.1
```

### 3. Start the Backend (FastAPI)

In one terminal:

```bash
# Start the FastAPI backend
python -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at: http://localhost:8000

Check the health endpoint: http://localhost:8000/health

### 4. Start the UI (Streamlit)

In another terminal:

```bash
# Start the Streamlit UI
streamlit run ui.py
```

The UI will automatically open in your browser at: http://localhost:8501

## Using the UI

### Features

1. **Chat Interface**: Type natural language questions about countries
2. **Real-time Status**: See backend connection status in the sidebar
3. **Chat History**: All conversations are preserved during the session
4. **Metadata Display**: See which fields were retrieved and execution time
5. **Supported Fields**: View all queryable fields in the sidebar
6. **Example Questions**: Get inspired by example queries
7. **Clear Chat**: Reset the conversation anytime

### Example Questions

- "What is the population of Germany?"
- "What currency does Japan use?"
- "What is the capital and population of Brazil?"
- "Tell me about France"
- "What languages are spoken in Switzerland?"
- "What are the borders of Poland?"

## Deployment Options

### Option 1: Local Development (Current Setup)

Best for development and testing.

- Backend: `uvicorn app.main:app --reload`
- Frontend: `streamlit run ui.py`

### Option 2: Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    
  frontend:
    build: .
    ports:
      - "8501:8501"
    depends_on:
      - backend
    environment:
      - API_BASE_URL=http://backend:8000
    command: streamlit run ui.py --server.address 0.0.0.0
```

Run with:
```bash
docker-compose up
```

### Option 3: Cloud Deployment

#### Backend (FastAPI) on Railway/Render/Fly.io

1. Connect your GitHub repository
2. Set environment variables (OPENAI_API_KEY, etc.)
3. Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

#### Frontend (Streamlit) on Streamlit Cloud

1. Push your code to GitHub
2. Go to https://share.streamlit.io
3. Deploy directly from your repository
4. Set `API_BASE_URL` to your backend URL in `ui.py`

### Option 4: Kubernetes

For production-grade deployments, use the following manifest structure:

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: country-info-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: country-info-backend
  template:
    metadata:
      labels:
        app: country-info-backend
    spec:
      containers:
      - name: backend
        image: your-registry/country-info-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-key
---
apiVersion: v1
kind: Service
metadata:
  name: country-info-backend
spec:
  selector:
    app: country-info-backend
  ports:
  - port: 8000
    targetPort: 8000
```

## Configuration

### Backend Configuration (`app/config.py`)

- `OPENAI_API_KEY`: Your OpenAI API key
- `RATE_LIMIT_PER_MINUTE`: API rate limiting (default: 60)
- `REST_COUNTRIES_BASE_URL`: REST Countries API endpoint

### Frontend Configuration (`ui.py`)

- `API_BASE_URL`: Backend API URL (default: http://localhost:8000)
- Change this when deploying to production

## Troubleshooting

### Backend Not Connecting

1. Check if backend is running: `curl http://localhost:8000/health`
2. Check firewall settings
3. Verify CORS settings in `app/main.py`

### OpenAI API Errors

1. Verify `OPENAI_API_KEY` is set correctly
2. Check API quota and billing
3. Review logs for specific error messages

### Rate Limiting

If you see rate limit errors:
1. Increase `RATE_LIMIT_PER_MINUTE` in settings
2. Implement request queuing
3. Consider caching frequent queries

## API Documentation

When the backend is running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitoring and Logs

### Backend Logs

The FastAPI backend uses structured logging with `structlog`:

```bash
# View logs
python -m uvicorn app.main:app --log-level info
```

### Streamlit Logs

Streamlit logs appear in the terminal where you run the UI.

## Security Considerations

1. **API Keys**: Never commit `.env` files
2. **CORS**: Configure `allow_origins` properly for production
3. **Rate Limiting**: Adjust based on your needs
4. **HTTPS**: Use SSL/TLS in production
5. **Authentication**: Add user authentication for public deployments

## Performance Tips

1. **Caching**: The backend already implements caching for REST Countries API
2. **Scaling**: Use multiple backend replicas with a load balancer
3. **CDN**: Serve static assets via CDN
4. **Database**: Consider adding a database for conversation history

## License

See main project LICENSE file.
