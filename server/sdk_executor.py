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

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator, Tuple

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

from observability import ObservabilityHub


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

    def process_message(self, message: Any, message_count: int):
        """Process a single message from SDK"""
        self.raw_messages.append(message)
        self.hub.log_message_received(self.config, message, message_count)

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
        message_count = 0

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
                    message_count += 1
                    processor.process_message(message, message_count)

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
        message_count = 0

        try:
            self.hub.log_request_start(config, prompt)

            claude_options = self._build_options(config)
            processor = ResponseProcessor(config, self.hub)

            async with ClaudeSDKClient(options=claude_options) as client:
                await client.query(prompt)

                async for message in client.receive_response():
                    message_count += 1
                    processor.process_message(message, message_count)
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
