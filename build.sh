#!/bin/bash

# Build script for Claude Code SDK Docker images
# Builds unified images with both TypeScript and Python support

set -e  # Exit on error

echo "=========================================="
echo "Building Claude Code SDK Docker Images"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
NO_CACHE=${NO_CACHE:-false}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-cache)
      NO_CACHE=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --no-cache       Build without using cache"
      echo "  --help           Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Build Debian image (TypeScript + Python)"
      echo "  $0 --no-cache         # Fresh build without cache"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Build flags
CACHE_FLAG=""
if [ "$NO_CACHE" = true ]; then
  CACHE_FLAG="--no-cache"
  echo -e "${YELLOW}Building without cache...${NC}"
fi

# Build Debian image (includes both TypeScript and Python)
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Building Debian image (TypeScript + Python)...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

docker build \
  $CACHE_FLAG \
  -f Dockerfile \
  -t claude-agent-sdk:latest \
  .

echo -e "${GREEN}✓ Debian image built: claude-agent-sdk:latest${NC}"
echo -e "${GREEN}  Includes: TypeScript SDK + Python SDK${NC}"

# Summary
echo ""
echo -e "${GREEN}=========================================="
echo "✓ Build Complete!"
echo "==========================================${NC}"
echo ""
echo "Available images:"
docker images | grep -E "claude-agent-sdk|REPOSITORY" | head -10

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""

echo "  # Run container:"
echo "  docker compose up -d"
echo ""

echo ""
echo -e "${BLUE}To rebuild without cache: $0 --no-cache${NC}"
echo ""
