# Slack Bot Setup Guide

This guide walks you through setting up and testing the Claude Code Slack bot.

## Prerequisites

1. **Slack Workspace** - Admin access to install apps
2. **Claude Code SDK** authentication configured
3. **Python 3.11+** installed

## Step 1: Create a Slack App

### 1.1 Create New App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter:
   - **App Name**: `Claude Code Bot` (or your preferred name)
   - **Workspace**: Select your workspace
5. Click **"Create App"**

### 1.2 Configure Bot Token Scopes

1. In the left sidebar, go to **"OAuth & Permissions"**
2. Scroll to **"Scopes" → "Bot Token Scopes"**
3. Click **"Add an OAuth Scope"** and add these scopes:

   **Required scopes:**
   - `app_mentions:read` - See when bot is mentioned
   - `chat:write` - Send messages
   - `commands` - Add slash commands
   - `im:history` - Read DM history
   - `im:read` - View basic DM info
   - `im:write` - Send DMs
   - `channels:history` - Read channel messages (if using in channels)
   - `channels:read` - View basic channel info (if using in channels)

4. Scroll up and click **"Install to Workspace"**
5. Review permissions and click **"Allow"**
6. **Copy the "Bot User OAuth Token"** (starts with `xoxb-...`)
   - Save this as `SLACK_BOT_TOKEN`

### 1.3 Enable Socket Mode

Socket Mode allows the bot to connect without exposing a public webhook endpoint.

1. In the left sidebar, go to **"Socket Mode"**
2. Toggle **"Enable Socket Mode"** to ON
3. Enter a token name (e.g., "Claude Bot Socket Token")
4. Click **"Generate"**
5. **Copy the "App-Level Token"** (starts with `xapp-...`)
   - Save this as `SLACK_APP_TOKEN`
6. Click **"Done"**

### 1.4 Enable Events

1. In the left sidebar, go to **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. Under **"Subscribe to bot events"**, add:
   - `app_mention` - When bot is mentioned
   - `message.im` - Direct messages to bot
   - `message.channels` - Messages in channels (optional)
4. Click **"Save Changes"**

### 1.5 Create Slash Commands

1. In the left sidebar, go to **"Slash Commands"**
2. Click **"Create New Command"** for each:

| Command | Description | Usage Hint |
|---------|-------------|------------|
| `/start` | Show welcome message | |
| `/help` | Show help message | |
| `/setcwd` | Set working directory | `/setcwd /path/to/dir` |
| `/getcwd` | Show current working directory | |
| `/searchcwd` | Search for directories | `/searchcwd projects` |
| `/reset` | Clear conversation history | |

3. For each command, leave **Request URL** empty (Socket Mode handles this)
4. Click **"Save"**

### 1.6 Configure App Home

1. In the left sidebar, go to **"App Home"**
2. Under **"Show Tabs"**:
   - Enable **"Messages Tab"**
   - Check **"Allow users to send Slash commands and messages from the messages tab"**
3. Click **"Save Changes"**

## Step 2: Set Up Environment

### 2.1 Create or Update `.env` File

```bash
# Create .env if it doesn't exist
touch .env
```

Add the following to your `.env` file:

```bash
# Claude Code authentication (required)
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Slack bot tokens (required)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Optional: Default working directory
SLACK_WORKING_DIRECTORY=/workspace
SLACK_WORKSPACE=./workspace
```

**Replace:**
- `sk-ant-oat01-...` with your Claude Code OAuth token
- `xoxb-...` with your Bot User OAuth Token (from Step 1.2)
- `xapp-...` with your App-Level Token (from Step 1.3)

## Step 3: Install Dependencies

```bash
# Install all dependencies (includes Slack bot)
pip install -r server/requirements.txt

# Or install Slack SDK individually
pip install slack-bolt
```

## Step 4: Run the Bot

### Option A: Run Locally (Without Docker)

```bash
# From the project root
python server/slack_bot.py
```

You should see:
```
INFO - Initializing Slack bot...
INFO - Starting Slack bot in Socket Mode...
INFO - Bot is ready to receive messages!
```

### Option B: Run with Docker

```bash
# Build image
docker compose build

# Start Slack bot only
docker compose up -d slack-bot

# View logs
docker compose logs slack-bot -f
```

## Step 5: Test the Bot

### Test in Direct Messages

1. Open Slack
2. In the left sidebar, under **"Apps"**, find your bot
3. Click on the bot to open a DM
4. Send `/start` - You should get a welcome message
5. Try these commands:
   - `/help` - View available commands
   - `/setcwd /tmp` - Set working directory
   - `/getcwd` - Verify working directory
   - Send a message: `Hello! What can you do?`
   - Ask Claude: `List files in the current directory`

### Test in Channels

1. Go to any channel where the bot has been invited
2. Mention the bot: `@Claude Code Bot hello!`
3. The bot should respond in the channel (or in a thread)

### Test Commands

| Command | Expected Result |
|---------|----------------|
| `/start` | Welcome message with bot info |
| `/help` | List of available commands |
| `/setcwd /workspace` | Confirmation that directory was set |
| `/getcwd` | Display current working directory |
| `/searchcwd documents` | List of matching directories |
| `/reset` | Confirmation that conversation was cleared |

### Test Claude Interactions

1. **Simple question:**
   ```
   What programming languages do you support?
   ```
   Expected: Claude responds with information

2. **File listing:**
   ```
   List all files in the current directory
   ```
   Expected: Claude uses Bash tool and shows file list with "🔧 BASH" indicator

3. **File reading:**
   ```
   Read the README.md file
   ```
   Expected: Claude uses Read tool and shows contents with "🔧 READ" indicator

4. **Multi-turn conversation:**
   ```
   Message 1: What files are in the current directory?
   Message 2: Read the first file you found
   Message 3: Summarize what you just read
   ```
   Expected: Claude maintains context across all messages

## Step 6: Invite Bot to Channels (Optional)

If you want the bot to work in channels:

1. Go to a channel
2. Click the channel name at the top
3. Click **"Integrations"** tab
4. Click **"Add apps"**
5. Search for your bot and click **"Add"**

Now you can mention the bot in that channel: `@Claude Code Bot help me with this code`

## Troubleshooting

### Bot doesn't respond

**Check:**
1. Is the bot running? (Check terminal or Docker logs)
2. Are tokens correct in `.env`?
3. Is Socket Mode enabled in Slack app settings?
4. Are Event Subscriptions enabled?

**Solution:**
```bash
# Check environment variables
cat .env | grep SLACK

# Restart bot
docker compose restart slack-bot

# View logs
docker compose logs slack-bot --tail=50
```

### "Invalid auth" or token errors

**Check:**
1. Is `SLACK_BOT_TOKEN` set correctly? (starts with `xoxb-`)
2. Is `SLACK_APP_TOKEN` set correctly? (starts with `xapp-`)
3. Did you reinstall the app after changing scopes?

**Solution:**
```bash
# Verify tokens in .env
cat .env | grep SLACK_

# Test bot token (from your machine)
curl -H "Authorization: Bearer xoxb-your-token" \
  https://slack.com/api/auth.test

# Should return: "ok": true
```

### Bot sees messages but doesn't respond

**Check:**
1. Are Event Subscriptions enabled?
2. Are bot scopes correct?
3. Are there errors in logs?

**Solution:**
```bash
# Check logs for errors
docker compose logs slack-bot | grep ERROR

# Verify bot permissions in Slack:
# Settings → OAuth & Permissions → Scopes
```

### Claude SDK errors

**Check:**
1. Is `CLAUDE_CODE_OAUTH_TOKEN` set?
2. Is the token valid? (Not expired)

**Solution:**
```bash
# Verify Claude token
docker compose exec slack-bot env | grep CLAUDE_CODE_OAUTH_TOKEN

# Regenerate token on host machine
claude setup-token

# Update .env and restart
docker compose restart slack-bot
```

### Sessions not persisting

**Check:**
1. Does `slack_sessions/` directory exist?
2. Does bot have write permissions?
3. Is Docker volume properly mounted?

**Solution:**
```bash
# Check session directory
docker compose exec slack-bot ls -la /app/slack_sessions/

# View a session file
docker compose exec slack-bot cat /app/slack_sessions/U12345678.json
```

### Commands not working

**Check:**
1. Are slash commands created in Slack app settings?
2. Is Socket Mode enabled?
3. Is Request URL empty (Socket Mode doesn't need it)?

**Solution:**
1. Go to https://api.slack.com/apps
2. Select your app
3. Go to **Slash Commands**
4. Verify all commands are listed
5. Ensure Request URL is empty

## Advanced Configuration

### User Access Control

Add user whitelist to limit bot access:

```python
# In slack_bot.py, add at the top:
ALLOWED_USER_IDS = [
    "U12345ABC",  # Your Slack user ID
    "U67890DEF",  # Another user's ID
]

# In handle_message and handle_mention:
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

### Custom System Prompt

Modify the system prompt in bot_common.py:

```python
system_prompt = """You are Claude Code, a helpful AI assistant.
You specialize in Python development and DevOps tasks.
Always be concise and provide code examples when relevant."""
```

### Resource Limits

Add to compose.yaml:

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

Run separate bot instances for different workspaces:

```yaml
# compose.yaml
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
docker compose exec slack-bot ls /app/slack_sessions/*.json | wc -l
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

## Deployment to Production

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for complete deployment instructions to Digital Ocean or other VPS providers.

**Quick summary:**
1. Create droplet (2GB RAM minimum)
2. Install Docker
3. Clone repo
4. Set up `.env` with tokens
5. Run `docker compose up -d slack-bot`
6. Bot runs 24/7, no open ports needed (Socket Mode)

**Cost:** $6-12/month for Slack bot only

## Security Best Practices

1. **Never commit tokens** - Add `.env` to `.gitignore`
2. **Use user whitelist** - Restrict access to authorized users
3. **Limit workspace access** - Mount only safe directories
4. **Monitor usage** - Check logs regularly
5. **Rotate tokens** - Regenerate tokens periodically
6. **Set resource limits** - Prevent resource abuse
7. **Use separate workspaces** - Don't share bot across orgs

## Next Steps

After setup:
1. Customize bot responses in slack_bot.py
2. Add custom commands
3. Implement user authentication/authorization
4. Set up monitoring and alerting
5. Deploy to production
6. Share with your team!

## Getting Help

- Check logs: `docker compose logs slack-bot -f`
- View sessions: `docker compose exec slack-bot ls /app/slack_sessions/`
- Test bot locally before deploying
- Verify tokens: `curl -H "Authorization: Bearer $SLACK_BOT_TOKEN" https://slack.com/api/auth.test`
- Review Slack API docs: https://api.slack.com/

## Comparison with Telegram Bot

| Feature | Slack Bot | Telegram Bot |
|---------|-----------|--------------|
| Setup complexity | Medium (OAuth + Socket Mode) | Easy (Just bot token) |
| Commands | ✓ Slash commands | ✓ Bot commands |
| DMs | ✓ | ✓ |
| Channels | ✓ Native support | ✗ |
| Threading | ✓ | Limited |
| Rich UI | ✓ Block Kit | Limited |
| Enterprise ready | ✓✓✓ | ✓ |
| Deployment | Identical | Identical |
| Session management | Shared codebase | Shared codebase |

Both bots share 95% of code via `bot_common.py`!
