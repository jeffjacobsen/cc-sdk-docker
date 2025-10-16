# Deployment Guide - Digital Ocean

This guide shows you how to deploy the Claude Code SDK Docker container on a Digital Ocean droplet.

## Prerequisites

- Digital Ocean account
- Claude Code OAuth token (get with `claude setup-token` on your local machine)
- Basic familiarity with SSH and Linux commands

## Quick Deployment

### 1. Create a Digital Ocean Droplet

**Via Digital Ocean Dashboard:**

1. Go to https://cloud.digitalocean.com/droplets/new
2. Choose image: **Docker** (from Marketplace)
   - Or select **Ubuntu 24.04 LTS** if you want to install Docker manually
3. Choose droplet size:
   - **Minimum**: Basic - 2 GB RAM / 1 CPU ($12/month)
   - **Recommended**: Basic - 4 GB RAM / 2 CPU ($24/month)
   - For production with multiple users: 8 GB+ RAM
4. Choose datacenter region (closest to your users)
5. Add SSH key or use password authentication
6. Create droplet

Wait 1-2 minutes for the droplet to initialize.

### 2. SSH into Your Droplet

```bash
# Get your droplet's IP from Digital Ocean dashboard
ssh root@your-droplet-ip

# If using SSH key:
ssh -i ~/.ssh/your_key root@your-droplet-ip
```

### 3. Install Docker (if not using Docker image)

If you chose Ubuntu instead of the Docker marketplace image:

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### 4. Clone the Repository

```bash
# Install git if needed
apt install git -y

# Clone the repository
cd /opt
git clone https://github.com/your-username/cc-sdk-docker.git
cd cc-sdk-docker
```

Or upload your local copy:
```bash
# On your local machine
rsync -avz --exclude 'node_modules' --exclude '.git' \
  /path/to/cc-sdk-docker/ root@your-droplet-ip:/opt/cc-sdk-docker/
```

### 5. Configure Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit with your token
nano .env
```

Add your OAuth token and optionally bot tokens (Telegram/Slack):
```bash
# Required: Claude Code authentication
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Optional: FastAPI server port
PORT=3000

# Optional: Telegram bot (if deploying bot)
TELEGRAM_BOT_API_KEY=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_WORKING_DIRECTORY=/workspace
TELEGRAM_WORKSPACE=./workspace

# Optional: Slack bot (if deploying bot)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_WORKING_DIRECTORY=/workspace
SLACK_WORKSPACE=./workspace
```

Save and exit (Ctrl+X, then Y, then Enter)

### 6. Build and Start the Container

```bash
# Build the image
./build.sh

# Start the FastAPI server only
docker compose up -d server

# OR: Start both server and Telegram bot
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs server -f
docker compose logs telegram-bot -f
```

### 7. Configure Firewall

```bash
# Allow SSH (if using ufw)
ufw allow 22/tcp

# Allow HTTP (port 3000) - only if deploying FastAPI server
ufw allow 3000/tcp

# Note: Telegram bot doesn't need open ports (it connects outbound)

# Enable firewall
ufw enable

# Check status
ufw status
```

### 8. Test the Deployment

#### Test FastAPI Server

```bash
# From the droplet
curl http://localhost:3000/health

# From your local machine
curl http://your-droplet-ip:3000/health
```

You should see:
```json
{
  "status": "healthy",
  "authenticated": true,
  "active_sessions": 0,
  "timestamp": "..."
}
```

#### Test Telegram Bot

If you deployed the Telegram bot:

```bash
# Check bot logs
docker compose logs telegram-bot --tail=50

# You should see:
# INFO - Initializing Telegram bot...
# INFO - Starting Telegram bot polling...
# INFO - Bot is ready to receive messages!
```

Then open Telegram, search for your bot by username, and send `/start` to test it!

## Telegram Bot Deployment

The Telegram bot can run on the same droplet as the FastAPI server, or on a separate droplet.

### Deployment Options

#### Option 1: Telegram Bot Only (No FastAPI Server)

If you only want to run the Telegram bot:

```bash
# Start only the Telegram bot
docker compose up -d telegram-bot

# Check status
docker compose ps telegram-bot

# View logs
docker compose logs telegram-bot -f
```

**Benefits:**
- Smaller resource footprint (2GB RAM is sufficient)
- No need for open ports (bot connects outbound)
- Simpler firewall configuration

**Droplet Sizing:**
- **Minimum**: 1 GB RAM / 1 CPU ($6/month)
- **Recommended**: 2 GB RAM / 1 CPU ($12/month)

#### Option 2: Both Services on One Droplet

Run both FastAPI server and Telegram bot:

```bash
# Start both services
docker compose up -d

# Check status
docker compose ps

# View logs for both
docker compose logs -f
```

**Droplet Sizing:**
- **Minimum**: 2 GB RAM / 1 CPU ($12/month)
- **Recommended**: 4 GB RAM / 2 CPU ($24/month)

#### Option 3: Separate Droplets

For isolation and scaling:

1. **Droplet 1** - FastAPI server (for programmatic access)
2. **Droplet 2** - Telegram bot (for user interaction)

Both share the same Claude OAuth token but have separate workspaces.

### Getting Your Telegram Bot Token

Before deployment, get your bot token from Telegram:

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` to BotFather
3. Choose a name for your bot (e.g., "My Claude Assistant")
4. Choose a username ending in 'bot' (e.g., "my_claude_assistant_bot")
5. BotFather gives you an API token like: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`
6. Save this token securely

### Configure Telegram Bot

Add to your `.env` file on the droplet:

```bash
# Required
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
TELEGRAM_BOT_API_KEY=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Optional: Default working directory for all users
TELEGRAM_WORKING_DIRECTORY=/workspace

# Optional: Host directory to mount (for file access)
TELEGRAM_WORKSPACE=/opt/telegram-workspace
```

Create workspace directory:

```bash
# Create workspace on host
mkdir -p /opt/telegram-workspace
chmod 755 /opt/telegram-workspace
```

### Start and Test

```bash
# Start bot
docker compose up -d telegram-bot

# Monitor startup
docker compose logs telegram-bot -f

# Wait for: "Bot is ready to receive messages!"
```

Then in Telegram:
1. Search for your bot by username
2. Click START or send `/start`
3. Send `/setcwd /workspace` to set working directory
4. Ask Claude anything: "List files in current directory"

### Managing User Sessions

User sessions are stored persistently in a Docker volume:

```bash
# View session files
docker compose exec telegram-bot ls -la /app/telegram_sessions/

# View specific user session (user ID is the filename)
docker compose exec telegram-bot cat /app/telegram_sessions/12345678.json

# Clear all sessions (users will need to reconfigure)
docker compose exec telegram-bot rm -f /app/telegram_sessions/*.json

# Backup sessions
docker compose cp telegram-bot:/app/telegram_sessions ./telegram_sessions_backup
```

### Workspace Management

Each user can set their own working directory via `/setcwd` command:

```bash
# Create additional workspace directories
mkdir -p /opt/telegram-workspace/project1
mkdir -p /opt/telegram-workspace/project2

# Users can then:
# /setcwd /workspace/project1
# /setcwd /workspace/project2
```

To limit user access to specific directories, mount only those directories:

```yaml
# In compose.yaml
volumes:
  - /opt/safe-workspace:/workspace:ro  # Read-only
```

### Security Considerations for Telegram Bot

1. **Bot Token Security**
   - Never share your bot token publicly
   - Store in `.env` file, never in code
   - Regenerate if compromised (via BotFather: `/revoke`)

2. **User Access Control**
   - By default, anyone who finds your bot can use it
   - Consider adding user whitelist to `telegram_bot.py`:
   ```python
   ALLOWED_USER_IDS = [12345678, 87654321]  # Your Telegram user IDs

   async def handle_message(update, context):
       if update.effective_user.id not in ALLOWED_USER_IDS:
           await update.message.reply_text("Unauthorized")
           return
       # ... rest of handler
   ```

3. **Workspace Restrictions**
   - Mount only directories users should access
   - Use read-only mounts where possible
   - Never mount system directories (`/etc`, `/root`, etc.)

4. **Resource Limits**
   - Add memory limits to prevent abuse:
   ```yaml
   telegram-bot:
     deploy:
       resources:
         limits:
           memory: 1G
   ```

5. **Rate Limiting**
   - Consider implementing per-user rate limits
   - Monitor usage via logs

### Monitoring Telegram Bot

```bash
# View real-time logs
docker compose logs telegram-bot -f

# Check resource usage
docker stats telegram-bot

# View recent user activity
docker compose logs telegram-bot --tail=100 | grep "User"

# Monitor errors
docker compose logs telegram-bot | grep ERROR

# Check if bot is responsive
docker compose exec telegram-bot ps aux | grep telegram_bot
```

### Troubleshooting Telegram Bot

#### Bot doesn't respond

```bash
# Check if container is running
docker compose ps telegram-bot

# Check logs for errors
docker compose logs telegram-bot --tail=50

# Restart bot
docker compose restart telegram-bot
```

#### "Unauthorized" or token errors

```bash
# Verify token is set
docker compose exec telegram-bot env | grep TELEGRAM_BOT_API_KEY

# Test token validity (from your local machine)
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Should return bot info if token is valid
```

#### Bot uses too much memory

```bash
# Check memory usage
docker stats telegram-bot

# Clear old sessions
docker compose exec telegram-bot rm -f /app/telegram_sessions/*.json

# Add memory limit in compose.yaml
# Restart: docker compose up -d telegram-bot
```

#### Users report bot is slow

```bash
# Check Claude API latency in logs
docker compose logs telegram-bot | grep "session ID"

# Increase droplet resources in Digital Ocean dashboard
# Check for rate limits in logs

# Consider moving to larger droplet
```

### Updating Telegram Bot

```bash
cd /opt/cc-sdk-docker

# Pull latest changes
git pull

# Rebuild image
./build.sh

# Restart bot (preserves sessions via volume)
docker compose up -d telegram-bot

# Verify update
docker compose logs telegram-bot --tail=20
```

## Slack Bot Deployment

The Slack bot can run on the same droplet as the FastAPI server and/or Telegram bot, or on a separate droplet.

### Deployment Options

#### Option 1: Slack Bot Only (No Other Services)

If you only want to run the Slack bot:

```bash
# Start only the Slack bot
docker compose up -d slack-bot

# Check status
docker compose ps slack-bot

# View logs
docker compose logs slack-bot -f
```

**Benefits:**
- Smaller resource footprint (2GB RAM is sufficient)
- No need for open ports (Socket Mode connects outbound)
- Simpler firewall configuration

**Droplet Sizing:**
- **Minimum**: 1 GB RAM / 1 CPU ($6/month)
- **Recommended**: 2 GB RAM / 1 CPU ($12/month)

#### Option 2: Slack + FastAPI Server (or + Telegram)

Run multiple services on one droplet:

```bash
# Start Slack bot + FastAPI server
docker compose up -d server slack-bot

# Or all three services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

**Droplet Sizing:**
- **Minimum**: 2 GB RAM / 1 CPU ($12/month)
- **Recommended**: 4 GB RAM / 2 CPU ($24/month)

#### Option 3: Separate Droplets

For isolation and scaling:

1. **Droplet 1** - FastAPI server (for programmatic access)
2. **Droplet 2** - Telegram bot (for Telegram users)
3. **Droplet 3** - Slack bot (for Slack users)

All share the same Claude OAuth token but have separate workspaces.

### Getting Your Slack Bot Tokens

Before deployment, you need two tokens from Slack:

#### Step-by-Step Token Setup

1. **Create Slack App**
   - Go to https://api.slack.com/apps
   - Click **"Create New App"** → **"From scratch"**
   - Enter app name (e.g., "Claude Code Bot") and select workspace
   - Click **"Create App"**

2. **Configure OAuth Scopes**
   - In left sidebar → **"OAuth & Permissions"**
   - Scroll to **"Bot Token Scopes"**
   - Add these scopes:
     - `app_mentions:read`
     - `chat:write`
     - `commands`
     - `im:history`
     - `im:read`
     - `im:write`
     - `channels:history` (if using in channels)
     - `channels:read` (if using in channels)
   - Click **"Install to Workspace"** at top
   - Click **"Allow"**
   - **Copy "Bot User OAuth Token"** (starts with `xoxb-...`)
   - Save as `SLACK_BOT_TOKEN`

3. **Enable Socket Mode**
   - In left sidebar → **"Socket Mode"**
   - Toggle **"Enable Socket Mode"** to ON
   - Enter token name (e.g., "Socket Token")
   - Click **"Generate"**
   - **Copy "App-Level Token"** (starts with `xapp-...`)
   - Save as `SLACK_APP_TOKEN`

4. **Create Slash Commands**
   - In left sidebar → **"Slash Commands"**
   - Click **"Create New Command"** for each:
     - `/start` - Show welcome message
     - `/help` - Show help
     - `/setcwd` - Set working directory
     - `/getcwd` - Show current directory
     - `/searchcwd` - Search directories
     - `/reset` - Clear conversation
   - Leave **Request URL** empty (Socket Mode handles this)

5. **Enable Events**
   - In left sidebar → **"Event Subscriptions"**
   - Toggle **"Enable Events"** to ON
   - Under **"Subscribe to bot events"**, add:
     - `app_mention`
     - `message.im`
     - `message.channels` (if using in channels)
   - Click **"Save Changes"**

**Full setup guide**: [server/SLACK_SETUP.md](../server/SLACK_SETUP.md)

### Configure Slack Bot on Droplet

Add to your `.env` file on the droplet:

```bash
# Required
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Optional: Default working directory for all users
SLACK_WORKING_DIRECTORY=/workspace

# Optional: Host directory to mount (for file access)
SLACK_WORKSPACE=/opt/slack-workspace
```

Create workspace directory:

```bash
# Create workspace on host
mkdir -p /opt/slack-workspace
chmod 755 /opt/slack-workspace
```

### Start and Test

```bash
# Start bot
docker compose up -d slack-bot

# Monitor startup
docker compose logs slack-bot -f

# Wait for: "Bot is ready to receive messages!"
```

Then in Slack:
1. Search for your bot in Slack
2. Open a DM with the bot
3. Send `/start` to get welcome message
4. Send `/setcwd /workspace` to set working directory
5. Ask Claude anything: "List files in current directory"

### Managing User Sessions

User sessions are stored persistently in a Docker volume:

```bash
# View session files
docker compose exec slack-bot ls -la /app/slack_sessions/

# View specific user session (user ID is the filename)
docker compose exec slack-bot cat /app/slack_sessions/U12345ABC.json

# Clear all sessions (users will need to reconfigure)
docker compose exec slack-bot rm -f /app/slack_sessions/*.json

# Backup sessions
docker compose cp slack-bot:/app/slack_sessions ./slack_sessions_backup

# Restore sessions
docker compose cp ./slack_sessions_backup/. slack-bot:/app/slack_sessions/
```

### Workspace Management

Each user can set their own working directory via `/setcwd` command:

```bash
# Create additional workspace directories
mkdir -p /opt/slack-workspace/project1
mkdir -p /opt/slack-workspace/project2

# Users can then in Slack:
# /setcwd /workspace/project1
# /setcwd /workspace/project2
```

To limit user access to specific directories, mount only those directories:

```yaml
# In compose.yaml
volumes:
  - /opt/safe-workspace:/workspace:ro  # Read-only
```

### Security Considerations for Slack Bot

1. **Bot Token Security**
   - Never share your bot tokens publicly
   - Store in `.env` file, never in code
   - Regenerate if compromised (reinstall app in workspace)

2. **User Access Control**
   - By default, anyone in your Slack workspace can use the bot
   - Consider adding user whitelist to `slack_bot.py`:
   ```python
   ALLOWED_USER_IDS = [
       "U12345ABC",  # Your Slack user ID
       "U67890DEF",  # Another user's ID
   ]

   @app.event("message")
   async def handle_message(event, say):
       user_id = event['user']
       if user_id not in ALLOWED_USER_IDS:
           await say("⛔ Unauthorized. Contact admin for access.")
           return
       # ... rest of handler
   ```

3. **Workspace Restrictions**
   - Mount only directories users should access
   - Use read-only mounts where possible
   - Never mount system directories (`/etc`, `/root`, etc.)

4. **Resource Limits**
   - Add memory limits to prevent abuse:
   ```yaml
   slack-bot:
     deploy:
       resources:
         limits:
           memory: 1G
   ```

### Monitoring Slack Bot

```bash
# View real-time logs
docker compose logs slack-bot -f

# Check resource usage
docker stats slack-bot

# View recent user activity
docker compose logs slack-bot --tail=100 | grep "Received message"

# Monitor errors
docker compose logs slack-bot | grep ERROR

# Check if bot is responsive
docker compose exec slack-bot ps aux | grep slack_bot
```

### Troubleshooting Slack Bot

#### Bot doesn't respond

```bash
# Check if container is running
docker compose ps slack-bot

# Check logs for errors
docker compose logs slack-bot --tail=50

# Common issue: Missing tokens
docker compose exec slack-bot env | grep SLACK

# Restart bot
docker compose restart slack-bot
```

#### "Invalid auth" or token errors

```bash
# Verify tokens are set correctly
docker compose exec slack-bot env | grep SLACK_BOT_TOKEN
docker compose exec slack-bot env | grep SLACK_APP_TOKEN

# Test bot token validity (from your local machine)
curl -H "Authorization: Bearer xoxb-your-token" \
  https://slack.com/api/auth.test

# Should return: "ok": true
# If not, regenerate tokens in Slack app settings
```

#### Bot sees messages but doesn't respond

```bash
# Check Event Subscriptions are enabled
# Go to: https://api.slack.com/apps → Your App → Event Subscriptions

# Check bot scopes
# Go to: https://api.slack.com/apps → Your App → OAuth & Permissions

# View detailed error logs
docker compose logs slack-bot | grep -A 5 ERROR
```

#### Sessions not persisting

```bash
# Check session volume
docker volume ls | grep slack-sessions

# View sessions directory
docker compose exec slack-bot ls -la /app/slack_sessions/

# If empty, check bot has write permissions
docker compose exec slack-bot touch /app/slack_sessions/test.txt
docker compose exec slack-bot rm /app/slack_sessions/test.txt
```

### Updating Slack Bot

```bash
cd /opt/cc-sdk-docker

# Pull latest changes
git pull

# Rebuild image
./build.sh

# Restart bot (preserves sessions via volume)
docker compose up -d slack-bot

# Verify update
docker compose logs slack-bot --tail=20
```

### Slack Bot vs Telegram Bot

| Feature | Slack Bot | Telegram Bot |
|---------|-----------|--------------|
| Setup complexity | Medium (2 tokens + OAuth) | Easy (1 token) |
| Open ports needed | No (Socket Mode) | No (polling) |
| Channel support | ✓ Native | ✗ |
| Threading | ✓ | Limited |
| Rich UI | ✓ Block Kit | Limited |
| Enterprise ready | ✓✓✓ | ✓ |
| Deployment | Identical | Identical |
| Resource needs | Same | Same |
| Code shared | 95% | 95% |

**Both bots share the same codebase via `bot_common.py`!**

## Production Setup

### Add HTTPS with Nginx and Let's Encrypt

For production, you should use HTTPS. Here's how to set it up:

#### 1. Point a Domain to Your Droplet

In your domain registrar, create an A record:
```
your-domain.com → your-droplet-ip
```

#### 2. Install Nginx

```bash
apt install nginx -y
```

#### 3. Configure Nginx as Reverse Proxy

Create nginx config:
```bash
nano /etc/nginx/sites-available/claude-api
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/claude-api /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Update firewall:
```bash
ufw allow 'Nginx Full'
ufw delete allow 3000/tcp  # Remove direct port access
```

#### 4. Install SSL Certificate (Let's Encrypt)

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get certificate (follow prompts)
certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
certbot renew --dry-run
```

Now access your API at: `https://your-domain.com`

### Add Basic Authentication

To protect your API, add basic auth to Nginx:

```bash
# Install htpasswd tool
apt install apache2-utils -y

# Create password file
htpasswd -c /etc/nginx/.htpasswd apiuser

# You'll be prompted to enter a password
```

Update nginx config:
```nginx
server {
    # ... existing config ...

    location / {
        auth_basic "Claude API";
        auth_basic_user_file /etc/nginx/.htpasswd;

        # ... rest of proxy config ...
    }
}
```

Restart nginx:
```bash
systemctl restart nginx
```

Test with authentication:
```bash
curl -u apiuser:yourpassword https://your-domain.com/health
```

## Monitoring and Maintenance

### View Logs

```bash
# Container logs
docker compose logs -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
journalctl -u docker -f
```

### Check Resource Usage

```bash
# System resources
htop  # or: apt install htop

# Docker stats
docker stats

# Disk usage
df -h
docker system df
```

### Restart the Service

```bash
# Restart container
docker compose restart

# Full rebuild and restart
docker compose down
./build.sh --no-cache
docker compose up -d
```

### Update the Application

```bash
cd /opt/cc-sdk-docker

# Pull latest changes
git pull

# Rebuild
./build.sh

# Restart
docker compose down
docker compose up -d
```

### Backup Configuration

```bash
# Backup environment file
cp .env /root/backups/.env.backup

# Backup Docker volume
docker run --rm \
  -v cc-sdk-docker_claude-auth:/data \
  -v /root/backups:/backup \
  ubuntu tar czf /backup/claude-auth-backup.tar.gz /data
```

## Security Best Practices

### 1. Use SSH Keys (Disable Password Authentication)

```bash
nano /etc/ssh/sshd_config
```

Set these values:
```
PasswordAuthentication no
PermitRootLogin prohibit-password
```

Restart SSH:
```bash
systemctl restart sshd
```

### 2. Keep System Updated

```bash
# Set up automatic security updates
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades
```

### 3. Use Docker Secrets (Production)

Instead of `.env` file:

```bash
# Create secrets
echo "sk-ant-oat01-your-token" | docker secret create claude_token -

# Update docker-compose.yml to use secrets
```

### 4. Limit API Access by IP

In nginx config:
```nginx
location / {
    # Only allow specific IPs
    allow 1.2.3.4;      # Your IP
    allow 5.6.7.0/24;   # Your network
    deny all;

    # ... rest of config ...
}
```

### 5. Set Up Fail2Ban

```bash
# Install fail2ban
apt install fail2ban -y

# Enable for SSH
systemctl enable fail2ban
systemctl start fail2ban
```

## Troubleshooting

### Container Won't Start

```bash
# Check Docker logs
docker compose logs

# Check if port is in use
netstat -tlnp | grep 3000

# Check Docker daemon
systemctl status docker
```

### Authentication Errors

```bash
# Verify token in container
docker compose exec server env | grep CLAUDE_CODE_OAUTH_TOKEN

# Check credential files
docker compose exec server cat ~/.claude/.credentials.json

# Try with a new token
# On your local machine: claude setup-token
# Update .env and restart: docker compose restart
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Increase droplet size in Digital Ocean dashboard
# Or add swap:
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Can't Connect from Outside

```bash
# Check if container is running
docker compose ps

# Check if port is listening
netstat -tlnp | grep 3000

# Check firewall
ufw status

# Check if nginx is running (if using reverse proxy)
systemctl status nginx
```

### SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Renew manually if needed
certbot renew --force-renewal

# Check nginx config
nginx -t
```

## Scaling Considerations

### Multiple Containers (Load Balancing)

For high traffic, run multiple containers behind nginx:

```bash
# In docker-compose.yml, use scale:
docker compose up -d --scale server=3
```

Update nginx to load balance:
```nginx
upstream claude_backend {
    server localhost:3000;
    server localhost:3001;
    server localhost:3002;
}

server {
    location / {
        proxy_pass http://claude_backend;
        # ... rest of config ...
    }
}
```

### Database for Session Storage

For persistent sessions across restarts, modify [server/api.py](../server/api.py) to use Redis or PostgreSQL instead of in-memory storage.

### Monitoring Setup

Add monitoring with:
- **Prometheus + Grafana** for metrics
- **Loki** for log aggregation
- **Digital Ocean Monitoring** (built-in)

## Cost Estimation

**Monthly Costs:**
- Droplet: $12-48/month (depends on size)
- Bandwidth: 1TB included, $0.01/GB overage
- Backups: $2.40-9.60/month (20% of droplet cost, optional)

**Estimated Total:** $15-60/month depending on your needs

## Digital Ocean Alternatives

This same setup works on:
- **AWS EC2** - Use Ubuntu AMI + Docker
- **Google Cloud Compute Engine** - Use Container-Optimized OS
- **Linode** - Similar to Digital Ocean
- **Hetzner Cloud** - More affordable, Europe-based
- **Any VPS** - Works anywhere Docker runs

## See Also

- [Main README](../README.md) - Project overview
- [Authentication Guide](AUTHENTICATION.md) - Token setup
- [Server API Reference](SERVER.md) - API documentation
- [Telegram Bot Testing Guide](../server/TELEGRAM_TESTING.md) - Local Telegram testing
- [Telegram Docker Guide](TELEGRAM_DOCKER.md) - Docker-specific Telegram setup
- [Slack Bot Setup Guide](../server/SLACK_SETUP.md) - Complete Slack setup instructions
- [Slack Bot Guide](SLACK_BOT_GUIDE.md) - Implementation comparison
- [Digital Ocean Docker Docs](https://docs.digitalocean.com/products/droplets/how-to/install-docker/)
- [Digital Ocean Firewall Guide](https://docs.digitalocean.com/products/networking/firewalls/)

## Quick Reference Commands

### FastAPI Server

```bash
# View logs
docker compose logs server -f

# Restart
docker compose restart server

# Check health
curl http://localhost:3000/health

# View resource usage
docker stats server
```

### Telegram Bot

```bash
# View logs
docker compose logs telegram-bot -f

# Restart
docker compose restart telegram-bot

# Check if running
docker compose ps telegram-bot

# View sessions
docker compose exec telegram-bot ls -la /app/telegram_sessions/

# View resource usage
docker stats telegram-bot
```

### Slack Bot

```bash
# View logs
docker compose logs slack-bot -f

# Restart
docker compose restart slack-bot

# Check if running
docker compose ps slack-bot

# View sessions
docker compose exec slack-bot ls -la /app/slack_sessions/

# View resource usage
docker stats slack-bot
```

### All Services

```bash
# Start all (server + bots)
docker compose up -d

# Stop all
docker compose down

# Update and restart all
git pull && ./build.sh && docker compose up -d

# View all logs
docker compose logs -f

# View all resource usage
docker stats

# Clean up old images
docker system prune -a
```
