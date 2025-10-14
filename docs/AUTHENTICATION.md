# Authentication Guide

This guide explains how authentication works in the Claude Code SDK Docker container.

## Quick Setup

```bash
# On your host machine
claude setup-token

# Copy the token (starts with sk-ant-oat01-)
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here

# Start the container
docker compose up -d
```

That's it! The container will automatically configure authentication on startup.

## The Problem

The Claude Code SDK uses interactive browser-based OAuth authentication by default. This doesn't work well in containers because:
- Containers typically don't have GUI/browser access
- Session tokens expire, requiring repeated manual intervention
- Interactive auth requires `docker exec` into the container

## The Solution

We use **long-lived OAuth tokens** instead:

1. Generate a token on your **host machine** (where you have a browser)
2. Pass the token to the container via environment variable
3. The container automatically configures the SDK to use the token

### Why This Works

Long-lived OAuth tokens (`sk-ant-oat01-*`):
- Last for **1 year** before expiring
- Can be passed via environment variables
- Don't require browser interaction
- Work perfectly in containerized environments

## How It Works

### Container Startup Process

When the container starts, [scripts/docker-entrypoint.sh](../scripts/docker-entrypoint.sh):

1. Checks if `CLAUDE_CODE_OAUTH_TOKEN` is set
2. If found, creates two credential files:
   - `~/.claude/.credentials.json` - Contains the authentication token
   - `~/.claude.json` - Contains session configuration
3. The Claude Code SDK automatically uses these files

### Authentication Files

**`~/.claude/.credentials.json`**
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-oat01-...",
    "expiresAt": "2099-12-31T23:59:59.999Z",
    "scopes": ["read", "write"],
    "subscriptionType": "pro"
  }
}
```

**`~/.claude.json`**
```json
{
  "oauthAccount": {
    "accountUuid": "...",
    "emailAddress": "docker@claude-sdk.local",
    "organizationName": "Claude SDK Docker"
  },
  "hasCompletedOnboarding": true
}
```

### Persistence

The [compose.yaml](../compose.yaml) uses a Docker volume to persist authentication:

```yaml
volumes:
  - claude-auth:/home/claude/.claude
```

This ensures:
- Authentication persists across container restarts
- You don't need to re-authenticate after stopping/starting

## Alternative Authentication Methods

### Option 1: Long-lived OAuth Token (Recommended)
```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token
docker compose up -d
```

**Pros:** Simple, long-lasting, no browser needed
**Cons:** Must regenerate annually

### Option 2: Anthropic API Key
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key
docker compose up -d
```

**Pros:** Never expires
**Cons:** Uses API credits instead of Pro/Max subscription, may have different rate limits

### Option 3: Interactive Authentication (Not Recommended)
```bash
# Start container without token
docker compose up -d

# Exec into container
docker compose exec server bash

# Run interactive auth (requires host browser)
claude
```

**Pros:** None in container context
**Cons:** Requires manual intervention, session expires, impractical for automation

## Troubleshooting

### Check if authenticated

```bash
# Health endpoint
curl http://localhost:3000/health

# Should return:
# {
#   "status": "healthy",
#   "authenticated": true,
#   ...
# }
```

### Token not working

```bash
# Verify token is set in container
docker compose exec server env | grep CLAUDE_CODE_OAUTH_TOKEN

# Check credential files
docker compose exec server ls -la ~/.claude/
docker compose exec server cat ~/.claude/.credentials.json
```

### Generate a new token

```bash
# On host machine
claude setup-token

# Copy new token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-new-token

# Restart container
docker compose restart
```

### Clear authentication

```bash
# Remove the persistent volume
docker compose down -v

# Restart with new token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token
docker compose up -d
```

## Security Best Practices

1. **Never commit tokens** - Use `.env` (gitignored) or environment variables
2. **Don't hardcode tokens** - Always pass via environment variables
3. **Rotate tokens** - Generate new tokens periodically
4. **Use secrets in production** - For deployment, use proper secret management (Docker secrets, Kubernetes secrets, etc.)
5. **Limit token scope** - OAuth tokens are scoped to your Claude Code subscription

## Environment Variable Priority

The container checks for authentication in this order:

1. `CLAUDE_CODE_OAUTH_TOKEN` - Long-lived OAuth token (recommended)
2. `ANTHROPIC_API_KEY` - Direct API key (alternative)
3. `CLAUDE_CODE_SESSION` - Legacy session token (not recommended)
4. Existing credential files - From previous authentication

## See Also

- [Main README](../README.md) - Project overview
- [Server Documentation](SERVER.md) - API usage
- [Claude Code SDK Docs](https://docs.claude.com/en/docs/claude-code/sdk/sdk-python) - Official SDK documentation
