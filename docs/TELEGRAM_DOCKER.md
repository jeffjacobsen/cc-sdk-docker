# Running Telegram Bot in Docker

This guide shows you how to run the Claude Code Telegram bot as a Docker container alongside the FastAPI server.

## Architecture

The Docker setup includes two services:
1. **server** - FastAPI REST API server (port 3000)
2. **telegram-bot** - Telegram bot for interactive chat

Both services:
- Share the same Docker image (`claude-code-sdk:latest`)
- Use the same Claude Code OAuth token
- Have isolated workspaces and sessions
- Run as the `claude` user for security

## Quick Start

### 1. Set Up Environment Variables

Edit your `.env` file to include Telegram bot configuration:

```bash
# Claude Code authentication (required for both services)
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...

# Telegram bot configuration
TELEGRAM_BOT_API_KEY=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Optional: Set working directory for Telegram bot
TELEGRAM_WORKING_DIRECTORY=/workspace

# Optional: Set host directory to mount as workspace
TELEGRAM_WORKSPACE=./workspace
```

### 2. Get Your Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the API token BotFather gives you
4. Add it to `.env` as `TELEGRAM_BOT_API_KEY`

### 3. Create Workspace Directory (Optional)

```bash
# Create a workspace directory for the bot to access
mkdir -p workspace
```

### 4. Build and Start Services

```bash
# Build the image (includes Telegram dependencies)
docker compose build

# Start both services
docker compose up -d

# Or start only the Telegram bot
docker compose up -d telegram-bot
```

### 5. Verify Bot is Running

```bash
# Check container status
docker compose ps

# View bot logs
docker compose logs telegram-bot -f
```

You should see:
```
INFO - Initializing Telegram bot...
INFO - Starting Telegram bot polling...
INFO - Bot is ready to receive messages!
```

### 6. Test in Telegram

1. Open Telegram
2. Search for your bot by username
3. Send `/start`
4. Chat with Claude!

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | - | Claude Code authentication token |
| `TELEGRAM_BOT_API_KEY` | Yes | - | Telegram Bot API token from BotFather |
| `TELEGRAM_WORKING_DIRECTORY` | No | `/workspace` | Default working directory inside container |
| `TELEGRAM_WORKSPACE` | No | `./workspace` | Host directory to mount as workspace |

### Volume Mounts

The Telegram bot service uses several volumes:

```yaml
volumes:
  # Development: Live code changes
  - .:/app

  # Authentication: Shared with server
  - claude-auth:/home/claude/.claude

  # Workspace: User files (configurable)
  - ${TELEGRAM_WORKSPACE:-./workspace}:/workspace

  # Sessions: Persistent conversation history
  - telegram-sessions:/app/telegram_sessions
```

## Usage Examples

### Run Both Services Together

```bash
# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs from both services
docker compose logs -f
```

### Run Only the Telegram Bot

```bash
# Start only telegram-bot
docker compose up -d telegram-bot

# View logs
docker compose logs telegram-bot -f
```

### Stop Services

```bash
# Stop all services
docker compose down

# Stop only telegram-bot
docker compose stop telegram-bot
```

### Restart After Changes

```bash
# Restart telegram-bot (useful after code changes)
docker compose restart telegram-bot

# Rebuild and restart
docker compose up -d --build telegram-bot
```

## Managing Sessions

### View Session Data

Sessions are stored in a Docker volume. To inspect:

```bash
# List session files
docker compose exec telegram-bot ls -la /app/telegram_sessions/

# View a specific session
docker compose exec telegram-bot cat /app/telegram_sessions/12345678.json
```

### Clear All Sessions

```bash
# Remove all session files
docker compose exec telegram-bot rm -rf /app/telegram_sessions/*
```

### Backup Sessions

```bash
# Copy sessions to host
docker compose cp telegram-bot:/app/telegram_sessions ./telegram_sessions_backup

# Restore sessions
docker compose cp ./telegram_sessions_backup/. telegram-bot:/app/telegram_sessions/
```

## Workspace Management

### Access Bot's Workspace

```bash
# List files in workspace
docker compose exec telegram-bot ls -la /workspace

# Read a file
docker compose exec telegram-bot cat /workspace/example.txt

# Create a test file
echo "Hello from host" > workspace/test.txt

# Ask bot to read it in Telegram:
# "Read the file test.txt"
```

### Mount Different Workspace

Edit `.env`:
```bash
TELEGRAM_WORKSPACE=/path/to/your/project
```

Then restart:
```bash
docker compose up -d telegram-bot
```

## Monitoring and Debugging

### View Live Logs

```bash
# Follow logs (Ctrl+C to exit)
docker compose logs telegram-bot -f

# View last 100 lines
docker compose logs telegram-bot --tail=100
```

### Enter Container Shell

```bash
# As root
docker compose exec -u root telegram-bot bash

# As claude user
docker compose exec telegram-bot bash
```

### Check Bot Health

```bash
# Check if bot process is running
docker compose exec telegram-bot ps aux | grep telegram_bot.py

# Check Python environment
docker compose exec telegram-bot python --version
docker compose exec telegram-bot pip list | grep telegram
```

### Test Bot Locally Inside Container

```bash
# Enter container
docker compose exec telegram-bot bash

# Run test script
python server/test_telegram_bot.py

# Manually start bot (for debugging)
python server/telegram_bot.py
```

## Troubleshooting

### Bot container exits immediately

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

# Restart with logs
docker compose up telegram-bot
```

### "Module not found" errors

**Cause:** Dependencies not installed

**Solution:**
```bash
# Rebuild image to include dependencies
docker compose build --no-cache telegram-bot

# Restart
docker compose up -d telegram-bot
```

### Bot doesn't respond to messages

**Check:**
1. Is the container running? `docker compose ps`
2. Are there errors in logs? `docker compose logs telegram-bot`
3. Did you start a chat with the bot in Telegram?
4. Is the bot token correct?

**Solution:**
```bash
# Restart bot
docker compose restart telegram-bot

# Check logs for errors
docker compose logs telegram-bot --tail=50
```

### Authentication errors with Claude SDK

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
echo "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..." > .env

# Restart to reload environment
docker compose up -d telegram-bot
```

### Permission errors in workspace

**Check permissions:**
```bash
docker compose exec telegram-bot ls -ld /workspace
```

**Solution:**
```bash
# Fix host directory permissions
chmod -R 755 workspace

# Or run bot as root (not recommended)
docker compose exec -u root telegram-bot bash
```

### Sessions not persisting across restarts

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

## Production Deployment

### Run with Docker Compose on a VPS

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

### Using Docker Run (Without Compose)

```bash
# Build image
docker build -t claude-code-sdk:latest .

# Run telegram bot
docker run -d \
  --name claude-telegram-bot \
  --restart unless-stopped \
  -e CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..." \
  -e TELEGRAM_BOT_API_KEY="1234567890:ABC..." \
  -e WORKING_DIRECTORY=/workspace \
  -v $(pwd)/workspace:/workspace \
  -v telegram-sessions:/app/telegram_sessions \
  -v claude-auth:/home/claude/.claude \
  claude-code-sdk:latest \
  bash -c "pip install -r /app/server/requirements.txt && su claude -c 'python /app/server/telegram_bot.py'"
```

### Monitoring in Production

```bash
# Auto-restart on failure
docker compose up -d --restart=always telegram-bot

# Monitor logs with logrotate
docker compose logs telegram-bot -f | tee -a telegram-bot.log

# Set up systemd service
sudo nano /etc/systemd/system/claude-telegram-bot.service
```

Example systemd service:
```ini
[Unit]
Description=Claude Telegram Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/cc-sdk-docker
ExecStart=/usr/bin/docker compose up -d telegram-bot
ExecStop=/usr/bin/docker compose stop telegram-bot
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable claude-telegram-bot
sudo systemctl start claude-telegram-bot
```

## Advanced Configuration

### Multiple Bots

Run multiple bot instances with different tokens:

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

Add resource constraints:

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

### Network Isolation

Isolate bot from server:

```yaml
services:
  telegram-bot:
    networks:
      - telegram-net

networks:
  telegram-net:
    driver: bridge
```

## Integration with Existing Services

### Share Workspace with Server

Both services can access the same workspace:

```yaml
services:
  server:
    volumes:
      - ./workspace:/workspace

  telegram-bot:
    volumes:
      - ./workspace:/workspace
```

Now files created via REST API are accessible via Telegram bot!

### Separate Workspaces

Keep workspaces isolated:

```yaml
services:
  server:
    volumes:
      - ./api-workspace:/workspace

  telegram-bot:
    volumes:
      - ./telegram-workspace:/workspace
```

## Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use strong bot tokens** - Generate new tokens for each deployment
3. **Restrict workspace access** - Don't mount sensitive directories
4. **Monitor bot usage** - Check logs regularly
5. **Update regularly** - Keep base image and dependencies updated
6. **Use non-root user** - Already configured (`claude` user)
7. **Limit resource usage** - Add CPU and memory limits
8. **Enable SSL/TLS** - For webhook mode (future enhancement)

## Next Steps

- Set up webhook mode instead of polling (more efficient)
- Add user authentication/authorization
- Implement rate limiting per user
- Set up centralized logging (e.g., ELK stack)
- Add monitoring (e.g., Prometheus + Grafana)
- Configure backups for session data
- Deploy behind reverse proxy (e.g., Nginx)

## Getting Help

- Check logs: `docker compose logs telegram-bot -f`
- View container details: `docker compose ps telegram-bot`
- Enter container: `docker compose exec telegram-bot bash`
- Test setup: `docker compose exec telegram-bot python server/test_telegram_bot.py`
- Review [TELEGRAM_TESTING.md](../server/TELEGRAM_TESTING.md) for non-Docker testing
