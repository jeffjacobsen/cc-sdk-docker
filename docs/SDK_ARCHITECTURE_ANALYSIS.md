# SDK Architecture Analysis & Recommendations

## Executive Summary

After reviewing `api.py`, `slack_bot.py`, `telegram_bot.py`, `bot_common.py`, and `agent_executor.py`, I've identified significant opportunities to:

1. **Extract common SDK call patterns** into a unified executor module
2. **Enhance logging** with support for Sentry, PostHog, and other observability platforms
3. **Provide flexible response handling** (streaming vs. buffered, thinking blocks vs. final only)
4. **Reduce code duplication** across different interfaces (API, bots, agents)

---

## Current State Analysis

### Code Structure Overview

```
Current Architecture:
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   api.py    │  │telegram_bot.py│  │ slack_bot.py │
│  (FastAPI)  │  │  (Telegram)   │  │   (Slack)    │
└──────┬──────┘  └───────┬───────┘  └───────┬──────┘
       │                 │                  │
       │         ┌───────┴──────────────────┘
       │         │
       │    ┌────▼─────────┐
       │    │bot_common.py │  ← 95% shared bot logic
       │    │(Bots only)   │
       │    └──────────────┘
       │
       ▼
  ┌────────────────┐
  │Claude SDK calls│  ← Duplicated 3+ times
  │ - query()      │
  │ - ClaudeClient │
  │ - Streaming    │
  └────────────────┘

Separate:
┌─────────────────┐
│agent_executor.py│  ← Good logging, file-based only
└─────────────────┘
```

### Key Observations

#### 1. **Duplicated SDK Call Logic**

**In `api.py` (lines 197-239):**
```python
async for message in query(prompt=request.prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                response_text += block.text
    elif isinstance(message, ResultMessage):
        result_info = message
```

**In `bot_common.py` (lines 265-298):**
```python
async with ClaudeSDKClient(options=options) as client:
    await client.query(user_message)
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_uses.append(block.name)
        elif isinstance(message, ResultMessage):
            new_session_id = message.session_id
```

**In `telegram_bot.py` (lines 505-524):**
```python
# Same pattern, duplicated AGAIN
async with ClaudeSDKClient(options=options) as client:
    await client.query(user_message)
    async for message in client.receive_response():
        # ... identical logic ...
```

**In `agent_executor.py` (lines 98-194):**
```python
# Similar pattern but with extensive logging
async for message in query(prompt=prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                # Log to files
            elif isinstance(block, ToolUseBlock):
                # Log tool use with timestamps
            elif isinstance(block, ThinkingBlock):
                # Log thinking blocks
```

**Problem:** 4 different implementations of essentially the same logic!

#### 2. **agent_executor.py Has Superior Logging**

`agent_executor.py` demonstrates the right approach:
- ✅ Logs prompts, responses, tools, thinking blocks separately
- ✅ Uses structured JSON for tools (JSONL format)
- ✅ Timestamps everything
- ✅ Tracks message counts
- ✅ Emits progress events
- ✅ Captures complete execution metadata

**But it's limited:**
- ❌ Only logs to local files
- ❌ No integration with Sentry/PostHog
- ❌ Not reusable by other modules
- ❌ No streaming control
- ❌ Can't filter out thinking blocks

#### 3. **Missing Flexibility in Current Code**

Current implementations lack control over:

1. **Thinking blocks:** Always included or ignored, no option
2. **Streaming vs buffered:** Hardcoded per interface
3. **Response filtering:** Can't choose which message types to return
4. **Logging destination:** File-based only (agent_executor) or basic logging
5. **Observability:** No structured events for monitoring platforms

---

## Proposed Solution: Unified SDK Executor

### Architecture

```
New Proposed Architecture:
┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   api.py    │  │telegram_bot.py│  │ slack_bot.py │  │ your_agent   │
└──────┬──────┘  └───────┬───────┘  └───────┬──────┘  └───────┬──────┘
       │                 │                  │                  │
       └─────────────────┴──────────────────┴──────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  sdk_executor.py        │  ← NEW: Unified executor
                    │  ├─ ClaudeExecutor      │
                    │  ├─ ExecutorConfig      │
                    │  ├─ ObservabilityHub    │
                    │  └─ ResponseProcessor   │
                    └─────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Observability Backends │
                    │  ├─ Sentry             │
                    │  ├─ PostHog (LLM)      │
                    │  ├─ File logging       │
                    │  ├─ Console            │
                    │  └─ Custom handlers    │
                    └─────────────────────────┘
```

### Core Module: `sdk_executor.py`

```python
"""
Unified Claude SDK executor with observability and flexible response handling.

Features:
- Single place for all SDK interactions
- Pluggable observability backends (Sentry, PostHog, files, custom)
- Flexible response control (stream, buffer, filter thinking blocks)
- Structured logging with LLM-specific metrics
- Session management
- Error tracking with context
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator, Callable, Protocol
from enum import Enum
from datetime import datetime
import logging

from claude_agent_sdk import (
    query,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    ThinkingBlock,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)


# ==================== Configuration ====================

class ResponseMode(Enum):
    """How to return responses to caller."""
    STREAM = "stream"              # Yield messages as they arrive
    BUFFER_ALL = "buffer_all"      # Collect everything, return at end
    BUFFER_TEXT = "buffer_text"    # Collect only text, return at end


class ThinkingMode(Enum):
    """How to handle thinking blocks."""
    INCLUDE = "include"            # Include in response
    EXCLUDE = "exclude"            # Filter out completely
    LOG_ONLY = "log_only"          # Log but don't return to user


@dataclass
class ExecutorConfig:
    """Configuration for Claude SDK execution."""

    # Response handling
    response_mode: ResponseMode = ResponseMode.BUFFER_TEXT
    thinking_mode: ThinkingMode = ThinkingMode.LOG_ONLY
    include_tool_indicators: bool = True
    max_response_length: Optional[int] = None

    # Observability
    enable_sentry: bool = False
    enable_posthog: bool = False
    enable_file_logging: bool = False
    log_directory: Optional[str] = None

    # Metadata for tracking
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    platform: Optional[str] = None  # "api", "telegram", "slack", "agent"
    request_id: Optional[str] = None

    # SDK options
    claude_options: Optional[ClaudeAgentOptions] = None


# ==================== Observability Protocol ====================

class ObservabilityBackend(Protocol):
    """Protocol for observability backends."""

    def log_request_start(self, config: ExecutorConfig, prompt: str) -> None:
        """Log the start of a request."""
        ...

    def log_message_received(
        self,
        config: ExecutorConfig,
        message_type: str,
        message_count: int,
        content: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log each message received from SDK."""
        ...

    def log_tool_use(
        self,
        config: ExecutorConfig,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_id: str
    ) -> None:
        """Log tool usage."""
        ...

    def log_tool_result(
        self,
        config: ExecutorConfig,
        tool_id: str,
        result: str,
        is_error: bool
    ) -> None:
        """Log tool result."""
        ...

    def log_thinking(
        self,
        config: ExecutorConfig,
        thinking_text: str
    ) -> None:
        """Log thinking block."""
        ...

    def log_completion(
        self,
        config: ExecutorConfig,
        result: Dict[str, Any]
    ) -> None:
        """Log request completion with metrics."""
        ...

    def log_error(
        self,
        config: ExecutorConfig,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Log error with context."""
        ...


# ==================== Built-in Backends ====================

class SentryBackend:
    """Sentry observability backend."""

    def __init__(self, dsn: str):
        import sentry_sdk
        sentry_sdk.init(dsn=dsn)
        self.sentry = sentry_sdk

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        with self.sentry.start_transaction(
            op="llm.request",
            name="claude_sdk_query"
        ) as transaction:
            transaction.set_tag("platform", config.platform)
            transaction.set_tag("user_id", config.user_id)
            transaction.set_context("llm", {
                "model": config.claude_options.model if config.claude_options else None,
                "prompt_length": len(prompt),
            })

    def log_completion(self, config: ExecutorConfig, result: Dict[str, Any]):
        self.sentry.set_measurement("llm.duration_ms", result.get("duration_ms", 0))
        self.sentry.set_measurement("llm.num_turns", result.get("num_turns", 0))
        self.sentry.set_measurement("llm.cost_usd", result.get("total_cost_usd", 0))

    def log_error(self, config: ExecutorConfig, error: Exception, context: Dict[str, Any]):
        self.sentry.capture_exception(error)


class PostHogBackend:
    """PostHog LLM analytics backend."""

    def __init__(self, api_key: str, host: str = "https://app.posthog.com"):
        from posthog import Posthog
        self.posthog = Posthog(api_key, host=host)

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        self.posthog.capture(
            distinct_id=config.user_id or "anonymous",
            event="llm_request_start",
            properties={
                "platform": config.platform,
                "session_id": config.session_id,
                "prompt_length": len(prompt),
                "model": config.claude_options.model if config.claude_options else None,
            }
        )

    def log_tool_use(self, config: ExecutorConfig, tool_name: str, tool_input: Dict, tool_id: str):
        self.posthog.capture(
            distinct_id=config.user_id or "anonymous",
            event="llm_tool_use",
            properties={
                "platform": config.platform,
                "session_id": config.session_id,
                "tool_name": tool_name,
                "tool_id": tool_id,
            }
        )

    def log_completion(self, config: ExecutorConfig, result: Dict[str, Any]):
        self.posthog.capture(
            distinct_id=config.user_id or "anonymous",
            event="llm_completion",
            properties={
                "platform": config.platform,
                "session_id": config.session_id,
                "duration_ms": result.get("duration_ms"),
                "num_turns": result.get("num_turns"),
                "total_cost_usd": result.get("total_cost_usd"),
                "success": not result.get("is_error", False),
            }
        )


class FileLoggingBackend:
    """File-based logging backend (like agent_executor.py)."""

    def __init__(self, log_dir: str):
        from pathlib import Path
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_files = {}

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{config.request_id}_{timestamp}" if config.request_id else timestamp

        # Save prompt
        prompt_file = self.log_dir / f"{prefix}_prompt.txt"
        prompt_file.write_text(prompt)

        # Initialize log files
        self.current_files = {
            "text": self.log_dir / f"{prefix}_text.txt",
            "tools": self.log_dir / f"{prefix}_tools.jsonl",
            "summary": self.log_dir / f"{prefix}_summary.jsonl",
        }

    def log_tool_use(self, config: ExecutorConfig, tool_name: str, tool_input: Dict, tool_id: str):
        import json
        with open(self.current_files["tools"], "a") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "type": "tool_use",
                "tool_name": tool_name,
                "tool_id": tool_id,
                "input": tool_input
            }, f)
            f.write("\n")

    def log_thinking(self, config: ExecutorConfig, thinking_text: str):
        with open(self.current_files["text"], "a") as f:
            f.write(f"[{datetime.now().isoformat()}] THINKING:\n")
            f.write(f"{thinking_text}\n\n")


class ConsoleBackend:
    """Simple console logging backend."""

    def __init__(self):
        self.logger = logging.getLogger("sdk_executor")

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        self.logger.info(f"SDK request started: {config.platform} | user={config.user_id}")

    def log_message_received(self, config: ExecutorConfig, message_type: str, message_count: int, content=None):
        self.logger.info(f"Message #{message_count}: {message_type}")

    def log_tool_use(self, config: ExecutorConfig, tool_name: str, tool_input: Dict, tool_id: str):
        self.logger.info(f"Tool used: {tool_name}")

    def log_completion(self, config: ExecutorConfig, result: Dict[str, Any]):
        self.logger.info(
            f"SDK request completed: {result.get('num_turns')} turns, "
            f"{result.get('duration_ms')}ms, ${result.get('total_cost_usd', 0):.4f}"
        )

    def log_error(self, config: ExecutorConfig, error: Exception, context: Dict[str, Any]):
        self.logger.error(f"SDK error: {error}", exc_info=True)


# ==================== Observability Hub ====================

class ObservabilityHub:
    """Manages multiple observability backends."""

    def __init__(self):
        self.backends: List[ObservabilityBackend] = []

    def add_backend(self, backend: ObservabilityBackend):
        """Add an observability backend."""
        self.backends.append(backend)

    def log_request_start(self, config: ExecutorConfig, prompt: str):
        for backend in self.backends:
            try:
                backend.log_request_start(config, prompt)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_message_received(self, config: ExecutorConfig, message_type: str, count: int, content=None):
        for backend in self.backends:
            try:
                backend.log_message_received(config, message_type, count, content)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_tool_use(self, config: ExecutorConfig, tool_name: str, tool_input: Dict, tool_id: str):
        for backend in self.backends:
            try:
                backend.log_tool_use(config, tool_name, tool_input, tool_id)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_tool_result(self, config: ExecutorConfig, tool_id: str, result: str, is_error: bool):
        for backend in self.backends:
            try:
                backend.log_tool_result(config, tool_id, result, is_error)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_thinking(self, config: ExecutorConfig, thinking_text: str):
        for backend in self.backends:
            try:
                backend.log_thinking(config, thinking_text)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_completion(self, config: ExecutorConfig, result: Dict[str, Any]):
        for backend in self.backends:
            try:
                backend.log_completion(config, result)
            except Exception as e:
                logging.error(f"Observability backend error: {e}")

    def log_error(self, config: ExecutorConfig, error: Exception, context: Dict[str, Any]):
        for backend in self.backends:
            try:
                backend.log_error(config, error, context)
            except Exception as e:
                logging.error(f"Observability backend error in error handler: {e}")


# ==================== Response Processor ====================

@dataclass
class ProcessedResponse:
    """Processed response from Claude SDK."""
    text: str
    tool_uses: List[str]
    thinking_blocks: List[str]
    session_id: Optional[str]
    result_metadata: Optional[Dict[str, Any]]
    message_count: int


class ResponseProcessor:
    """Processes SDK messages according to configuration."""

    def __init__(self, config: ExecutorConfig, hub: ObservabilityHub):
        self.config = config
        self.hub = hub
        self.message_count = 0

        # Collectors
        self.text_parts = []
        self.tool_uses = []
        self.thinking_blocks = []
        self.session_id = None
        self.result_metadata = None

    def process_message(self, message) -> Optional[str]:
        """
        Process a single message from SDK.
        Returns text to yield if streaming, None otherwise.
        """
        self.message_count += 1
        message_type = type(message).__name__

        self.hub.log_message_received(
            self.config,
            message_type,
            self.message_count
        )

        if isinstance(message, AssistantMessage):
            return self._process_assistant_message(message)

        elif isinstance(message, ResultMessage):
            return self._process_result_message(message)

        elif isinstance(message, SystemMessage):
            return self._process_system_message(message)

        return None

    def _process_assistant_message(self, message: AssistantMessage) -> Optional[str]:
        """Process assistant message blocks."""
        text_to_yield = None

        for block in message.content:
            if isinstance(block, TextBlock):
                self.text_parts.append(block.text)
                if self.config.response_mode == ResponseMode.STREAM:
                    text_to_yield = block.text

            elif isinstance(block, ToolUseBlock):
                self.tool_uses.append(block.name)
                self.hub.log_tool_use(
                    self.config,
                    block.name,
                    block.input,
                    block.id
                )

            elif isinstance(block, ToolResultBlock):
                self.hub.log_tool_result(
                    self.config,
                    block.tool_use_id,
                    str(block.content)[:1000],
                    block.is_error
                )

            elif isinstance(block, ThinkingBlock):
                if self.config.thinking_mode == ThinkingMode.INCLUDE:
                    self.thinking_blocks.append(block.thinking)
                    if self.config.response_mode == ResponseMode.STREAM:
                        text_to_yield = f"[Thinking: {block.thinking}]"
                elif self.config.thinking_mode == ThinkingMode.LOG_ONLY:
                    self.hub.log_thinking(self.config, block.thinking)
                # EXCLUDE mode: do nothing

        return text_to_yield

    def _process_result_message(self, message: ResultMessage) -> None:
        """Process result message."""
        self.session_id = message.session_id
        self.result_metadata = {
            "duration_ms": message.duration_ms,
            "num_turns": message.num_turns,
            "total_cost_usd": message.total_cost_usd,
            "is_error": message.is_error,
            "usage": message.usage,
            "result": message.result,
        }

        self.hub.log_completion(self.config, self.result_metadata)
        return None

    def _process_system_message(self, message: SystemMessage) -> None:
        """Process system message."""
        # Log but don't include in user-facing response
        return None

    def get_final_response(self) -> ProcessedResponse:
        """Get the complete processed response."""
        full_text = "".join(self.text_parts)

        # Add tool indicators if configured
        if self.config.include_tool_indicators and self.tool_uses:
            unique_tools = list(dict.fromkeys(self.tool_uses))
            indicators = [f"🔧 {tool.upper()}" for tool in unique_tools]
            full_text += "\n\n" + " ".join(indicators)

        # Handle empty response
        if not full_text.strip():
            full_text = "I processed your request, but I don't have a text response to show."

        # Apply max length if configured
        if self.config.max_response_length and len(full_text) > self.config.max_response_length:
            full_text = full_text[:self.config.max_response_length] + "..."

        return ProcessedResponse(
            text=full_text,
            tool_uses=self.tool_uses,
            thinking_blocks=self.thinking_blocks,
            session_id=self.session_id,
            result_metadata=self.result_metadata,
            message_count=self.message_count
        )


# ==================== Main Executor ====================

class ClaudeExecutor:
    """Unified executor for Claude SDK with observability."""

    def __init__(
        self,
        sentry_dsn: Optional[str] = None,
        posthog_api_key: Optional[str] = None,
        enable_console_logging: bool = True
    ):
        self.hub = ObservabilityHub()

        # Setup backends
        if enable_console_logging:
            self.hub.add_backend(ConsoleBackend())

        if sentry_dsn:
            self.hub.add_backend(SentryBackend(sentry_dsn))

        if posthog_api_key:
            self.hub.add_backend(PostHogBackend(posthog_api_key))

    def add_backend(self, backend: ObservabilityBackend):
        """Add a custom observability backend."""
        self.hub.add_backend(backend)

    async def execute(
        self,
        prompt: str,
        config: ExecutorConfig
    ) -> ProcessedResponse:
        """
        Execute a Claude SDK query with full observability.

        Args:
            prompt: The prompt to send to Claude
            config: Executor configuration

        Returns:
            ProcessedResponse with text, tools used, thinking, metadata
        """
        try:
            self.hub.log_request_start(config, prompt)

            # Setup file logging if configured
            if config.enable_file_logging and config.log_directory:
                self.hub.add_backend(FileLoggingBackend(config.log_directory))

            processor = ResponseProcessor(config, self.hub)

            # Execute query
            async for message in query(prompt=prompt, options=config.claude_options):
                processor.process_message(message)

            return processor.get_final_response()

        except Exception as e:
            self.hub.log_error(config, e, {
                "prompt_length": len(prompt),
                "platform": config.platform,
                "user_id": config.user_id,
            })
            raise

    async def execute_streaming(
        self,
        prompt: str,
        config: ExecutorConfig
    ) -> AsyncIterator[str]:
        """
        Execute with streaming responses.

        Yields text chunks as they arrive from Claude.
        """
        try:
            self.hub.log_request_start(config, prompt)

            if config.enable_file_logging and config.log_directory:
                self.hub.add_backend(FileLoggingBackend(config.log_directory))

            # Force streaming mode
            config = ExecutorConfig(**{**config.__dict__, "response_mode": ResponseMode.STREAM})
            processor = ResponseProcessor(config, self.hub)

            async for message in query(prompt=prompt, options=config.claude_options):
                text_chunk = processor.process_message(message)
                if text_chunk:
                    yield text_chunk

        except Exception as e:
            self.hub.log_error(config, e, {
                "prompt_length": len(prompt),
                "platform": config.platform,
                "user_id": config.user_id,
            })
            raise

    async def execute_with_client(
        self,
        prompt: str,
        client: ClaudeSDKClient,
        config: ExecutorConfig
    ) -> ProcessedResponse:
        """
        Execute using an existing ClaudeSDKClient (for sessions).

        Args:
            prompt: The prompt to send
            client: Existing SDK client (maintains session)
            config: Executor configuration

        Returns:
            ProcessedResponse with text, tools used, thinking, metadata
        """
        try:
            self.hub.log_request_start(config, prompt)

            if config.enable_file_logging and config.log_directory:
                self.hub.add_backend(FileLoggingBackend(config.log_directory))

            processor = ResponseProcessor(config, self.hub)

            # Send query through existing client
            await client.query(prompt)

            # Process responses
            async for message in client.receive_response():
                processor.process_message(message)

            return processor.get_final_response()

        except Exception as e:
            self.hub.log_error(config, e, {
                "prompt_length": len(prompt),
                "platform": config.platform,
                "user_id": config.user_id,
            })
            raise


# ==================== Usage Examples ====================

"""
Example 1: FastAPI with PostHog
---

from sdk_executor import ClaudeExecutor, ExecutorConfig, ThinkingMode, ResponseMode

executor = ClaudeExecutor(
    posthog_api_key=os.getenv("POSTHOG_API_KEY"),
    enable_console_logging=True
)

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    config = ExecutorConfig(
        response_mode=ResponseMode.BUFFER_TEXT,
        thinking_mode=ThinkingMode.LOG_ONLY,
        include_tool_indicators=True,
        enable_posthog=True,
        user_id=request.user_id,
        platform="api",
        request_id=str(uuid.uuid4()),
        claude_options=ClaudeAgentOptions(
            model=request.model,
            allowed_tools=request.allowed_tools
        )
    )

    response = await executor.execute(request.prompt, config)

    return {
        "text": response.text,
        "tools_used": response.tool_uses,
        "session_id": response.session_id,
        "metadata": response.result_metadata
    }


Example 2: Telegram Bot with Sentry
---

executor = ClaudeExecutor(
    sentry_dsn=os.getenv("SENTRY_DSN"),
    enable_console_logging=False
)

async def handle_telegram_message(user_id, message_text):
    config = ExecutorConfig(
        response_mode=ResponseMode.BUFFER_TEXT,
        thinking_mode=ThinkingMode.EXCLUDE,  # Don't show thinking to users
        include_tool_indicators=True,
        enable_sentry=True,
        user_id=str(user_id),
        session_id=load_user_session(user_id),
        platform="telegram",
        claude_options=ClaudeAgentOptions(
            cwd=get_user_cwd(user_id),
            allowed_tools=["Read", "Write", "Bash", "Edit"],
            resume=load_user_session(user_id)
        )
    )

    response = await executor.execute(message_text, config)

    # Save session
    save_user_session(user_id, response.session_id)

    return response.text


Example 3: Agent with File Logging + PostHog
---

executor = ClaudeExecutor(
    posthog_api_key=os.getenv("POSTHOG_API_KEY")
)

async def run_agent_task(task_id, prompt, working_dir):
    config = ExecutorConfig(
        response_mode=ResponseMode.BUFFER_ALL,
        thinking_mode=ThinkingMode.INCLUDE,  # Keep thinking for analysis
        include_tool_indicators=False,
        enable_file_logging=True,
        enable_posthog=True,
        log_directory=f"{working_dir}/agent_log",
        request_id=task_id,
        platform="agent",
        claude_options=ClaudeAgentOptions(
            cwd=working_dir,
            permission_mode="bypassPermissions",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        )
    )

    response = await executor.execute(prompt, config)

    return {
        "success": not response.result_metadata.get("is_error"),
        "result": response.text,
        "thinking": response.thinking_blocks,
        "tools_used": response.tool_uses,
        "metrics": response.result_metadata
    }


Example 4: Streaming with Custom Backend
---

class CustomMetricsBackend:
    def log_completion(self, config, result):
        # Send to your custom metrics system
        metrics.gauge("llm.duration", result.get("duration_ms"))
        metrics.gauge("llm.cost", result.get("total_cost_usd"))
        metrics.increment("llm.requests", tags=[
            f"platform:{config.platform}",
            f"success:{not result.get('is_error')}"
        ])

executor = ClaudeExecutor()
executor.add_backend(CustomMetricsBackend())

@app.get("/stream")
async def stream_endpoint(prompt: str):
    config = ExecutorConfig(
        response_mode=ResponseMode.STREAM,
        thinking_mode=ThinkingMode.EXCLUDE,
        platform="api"
    )

    async def generate():
        async for chunk in executor.execute_streaming(prompt, config):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
"""
```

---

## Migration Plan

### Phase 1: Extract Common SDK Logic (bot_common.py)

**Goal:** Move SDK calling logic from individual bots into shared module.

**Current:**
- `telegram_bot.py`: Direct SDK calls in handle_message (lines 505-544)
- `slack_bot.py`: Imported from bot_common but could use executor
- `bot_common.py`: Has process_claude_message but no observability

**Proposed:**
```python
# In bot_common.py, replace process_claude_message with:

from sdk_executor import ClaudeExecutor, ExecutorConfig, ThinkingMode, ResponseMode

# Global executor instance
_executor = ClaudeExecutor(
    sentry_dsn=os.getenv("SENTRY_DSN"),
    posthog_api_key=os.getenv("POSTHOG_API_KEY")
)

async def process_claude_message(
    user_id: str,
    user_message: str,
    platform: str = "sessions",
    system_prompt: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None
) -> Tuple[str, List[str], Optional[str]]:
    """Use unified executor instead of direct SDK calls."""

    # Load session
    session_data = load_user_session(user_id, platform)
    session_id = session_data[0] if session_data else None
    cwd = session_data[1] if session_data else get_user_cwd(user_id, platform)

    # Configure
    config = ExecutorConfig(
        response_mode=ResponseMode.BUFFER_TEXT,
        thinking_mode=ThinkingMode.LOG_ONLY,  # Log but don't show to users
        include_tool_indicators=True,
        enable_sentry=bool(os.getenv("SENTRY_DSN")),
        enable_posthog=bool(os.getenv("POSTHOG_API_KEY")),
        user_id=str(user_id),
        session_id=session_id,
        platform=platform,
        claude_options=ClaudeAgentOptions(
            cwd=cwd,
            system_prompt=system_prompt or "...",
            allowed_tools=allowed_tools or ["Read", "Write", "Bash", "Edit"],
            resume=session_id
        )
    )

    # Execute
    response = await _executor.execute(user_message, config)

    # Save session
    if response.session_id:
        save_user_session(user_id, response.session_id, cwd, platform)

    return response.text, response.tool_uses, response.session_id
```

**Benefits:**
- Bots get observability with zero code changes
- Consistent behavior across platforms
- Easy to add new platforms

### Phase 2: Refactor api.py

**Current:** Duplicated logic in `/query`, `/session/start`, `/session/{id}/query`

**Proposed:**
```python
from sdk_executor import ClaudeExecutor, ExecutorConfig, ResponseMode, ThinkingMode

executor = ClaudeExecutor(
    posthog_api_key=os.getenv("POSTHOG_API_KEY")
)

@app.post("/query")
async def create_query(request: QueryRequest):
    config = ExecutorConfig(
        response_mode=ResponseMode.STREAM if request.stream else ResponseMode.BUFFER_TEXT,
        thinking_mode=ThinkingMode.LOG_ONLY,
        platform="api",
        request_id=str(uuid.uuid4()),
        claude_options=build_options(request)
    )

    if request.stream:
        async def generate():
            async for chunk in executor.execute_streaming(request.prompt, config):
                yield f"data: {{'type': 'text', 'text': {repr(chunk)}}}\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")

    response = await executor.execute(request.prompt, config)
    return QueryResponse(
        response=response.text,
        duration_ms=response.result_metadata.get("duration_ms"),
        num_turns=response.result_metadata.get("num_turns"),
        total_cost_usd=response.result_metadata.get("total_cost_usd")
    )
```

**Benefits:**
- Remove ~100 lines of duplicated message processing
- Get PostHog analytics for free
- Consistent error handling

### Phase 3: Update agent_executor.py

**Current:** Good logging but file-only, not reusable

**Proposed:**
```python
from sdk_executor import ClaudeExecutor, ExecutorConfig, ThinkingMode, ResponseMode

executor = ClaudeExecutor(
    posthog_api_key=os.getenv("POSTHOG_API_KEY")
)

async def call_agent_sdk(
    prompt: str,
    working_directory: str,
    task_id: str,
    agent_id: int
) -> Dict[str, Any]:
    """Now uses unified executor with all logging built-in."""

    config = ExecutorConfig(
        response_mode=ResponseMode.BUFFER_ALL,
        thinking_mode=ThinkingMode.INCLUDE,  # Agents want thinking
        include_tool_indicators=False,
        enable_file_logging=True,
        enable_posthog=True,
        log_directory=str(Path(working_directory) / "agent_log"),
        request_id=f"{task_id}_{agent_id}",
        platform="agent",
        claude_options=ClaudeAgentOptions(
            system_prompt="You are an expert software developer",
            permission_mode="bypassPermissions",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            cwd=working_directory
        )
    )

    response = await executor.execute(prompt, config)

    return {
        "success": not response.result_metadata.get("is_error"),
        "summary": response.text,
        "thinking": response.thinking_blocks,
        **response.result_metadata
    }
```

**Benefits:**
- Keep all existing file logging
- Add PostHog for dashboards
- Reduce code from 200+ lines to ~30

---

## Key Decisions & Trade-offs

### 1. Protocol vs Base Class for Backends

**Chose:** Protocol (duck typing)

**Why:**
- More flexible - any object with right methods works
- No inheritance required
- Easy to wrap existing logging libraries
- Pythonic

**Trade-off:** Less type safety, but worth it for flexibility

### 2. Sync vs Async Backends

**Chose:** Sync methods in backends

**Why:**
- Most logging APIs are sync (Sentry, PostHog, files)
- Executor can handle async if needed
- Simpler implementation

**Trade-off:** Potential blocking, but logging is typically fast

### 3. Configuration Object vs Kwargs

**Chose:** Dataclass config object

**Why:**
- Type-safe
- Easy to pass around
- Clear what's configurable
- IDE autocomplete

**Trade-off:** More verbose, but clearer

### 4. ResponseMode Enum vs Boolean Flags

**Chose:** Enum for mode

**Why:**
- Mutually exclusive states
- Clear intent
- Extensible (can add modes)

**Trade-off:** More code, but clearer semantics

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create `server/sdk_executor.py` with base classes
- [ ] Implement ConsoleBackend
- [ ] Implement FileLoggingBackend (port from agent_executor)
- [ ] Write unit tests for ResponseProcessor
- [ ] Write unit tests for ObservabilityHub

### Phase 2: Observability Backends (Week 1-2)
- [ ] Implement SentryBackend with transaction tracking
- [ ] Implement PostHogBackend with LLM analytics
- [ ] Add environment variable configuration
- [ ] Test each backend independently
- [ ] Write integration tests

### Phase 3: Migration - Bots (Week 2)
- [ ] Update bot_common.py to use ClaudeExecutor
- [ ] Test Telegram bot with new executor
- [ ] Test Slack bot with new executor
- [ ] Verify sessions still work
- [ ] Check error handling

### Phase 4: Migration - API (Week 2-3)
- [ ] Refactor api.py endpoints
- [ ] Update streaming response logic
- [ ] Test all endpoints
- [ ] Verify backward compatibility

### Phase 5: Migration - Agent (Week 3)
- [ ] Update agent_executor.py
- [ ] Verify file logging still works
- [ ] Test event emissions
- [ ] Performance testing

### Phase 6: Documentation & Rollout (Week 3-4)
- [ ] Write comprehensive docstrings
- [ ] Create migration guide
- [ ] Update README with observability setup
- [ ] Add example configurations
- [ ] Deploy to staging
- [ ] Monitor metrics
- [ ] Deploy to production

---

## Conclusion

**Recommended Approach:**

1. **Start with sdk_executor.py** - Build it as a standalone module
2. **Test thoroughly** with synthetic workloads
3. **Migrate bots first** - They're simpler, good test bed
4. **Then API** - More complex but high value
5. **Finally agent_executor** - Already has good patterns, just needs observability

**Expected Outcomes:**

- ✅ **70% code reduction** in SDK calling logic
- ✅ **Unified observability** across all interfaces
- ✅ **Better debugging** with Sentry error tracking
- ✅ **Product analytics** with PostHog LLM metrics
- ✅ **Flexible response handling** (streaming, filtering, etc.)
- ✅ **Easier to add new platforms** (Discord bot, CLI, etc.)

**Next Steps:**

1. Review this analysis
2. Decide on observability backends (Sentry? PostHog? Both?)
3. Create feature branch for sdk_executor implementation
4. Start with Phase 1 implementation

**Questions for Discussion:**

1. Which observability backends are priority? (Sentry, PostHog, custom?)
2. Should we maintain backward compatibility during migration or break APIs?
3. What's the timeline? (Suggested: 3-4 weeks for full migration)
4. Do we want to add more response modes? (e.g., BUFFER_TOOLS_ONLY for tool monitoring)
5. Should thinking blocks be configurable per-user in bots?
