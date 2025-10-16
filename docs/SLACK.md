# Slack Bot Documentation

Complete guide for setting up and using the Claude Code Slack bot.

## Overview

The Slack bot enables teams to interact with Claude Code directly in Slack through:
- Direct messages (DMs)
- Channel mentions (@bot)
- Slash commands
- Per-user conversation context
- Shared codebase with Telegram bot (95% code reuse)

## Quick Start

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Enter app name and select workspace
4. Get two tokens:
   - **Bot Token** (`xoxb-...`) - from OAuth & Permissions
   - **App Token** (`xapp-...`) - from Socket Mode

### 2. Configure Environment

```bash
# Add to .env file
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token
```

### 3. Run the Bot

**Locally:**
```bash
pip install -r server/requirements.txt
python server/slack_bot.py
```

**Docker:**
```bash
docker compose up -d slack-bot
docker compose logs slack-bot -f
```

### 4. Test in Slack

1. Open Slack workspace
2. Find your bot under "Apps"
3. Send `/start` to get welcome message
4. Chat with Claude!

---

## Detailed Setup

### Step 1: Configure Slack App Settings

#### 1.1 OAuth Scopes

Go to **OAuth & Permissions** and add Bot Token Scopes:

**Required:**
- `app_mentions:read` - See when bot is mentioned
- `chat:write` - Send messages
- `commands` - Add slash commands
- `im:history` - Read DM history
- `im:read` - View basic DM info
- `im:write` - Send DMs

**Optional (for channels):**
- `channels:history` - Read channel messages
- `channels:read` - View basic channel info

After adding scopes, click **"Install to Workspace"** and copy the **Bot User OAuth Token**.

#### 1.2 Enable Socket Mode

1. Go to **Socket Mode** in left sidebar
2. Toggle **"Enable Socket Mode"** to ON
3. Create token with name "Claude Bot Socket Token"
4. Copy the **App-Level Token** (starts with `xapp-...`)

Socket Mode allows the bot to connect without exposing a public webhook endpoint.

#### 1.3 Enable Events

Go to **Event Subscriptions**:

1. Toggle **"Enable Events"** to ON
2. Under **"Subscribe to bot events"**, add:
   - `app_mention` - When bot is mentioned
   - `message.im` - Direct messages to bot
   - `message.channels` - Messages in channels (optional)
3. Click **"Save Changes"**

#### 1.4 Create Slash Commands

Go to **Slash Commands** and create these:

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/start` | Show welcome message | |
| `/help` | Show help message | |
| `/setcwd` | Set working directory | `/setcwd /path/to/dir` |
| `/getcwd` | Show current working directory | |
| `/searchcwd` | Search for directories | `/searchcwd projects` |
| `/reset` | Clear conversation history | |
| `/showthinking` | Toggle thinking blocks | `/showthinking on` |

Leave **Request URL** empty (Socket Mode handles routing).

#### 1.5 Configure App Home

Go to **App Home**:

1. Under **"Show Tabs"**, enable **"Messages Tab"**
2. Check **"Allow users to send Slash commands and messages from the messages tab"**
3. Click **"Save Changes"**

### Step 2: Environment Configuration

Create or update `.env` file:

```bash
# Required: Claude authentication
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Required: Slack tokens
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Optional: Default working directory
SLACK_WORKING_DIRECTORY=/workspace
SLACK_WORKSPACE=./workspace

# Optional: Observability
FILE_LOGGING=true
# SENTRY_DSN=your-sentry-dsn
# POSTHOG_API_KEY=your-posthog-key
```

### Step 3: Install Dependencies

```bash
pip install -r server/requirements.txt
```

This installs:
- `slack-bolt` - Slack bot framework
- `claude-agent-sdk` - Claude SDK
- Other shared dependencies

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

### Direct Messages

Send any message to the bot in a DM:

```
You: List files in the current directory
Bot: [Uses Bash tool]
     file1.txt
     file2.py
     README.md
     🔧 BASH
```

### Channel Mentions

Mention the bot in any channel:

```
@Claude Code Bot help me understand this code
```

The bot will respond in a thread to keep channels clean.

### Multi-turn Conversations

The bot remembers context within each conversation:

```
You: What files are in the current directory?
Bot: [Lists files]

You: Read the first file
Bot: [Reads and shows content]

You: Summarize what you just read
Bot: [Provides summary based on previous context]
```

### Tool Usage

When Claude uses tools, you'll see indicators:

- `🔧 READ` - Read files
- `🔧 WRITE` - Write files
- `🔧 EDIT` - Edit files
- `🔧 BASH` - Execute commands
- `🔧 GLOB` - Find files
- `🔧 GREP` - Search content

---

## Testing

### Manual Testing

1. **Commands**: Test all slash commands
   ```
   /start
   /help
   /setcwd /tmp
   /getcwd
   /searchcwd documents
   /reset
   ```

2. **Direct messages**: Send questions in DM
   ```
   Hello!
   What can you help me with?
   List Python files
   ```

3. **Channel mentions**: Test in a channel
   ```
   @Claude Code Bot explain this code snippet
   ```

4. **Tool usage**: Verify tool indicators appear
   ```
   Read the README.md file
   Create a test.py file
   ```

5. **Context retention**: Test multi-turn conversations
   ```
   What is Docker? (Message 1)
   Tell me more about containers (Message 2)
   ```

### Automated Testing

Run the test suite:

```bash
python server/test_slack_bot.py
```

Checks:
- Environment variables
- Token formats
- Dependencies
- File structure
- Bot modules

---

## Architecture

### Code Sharing

95% of code is shared between Telegram and Slack bots via `bot_common.py`:

```
server/
├── bot_common.py          # Shared logic (sessions, Claude SDK, utilities)
├── telegram_bot.py        # Telegram-specific handlers
└── slack_bot.py           # Slack-specific handlers
```

### Docker Services

Three independent services in `compose.yaml`:

```yaml
services:
  server:        # FastAPI REST API (port 3000)
  telegram-bot:  # Telegram bot (polling)
  slack-bot:     # Slack bot (Socket Mode)
```

Run individually or together:

```bash
docker compose up -d server        # API only
docker compose up -d telegram-bot  # Telegram only
docker compose up -d slack-bot     # Slack only
docker compose up -d               # All services
```

### Session Storage

- Per-user sessions stored in `slack_sessions/` directory
- JSON format with session ID, working directory, preferences
- Persistent across bot restarts (Docker volume)

Example session file (`slack_sessions/U12345678.json`):

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "cwd": "/workspace",
  "show_thinking": false,
  "created_at": "2025-10-16T10:30:00Z",
  "last_updated": "2025-10-16T10:35:00Z"
}
```

---

## Troubleshooting

### Bot Doesn't Respond

**Check:**
1. Is the bot running?
2. Are tokens correct in `.env`?
3. Is Socket Mode enabled?
4. Are Event Subscriptions enabled?

**Solution:**
```bash
# View logs
docker compose logs slack-bot -f

# Check environment
docker compose exec slack-bot env | grep SLACK

# Restart bot
docker compose restart slack-bot
```

### Invalid Auth or Token Errors

**Check:**
1. `SLACK_BOT_TOKEN` starts with `xoxb-`
2. `SLACK_APP_TOKEN` starts with `xapp-`
3. Tokens copied correctly (no spaces)

**Solution:**
```bash
# Verify tokens
cat .env | grep SLACK_

# Test bot token
curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/auth.test
```

### Commands Not Working

**Check:**
1. Are slash commands created in Slack app settings?
2. Is Socket Mode enabled?
3. Is Request URL empty?

**Solution:**
1. Go to https://api.slack.com/apps
2. Select your app → Slash Commands
3. Verify all commands are listed
4. Ensure Request URL is empty

### Claude SDK Errors

**Check:**
1. Is `CLAUDE_CODE_OAUTH_TOKEN` set?
2. Is the token valid?

**Solution:**
```bash
# Verify token
docker compose exec slack-bot env | grep CLAUDE_CODE_OAUTH_TOKEN

# Check logs for SDK errors
docker compose logs slack-bot | grep ERROR
```

### Sessions Not Persisting

**Check:**
1. Does `slack_sessions/` directory exist?
2. Is Docker volume properly mounted?

**Solution:**
```bash
# Check session directory
docker compose exec slack-bot ls -la /app/slack_sessions/

# View a session
docker compose exec slack-bot cat /app/slack_sessions/U12345678.json

# Check volume mounts
docker compose config | grep slack_sessions
```

---

## Advanced Configuration

### User Access Control

Limit bot access to specific users:

```python
# In slack_bot.py, add at the top:
ALLOWED_USER_IDS = [
    "U12345ABC",  # Your Slack user ID
    "U67890DEF",  # Another user's ID
]

# In message handlers:
async def handle_message(event, say):
    user_id = event['user']

    if user_id not in ALLOWED_USER_IDS:
        await say("⛔ Unauthorized. Contact admin for access.")
        return

    # ... rest of handler
```

To find user IDs:
1. Click on a user in Slack
2. Click **"..."** (More)
3. Click **"Copy member ID"**

### Resource Limits

Add to `compose.yaml`:

```yaml
slack-bot:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
```

### Multiple Workspaces

Run separate bot instances:

```yaml
services:
  slack-bot-workspace1:
    # ... config ...
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN_WS1}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN_WS1}

  slack-bot-workspace2:
    # ... config ...
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN_WS2}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN_WS2}
```

---

## Monitoring

### View Logs

```bash
# Live logs
docker compose logs slack-bot -f

# Recent logs
docker compose logs slack-bot --tail=100

# Search for errors
docker compose logs slack-bot | grep ERROR

# View user activity
docker compose logs slack-bot | grep "Received message"
```

### Check Sessions

```bash
# List all sessions
docker compose exec slack-bot ls -la /app/slack_sessions/

# View specific session
docker compose exec slack-bot cat /app/slack_sessions/U12345678.json

# Count active sessions
docker compose exec slack-bot ls /app/slack_sessions/*.json 2>/dev/null | wc -l
```

### Resource Usage

```bash
# Check memory and CPU
docker stats slack-bot

# Check disk usage
docker compose exec slack-bot df -h

# Check session storage size
docker compose exec slack-bot du -sh /app/slack_sessions/
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment instructions.

**Quick summary:**

1. Create VPS (2GB RAM minimum)
2. Install Docker
3. Clone repo
4. Set up `.env` with tokens
5. Run `docker compose up -d slack-bot`

Bot runs 24/7, no open ports needed (Socket Mode).

**Cost:** $6-12/month for basic droplet

---

## Features

| Feature | Status | Notes |
|---------|--------|-------|
| Slash Commands | ✓ | All 7 commands |
| Direct Messages | ✓ | Full support |
| Channel Messages | ✓ | Via @mention |
| Threading | ✓ | Replies in threads |
| Per-user sessions | ✓ | Persistent |
| Working directories | ✓ | Per user |
| Long messages | ✓ | Auto-split at 3000 chars |
| Tool indicators | ✓ | 🔧 READ, BASH, etc. |
| Thinking blocks | ✓ | Toggle with /showthinking |
| Error handling | ✓ | Graceful errors |
| Socket Mode | ✓ | No webhooks needed |
| File logging | ✓ | Optional (FILE_LOGGING=true) |

---

## Comparison: Slack vs Telegram

| Feature | Slack Bot | Telegram Bot |
|---------|-----------|--------------|
| Setup complexity | Medium (2 tokens + OAuth) | Easy (1 token) |
| Commands | Slash commands | Bot commands |
| DMs | ✓ | ✓ |
| Channels | ✓ Native support | ✗ |
| Threading | ✓ | Limited |
| Rich UI | ✓ Block Kit | Limited |
| Enterprise ready | ✓✓✓ | ✓ |
| Deployment | Identical | Identical |
| Code sharing | 95% | 95% |

Both bots share the same core logic via `bot_common.py`!

---

## Security Best Practices

1. **Never commit tokens** - Add `.env` to `.gitignore`
2. **Use user whitelist** - Restrict access to authorized users
3. **Limit workspace access** - Mount only safe directories
4. **Monitor usage** - Check logs regularly
5. **Rotate tokens** - Regenerate tokens periodically
6. **Set resource limits** - Prevent resource abuse
7. **Use separate workspaces** - Don't share bot across orgs

---

## See Also

- [Main README](../README.md) - Project overview
- [Authentication Guide](AUTHENTICATION.md) - Token setup
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Slack API Docs](https://api.slack.com/) - Official Slack documentation
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python) - Claude SDK
