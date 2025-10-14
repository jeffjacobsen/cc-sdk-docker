# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Purpose

This is a **simple example project** that demonstrates how to:
1. Package the Claude Code SDK (both Python and TypeScript) in a Docker container
2. Run an example FastAPI server that exposes Claude Code SDK functionality via HTTP REST API
3. Serve as a starting point for building more advanced Claude-powered servers

## The Problem This Solves

The Claude Code SDK normally uses interactive browser-based OAuth authentication, which doesn't work in containerized environments. This project solves that by:

- Using **long-lived OAuth tokens** (`sk-ant-oat01-*`) generated on the host machine
- Passing tokens to containers via environment variables (`CLAUDE_CODE_OAUTH_TOKEN`)
- Configuring the SDK to use these tokens automatically on container startup

## Architecture

### Single Docker Image
- **Base**: Node.js 22 slim
- **Multi-stage build** to minimize final image size
- **Stage 1**: Build Node.js dependencies (Claude Code CLI + TypeScript SDK)
- **Stage 2**: Build Python dependencies (Python SDK)
- **Stage 3**: Runtime image with both SDKs + server code
- **Non-root user**: Runs as `claude` user for security

### Example Server
- **FastAPI** HTTP server ([server/api.py](server/api.py))
- **REST endpoints** for interacting with Claude Code SDK
- **Features**:
  - One-off queries (stateless)
  - Conversation sessions (stateful, maintains context)
  - Streaming responses via Server-Sent Events
  - Tool permission controls

### Docker Compose Setup
- **Single service** (`server`) defined in [compose.yaml](compose.yaml)
- **Environment variables** for authentication
- **Volume mounts** for development (bind mount current directory)
- **Health checks** to verify server is running
- **Port mapping** (default 3000, configurable via `PORT` env var)

## Repository Structure

```
.
├── Dockerfile              # Single unified image (TypeScript + Python)
├── compose.yaml            # Single service configuration
├── build.sh                # Build helper script
├── server/
│   ├── api.py             # FastAPI server implementation
│   ├── requirements.txt   # Python dependencies for server
│   └── README.md          # Quick reference
├── examples/client/       # Test clients
│   ├── test_server.py     # Python client
│   ├── test_server.sh     # Bash client
│   └── curl-examples.md   # HTTP examples
├── docs/
│   ├── AUTHENTICATION.md  # How authentication works
│   ├── SERVER.md          # API documentation
│   └── DEPLOYMENT.md      # Production deployment guide
└── scripts/
    └── docker-entrypoint.sh  # Container startup script
```

## Key Files

### [Dockerfile](Dockerfile)
- Multi-stage build for optimal size
- Installs both Claude Code SDKs
- Sets up non-root user
- Copies example code and scripts

### [compose.yaml](compose.yaml)
- Defines the `server` service
- Mounts current directory for development
- Sets environment variables for authentication
- Configures health checks

### [server/api.py](server/api.py)
- FastAPI application
- Implements REST endpoints for Claude interactions
- Manages conversation sessions in memory
- Handles streaming responses

### [scripts/docker-entrypoint.sh](scripts/docker-entrypoint.sh)
- Container startup script
- Configures authentication if `CLAUDE_CODE_OAUTH_TOKEN` is set
- Creates necessary credential files

## Development Guidelines

When modifying this repository:

1. **Keep it simple** - This is meant to be an example/starting point, not a production framework
2. **Authentication via environment variables** - Don't change this; it's the core solution
3. **Maintain both SDKs** - The image supports both Python and TypeScript
4. **Test with the example clients** - Use [examples/client/test_server.py](examples/client/test_server.py) to verify changes
5. **Update documentation** - Keep [README.md](README.md) and [docs/SERVER.md](docs/SERVER.md) in sync with code changes

## Common Tasks

### Adding a new API endpoint
1. Edit [server/api.py](server/api.py)
2. Add the endpoint function
3. Test with [examples/client/test_server.py](examples/client/test_server.py)
4. Update [docs/SERVER.md](docs/SERVER.md)

### Adding Python dependencies
1. Add to [server/requirements.txt](server/requirements.txt)
2. Rebuild: `./build.sh --no-cache`
3. Restart: `docker compose up -d`

### Adding Node.js dependencies
1. Edit [Dockerfile](Dockerfile) to add `npm install` command
2. Rebuild: `./build.sh --no-cache`
3. Restart: `docker compose up -d`

## What This Is NOT

This is **not**:
- A production-ready server framework
- A comprehensive SDK wrapper
- A multi-container microservices architecture
- A project with multiple image variants

This **is**:
- A simple starting example
- A demonstration of SDK + FastAPI integration
- A solution to the container authentication problem
- A foundation you can build upon

## Testing

Run the test clients to verify functionality:

```bash
# Start the server
docker compose up -d

# Python client
python examples/client/test_server.py

# Bash client
bash examples/client/test_server.sh

# Health check
curl http://localhost:3000/health
```

## Deployment

For production deployment, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The guide covers:
- Setting up on Digital Ocean droplets (or any VPS)
- HTTPS with Nginx and Let's Encrypt
- Authentication and security
- Monitoring and maintenance

## Future Enhancements (for users to implement)

Users of this example may want to add:
- Persistent session storage (database)
- User authentication and API keys
- Rate limiting
- Request logging
- Error handling and retries
- Monitoring and metrics
- Multiple Claude model support
- Custom tool implementations
- Webhook support
- WebSocket connections

But we keep this example simple and focused on the core functionality.
