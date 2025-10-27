#!/bin/bash

# Start my frontend for development

echo "🎨 Starting FRC RAG Frontend Server..."

# Find where this script is
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR"

# Set up Python environment if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Turn on virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install packages
echo "📚 Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env with your configuration."
    echo "   Ensure BACKEND_URL points to your backend server."
    echo ""
fi

# Check if backend is accessible
source .env 2>/dev/null || BACKEND_URL="http://localhost:5000"
echo "🔍 Checking backend connectivity..."
if ! curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "⚠️  Backend is not accessible at: $BACKEND_URL"
    echo "   Make sure the backend server is running."
    echo "   You can start it with: cd ../backend && ./start.sh"
    echo ""
    read -p "Press Enter to continue anyway..."
fi

echo ""
echo "================================"
echo "🚀 Starting Frontend Server"
echo "================================"
echo "Backend URL: $BACKEND_URL"
echo ""

# Start the server
python server.py
