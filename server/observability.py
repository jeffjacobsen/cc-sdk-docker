"""
Observability backends for Claude SDK execution

This module provides pluggable observability backends for tracking:
- Request lifecycle (start, completion, errors)
- Message processing
- Performance metrics
- User tracking

Supported backends:
- File logging: JSONL-based logging for debugging
- Console: Development-time logging

Environment variables:
- FILE_LOGGING: Enable file logging (1, true, yes)
- DEBUG: Enable console logging (1, true, yes)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sdk_executor import ExecutorConfig, ProcessedResponse

from claude_agent_sdk import (
    AssistantMessage,
    UserMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
)

# ============================================================================
# Base Backend Interface
# ============================================================================

class ObservabilityBackend:
    """Base class for observability backends"""

    def log_request_start(self, config: "ExecutorConfig", prompt: str):
        """Called when SDK request starts"""
        pass

    def log_message_received(self, config: "ExecutorConfig", message: Any):
        """Called for each message received from SDK"""
        pass

    def log_completion(self, config: "ExecutorConfig", result: "ProcessedResponse"):
        """Called when SDK request completes"""
        pass

    def log_error(self, config: "ExecutorConfig", error: Exception):
        """Called when SDK request fails"""
        pass


# ============================================================================
# File Logging Backend
# ============================================================================

class FileLoggingBackend(ObservabilityBackend):
    """File-based logging in JSONL format (like agent_executor.py)"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enabled = True
        self.start_time = None

    def log_request_start(self, config: "ExecutorConfig", prompt: str):
        self.start_time = time.time()
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                "event": "request_start",
                "user_id": config.user_id,
                "platform": config.platform,
                "prompt_length": len(prompt),
                "prompt_preview": prompt[:200],
                "session_id": config.session_id,
            }, f)
            f.write("\n")

    def log_message_received(self, config: "ExecutorConfig", message: Any):
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"
        
        # Handle Assistant or User messages
        if isinstance(message, AssistantMessage) or isinstance(message, UserMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    # Log text blocks
                    with open(log_file, "a") as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                            "type": "text",
                            "content": block.text[:1000]  # Limit size
                        }, f)
                        f.write("\n")

                elif isinstance(block, ToolUseBlock):
                    # Log tool use
                    with open(log_file, "a") as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_use_id": block.id,
                            "input": block.input
                        }, f)
                        f.write("\n")

                elif isinstance(block, ToolResultBlock):
                    # Log tool result
                    with open(log_file, "a") as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content[:1000] if isinstance(block.content, str) else str(block.content)[:1000],
                            "is_error": block.is_error
                        }, f)
                        f.write("\n")

                elif isinstance(block, ThinkingBlock):
                    # Log thinking blocks
                    with open(log_file, "a") as f:
                        json.dump({
                            "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                            "type": "thinking",
                            "content": block.thinking[:1000]  # Limit size
                        }, f)
                        f.write("\n")

        # Handle system messages
        elif isinstance(message, SystemMessage):
            # Log system messages to summary
            with open(log_file, "a") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                    "type": "SystemMessage",
                    "subtype": message.subtype,
                    "message": str(message)
                }, f)
                f.write("\n")

        # Handle result message (final)
        elif isinstance(message, ResultMessage):
            result_data = {
                "success": not message.is_error,
                "summary": message.result or "Task completed",
                "duration_ms": message.duration_ms,
                "num_turns": message.num_turns,
                "session_id": message.session_id,
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage
            }

            # Log result message to summary
            with open(log_file, "a") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                    "type": "ResultMessage",
                    "is_error": message.is_error,
                    "result": message.result,
                    "duration_ms": message.duration_ms,
                    "num_turns": message.num_turns,
                    "session_id": message.session_id,
                    "total_cost_usd": message.total_cost_usd,
                    "usage": message.usage
                }, f)
                f.write("\n")


    def log_completion(self, config: "ExecutorConfig", result: "ProcessedResponse"):
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": datetime.now().isoformat('T',timespec='seconds'),
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

    def log_error(self, config: "ExecutorConfig", error: Exception):
        log_file = self.log_dir / f"{config.platform or 'sdk'}_requests.jsonl"

        with open(log_file, "a") as f:
            json.dump({
                "timestamp": datetime.now().isoformat('T',timespec='seconds'),
                "event": "request_error",
                "user_id": config.user_id,
                "platform": config.platform,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }, f)
            f.write("\n")


# ============================================================================
# Console Backend
# ============================================================================

class ConsoleBackend(ObservabilityBackend):
    """Console logging for development"""

    def __init__(self):
        self.enabled = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

    def log_request_start(self, config: "ExecutorConfig", prompt: str):
        if self.enabled:
            print(f"[SDK] Request start: user={config.user_id}, platform={config.platform}, prompt_len={len(prompt)}")

    def log_completion(self, config: "ExecutorConfig", result: "ProcessedResponse"):
        if self.enabled:
            print(f"[SDK] Request complete: response_len={len(result.text)}, tools={len(result.tool_uses)}, duration={result.metrics.get('duration_ms', 0)}ms")

    def log_error(self, config: "ExecutorConfig", error: Exception):
        if self.enabled:
            print(f"[SDK] Request error: {type(error).__name__}: {error}")


# ============================================================================
# Observability Hub
# ============================================================================

class ObservabilityHub:
    """Manages multiple observability backends"""

    def __init__(self, backends: Optional[List[ObservabilityBackend]] = None):
        if backends is None:
            # Auto-configure based on environment
            backends = [
                # SentryBackend(),
                # PostHogBackend(),
                ConsoleBackend(),
            ]
            # Add file logging if explicitly enabled
            if os.getenv("FILE_LOGGING", "").lower() in ("1", "true", "yes"):
                backends.append(FileLoggingBackend())

        self.backends = [b for b in backends if getattr(b, 'enabled', True)]

    def log_request_start(self, config: "ExecutorConfig", prompt: str):
        for backend in self.backends:
            try:
                backend.log_request_start(config, prompt)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_message_received(self, config: "ExecutorConfig", message: Any, message_count: int):
        # Emit progress event for each message received
        # emit_event(task_id, "progress", {
        #    "message_count": message_count,
        #    "message_type": type(message).__name__
        # })
        for backend in self.backends:
            try:
                backend.log_message_received(config, message)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_completion(self, config: "ExecutorConfig", result: "ProcessedResponse"):
        for backend in self.backends:
            try:
                backend.log_completion(config, result)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")

    def log_error(self, config: "ExecutorConfig", error: Exception):
        for backend in self.backends:
            try:
                backend.log_error(config, error)
            except Exception as e:
                print(f"[SDK] Observability error in {type(backend).__name__}: {e}")
