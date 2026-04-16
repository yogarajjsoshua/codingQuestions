#!/bin/bash

# Country Information AI Agent - Quick Start Script
# This script helps you quickly deploy the application locally

set -e  # Exit on error

echo "🌍 Country Information AI Agent - Quick Deploy"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating one...${NC}"
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
RATE_LIMIT_PER_MINUTE=60
REST_COUNTRIES_BASE_URL=https://restcountries.com/v3.1
EOF
    echo -e "${RED}❌ Please edit .env file and add your OPENAI_API_KEY${NC}"
    echo "   Then run this script again."
    exit 1
fi

# Check if OPENAI_API_KEY is set
source .env
if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ Please set your OPENAI_API_KEY in the .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment configuration found${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
echo ""

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment exists${NC}"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Function to check if port is available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Check if ports are available
if ! check_port 8000; then
    echo -e "${RED}❌ Port 8000 is already in use. Please stop the process using this port.${NC}"
    echo "   You can find it with: lsof -i :8000"
    exit 1
fi

if ! check_port 8501; then
    echo -e "${RED}❌ Port 8501 is already in use. Please stop the process using this port.${NC}"
    echo "   You can find it with: lsof -i :8501"
    exit 1
fi

echo -e "${GREEN}✅ Ports 8000 and 8501 are available${NC}"
echo ""

# Ask user how they want to run
echo "How would you like to deploy?"
echo "1) Local (separate terminals - recommended for development)"
echo "2) Docker Compose (containerized deployment)"
echo ""
read -p "Enter choice (1 or 2): " DEPLOY_CHOICE

if [ "$DEPLOY_CHOICE" = "2" ]; then
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
        exit 1
    fi
    
    echo ""
    echo "🐳 Starting services with Docker Compose..."
    docker-compose up --build -d
    
    echo ""
    echo -e "${GREEN}✅ Services are starting up...${NC}"
    echo ""
    echo "Waiting for backend to be ready..."
    
    # Wait for backend to be healthy
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    echo ""
    echo -e "${GREEN}🎉 Deployment complete!${NC}"
    echo ""
    echo "📍 Backend API: http://localhost:8000"
    echo "📍 API Docs: http://localhost:8000/docs"
    echo "📍 Frontend UI: http://localhost:8501"
    echo ""
    echo "View logs with: docker-compose logs -f"
    echo "Stop services with: docker-compose down"
    
else
    # Local deployment
    echo ""
    echo "🚀 Starting local deployment..."
    echo ""
    echo "This will open two terminal windows:"
    echo "  1. Backend (FastAPI) on port 8000"
    echo "  2. Frontend (Streamlit) on port 8501"
    echo ""
    
    # Detect terminal type and OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "Starting Backend..."
        osascript -e 'tell application "Terminal" to do script "cd \"'"$(pwd)"'\" && source venv/bin/activate && echo \"🚀 Starting FastAPI Backend...\" && python -m uvicorn app.main:app --reload --port 8000"'
        
        sleep 3
        
        echo "Starting Frontend..."
        osascript -e 'tell application "Terminal" to do script "cd \"'"$(pwd)"'\" && source venv/bin/activate && echo \"🚀 Starting Streamlit Frontend...\" && streamlit run ui.py"'
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "source venv/bin/activate && echo '🚀 Starting FastAPI Backend...' && python -m uvicorn app.main:app --reload --port 8000; exec bash"
            sleep 3
            gnome-terminal -- bash -c "source venv/bin/activate && echo '🚀 Starting Streamlit Frontend...' && streamlit run ui.py; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "source venv/bin/activate && echo '🚀 Starting FastAPI Backend...' && python -m uvicorn app.main:app --reload --port 8000; exec bash" &
            sleep 3
            xterm -e "source venv/bin/activate && echo '🚀 Starting Streamlit Frontend...' && streamlit run ui.py; exec bash" &
        else
            echo -e "${YELLOW}⚠️  Could not detect terminal. Please run manually:${NC}"
            echo ""
            echo "Terminal 1: python -m uvicorn app.main:app --reload --port 8000"
            echo "Terminal 2: streamlit run ui.py"
            exit 0
        fi
    else
        echo -e "${YELLOW}⚠️  Unsupported OS. Please run manually:${NC}"
        echo ""
        echo "Terminal 1: python -m uvicorn app.main:app --reload --port 8000"
        echo "Terminal 2: streamlit run ui.py"
        exit 0
    fi
    
    echo ""
    echo -e "${GREEN}✅ Services are starting...${NC}"
    echo ""
    echo "Waiting for backend to be ready..."
    
    # Wait for backend
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    echo ""
    echo -e "${GREEN}🎉 Deployment complete!${NC}"
    echo ""
    echo "📍 Backend API: http://localhost:8000"
    echo "📍 API Docs: http://localhost:8000/docs"
    echo "📍 Frontend UI: http://localhost:8501"
    echo ""
    echo "The UI should open automatically in your browser."
    echo "If not, visit: http://localhost:8501"
fi

echo ""
echo "📖 For more information, see README_UI.md"
echo ""
