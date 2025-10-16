# Telegram Bot Documentation

Complete guide for setting up and using the Claude Code Telegram bot.

## Overview

The Telegram bot enables users to interact with Claude Code through direct messages with:
- Bot commands (`/start`, `/help`, etc.)
- Natural language conversations
- Per-user conversation context and settings
- Persistent sessions across restarts
- Shared codebase with Slack bot (95% code reuse)

## Quick Start

### 1. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Choose a name (e.g., "My Claude Code Bot")
4. Choose a username (must end in 'bot', e.g., "my_claude_code_bot")
5. BotFather gives you an API token: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`

### 2. Configure Environment

```bash
# Add to .env file
TELEGRAM_BOT_API_KEY=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token

# Optional
TELEGRAM_WORKING_DIRECTORY=/workspace
TELEGRAM_WORKSPACE=./workspace
```

### 3. Run the Bot

**Locally:**
```bash
pip install -r server/requirements.txt
python server/telegram_bot.py
```

**Docker:**
```bash
docker compose up -d telegram-bot
docker compose logs telegram-bot -f
```

### 4. Test in Telegram

1. Search for your bot by username
2. Click "START" or send `/start`
3. Chat with Claude!

---

## Usage

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Show welcome message | `/start` |
| `/help` | List available commands | `/help` |
| `/setcwd <path>` | Set working directory | `/setcwd /workspace` |
| `/getcwd` | Show current directory | `/getcwd` |
| `/searchcwd <query>` | Search for directories | `/searchcwd projects` |
| `/reset` | Clear conversation history | `/reset` |
| `/showthinking on\|off` | Toggle thinking blocks | `/showthinking on` |

### Natural Language Messages

Send any message to interact with Claude:

```
You: List files in the current directory
Bot: [Uses Bash tool]
     file1.txt
     file2.py
     README.md
     🔧 BASH
```

### Claude Code Slash Commands

To use Claude Code's built-in slash commands (like `/help` or `/clear`), use double slashes:

```
//help     → Claude receives /help
//clear    → Claude receives /clear
```

### Multi-turn Conversations

The bot maintains context:

```
You: What files are in the current directory?
Bot: [Lists files]

You: Read the first file
Bot: [Reads and shows content]

You: Summarize what you just read
Bot: [Provides summary based on previous context]
```

### Tool Usage Indicators

When Claude uses tools, you'll see indicators:

- `🔧 READ` - Read files
- `🔧 WRITE` - Write files
- `🔧 EDIT` - Edit files
- `🔧 BASH` - Execute commands
- `🔧 GLOB` - Find files
- `🔧 GREP` - Search content

---

## Docker Deployment

### Architecture

The Docker setup includes multiple independent services:

```yaml
services:
  server:        # FastAPI REST API (port 3000)
  telegram-bot:  # Telegram bot (polling)
  slack-bot:     # Slack bot (Socket Mode)
```

All services:
- Share the same Docker image
- Use the same Claude Code OAuth token
- Have isolated workspaces and sessions
- Run as the `claude` user for security

### Configuration

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | - | Claude authentication token |
| `TELEGRAM_BOT_API_KEY` | Yes | - | Telegram Bot API token from BotFather |
| `TELEGRAM_WORKING_DIRECTORY` | No | `/workspace` | Default working directory inside container |
| `TELEGRAM_WORKSPACE` | No | `./workspace` | Host directory to mount as workspace |
| `FILE_LOGGING` | No | `false` | Enable file logging to logs/ directory |

#### Volume Mounts

```yaml
volumes:
  # Development: Live code changes
  - .:/app

  # Authentication: Shared with other services
  - claude-auth:/home/claude/.claude

  # Workspace: User files (configurable)
  - ${TELEGRAM_WORKSPACE:-./workspace}:/workspace

  # Sessions: Persistent conversation history
  - telegram-sessions:/app/telegram_sessions
```

### Running Services

```bash
# Start all services
docker compose up -d

# Start only Telegram bot
docker compose up -d telegram-bot

# View logs
docker compose logs telegram-bot -f

# Check status
docker compose ps

# Stop bot
docker compose stop telegram-bot
```

### Managing Sessions

```bash
# List session files
docker compose exec telegram-bot ls -la /app/telegram_sessions/

# View a specific session
docker compose exec telegram-bot cat /app/telegram_sessions/12345678.json

# Clear all sessions
docker compose exec telegram-bot rm -rf /app/telegram_sessions/*

# Backup sessions
docker compose cp telegram-bot:/app/telegram_sessions ./telegram_sessions_backup

# Restore sessions
docker compose cp ./telegram_sessions_backup/. telegram-bot:/app/telegram_sessions/
```

### Workspace Management

```bash
# List files in workspace
docker compose exec telegram-bot ls -la /workspace

# Read a file
docker compose exec telegram-bot cat /workspace/example.txt

# Create a test file on host
echo "Hello from host" > workspace/test.txt

# Ask bot to read it in Telegram:
# "Read the file test.txt"
```

To mount a different workspace, edit `.env`:

```bash
TELEGRAM_WORKSPACE=/path/to/your/project
```

Then restart:

```bash
docker compose up -d telegram-bot
```

---

## Testing

### Basic Tests

1. **Commands**: Test all bot commands
   ```
   /start
   /help
   /setcwd /tmp
   /getcwd
   /searchcwd documents
   /reset
   /showthinking on
   ```

2. **Simple questions**:
   ```
   Hello! What can you help me with?
   ```

3. **File operations**:
   ```
   List all files in the current directory
   Read the README.md file
   Create a file called test.txt with "Hello!"
   ```

4. **Multi-turn conversations**:
   ```
   Message 1: What files are in the current directory?
   Message 2: Now read the first file you found
   Message 3: What was in that file?
   ```

### Verify Features

#### Per-User Sessions

1. Have multiple users connect to your bot
2. Each user sends messages
3. Verify that:
   - Each user gets their own responses
   - Each user's conversation context is separate
   - Sessions are stored in `telegram_sessions/` directory

#### Working Directory Configuration

1. User A: `/setcwd /tmp`
2. User B: `/setcwd /home/user`
3. Both users: `List files here`
4. Verify each user sees files from their configured directory

#### Long Message Handling

Ask Claude to generate a very long response:

```
Write a detailed explanation of how TCP/IP networking works
```

Verify that long responses are split across multiple messages with "(continued)" indicators.

### Inspect Logs and Data

```bash
# View logs
docker compose logs telegram-bot -f

# List session files
ls -la telegram_sessions/

# View a session file
cat telegram_sessions/12345678.json
```

Expected session format:

```json
{
  "session_id": "abc-123-def-456",
  "cwd": "/path/to/workspace",
  "show_thinking": false,
  "created_at": "2025-10-16T10:30:00Z",
  "last_updated": "2025-10-16T11:45:00Z"
}
```

---

## Troubleshooting

### Bot Doesn't Respond

**Check:**
1. Is the bot running?
2. Is the `TELEGRAM_BOT_API_KEY` correct?
3. Did you start a conversation with the bot?

**Solution:**
```bash
# View logs
docker compose logs telegram-bot

# Check environment
docker compose exec telegram-bot env | grep TELEGRAM

# Restart bot
docker compose restart telegram-bot
```

### Container Exits Immediately

**Check logs:**
```bash
docker compose logs telegram-bot
```

**Common issues:**
- Missing `TELEGRAM_BOT_API_KEY` in `.env`
- Missing `CLAUDE_CODE_OAUTH_TOKEN` in `.env`
- Invalid token format

**Solution:**
```bash
# Verify .env file
cat .env | grep TELEGRAM

# Restart with logs visible
docker compose up telegram-bot
```

### "Module not found" Errors

**Cause:** Dependencies not installed

**Solution:**
```bash
# Rebuild image
docker compose build --no-cache telegram-bot

# Restart
docker compose up -d telegram-bot
```

### Claude SDK Errors

**Check:**
```bash
# Verify token is set
docker compose exec telegram-bot env | grep CLAUDE_CODE_OAUTH_TOKEN

# Check auth directory
docker compose exec telegram-bot ls -la /home/claude/.claude/
```

**Solution:**
```bash
# Ensure .env has valid token
cat .env | grep CLAUDE_CODE_OAUTH_TOKEN

# Restart to reload environment
docker compose up -d telegram-bot
```

### Permission Errors in Workspace

**Check permissions:**
```bash
docker compose exec telegram-bot ls -ld /workspace
```

**Solution:**
```bash
# Fix host directory permissions
chmod -R 755 workspace

# Or enter container as root
docker compose exec -u root telegram-bot bash
```

### Sessions Not Persisting

**Verify volume:**
```bash
# Check volume exists
docker volume ls | grep telegram-sessions

# Inspect volume
docker volume inspect cc-sdk-docker_telegram-sessions
```

**Recreate volume if needed:**
```bash
docker compose down
docker volume rm cc-sdk-docker_telegram-sessions
docker compose up -d telegram-bot
```

### File Logging Not Working

**Check:**
1. Is `FILE_LOGGING=true` in `.env`?
2. Is bot using the unified SDK executor?

**Solution:**
```bash
# Verify environment variable
docker compose exec telegram-bot env | grep FILE_LOGGING

# Check if logs directory exists
docker compose exec telegram-bot ls -la /app/logs/

# View log files
docker compose exec telegram-bot cat /app/logs/telegram_requests.jsonl
```

---

## Production Deployment

### Docker Compose on VPS

```bash
# On your server
git clone <your-repo>
cd cc-sdk-docker

# Set up environment
nano .env
# Add TELEGRAM_BOT_API_KEY and CLAUDE_CODE_OAUTH_TOKEN

# Build and start
docker compose up -d telegram-bot

# Enable restart on boot
docker compose up -d --restart=always telegram-bot
```

### Monitoring

```bash
# Auto-restart on failure
docker compose up -d --restart=always telegram-bot

# View live logs
docker compose logs telegram-bot -f

# Check resource usage
docker stats telegram-bot

# Check session storage size
docker compose exec telegram-bot du -sh /app/telegram_sessions/
```

### Security Best Practices

1. **Never commit tokens** - Add `.env` to `.gitignore`
2. **Use strong bot tokens** - Generate new tokens for each deployment
3. **Restrict workspace access** - Don't mount sensitive directories
4. **Monitor bot usage** - Check logs regularly
5. **Update regularly** - Keep base image and dependencies updated
6. **Use non-root user** - Already configured (`claude` user)
7. **Limit resource usage** - Add CPU and memory limits
8. **Implement user whitelist** - Restrict access to authorized users

---

## Advanced Configuration

### Multiple Bots

Run multiple bot instances:

```yaml
# compose.yaml
services:
  telegram-bot-1:
    # ... same config ...
    environment:
      - TELEGRAM_BOT_API_KEY=${TELEGRAM_BOT_API_KEY_1}
      - WORKING_DIRECTORY=/workspace1
    volumes:
      - ./workspace1:/workspace1

  telegram-bot-2:
    # ... same config ...
    environment:
      - TELEGRAM_BOT_API_KEY=${TELEGRAM_BOT_API_KEY_2}
      - WORKING_DIRECTORY=/workspace2
    volumes:
      - ./workspace2:/workspace2
```

### Resource Limits

Add to `compose.yaml`:

```yaml
telegram-bot:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### User Access Control

Implement user whitelist in `telegram_bot.py`:

```python
# Add at the top
ALLOWED_USER_IDS = [
    12345678,  # Your Telegram user ID
    87654321,  # Another user's ID
]

# In handle_message function:
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Unauthorized. Contact admin for access.")
        return

    # ... rest of handler
```

To find your user ID, send any message to the bot and check logs for:
```
INFO - Received message from user 12345678
```

---

## Features

| Feature | Status | Notes |
|---------|--------|-------|
| Bot Commands | ✓ | All 7 commands |
| Natural Language | ✓ | Full support |
| Per-user Sessions | ✓ | Persistent |
| Working Directories | ✓ | Per user |
| Long Messages | ✓ | Auto-split at 4096 chars |
| Tool Indicators | ✓ | 🔧 READ, BASH, etc. |
| Thinking Blocks | ✓ | Toggle with /showthinking |
| Slash Command Escape | ✓ | Use // prefix |
| Error Handling | ✓ | Graceful errors |
| File Logging | ✓ | Optional (FILE_LOGGING=true) |
| Docker Support | ✓ | Full container support |

---

## Comparison: Telegram vs Slack

| Feature | Telegram Bot | Slack Bot |
|---------|--------------|-----------|
| Setup complexity | Easy (1 token) | Medium (2 tokens + OAuth) |
| Commands | Bot commands | Slash commands |
| DMs | ✓ | ✓ |
| Channels | ✗ | ✓ Native support |
| Threading | Limited | ✓ |
| Rich UI | Limited | ✓ Block Kit |
| Enterprise ready | ✓ | ✓✓✓ |
| Deployment | Identical | Identical |
| Code sharing | 95% | 95% |

Both bots share the same core logic via `bot_common.py`!

---

## See Also

- [Main README](../README.md) - Project overview
- [Authentication Guide](AUTHENTICATION.md) - Token setup
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Telegram Bot API](https://core.telegram.org/bots/api) - Official Telegram documentation
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python) - Claude SDK
