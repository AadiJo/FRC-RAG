#!/bin/bash

# Deploy my frontend to a VPS

echo "🚀 FRC RAG Frontend Deployment Script"
echo "====================================="
echo ""

# Ask where to deploy
read -p "Enter VPS IP address or domain: " VPS_HOST
read -p "Enter SSH user (default: root): " SSH_USER
SSH_USER=${SSH_USER:-root}
read -p "Enter remote path (default: /var/www/frc-rag): " REMOTE_PATH
REMOTE_PATH=${REMOTE_PATH:-/var/www/frc-rag}

echo ""
echo "Configuration:"
echo "  VPS: $SSH_USER@$VPS_HOST"
echo "  Remote path: $REMOTE_PATH"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

# Find where this script is
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR"

echo ""
echo "📦 Preparing deployment..."

# Make a temp directory for the files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy what I need
echo "  Copying files..."
cp -r templates static server.py requirements.txt .env.example "$TEMP_DIR/"

# Warn about local .env
if [ -f ".env" ]; then
    echo "  ⚠️  Local .env found - NOT copying to VPS"
    echo "  You'll need to configure .env on the VPS manually"
fi

echo ""
echo "📤 Uploading to VPS..."

# Make the directory on the server
ssh "$SSH_USER@$VPS_HOST" "mkdir -p $REMOTE_PATH"

# Send the files
rsync -avz --progress "$TEMP_DIR/" "$SSH_USER@$VPS_HOST:$REMOTE_PATH/"

echo ""
echo "🔧 Setting up on VPS..."

# Run setup commands on the server
ssh "$SSH_USER@$VPS_HOST" bash << EOF
    cd $REMOTE_PATH
    
    # Install stuff I need
    echo "Installing system packages..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv nginx
    
    # Set up Python environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Install Python packages
    echo "Installing Python packages..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create .env if needed
    if [ ! -f ".env" ]; then
        echo "Creating .env from template..."
        cp .env.example .env
        echo "⚠️  Please edit .env and set BACKEND_URL!"
    fi
    
    echo ""
    echo "✅ Frontend deployed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env: nano $REMOTE_PATH/.env"
    echo "2. Set BACKEND_URL to your backend server URL"
    echo "3. Setup systemd service (see docs/DEPLOYMENT.md)"
    echo "4. Setup nginx reverse proxy (see docs/DEPLOYMENT.md)"
    echo ""
EOF

echo ""
echo "=================================="
echo "✅ Deployment Complete!"
echo "=================================="
echo ""
echo "Frontend deployed to: $SSH_USER@$VPS_HOST:$REMOTE_PATH"
echo ""
echo "Important: Configure the following on VPS:"
echo ""
echo "1. Edit .env file:"
echo "   ssh $SSH_USER@$VPS_HOST"
echo "   cd $REMOTE_PATH"
echo "   nano .env"
echo "   Set: BACKEND_URL=<your-backend-url>"
echo ""
echo "2. Setup systemd service:"
echo "   See: docs/DEPLOYMENT.md#step-4-setup-systemd-service"
echo ""
echo "3. Setup nginx reverse proxy:"
echo "   See: docs/DEPLOYMENT.md#step-5-setup-nginx-reverse-proxy"
echo ""
echo "4. Setup SSL certificate:"
echo "   sudo certbot --nginx -d yourdomain.com"
echo ""
