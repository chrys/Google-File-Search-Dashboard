#!/bin/bash

# RAG API Production Deployment Checklist
# Run this script on the production server to deploy the API

set -e

echo "======================================"
echo "RAG API Production Deployment"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 0. Pull latest code
# echo -e "${YELLOW}[1/6]${NC} Pulling latest code from repository..."
# cd /srv/rag-dashboard
# sudo git pull origin main
# echo -e "${GREEN}✓ Code pulled${NC}"
# echo ""

# 2. Install/update dependencies
echo -e "${YELLOW}[2/6]${NC} Installing/updating Python dependencies..."
sudo -u deploy /srv/rag-dashboard/.venv/bin/pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# 3. Deploy service files
echo -e "${YELLOW}[3/6]${NC} Deploying systemd service files..."
sudo cp live_configuration/rag-dashboard.service /etc/systemd/system/
sudo cp live_configuration/rag-api-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Service files deployed${NC}"
echo ""

# 4. Deploy Nginx config
echo -e "${YELLOW}[4/6]${NC} Deploying Nginx configuration..."
sudo cp live_configuration/fasolaki.com /etc/nginx/sites-enabled/
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx config valid${NC}"
else
    echo -e "${RED}✗ Nginx config has errors${NC}"
    exit 1
fi
echo ""

# 5. Restart services
echo -e "${YELLOW}[5/6]${NC} Restarting services..."
sudo systemctl restart rag-dashboard
sudo systemctl restart rag-api-dashboard
sleep 2
sudo systemctl reload nginx
echo -e "${GREEN}✓ Services restarted${NC}"
echo ""

# 6. Verify services
echo -e "${YELLOW}[6/6]${NC} Verifying services..."
echo ""

# Check Flask app
if sudo systemctl is-active --quiet rag-dashboard; then
    echo -e "${GREEN}✓${NC} Flask App (rag-dashboard): RUNNING"
else
    echo -e "${RED}✗${NC} Flask App (rag-dashboard): FAILED"
    sudo systemctl status rag-dashboard
fi

# Check API app
if sudo systemctl is-active --quiet rag-api-dashboard; then
    echo -e "${GREEN}✓${NC} FastAPI App (rag-api-dashboard): RUNNING"
else
    echo -e "${RED}✗${NC} FastAPI App (rag-api-dashboard): FAILED"
    sudo systemctl status rag-api-dashboard
fi

# Check if port 8002 is listening
if sudo netstat -tuln 2>/dev/null | grep -q 8002; then
    echo -e "${GREEN}✓${NC} API listening on port 8002"
else
    echo -e "${RED}✗${NC} API not listening on port 8002"
fi

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Test the services:"
echo "  Flask:  https://www.fasolaki.com/rag/"
echo "  API:    https://www.fasolaki.com/rag-api/health"
echo "  API UI: https://www.fasolaki.com/rag-api/docs"
echo ""
echo "View logs:"
echo "  Flask:  sudo journalctl -u rag-dashboard -f"
echo "  API:    sudo journalctl -u rag-api-dashboard -f"
echo ""
