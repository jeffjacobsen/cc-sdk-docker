# Claude Code SDK Server - Quick Reference

## Start the Server

```bash
# Make sure you have your OAuth token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Start the server
docker compose up -d

# View logs
docker compose logs -f python-server
```

## Quick Test

```bash
# Health check
curl http://localhost:3000/health

# Simple query
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Interactive API docs
open http://localhost:3000/docs
```

## Common Commands

```bash
# Stop server
docker compose down

# Restart server
docker compose restart

# View logs
docker compose logs -f

# Access container shell
docker compose exec python-server bash

# Check if server is running
docker compose ps
```

## Test Scripts

```bash
# Python test client
docker compose exec python-server python /app/examples/client/test_server.py

# Bash test script
bash examples/client/test_server.sh
```

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/query` | POST | One-off query (no context) |
| `/session/start` | POST | Start conversation |
| `/session/{id}/query` | POST | Continue conversation |
| `/session/{id}/interrupt` | POST | Interrupt task |
| `/session/{id}` | GET | Session info |
| `/sessions` | GET | List sessions |
| `/session/{id}` | DELETE | Close session |

## Example: Conversation Session

```bash
# Start session
SESSION=$(curl -s -X POST http://localhost:3000/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "What is Docker?"}' | jq -r '.session_id')

# Continue conversation (remembers context)
curl -X POST http://localhost:3000/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I install it?"}' | jq '.response'

# Close session
curl -X DELETE http://localhost:3000/session/$SESSION
```

## Troubleshooting

**Server won't start:**
```bash
# Check logs
docker compose logs python-server

# Check auth
docker compose exec python-server env | grep CLAUDE
```

**Connection refused:**
```bash
# Check if running
docker compose ps

# Check port
curl http://localhost:3000/health
```

For full documentation, see [docs/SERVER.md](../docs/SERVER.md)
