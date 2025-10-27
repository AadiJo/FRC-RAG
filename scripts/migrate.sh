#!/bin/bash

# Help me move from the old structure to the new structure

echo "🔄 FRC RAG Project Migration Helper"
echo "===================================="
echo ""

# Find where this script is
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Project directory: $PROJECT_DIR"
echo ""

# Check if migration is needed
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: backend/ or frontend/ directories not found!"
    echo "   This script should be run after the refactoring is complete."
    exit 1
fi

echo "✓ New structure detected"
echo ""

# Show what can be removed
echo "The following old files/folders can be removed:"
echo "  - server.py (replaced by backend/app.py)"
echo "  - vps_full_server.py (replaced by backend/vps_server.py)"
echo "  - src/ (copied to backend/src/)"
echo "  - templates/ (copied to frontend/templates/)"
echo "  - static/ (copied to frontend/static/)"
echo "  - requirements.txt (split into backend/ and frontend/)"
echo "  - start.sh (replaced by scripts/start_backend.sh)"
echo "  - project_status.py (moved to backend/utils/)"
echo "  - test_setup.py (moved to backend/utils/)"
echo ""

read -p "Do you want to remove these old files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing old files..."
    
    # Back up first
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    [ -f "server.py" ] && mv server.py "$BACKUP_DIR/"
    [ -f "vps_full_server.py" ] && mv vps_full_server.py "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "src" ] && mv src "$BACKUP_DIR/"
    [ -d "templates" ] && mv templates "$BACKUP_DIR/"
    [ -d "static" ] && mv static "$BACKUP_DIR/"
    [ -f "requirements.txt" ] && mv requirements.txt "$BACKUP_DIR/"
    [ -f "start.sh" ] && mv start.sh "$BACKUP_DIR/" 2>/dev/null || true
    [ -f "project_status.py" ] && mv project_status.py "$BACKUP_DIR/"
    [ -f "test_setup.py" ] && mv test_setup.py "$BACKUP_DIR/"
    [ -d "deploy" ] && mv deploy "$BACKUP_DIR/" 2>/dev/null || true
    
    echo "✓ Old files moved to $BACKUP_DIR/"
    echo ""
fi

# Set up backend .env
echo "🔧 Setting up backend environment..."
if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env from template"
    echo "  📝 Please edit backend/.env with your settings"
else
    echo "  ℹ️  backend/.env already exists"
fi

# Set up frontend .env
echo "🔧 Setting up frontend environment..."
if [ ! -f "frontend/.env" ] && [ -f "frontend/.env.example" ]; then
    cp frontend/.env.example frontend/.env
    echo "✓ Created frontend/.env from template"
    echo "  📝 Please edit frontend/.env with your settings"
else
    echo "  ℹ️  frontend/.env already exists"
fi

echo ""
echo "=================================="
echo "✅ Migration Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure backend/.env:"
echo "   cd backend && nano .env"
echo ""
echo "2. Configure frontend/.env:"
echo "   cd frontend && nano .env"
echo "   Important: Set BACKEND_URL to your backend server"
echo ""
echo "3. Start backend:"
echo "   ./scripts/start_backend.sh"
echo ""
echo "4. Start frontend (in another terminal):"
echo "   ./scripts/start_frontend.sh"
echo ""
echo "5. Access the application:"
echo "   http://localhost:80 (or your configured port)"
echo ""
echo "📚 Documentation:"
echo "   - Main README: README.md"
echo "   - Backend: backend/README.md"
echo "   - Frontend: frontend/README.md"
echo "   - Deployment: docs/DEPLOYMENT.md"
echo ""

# Offer to migrate old .env
if [ -f ".env" ]; then
    echo "📋 Old .env file detected!"
    echo ""
    echo "You may want to migrate settings from .env to:"
    echo "  - backend/.env (for server, Ollama, database settings)"
    echo "  - frontend/.env (for frontend server settings)"
    echo ""
fi
