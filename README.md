# Claude Agent SDK Docker Example

A simple Docker container with Claude Agent SDK (Python + TypeScript) and an example FastAPI server to help you get started building Claude-powered applications.

## What Is This?

This repository provides:
- **Docker container** with Claude AgentPython SDK and TypeScript SDK pre-installed
- **Example FastAPI server** that exposes the Claude Agent SDK via HTTP REST API
- **Telegram bot** for interactive chat with Claude via Telegram
- **Slack bot** for interactive chat with Claude via Slack
- **Sample client code** showing how to interact with the server
- **Starting point** for building your own Claude-powered servers and applications

## Quick Start

### 1. Get Your OAuth Token

On your host machine (not in Docker):
```bash
# Install Claude Code CLI if you haven't already
npm install -g @anthropic-ai/claude-code

# Generate a long-lived OAuth token
claude setup-token
```

Copy the token that starts with `sk-ant-oat01-`

### 2. Set Environment Variable

```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your token
```

### 3. Build and Run

```bash
# Build the Docker image
./build.sh

# Start the server
docker compose up -d

# Check logs
docker compose logs -f
```

The server will be available at http://localhost:3000

### 4. Test It

```bash
# Health check
curl http://localhost:3000/health

# Ask Claude a question
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Docker?"}'

# Or run the Python test client
python examples/client/test_server.py
```

Interactive API docs available at: http://localhost:3000/docs

## What's Included

### Docker Image
- **Node.js 22** - For running TypeScript/JavaScript
- **Python 3** - For running Python code
- **Claude Code CLI** - Official CLI tool
- **TypeScript SDK** - [@anthropic-ai/claude-code](https://www.npmjs.com/package/@anthropic-ai/claude-code)
- **Python SDK** - [claude-agent-sdk](https://pypi.org/project/claude-agent-sdk/)
- **Development tools** - git, curl, jq, nano

### Example Server & Bots
- **FastAPI server** ([server/api.py](server/api.py)) - REST API for Claude interactions
- **Telegram bot** ([server/telegram_bot.py](server/telegram_bot.py)) - Chat with Claude via Telegram
- **Slack bot** ([server/slack_bot.py](server/slack_bot.py)) - Chat with Claude via Slack
- **Shared bot logic** ([server/bot_common.py](server/bot_common.py)) - Common code for all bots
- **One-off queries** - Send single prompts
- **Conversation sessions** - Multi-turn conversations with context
- **Streaming responses** - Real-time output via Server-Sent Events
- **Tool permissions** - Control which tools Claude can use

### Example Client
- **Python client** ([examples/client/test_server.py](examples/client/test_server.py)) - Test script
- **Bash client** ([examples/client/test_server.sh](examples/client/test_server.sh)) - Shell script examples
- **curl examples** ([examples/client/curl-examples.md](examples/client/curl-examples.md)) - HTTP examples

## Project Structure

```
.
├── Dockerfile                    # Multi-stage build: Node.js + Python + Claude SDKs
├── compose.yaml                  # Docker Compose: server + telegram-bot + slack-bot
├── build.sh                      # Build script
├── server/
│   ├── api.py                   # FastAPI server implementation
│   ├── telegram_bot.py          # Telegram bot implementation
│   ├── slack_bot.py             # Slack bot implementation
│   ├── bot_common.py            # Shared bot logic (sessions, Claude SDK)
│   ├── sdk_executor.py          # Unified SDK executor with observability
│   ├── agent_executor.py        # Legacy agent executor
│   ├── requirements.txt         # Python dependencies (server + bots)
│   ├── test_telegram_bot.py     # Telegram bot test script
│   └── test_slack_bot.py        # Slack bot test script
├── examples/client/             # Example client code
│   ├── test_server.py           # Python test client
│   └── test_server.sh           # Bash test client
└── docs/                        # Documentation
    ├── AUTHENTICATION.md        # Auth setup details
    ├── SERVER.md                # FastAPI API reference
    ├── TELEGRAM.md              # Telegram bot complete guide
    ├── SLACK.md                 # Slack bot complete guide
    └── DEPLOYMENT.md            # Production deployment guide
```

## Authentication

This project solves the authentication problem for containerized Claude Code SDK usage.

**The Problem:** Claude Code SDK normally uses interactive browser-based OAuth, which doesn't work well in containers.

**The Solution:** Use long-lived OAuth tokens generated on your host machine and passed to containers via environment variables.

See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for technical details.

## Example API Usage

### Simple Question
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain what FastAPI is in one sentence"}'
```

### Conversation with Context
```bash
# Start a session
SESSION_ID=$(curl -s -X POST http://localhost:3000/session/start \
  -H "Content-Type: application/json" \
  -d '{"initial_prompt": "What is Docker?"}' | jq -r '.session_id')

# Ask follow-up (Claude remembers context)
curl -X POST http://localhost:3000/session/$SESSION_ID/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I install it?"}'

# Close session
curl -X DELETE http://localhost:3000/session/$SESSION_ID
```

### Using Tools
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a file called hello.txt with Hello World",
    "allowed_tools": ["Write"],
    "permission_mode": "acceptEdits"
  }'
```

See [docs/SERVER.md](docs/SERVER.md) for complete API documentation.

## Using the Telegram Bot

Run Claude Code as a Telegram bot:

### Quick Start

```bash
# 1. Get a bot token from @BotFather on Telegram
# 2. Add to .env file
echo "TELEGRAM_BOT_API_KEY=your_token_here" >> .env

# 3. Start the bot
docker compose up -d telegram-bot

# 4. Open Telegram and chat with your bot!
```

### Features

- **Per-user conversations** - Each user has their own context
- **Working directory per user** - Configure where files are accessed
- **Persistent sessions** - Conversations saved across restarts
- **All Claude Code tools** - Read, Write, Edit, Bash commands
- **Commands** - `/start`, `/help`, `/setcwd`, `/getcwd`, `/reset`

### Documentation

- [docs/TELEGRAM.md](docs/TELEGRAM.md) - Complete setup, usage, and deployment guide

### Example Usage

In Telegram:
```
You: /start
Bot: 👋 Welcome to Claude Code Bot!

You: /setcwd /workspace
Bot: ✅ Working directory set to: /workspace

You: List all Python files in the current directory
Bot: [Claude executes Bash tool and shows results] 🔧 BASH

You: Read the first file
Bot: [Claude reads and shows file contents] 🔧 READ

You: \/help
Bot: [Shows Claude Code help - the backslash escapes the slash]
```

**Note:** To use Claude Code's built-in commands (like `/help`, `/clear`, `/prime`), escape the slash with a backslash: `\/help`

## Using the Slack Bot

Run Claude Code as a Slack bot:

### Quick Start

```bash
# 1. Create Slack app at api.slack.com/apps
# 2. Get Bot Token (xoxb-...) and App Token (xapp-...)
# 3. Add to .env file
echo "SLACK_BOT_TOKEN=xoxb-..." >> .env
echo "SLACK_APP_TOKEN=xapp-..." >> .env

# 4. Start the bot
docker compose up -d slack-bot

# 5. Open Slack and chat with your bot!
```

### Features

- **Per-user conversations** - Each user has their own context
- **Working directory per user** - Configure where files are accessed
- **Channel and DM support** - Works in channels and direct messages
- **Persistent sessions** - Conversations saved across restarts
- **All Claude Code tools** - Read, Write, Edit, Bash commands
- **Slash commands** - `/start`, `/help`, `/setcwd`, `/getcwd`, `/reset`
- **Rich formatting** - Threaded replies and markdown support

### Documentation

- [docs/SLACK.md](docs/SLACK.md) - Complete setup, usage, and deployment guide

### Example Usage

In Slack:
```
You: /start
Bot: 👋 Welcome to Claude Code Bot!

You: /setcwd /workspace
Bot: ✅ Working directory set to: /workspace

You: List all Python files in the current directory
Bot: [Claude executes Bash tool and shows results] 🔧 BASH

You: Read the first file
Bot: [Claude reads and shows file contents] 🔧 READ

You: \/help
Bot: [Shows Claude Code help - the backslash escapes the slash]
```

**Note:** To use Claude Code's built-in commands (like `/help`, `/clear`, `/prime`), escape the slash with a backslash: `\/help`

## Building Your Own Server

Use this as a starting point:

1. **Modify [server/api.py](server/api.py)** - Add your own endpoints and logic
2. **Add dependencies** - Update [server/requirements.txt](server/requirements.txt)
3. **Test locally** - Use the example client code
4. **Deploy** - Use the Docker container in your infrastructure

## Development

### Run Server Locally (Without Docker)

```bash
# Set your token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token

# Install dependencies
pip install -r server/requirements.txt

# Run the server
python server/api.py
```

### Access Container Shell

```bash
# Start container
docker compose up -d

# Access shell as claude user
docker compose exec server bash

# Try the SDKs
python -c "from claude_agent_sdk import query; print('Python SDK ready')"
node -e "console.log('TypeScript SDK ready')"
```

### Rebuild Container

```bash
# Clean build
./build.sh --no-cache

# Restart server
docker compose down
docker compose up -d
```

## Troubleshooting

### Server won't start
```bash
# Check logs for errors
docker compose logs

# Verify token is set
docker compose exec server env | grep CLAUDE_CODE_OAUTH_TOKEN
```

### Authentication errors
```bash
# Test health endpoint
curl http://localhost:3000/health

# Should show: "authenticated": true
# If false, regenerate your token:
claude setup-token
```

### Port already in use
```bash
# Use a different port
export PORT=3001
docker compose up -d
```

## Security Notes

- This example is for **development and testing**
- Don't expose the server to the public internet without authentication
- OAuth tokens are passed via environment variables (never hardcode them)
- The container runs as non-root user `claude` for security
- Use `.aiexclude` to prevent Claude from accessing sensitive files

## Deployment

Ready to deploy to production? See the [Deployment Guide](docs/DEPLOYMENT.md) for step-by-step instructions on deploying to Digital Ocean droplets (or any VPS).

The guide covers:
- Setting up a droplet with Docker
- Configuring HTTPS with Nginx and Let's Encrypt
- Adding authentication
- Security best practices
- Monitoring and maintenance

## What's Next?

1. **Explore the API** - http://localhost:3000/docs
2. **Read the server docs** - [docs/SERVER.md](docs/SERVER.md)
3. **Deploy to production** - [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
4. **Customize the server** - Modify [server/api.py](server/api.py) for your needs
5. **Build something cool** - Use this as a starting point for your project

## Resources

- [Claude Code SDK Python Docs](https://platform.claude.com/docs/en/agent-sdk/python)
- [Claude Code SDK TypeScript Docs](https://platform.claude.com/docs/en/agent-sdk/typescript)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

This is a simple example project to help you get started. Feel free to fork and modify for your own needs!

## Credits
- Added Cole Medin's [Telegram Bot](https://github.com/coleam00/ottomator-agents/blob/main/claude-agent-sdk-demos/telegram_integration/telegram_bot.py) 
- Thanks to [cabinlab/claude-code-sdk-docker](https://github.com/cabinlab/claude-code-sdk-docker) for implementing setup-token authentication flow.
- [receipting/claude-agent-sdk-container](https://github.com/receipting/claude-agent-sdk-container) is a similar project where you might find some ideas.