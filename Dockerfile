# Multi-language Claude Code SDK container
# Supports both TypeScript/JavaScript and Python
# Build Date: July 2025
# Claude Code CLI: Latest version (unpinned) - ~v1.0.64 as of July 2025
# Python SDK: Latest version (unpinned) - ~v0.0.17 as of July 2025

# Stage 1: Build Node.js dependencies
FROM node:22-slim AS node-builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    ca-certificates \
    build-essential \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI and tsx globally (includes TypeScript SDK)
RUN npm install -g @anthropic-ai/claude-code tsx && \
    # Remove unused platform-specific binaries to reduce image size
    find /usr/local/lib/node_modules/@anthropic-ai/claude-code -name "*.exe" -delete && \
    find /usr/local/lib/node_modules/@anthropic-ai/claude-code -path "*darwin*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/node_modules/@anthropic-ai/claude-code -path "*win32*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/node_modules/@anthropic-ai/claude-code -path "*jetbrains*" -type d -exec rm -rf {} + 2>/dev/null || true

# Stage 2: Build Python dependencies
FROM node:22-slim AS python-builder

# Install Python and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python SDK and Telegram bot dependencies in the virtual environment
RUN pip install --no-cache-dir \
    claude-code-sdk \
    python-telegram-bot \
    python-dotenv

# Stage 3: Runtime image with both TypeScript and Python
FROM node:22-slim AS runtime

# Install runtime dependencies including Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    nano \
    ca-certificates \
    python3 \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy Node.js global packages from node-builder
COPY --from=node-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder /usr/local/bin/ /usr/local/bin/
# Copy yoga.wasm to the same directory as claude binary
COPY --from=node-builder /usr/local/lib/node_modules/@anthropic-ai/claude-code/yoga.wasm /usr/local/bin/yoga.wasm

# Copy Python virtual environment from python-builder
COPY --from=python-builder /opt/venv /opt/venv

# Set NODE_PATH to include global modules
ENV NODE_PATH=/usr/local/lib/node_modules

# Set PATH to use Python virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Create Python symlink
RUN ln -s /usr/bin/python3 /usr/bin/python || true

# Create non-root user
RUN useradd -m -s /bin/bash claude

# Create directory for Claude auth and configuration
RUN mkdir -p /home/claude/.claude && \
    chmod 755 /home/claude/.claude && \
    chown -R claude:claude /home/claude/.claude

# Set up .claude configuration scaffolding
RUN mkdir -p /home/claude/.claude/commands /home/claude/.claude/hooks && \
    chown -R claude:claude /home/claude/.claude

# Copy Claude configuration scaffolding
COPY --chown=claude:claude .claude/ /home/claude/.claude/

# Copy examples and scripts
COPY --chown=claude:claude examples/ /app/examples/
COPY --chown=claude:claude scripts/ /app/scripts/

# Copy entrypoint script (as root)
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set working directory
WORKDIR /app
RUN chown claude:claude /app

# Switch to non-root user
USER claude

# Expose port (configurable via PORT env var, default 3000)
ARG PORT=3000
ENV PORT=${PORT}
EXPOSE ${PORT}

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command
CMD ["sleep", "infinity"]
