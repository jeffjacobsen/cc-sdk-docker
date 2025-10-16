# Testing the Telegram Bot

This guide walks you through testing the Claude Code Telegram bot.

## Prerequisites

1. **Python 3.11+** installed
2. **Claude Code SDK** authentication configured
3. **Telegram account**

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "My Claude Code Bot")
   - Choose a username (must end in 'bot', e.g., "my_claude_code_bot")
4. BotFather will give you an **API token** that looks like: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`
5. **Save this token** - you'll need it in the next step

## Step 2: Set Up Environment

1. **Create a `.env` file** in the project root if you don't have one:
   ```bash
   touch .env
   ```

2. **Add your Telegram bot token** to `.env`:
   ```bash
   echo "TELEGRAM_BOT_API_KEY=YOUR_TOKEN_HERE" >> .env
   ```

   Replace `YOUR_TOKEN_HERE` with the token from BotFather.

3. **Add your Claude Code OAuth token** (if not already present):
   ```bash
   echo "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..." >> .env
   ```

4. **Optionally set a default working directory**:
   ```bash
   echo "WORKING_DIRECTORY=/path/to/your/workspace" >> .env
   ```

Your `.env` file should look like this:
```
TELEGRAM_BOT_API_KEY=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
WORKING_DIRECTORY=/path/to/workspace
```

## Step 3: Install Dependencies

```bash
# Install all dependencies (includes Telegram bot + FastAPI server)
pip install -r server/requirements.txt

# Or install individually
pip install python-telegram-bot python-dotenv claude-agent-sdk
```

## Step 4: Run the Bot

```bash
# From the project root
python server/telegram_bot.py
```

You should see:
```
INFO - Initializing Telegram bot...
INFO - Starting Telegram bot polling...
INFO - Bot is ready to receive messages!
```

## Step 5: Test the Bot

### Basic Tests

1. **Open Telegram** and search for your bot by username
2. **Start a conversation** by clicking "START" or sending `/start`
3. **You should receive a welcome message** with available commands

### Command Tests

Test each command:

| Command | What to Test | Expected Result |
|---------|-------------|-----------------|
| `/start` | Send this command | Welcome message with bot info |
| `/help` | Send this command | List of available commands |
| `/setcwd /tmp` | Set working directory to /tmp | Confirmation message with absolute path |
| `/getcwd` | Get current working directory | Display current directory |
| `/searchcwd Documents` | Search for directories | List of matching directories |
| `/reset` | Clear conversation | Confirmation that session cleared |

### Message Tests

Test regular messages (these interact with Claude):

1. **Simple question:**
   ```
   Hello! What can you help me with?
   ```
   Expected: Claude responds with its capabilities

2. **File listing:**
   ```
   List all files in the current directory
   ```
   Expected: Claude uses the Bash tool and shows file list, with "🔧 BASH" indicator

3. **File reading:**
   ```
   Read the README.md file
   ```
   Expected: Claude uses the Read tool and shows file contents, with "🔧 READ" indicator

4. **File creation:**
   ```
   Create a file called test.txt with the content "Hello from Telegram!"
   ```
   Expected: Claude uses the Write tool and confirms creation, with "🔧 WRITE" indicator

5. **Multi-turn conversation:**
   ```
   Message 1: What files are in the current directory?
   Message 2: Now read the first file you found
   Message 3: What was in that file?
   ```
   Expected: Claude maintains context across all three messages

## Step 6: Verify Features

### Per-User Sessions

1. Have a friend also connect to your bot (or use a second Telegram account)
2. Both users send messages
3. Verify that:
   - Each user gets their own responses
   - Each user's conversation context is separate
   - Sessions are stored in `telegram_sessions/` directory

### Working Directory Configuration

1. User A: `/setcwd /tmp`
2. User B: `/setcwd /home/user`
3. Both users: `List files here`
4. Verify each user sees files from their configured directory

### Session Persistence

1. Send a message: `Remember this number: 42`
2. Claude responds
3. Send another message: `What number did I ask you to remember?`
4. Claude should respond with: 42

### Long Message Handling

1. Ask Claude to generate a very long response:
   ```
   Write a detailed explanation of how TCP/IP networking works
   ```
2. Verify that long responses are split across multiple messages with "(continued)" indicators

## Step 7: Check Logs and Session Data

### View Logs

The bot logs to console. Look for:
```
INFO - User 12345678 (username) started the bot
INFO - Received message from user 12345678
INFO - Using working directory for user 12345678: /path/to/dir
INFO - Tool used: Read
INFO - Received session ID: abc-123-def
INFO - Saved session for user 12345678
```

### Inspect Session Files

```bash
# List session files
ls -la telegram_sessions/

# View a session file
cat telegram_sessions/12345678.json
```

Expected format:
```json
{
  "session_id": "abc-123-def-456",
  "cwd": "/path/to/workspace",
  "created_at": "2025-01-15T10:30:00Z",
  "last_updated": "2025-01-15T11:45:00Z"
}
```

## Troubleshooting

### Bot doesn't respond to messages

**Check:**
1. Is the bot process still running? (Check terminal)
2. Is the `TELEGRAM_BOT_API_KEY` correct in `.env`?
3. Did you start a conversation with the bot in Telegram?

**Solution:**
```bash
# Restart the bot
python server/telegram_bot.py
```

### "TELEGRAM_BOT_API_KEY not found" error

**Cause:** Missing or incorrect environment variable

**Solution:**
```bash
# Check .env file exists
cat .env | grep TELEGRAM_BOT_API_KEY

# If missing, add it
echo "TELEGRAM_BOT_API_KEY=your_token_here" >> .env
```

### Claude SDK errors

**Check:**
1. Is `CLAUDE_CODE_OAUTH_TOKEN` set in `.env`?
2. Is the token valid? (Not expired)
3. Is the Claude Code SDK installed?

**Solution:**
```bash
# Verify Claude SDK is installed
pip show claude-agent-sdk

# Reinstall if needed
pip install --upgrade claude-agent-sdk
```

### File operations fail

**Check:**
1. Is the working directory set correctly? (`/getcwd`)
2. Does the directory exist and have proper permissions?
3. Is the path absolute?

**Solution:**
```
/setcwd /absolute/path/to/directory
/getcwd
```

### Session not persisting

**Check:**
1. Does `telegram_sessions/` directory exist?
2. Does the bot have write permissions?

**Solution:**
```bash
# Create directory if missing
mkdir -p telegram_sessions

# Check permissions
ls -ld telegram_sessions
```

## Advanced Testing

### Load Testing

Test with multiple concurrent users:
```python
# test_bot_load.py
import asyncio
from telegram import Bot

async def send_message(bot_token, chat_id, message):
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

# Run with different chat IDs
```

### Error Handling

Test error scenarios:
1. Send a very long message (>10,000 characters)
2. Send special characters and emojis
3. Request to read a non-existent file
4. Request to write to a read-only directory

### Tool Permission Testing

Modify [telegram_bot.py:488](server/telegram_bot.py#L488) to test with different tool sets:
```python
"allowed_tools": ["Read"],  # Only allow Read
"allowed_tools": ["Read", "Write"],  # No Bash
"allowed_tools": [],  # No tools at all
```

## Next Steps

After testing, you can:
1. Deploy to a server for 24/7 operation
2. Add more commands (e.g., `/status`, `/tools`, `/models`)
3. Implement user authentication/authorization
4. Add rate limiting per user
5. Store sessions in a database instead of JSON files
6. Add webhook support (instead of polling)
7. Implement inline keyboard buttons for common actions
8. Add support for file uploads (user sends files to Claude)

## Security Considerations

- **Never commit `.env` files** to version control
- **Limit bot access** - Only share bot username with trusted users
- **Validate user permissions** - Consider adding user whitelist
- **Monitor usage** - Log all requests and tool usage
- **Set working directory restrictions** - Don't allow access to sensitive directories
- **Rate limiting** - Implement per-user rate limits to prevent abuse

## Getting Help

If you encounter issues:
1. Check the bot logs in terminal
2. Review session files in `telegram_sessions/`
3. Test with `/reset` to clear state
4. Verify `.env` configuration
5. Check Claude Code SDK authentication: `claude-code auth status`
