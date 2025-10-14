# FastAPI Server API Reference

Complete API documentation for the Claude Code SDK FastAPI server.

## Quick Links

- **Interactive Docs**: http://localhost:3000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:3000/redoc (ReDoc)
- **Health Check**: http://localhost:3000/health

## Base URL

```
http://localhost:3000
```

Change the port with `PORT` environment variable.

---

## Endpoints

### Health & Status

#### `GET /health`
Check server health and authentication status.

**Response:**
```json
{
  "status": "healthy",
  "authenticated": true,
  "active_sessions": 2,
  "timestamp": "2025-10-14T10:30:00"
}
```

**Status Codes:**
- `200` - Server is healthy
- `500` - Server error

#### `GET /`
Get API information and available endpoints.

**Response:**
```json
{
  "name": "Claude Code SDK Server",
  "version": "1.0.0",
  "endpoints": ["/health", "/query", "/session/start", ...]
}
```

---

### One-off Queries

One-off queries start fresh each time with no conversation context.

#### `POST /query`
Send a single query to Claude without conversation history.

**Request Body:**
```json
{
  "prompt": "What is Python?",
  "model": "claude-3-5-sonnet-20241022",
  "allowed_tools": ["Read", "Write"],
  "permission_mode": "acceptEdits",
  "stream": false
}
```

**Parameters:**
- `prompt` (string, required) - The question or instruction
- `model` (string, optional) - Claude model to use (default: claude-3-5-sonnet-20241022)
- `allowed_tools` (array, optional) - List of tools Claude can use (default: all)
- `permission_mode` (string, optional) - Permission mode (default: "default")
- `stream` (boolean, optional) - Enable streaming response (default: false)

**Non-streaming Response:**
```json
{
  "response": "Python is a high-level programming language...",
  "duration_ms": 1234,
  "num_turns": 1,
  "total_cost_usd": 0.001234
}
```

**Streaming Response:**

Set `stream: true` to receive Server-Sent Events:

```
data: {"type": "text", "content": "Python "}
data: {"type": "text", "content": "is a "}
data: {"type": "text", "content": "high-level..."}
data: {"type": "done"}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Server error

**Example:**
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'
```

---

### Conversation Sessions

Sessions maintain context across multiple queries, allowing Claude to remember previous messages.

#### `POST /session/start`
Start a new conversation session.

**Request Body:**
```json
{
  "initial_prompt": "What is Docker?",
  "model": "claude-3-5-sonnet-20241022",
  "allowed_tools": ["Read"],
  "permission_mode": "default"
}
```

**Parameters:**
- `initial_prompt` (string, required) - First message in conversation
- `model` (string, optional) - Claude model to use
- `allowed_tools` (array, optional) - List of allowed tools
- `permission_mode` (string, optional) - Permission mode

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "initial_response": "Docker is a platform for containerization...",
  "created_at": "2025-10-14T10:30:00"
}
```

**Status Codes:**
- `200` - Session started
- `400` - Invalid request
- `500` - Server error

**Example:**
```bash
curl -X POST http://localhost:3000/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "Tell me about Python"}'
```

---

#### `POST /session/{session_id}/query`
Continue a conversation (Claude remembers previous context).

**Path Parameters:**
- `session_id` (string, required) - Session ID from `/session/start`

**Request Body:**
```json
{
  "prompt": "How do I install it?",
  "stream": false
}
```

**Parameters:**
- `prompt` (string, required) - Follow-up question or instruction
- `stream` (boolean, optional) - Enable streaming (default: false)

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "To install Python, you can...",
  "duration_ms": 1234
}
```

**Status Codes:**
- `200` - Success
- `404` - Session not found
- `500` - Server error

**Example:**
```bash
# Store session ID from /session/start
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

# Ask follow-up questions
curl -X POST http://localhost:3000/session/$SESSION_ID/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me more about that"}'
```

---

#### `POST /session/{session_id}/interrupt`
Interrupt the current task in a session.

**Path Parameters:**
- `session_id` (string, required) - Session ID

**Response:**
```json
{
  "status": "interrupted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200` - Interrupted successfully
- `404` - Session not found

---

#### `GET /session/{session_id}`
Get session information.

**Path Parameters:**
- `session_id` (string, required) - Session ID

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-10-14T10:30:00",
  "active": true,
  "model": "claude-3-5-sonnet-20241022"
}
```

**Status Codes:**
- `200` - Success
- `404` - Session not found

---

#### `GET /sessions`
List all active sessions.

**Response:**
```json
{
  "active_sessions": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "count": 2
}
```

---

#### `DELETE /session/{session_id}`
Close and cleanup a session.

**Path Parameters:**
- `session_id` (string, required) - Session ID

**Response:**
```json
{
  "status": "closed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes:**
- `200` - Session closed
- `404` - Session not found

---

## Configuration Options

### Permission Modes

Controls how Claude handles tool execution:

- `default` - Prompts for confirmations (interactive)
- `acceptEdits` - Auto-accept file edits
- `plan` - Planning mode, no execution
- `bypassPermissions` - Bypass all permission checks (use with caution)

### Available Tools

Common tools you can include in `allowed_tools`:

- `Read` - Read files
- `Write` - Write files
- `Edit` - Edit files
- `Bash` - Execute bash commands
- `Glob` - Find files by pattern
- `Grep` - Search file contents
- `WebFetch` - Fetch web content
- `WebSearch` - Search the web
- `Task` - Run sub-agents for complex tasks

Leave empty or omit to allow all tools.

### Claude Models

Available models (as of October 2025):
- `claude-3-5-sonnet-20241022` (default) - Latest Sonnet 3.5
- `claude-3-5-haiku-20241022` - Fast and efficient
- `claude-3-opus-20240229` - Most capable

---

## Complete Examples

### Example 1: Simple Q&A

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain REST APIs in one sentence"
  }' | jq '.response'
```

### Example 2: Multi-turn Conversation

```bash
# Start conversation
SESSION=$(curl -s -X POST http://localhost:3000/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "I want to learn Docker"}' | jq -r '.session_id')

echo "Session: $SESSION"

# Ask follow-up questions (Claude remembers context)
curl -X POST http://localhost:3000/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is a Dockerfile?"}' | jq '.response'

curl -X POST http://localhost:3000/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me an example"}' | jq '.response'

# Clean up
curl -X DELETE http://localhost:3000/session/$SESSION
```

### Example 3: File Operations

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a Python script that prints Hello World",
    "allowed_tools": ["Write"],
    "permission_mode": "acceptEdits"
  }' | jq '.response'
```

### Example 4: Streaming Response

```bash
curl -N -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Count from 1 to 10 slowly",
    "stream": true
  }'
```

### Example 5: Python Client

```python
import requests

base_url = "http://localhost:3000"

# Simple query
response = requests.post(
    f"{base_url}/query",
    json={"prompt": "What is FastAPI?"}
).json()
print(response['response'])

# Conversation session
session = requests.post(
    f"{base_url}/session/start",
    json={"initial_prompt": "I'm learning Python"}
).json()

session_id = session['session_id']

# Continue conversation
followup = requests.post(
    f"{base_url}/session/{session_id}/query",
    json={"prompt": "What are list comprehensions?"}
).json()
print(followup['response'])

# Close session
requests.delete(f"{base_url}/session/{session_id}")
```

---

## Architecture Notes

### Session Storage

- Sessions are stored **in-memory**
- Lost on server restart
- For production, implement persistent storage (database, Redis, etc.)

### Concurrency

- The server handles multiple concurrent requests
- Each session is independent
- Streaming responses use Server-Sent Events (SSE)

### Error Handling

All endpoints return standard HTTP error responses:

```json
{
  "detail": "Error message here"
}
```

Common errors:
- `400` - Invalid request parameters
- `404` - Session not found
- `500` - Server error (check logs)

---

## Development & Testing

### Test the API

Use the included test clients:

```bash
# Python client (comprehensive)
python examples/client/test_server.py

# Bash client (quick test)
bash examples/client/test_server.sh
```

### Monitor Server Logs

```bash
docker compose logs -f
```

### Access Interactive Docs

Open in browser:
- Swagger UI: http://localhost:3000/docs
- ReDoc: http://localhost:3000/redoc

You can test all endpoints directly from the browser!

---

## Security Considerations

- **No authentication** - Anyone with access can use the API
- **Sessions not isolated** - Any client can access any session ID
- **For development only** - Don't expose to public internet
- **Add auth in production** - Implement API keys, JWT, or other auth

---

## See Also

- [Main README](../README.md) - Project overview and quick start
- [Authentication Guide](AUTHENTICATION.md) - How to set up tokens
- [Claude Code SDK Docs](https://docs.claude.com/en/docs/claude-code/sdk/sdk-python) - Official SDK documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/) - FastAPI framework documentation
