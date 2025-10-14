# Claude Code SDK Server - curl Examples

Quick copy-paste examples for testing the server with curl.

## Setup

```bash
# Make sure server is running
docker compose up -d

# Set base URL
BASE_URL="http://localhost:3000"
```

## Basic Examples

### Health Check

```bash
curl $BASE_URL/health | jq '.'
```

### Simple Query

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is 2 + 2? Answer in one word."
  }' | jq '.response'
```

### Query with Model Selection

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in one sentence",
    "model": "claude-3-5-sonnet-20241022"
  }' | jq '.'
```

## Conversation Sessions

### Start Session

```bash
curl -X POST $BASE_URL/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "initial_prompt": "What is Docker?"
  }' | jq '.'
```

### Start Session and Save ID

```bash
SESSION=$(curl -s -X POST $BASE_URL/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "initial_prompt": "I want to learn Python programming"
  }' | jq -r '.session_id')

echo "Session ID: $SESSION"
```

### Continue Conversation

```bash
# Using saved SESSION variable from above
curl -X POST $BASE_URL/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the basics I should learn first?"
  }' | jq '.response'
```

### Multiple Follow-ups

```bash
# First follow-up
curl -X POST $BASE_URL/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How long will it take?"}' | jq '.response'

# Second follow-up
curl -X POST $BASE_URL/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What resources do you recommend?"}' | jq '.response'
```

### List All Sessions

```bash
curl $BASE_URL/sessions | jq '.'
```

### Get Session Info

```bash
curl $BASE_URL/session/$SESSION | jq '.'
```

### Close Session

```bash
curl -X DELETE $BASE_URL/session/$SESSION | jq '.'
```

## Complete Session Example

```bash
#!/bin/bash

# Start session about cooking
SESSION=$(curl -s -X POST http://localhost:3000/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "I want to make pasta carbonara"}' \
  | jq -r '.session_id')

echo "Started session: $SESSION"

# Ask about ingredients
echo -e "\n=== Ingredients ==="
curl -s -X POST http://localhost:3000/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What ingredients do I need?"}' \
  | jq -r '.response'

# Ask about steps
echo -e "\n=== Steps ==="
curl -s -X POST http://localhost:3000/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the steps?"}' \
  | jq -r '.response'

# Close session
curl -s -X DELETE http://localhost:3000/session/$SESSION > /dev/null
echo -e "\n✓ Session closed"
```

## Using Tools

### Write a File

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a file called test.txt with the content Hello World",
    "allowed_tools": ["Write"],
    "permission_mode": "acceptEdits"
  }' | jq '.'
```

### Bash Command

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List files in the current directory",
    "allowed_tools": ["Bash"],
    "permission_mode": "acceptEdits"
  }' | jq '.'
```

### Multiple Tools

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Read the README.md file and summarize it",
    "allowed_tools": ["Read", "Write", "Bash"],
    "permission_mode": "default"
  }' | jq '.'
```

## Streaming Examples

### Basic Streaming

```bash
curl -N -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Count from 1 to 5, one number at a time",
    "stream": true
  }'
```

### Streaming with Filtering

```bash
# Stream and filter for text blocks only
curl -N -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a short poem about clouds",
    "stream": true
  }' | grep "type.*text"
```

## Permission Modes

### Accept All Edits

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create three Python files with different sorting algorithms",
    "allowed_tools": ["Write"],
    "permission_mode": "acceptEdits"
  }' | jq '.'
```

### Plan Mode (No Execution)

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze this codebase and suggest improvements",
    "permission_mode": "plan"
  }' | jq '.'
```

### Bypass All Permissions (Use with Caution)

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Set up a complete web server",
    "permission_mode": "bypassPermissions"
  }' | jq '.'
```

## Advanced Examples

### With Max Turns

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Research and write a report on AI",
    "max_turns": 5
  }' | jq '.'
```

### Custom Model and Tools

```bash
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze the current directory structure",
    "model": "claude-3-5-sonnet-20241022",
    "allowed_tools": ["Glob", "Read", "Bash"],
    "permission_mode": "acceptEdits"
  }' | jq '.'
```

### Extract Specific Fields

```bash
# Get only the response text
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is FastAPI?"}' \
  | jq -r '.response'

# Get cost information
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain Docker"}' \
  | jq '{cost: .total_cost_usd, duration: .duration_ms, turns: .num_turns}'
```

## Testing & Debugging

### Test Authentication

```bash
# Should show authenticated: true
curl $BASE_URL/health | jq '.authenticated'
```

### Check Active Sessions Count

```bash
curl $BASE_URL/health | jq '.active_sessions'
```

### Pretty Print All Session Info

```bash
curl -s $BASE_URL/sessions | jq -C '.' | less -R
```

### Monitor Streaming Response

```bash
curl -N -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain machine learning concepts",
    "stream": true
  }' | while read line; do
    echo "$(date '+%H:%M:%S') - $line"
  done
```

## Error Handling

### Invalid Session ID

```bash
# Should return 404
curl -X POST $BASE_URL/session/invalid-id/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  | jq '.'
```

### Missing Required Fields

```bash
# Should return 422 validation error
curl -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{}' \
  | jq '.'
```

## Performance Testing

### Time a Request

```bash
time curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?"}' \
  > /dev/null
```

### Multiple Concurrent Requests

```bash
# Run 3 requests in parallel
for i in {1..3}; do
  curl -s -X POST $BASE_URL/query \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"What is $i + $i?\"}" \
    | jq '.response' &
done
wait
```

## Cleanup

### Close All Sessions

```bash
# Get all session IDs and close them
curl -s $BASE_URL/sessions | jq -r '.active_sessions[]' | while read sid; do
  echo "Closing session: $sid"
  curl -s -X DELETE $BASE_URL/session/$sid | jq '.'
done
```

### Verify No Active Sessions

```bash
curl $BASE_URL/sessions | jq '.count'
# Should return: 0
```

---

## Tips

1. **Use jq for formatting**: Always pipe to `jq '.'` for readable output
2. **Save session IDs**: Use `jq -r '.session_id'` to extract and save
3. **Stream with -N**: Use `curl -N` for streaming responses
4. **Silent mode**: Add `-s` flag to hide progress bar
5. **Follow redirects**: Add `-L` if needed
6. **Verbose debugging**: Add `-v` to see full request/response

## Common Patterns

```bash
# Pattern: Query and extract response
RESPONSE=$(curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Your question"}' | jq -r '.response')
echo "$RESPONSE"

# Pattern: Session with multiple queries
SESSION=$(curl -s -X POST $BASE_URL/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "Start topic"}' | jq -r '.session_id')

curl -s -X POST $BASE_URL/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Follow-up 1"}' | jq -r '.response'

curl -s -X POST $BASE_URL/session/$SESSION/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Follow-up 2"}' | jq -r '.response'

curl -s -X DELETE $BASE_URL/session/$SESSION > /dev/null

# Pattern: Error checking
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "Success: $BODY" | jq '.'
else
  echo "Error ($HTTP_CODE): $BODY"
fi
```
