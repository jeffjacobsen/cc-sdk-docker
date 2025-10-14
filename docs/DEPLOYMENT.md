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

Add your OAuth token:
```bash
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-your-token-here
PORT=3000
```

Save and exit (Ctrl+X, then Y, then Enter)

### 6. Build and Start the Container

```bash
# Build the image
./build.sh

# Start the server
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 7. Configure Firewall

```bash
# Allow SSH (if using ufw)
ufw allow 22/tcp

# Allow HTTP (port 3000)
ufw allow 3000/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### 8. Test the Deployment

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
- [Digital Ocean Docker Docs](https://docs.digitalocean.com/products/droplets/how-to/install-docker/)
- [Digital Ocean Firewall Guide](https://docs.digitalocean.com/products/networking/firewalls/)

## Quick Reference Commands

```bash
# View logs
docker compose logs -f

# Restart
docker compose restart

# Stop
docker compose down

# Update and restart
git pull && ./build.sh && docker compose up -d

# Check health
curl http://localhost:3000/health

# View resource usage
docker stats

# Clean up old images
docker system prune -a
```
