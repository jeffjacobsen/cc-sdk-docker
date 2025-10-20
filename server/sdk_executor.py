"""
Unified SDK Executor for Claude Agent SDK

This module provides a single entry point for all Claude SDK calls across
the application (FastAPI, Telegram bot, Slack bot, agent executor).

Features:
- Unified observability (Sentry, PostHog, file logging, console)
- Flexible response modes (stream, buffer text, buffer all)
- Thinking block control (include, exclude, log only)
- Per-user session management
- Automatic tool tracking and metrics

Environment variables:
- SENTRY_DSN: Enable Sentry if set
- POSTHOG_API_KEY: Enable PostHog if set
- POSTHOG_HOST: PostHog host (default: https://app.posthog.com)
"""

import os
import json
import time
import asyncio
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any, AsyncIterator, Tuple
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
)

# Optional imports based on environment
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

try:
    from posthog import Posthog
    POSTHOG_AVAILABLE = True
except ImportError:
    POSTHOG_AVAILABLE = False


# ============================================================================
# Configuration
# ============================================================================

class ResponseMode(str, Enum):
    """How to return SDK responses"""
    STREAM = "stream"           # Yield messages as they arrive (FastAPI SSE)
    BUFFER_TEXT = "buffer_text" # Return only final text + tools (bots)
    BUFFER_ALL = "buffer_all"   # Return complete structured data (API)


class ThinkingMode(str, Enum):
    """How to handle thinking blocks"""
    INCLUDE = "include"   # Include thinking in response
    EXCLUDE = "exclude"   # Strip thinking from response
    LOG_ONLY = "log_only" # Log to observability but don't return


@dataclass
class ExecutorConfig:
    """Configuration for a single SDK execution"""
    # Identity
    user_id: Optional[str] = None
    platform: Optional[str] = None  # "api", "telegram", "slack", "agent"

    # Claude SDK options
    cwd: Optional[str] = None
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: Optional[List[str]] = None

    # Response control
    response_mode: ResponseMode = ResponseMode.BUFFER_TEXT
    thinking_mode: ThinkingMode = ThinkingMode.EXCLUDE
    include_tool_indicators: bool = True

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedResponse:
    """Unified response from SDK execution"""
    text: str
    tool_uses: List[str]
    thinking_blocks: List[str]
    session_id: Optional[str]
    metrics: Dict[str, Any]
    raw_messages: List[Any] = field(default_factory=list)


# ============================================================================
# Observability Backends
# ============================================================================

class ObservabilityBackend:
    """Base class for observability backends"""

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        """Called when SDK request starts"""
        pass

    def log_message_received(self, config: ExecutorConfig, message: Any):
        """Called for each message received from SDK"""
        pass

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        """Called when SDK request completes"""
        pass

    def log_error(self, config: ExecutorConfig, error: Exception):
        """Called when SDK request fails"""
        pass


class SentryBackend(ObservabilityBackend):
    """Sentry integration for error tracking and transactions"""

    def __init__(self):
        self.enabled = SENTRY_AVAILABLE and bool(os.getenv("SENTRY_DSN"))
        if self.enabled:
            print(f"[DEBUG] Sentry: Initialized with DSN={os.getenv('SENTRY_DSN')[:20]}...")
            if not sentry_sdk.Hub.current.client:
                sentry_sdk.init(
                    dsn=os.getenv("SENTRY_DSN"),
                    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                )
        else:
            print(f"[DEBUG] Sentry: Disabled (available={SENTRY_AVAILABLE}, has_dsn={bool(os.getenv('SENTRY_DSN'))})")
        self.transaction = None

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        if not self.enabled:
            return

        print(f"[DEBUG] Sentry: Starting transaction for {config.platform or 'unknown'} user={config.user_id}")
        self.transaction = sentry_sdk.start_transaction(
            op="llm.request",
            name=f"claude_sdk_query_{config.platform or 'unknown'}"
        )
        self.transaction.set_tag("platform", config.platform or "unknown")
        self.transaction.set_tag("user_id", config.user_id or "anonymous")
        self.transaction.set_context("llm", {
            "model": "claude",
            "prompt_length": len(prompt),
            "has_session": bool(config.session_id),
        })

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        if not self.enabled or not self.transaction:
            return

        # Add measurements
        self.transaction.set_measurement("llm.response_length", len(result.text))
        self.transaction.set_measurement("llm.tool_uses", len(result.tool_uses))
        self.transaction.set_measurement("llm.thinking_blocks", len(result.thinking_blocks))

        if "duration_ms" in result.metrics:
            self.transaction.set_measurement("llm.duration_ms", result.metrics["duration_ms"])

        print(f"[DEBUG] Sentry: Finishing transaction - duration={result.metrics.get('duration_ms', 0)}ms, tools={len(result.tool_uses)}")
        self.transaction.finish()

    def log_error(self, config: ExecutorConfig, error: Exception):
        if not self.enabled:
            return

        print(f"[DEBUG] Sentry: Capturing exception - {type(error).__name__}: {error}")
        sentry_sdk.capture_exception(error)
        if self.transaction:
            self.transaction.finish()


class PostHogBackend(ObservabilityBackend):
    """PostHog integration for LLM analytics"""

    def __init__(self):
        api_key = os.getenv("POSTHOG_API_KEY")
        self.enabled = POSTHOG_AVAILABLE and bool(api_key)

        if self.enabled:
            host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
            print(f"[DEBUG] PostHog: Initialized with host={host}, key={api_key[:10] if api_key else 'none'}...")
            self.client = Posthog(api_key, host=host)
        else:
            print(f"[DEBUG] PostHog: Disabled (available={POSTHOG_AVAILABLE}, has_key={bool(api_key)})")
            self.client = None

        self.start_time = None

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        if not self.enabled:
            return

        self.start_time = time.time()

        print(f"[DEBUG] PostHog: Sending 'llm_request_start' event - user={config.user_id or 'anonymous'}, platform={config.platform}")
        self.client.capture(
            "llm_request_start",
            distinct_id=config.user_id or "anonymous",
            properties={
                "platform": config.platform or "unknown",
                "prompt_length": len(prompt),
                "has_session": bool(config.session_id),
                "thinking_mode": config.thinking_mode.value,
                "response_mode": config.response_mode.value,
                **config.metadata,
            }
        )

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        if not self.enabled:
            return

        duration_ms = result.metrics.get("duration_ms", 0)

        # Main completion event
        print(f"[DEBUG] PostHog: Sending 'llm_completion' event - user={config.user_id or 'anonymous'}, duration={duration_ms}ms, tools={result.tool_uses}")
        self.client.capture(
            "llm_completion",
            distinct_id=config.user_id or "anonymous",
            properties={
                "platform": config.platform or "unknown",
                "response_length": len(result.text),
                "tool_uses": len(result.tool_uses),
                "tool_list": result.tool_uses,
                "thinking_blocks": len(result.thinking_blocks),
                "duration_ms": duration_ms,
                "has_session": bool(result.session_id),
                **config.metadata,
            }
        )

    def log_error(self, config: ExecutorConfig, error: Exception):
        if not self.enabled:
            return

        print(f"[DEBUG] PostHog: Sending 'llm_error' event - user={config.user_id or 'anonymous'}, error={type(error).__name__}")
        self.client.capture(
            "llm_error",
            distinct_id=config.user_id or "anonymous",
            properties={
                "platform": config.platform or "unknown",
                "error_type": type(error).__name__,
                "error_message": str(error),
                **config.metadata,
            }
        )


class FileLoggingBackend(ObservabilityBackend):
    """File-based logging in JSONL format (like agent_executor.py)"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enabled = True
        self.start_time = None

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        self.start_time = time.time()
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": time.time(),
                "event": "request_start",
                "user_id": config.user_id,
                "platform": config.platform,
                "prompt_length": len(prompt),
                "prompt_preview": prompt[:200],
                "session_id": config.session_id,
            }, f)
            f.write("\n")

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": time.time(),
                "event": "request_complete",
                "user_id": config.user_id,
                "platform": config.platform,
                "response_length": len(result.text),
                "tool_uses": result.tool_uses,
                "thinking_blocks_count": len(result.thinking_blocks),
                "session_id": result.session_id,
                "metrics": result.metrics,
            }, f)
            f.write("\n")

    def log_error(self, config: ExecutorConfig, error: Exception):
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": time.time(),
                "event": "request_error",
                "user_id": config.user_id,
                "platform": config.platform,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }, f)
            f.write("\n")


class ConsoleBackend(ObservabilityBackend):
    """Console logging for development"""

    def __init__(self):
        self.enabled = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        if self.enabled:
            print(f"[SDK] Request start: user={config.user_id}, platform={config.platform}, prompt_len={len(prompt)}")

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        if self.enabled:
            print(f"[SDK] Request complete: response_len={len(result.text)}, tools={len(result.tool_uses)}, duration={result.metrics.get('duration_ms', 0)}ms")

    def log_error(self, config: ExecutorConfig, error: Exception):
        if self.enabled:
            print(f"[SDK] Request error: {type(error).__name__}: {error}")


class ObservabilityHub:
    """Manages multiple observability backends"""

    def __init__(self, backends: Optional[List[ObservabilityBackend]] = None):
        if backends is None:
            # Auto-configure based on environment
            backends = [
                SentryBackend(),
                PostHogBackend(),
                ConsoleBackend(),
            ]
            # Add file logging if explicitly enabled
            if os.getenv("FILE_LOGGING", "").lower() in ("1", "true", "yes"):
                backends.append(FileLoggingBackend())

        self.backends = [b for b in backends if getattr(b, 'enabled', True)]

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        for backend in self.backends:
            try:
                backend.log_request_start(config, prompt)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_message_received(self, config: ExecutorConfig, message: Any):
        for backend in self.backends:
            try:
                backend.log_message_received(config, message)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_completion(self, config: ExecutorConfig, result: ProcessedResponse):
        for backend in self.backends:
            try:
                backend.log_completion(config, result)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_error(self, config: ExecutorConfig, error: Exception):
        for backend in self.backends:
            try:
                backend.log_error(config, error)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")


# ============================================================================
# Response Processing
# ============================================================================

class ResponseProcessor:
    """Processes SDK messages according to config"""

    def __init__(self, config: ExecutorConfig, hub: ObservabilityHub):
        self.config = config
        self.hub = hub

        self.text_parts: List[str] = []
        self.tool_uses: List[str] = []
        self.thinking_blocks: List[str] = []
        self.session_id: Optional[str] = None
        self.raw_messages: List[Any] = []

    def process_message(self, message: Any):
        """Process a single message from SDK"""
        self.raw_messages.append(message)
        self.hub.log_message_received(self.config, message)

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    self.text_parts.append(block.text)

                elif isinstance(block, ThinkingBlock):
                    self.thinking_blocks.append(block.thinking)

                    # Include thinking in text if requested
                    if self.config.thinking_mode == ThinkingMode.INCLUDE:
                        self.text_parts.append(f"\n[Thinking: {block.thinking}]\n")

                elif isinstance(block, ToolUseBlock):
                    self.tool_uses.append(block.name)

        elif isinstance(message, ResultMessage):
            self.session_id = message.session_id

    def get_final_response(self) -> ProcessedResponse:
        """Build final response"""
        text = "".join(self.text_parts)

        # Add tool indicators if requested
        if self.config.include_tool_indicators and self.tool_uses:
            tool_indicator = self._format_tool_indicators(self.tool_uses)
            text = f"{text}\n\n{tool_indicator}"

        return ProcessedResponse(
            text=text.strip(),
            tool_uses=self.tool_uses,
            thinking_blocks=self.thinking_blocks,
            session_id=self.session_id,
            metrics={},
            raw_messages=self.raw_messages if self.config.response_mode == ResponseMode.BUFFER_ALL else [],
        )

    def _format_tool_indicators(self, tools: List[str]) -> str:
        """Format tool usage indicators"""
        if not tools:
            return ""

        unique_tools = []
        seen = set()
        for tool in tools:
            if tool not in seen:
                unique_tools.append(tool)
                seen.add(tool)

        tool_icons = {
            "Read": "📖",
            "Write": "✍️",
            "Edit": "✏️",
            "Bash": "💻",
            "Glob": "🔍",
            "Grep": "🔎",
        }

        indicators = [f"{tool_icons.get(t, '🔧')} {t}" for t in unique_tools]
        return f"Tools used: {' | '.join(indicators)}"


# ============================================================================
# Main Executor
# ============================================================================

class ClaudeExecutor:
    """Unified executor for Claude SDK calls"""

    def __init__(self, hub: Optional[ObservabilityHub] = None):
        self.hub = hub or ObservabilityHub()

    async def execute(self, prompt: str, config: ExecutorConfig) -> ProcessedResponse:
        """Execute SDK query with observability"""
        start_time = time.time()

        try:
            # Log request start
            self.hub.log_request_start(config, prompt)

            # Build Claude options
            claude_options = self._build_options(config)

            # Process response
            processor = ResponseProcessor(config, self.hub)

            async with ClaudeSDKClient(options=claude_options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    processor.process_message(message)

            # Build final response
            result = processor.get_final_response()
            result.metrics["duration_ms"] = int((time.time() - start_time) * 1000)

            # Log completion
            self.hub.log_completion(config, result)

            return result

        except Exception as e:
            self.hub.log_error(config, e)
            raise

    async def execute_stream(
        self,
        prompt: str,
        config: ExecutorConfig
    ) -> AsyncIterator[Tuple[Any, Optional[ProcessedResponse]]]:
        """Execute SDK query with streaming response (for FastAPI SSE)"""
        start_time = time.time()

        try:
            self.hub.log_request_start(config, prompt)

            claude_options = self._build_options(config)
            processor = ResponseProcessor(config, self.hub)

            async with ClaudeSDKClient(options=claude_options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    processor.process_message(message)
                    yield message, None

            # Build final response with metrics
            result = processor.get_final_response()
            result.metrics["duration_ms"] = int((time.time() - start_time) * 1000)

            self.hub.log_completion(config, result)

            yield None, result

        except Exception as e:
            self.hub.log_error(config, e)
            raise

    def _build_options(self, config: ExecutorConfig) -> ClaudeAgentOptions:
        """Build Claude SDK options from config"""
        options_dict = {}

        if config.cwd:
            options_dict["cwd"] = config.cwd

        if config.session_id:
            options_dict["resume"] = config.session_id

        if config.system_prompt:
            options_dict["system_prompt"] = config.system_prompt

        if config.allowed_tools:
            options_dict["allowed_tools"] = config.allowed_tools

        options_dict["setting_sources"] = ["project", "user", "local"]

        return ClaudeAgentOptions(**options_dict)


# ============================================================================
# Convenience Functions
# ============================================================================

# Global executor instance
_executor = None

def get_executor() -> ClaudeExecutor:
    """Get or create global executor instance"""
    global _executor
    if _executor is None:
        _executor = ClaudeExecutor()
    return _executor


async def execute_query(prompt: str, config: ExecutorConfig) -> ProcessedResponse:
    """Convenience function for executing queries"""
    executor = get_executor()
    return await executor.execute(prompt, config)
