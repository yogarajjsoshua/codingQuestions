#!/bin/bash

echo "🚀 Country Information AI Agent - Quick Start"
echo ""

if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    echo ""
fi

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📚 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env and add your OpenAI API key"
echo "   2. Run the server: python -m uvicorn app.main:app --reload"
echo "   3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "🧪 To run tests:"
echo "   pytest"
echo ""
