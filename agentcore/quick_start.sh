#!/bin/bash
# quick_start.sh
# Quick setup script for RepoIntegrator

set -e

echo "🚀 RepoIntegrator - Quick Start"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}❌ Python 3.10+ required. You have $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $python_version${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo ""
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✅ pip upgraded${NC}"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

# Setup .env file
echo ""
if [ ! -f ".env" ]; then
    echo "⚙️  Setting up environment variables..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created from .env.example${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and add your Lightning AI API key${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs cache data
echo -e "${GREEN}✅ Directories created${NC}"

# Initialize Reflex
echo ""
echo "🎨 Initializing Reflex..."
reflex init > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Reflex initialized${NC}"

# Check for Lightning AI key
echo ""
echo "🔑 Checking Lightning AI configuration..."
if grep -q "LIGHTNING_API_KEY=la-" .env; then
    echo -e "${RED}❌ Lightning AI API key not configured${NC}"
    echo ""
    echo "To get your API key:"
    echo "1. Go to https://lightning.ai"
    echo "2. Sign up (free)"
    echo "3. Go to Settings -> API Tokens"
    echo "4. Create a new token"
    echo "5. Add it to .env: LIGHTNING_API_KEY=la-your-key"
    echo ""
else
    echo -e "${GREEN}✅ Lightning AI key configured${NC}"
fi

# Test imports
echo ""
echo "🧪 Testing imports..."
python3 -c "
import reflex
import httpx
import asyncio
print('All imports successful!')
" 2>&1 | grep -q "successful" && echo -e "${GREEN}✅ All dependencies working${NC}" || echo -e "${RED}❌ Import test failed${NC}"

# Summary
echo ""
echo "================================"
echo "✨ Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Add your Lightning AI API key to .env:"
echo "   ${YELLOW}nano .env${NC}"
echo ""
echo "2. Run the application:"
echo "   ${GREEN}reflex run repo_integrator_ui.py${NC}"
echo ""
echo "3. Open your browser:"
echo "   ${GREEN}http://localhost:3000${NC}"
echo ""
echo "Need help? Check the documentation:"
echo "   - Lightning AI: https://lightning.ai/docs"
echo "   - Reflex: https://reflex.dev/docs"
echo ""
echo "Happy coding! 🚀"