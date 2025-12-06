#!/bin/bash

# Verification script for Claude Code SDK Docker setup
# Checks if local images are built and ready to use

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "Claude Code SDK - Setup Verification"
echo -e "==========================================${NC}\n"

# Check 1: Docker is installed
echo -e "${BLUE}1. Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓ Docker found: ${DOCKER_VERSION}${NC}"
else
    echo -e "${RED}✗ Docker not found${NC}"
    echo "  Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check 2: Docker Compose is available
echo -e "\n${BLUE}2. Checking Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    echo -e "${GREEN}✓ Docker Compose found: ${COMPOSE_VERSION}${NC}"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "  Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check 3: Local images built
echo -e "\n${BLUE}3. Checking for local images...${NC}"

PYTHON_EXISTS=$(docker images -q claude-agent-sdk:latest 2>/dev/null)

if [ -n "$PYTHON_EXISTS" ]; then
    echo -e "${GREEN}✓ Python image found${NC}"
    docker images claude-agent-sdk:latest --format "  Image: {{.Repository}}:{{.Tag}} ({{.Size}})"
else
    echo -e "${YELLOW}⚠ Python image not found${NC}"
    echo "  Run: ./build.sh"
fi

# Check 4: Authentication token
echo -e "\n${BLUE}4. Checking authentication...${NC}"

if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file found${NC}"
    if grep -q "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-" .env 2>/dev/null; then
        echo -e "${GREEN}✓ OAuth token appears to be set in .env${NC}"
    else
        echo -e "${YELLOW}⚠ OAuth token not found in .env${NC}"
        echo "  Edit .env and add: CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..."
    fi
elif [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo -e "${GREEN}✓ CLAUDE_CODE_OAUTH_TOKEN environment variable is set${NC}"
else
    echo -e "${YELLOW}⚠ No authentication found${NC}"
    echo "  Set up authentication:"
    echo "    1. Run: claude setup-token"
    echo "    2. Copy token to .env file"
    echo "  Or set: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..."
fi

# Check 5: Build script
echo -e "\n${BLUE}5. Checking build script...${NC}"
if [ -f "build.sh" ] && [ -x "build.sh" ]; then
    echo -e "${GREEN}✓ build.sh found and executable${NC}"
else
    echo -e "${YELLOW}⚠ build.sh not executable${NC}"
    echo "  Run: chmod +x build.sh"
fi

# Check 6: Compose files
echo -e "\n${BLUE}6. Checking Docker Compose files...${NC}"
COMPOSE_FILES=(
    "compose.yaml"
)

for file in "${COMPOSE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ ${file} found${NC}"
    else
        echo -e "${RED}✗ ${file} missing${NC}"
    fi
done

# Summary
echo -e "\n${BLUE}=========================================="
echo "Summary"
echo -e "==========================================${NC}\n"

READY=true

if [ -z "$PYTHON_EXISTS" ]; then
    echo -e "${YELLOW}⚠ Images need to be built${NC}"
    echo "  Run: ./build.sh"
    READY=false
fi

if [ ! -f ".env" ] && [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo -e "${YELLOW}⚠ Authentication needs to be configured${NC}"
    echo "  1. Run: claude setup-token"
    echo "  2. Copy .env.example to .env"
    echo "  3. Add your token to .env"
    READY=false
fi

if [ "$READY" = true ]; then
    echo -e "${GREEN}✓ Everything looks good!${NC}\n"
    echo "Next steps:"
    echo "  1. Start the server:"
    echo "     docker compose up -d"
    echo ""
    echo "  2. Test it:"
    echo "     curl http://localhost:3000/health"
    echo ""
    echo "  3. View logs:"
    echo "     docker compose logs -f"
else
    echo -e "${YELLOW}⚠ Some setup steps are needed${NC}"
    echo ""
    echo "Quick setup:"
    echo "  1. Build images: ./build.sh"
    echo "  2. Set up auth: cp .env.example .env && vi .env"
    echo "  3. Start server: docker compose up -d"
fi

echo -e "\n${BLUE}For more help, see:${NC}"
echo "  • README.md - Project overview"
echo "  • docs/TESTING.md - Detailed testing guide"
echo "  • docs/SERVER.md - Server documentation"
echo ""
