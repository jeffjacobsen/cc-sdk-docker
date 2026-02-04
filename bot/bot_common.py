"""
Shared Bot Functionality for Claude Code SDK
==============================================

Common code shared between Telegram and Slack bots:
- Session management (save/load/clear per user)
- Working directory configuration
- Claude SDK integration
- Message processing utilities

This module allows both bots to share core logic while having
platform-specific implementations.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, TYPE_CHECKING

# Lazy import to avoid circular dependencies
# Only imported when process_claude_message is called
if TYPE_CHECKING:
    from server.sdk_executor import (
        ClaudeExecutor,
        ExecutorConfig,
        ResponseMode,
        ThinkingMode,
        ProcessedResponse,
    )

logger = logging.getLogger(__name__)


# ==================== Session Management ====================

def get_sessions_dir(platform: str = "sessions") -> Path:
    """
    Get the sessions directory for a specific platform.

    Args:
        platform: Platform name (e.g., "telegram", "slack")

    Returns:
        Path to sessions directory
    """
    sessions_dir = Path(f"{platform}_sessions")
    sessions_dir.mkdir(exist_ok=True)
    return sessions_dir


def save_user_session(user_id: str, session_id: str, cwd: Optional[str] = None, platform: str = "sessions"):
    """
    Save session data for a user.

    Args:
        user_id: User ID (platform-specific)
        session_id: Claude SDK session ID
        cwd: Working directory path (optional)
        platform: Platform name (e.g., "telegram", "slack")
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    # Load existing data to preserve fields
    existing_data = {}
    if session_file.exists():
        with open(session_file, "r") as f:
            existing_data = json.load(f)

    # Update session data
    session_data = {
        "session_id": session_id,
        "cwd": cwd or existing_data.get("cwd"),
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

    # Preserve created_at timestamp
    if "created_at" in existing_data:
        session_data["created_at"] = existing_data["created_at"]
    else:
        session_data["created_at"] = session_data["last_updated"]

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    logger.info(f"Saved session for user {user_id} ({platform})")


def load_user_session(user_id: str, platform: str = "sessions") -> Optional[Tuple[str, str]]:
    """
    Load session data for a user.

    Args:
        user_id: User ID (platform-specific)
        platform: Platform name (e.g., "telegram", "slack")

    Returns:
        Tuple of (session_id, cwd) if session exists, None otherwise
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    if not session_file.exists():
        return None

    try:
        with open(session_file, "r") as f:
            data = json.load(f)
            session_id = data.get("session_id")
            cwd = data.get("cwd")
            return (session_id, cwd) if session_id else None
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error loading session for user {user_id} ({platform}): {e}")
        return None


def set_user_cwd(user_id: str, cwd: str, platform: str = "sessions"):
    """
    Set the working directory for a user.

    Args:
        user_id: User ID (platform-specific)
        cwd: Working directory path
        platform: Platform name (e.g., "telegram", "slack")
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    # Load existing data or create new
    session_data = {}
    if session_file.exists():
        with open(session_file, "r") as f:
            session_data = json.load(f)

    # Update cwd
    session_data["cwd"] = cwd
    session_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    if "created_at" not in session_data:
        session_data["created_at"] = session_data["last_updated"]

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    logger.info(f"Set cwd for user {user_id} ({platform}): {cwd}")


def get_user_cwd(user_id: str, platform: str = "sessions") -> str:
    """
    Get the working directory for a user.

    Args:
        user_id: User ID (platform-specific)
        platform: Platform name (e.g., "telegram", "slack")

    Returns:
        Working directory path (falls back to WORKING_DIRECTORY env or cwd)
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    if session_file.exists():
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                if data.get("cwd"):
                    return data["cwd"]
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback to environment variable or current directory
    return os.getenv("WORKING_DIRECTORY", os.getcwd())


def clear_user_session(user_id: str, platform: str = "sessions"):
    """
    Clear the session for a user (keeps cwd configuration).

    Args:
        user_id: User ID (platform-specific)
        platform: Platform name (e.g., "telegram", "slack")
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    if session_file.exists():
        try:
            with open(session_file, "r") as f:
                data = json.load(f)

            # Keep only cwd, remove session_id
            new_data = {
                "cwd": data.get("cwd"),
                "show_thinking": data.get("show_thinking", False),
                "created_at": data.get("created_at"),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }

            with open(session_file, "w") as f:
                json.dump(new_data, f, indent=2)

            logger.info(f"Cleared session for user {user_id} ({platform})")
        except Exception as e:
            logger.error(f"Error clearing session for user {user_id} ({platform}): {e}")


def set_show_thinking(user_id: str, show_thinking: bool, platform: str = "sessions"):
    """
    Set whether to show thinking blocks for a user.

    Args:
        user_id: User ID (platform-specific)
        show_thinking: Whether to show thinking blocks
        platform: Platform name (e.g., "telegram", "slack")
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    # Load existing data or create new
    session_data = {}
    if session_file.exists():
        with open(session_file, "r") as f:
            session_data = json.load(f)

    # Update show_thinking preference
    session_data["show_thinking"] = show_thinking
    session_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    if "created_at" not in session_data:
        session_data["created_at"] = session_data["last_updated"]

    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=2)

    logger.info(f"Set show_thinking for user {user_id} ({platform}): {show_thinking}")


def get_show_thinking(user_id: str, platform: str = "sessions") -> bool:
    """
    Get whether to show thinking blocks for a user.

    Args:
        user_id: User ID (platform-specific)
        platform: Platform name (e.g., "telegram", "slack")

    Returns:
        True if thinking blocks should be shown, False otherwise (default: False)
    """
    sessions_dir = get_sessions_dir(platform)
    session_file = sessions_dir / f"{user_id}.json"

    if session_file.exists():
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                return data.get("show_thinking", False)
        except (json.JSONDecodeError, KeyError):
            pass

    return False


# ==================== Claude SDK Integration ====================

async def process_claude_message(
    user_id: str,
    user_message: str,
    platform: str = "sessions",
    system_prompt: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None
) -> Tuple[str, List[str], Optional[str]]:
    """
    Process a user message through Claude SDK using the unified executor.

    Args:
        user_id: User ID (platform-specific)
        user_message: Message text from user
        platform: Platform name (e.g., "telegram", "slack")
        system_prompt: Optional system prompt override
        allowed_tools: Optional list of allowed tools

    Returns:
        Tuple of (response_text, tool_uses, new_session_id)
        - response_text: Claude's text response
        - tool_uses: List of tools used (e.g., ["Read", "Bash"])
        - new_session_id: New session ID for persistence
    """
    # Lazy import to avoid circular dependencies
    from server.sdk_executor import (
        ExecutorConfig,
        ResponseMode,
        ThinkingMode,
        get_executor
    )

    # Load user's session and working directory
    session_data = load_user_session(user_id, platform)
    session_id = None
    cwd = None

    if session_data:
        session_id, cwd = session_data
        if session_id:
            logger.info(f"Resuming session for user {user_id} ({platform}): {session_id}")

    # Get working directory (from session or default)
    if not cwd:
        cwd = get_user_cwd(user_id, platform)

    logger.info(f"Using working directory for user {user_id} ({platform}): {cwd}")

    # Get user's thinking preference
    show_thinking = get_show_thinking(user_id, platform)
    thinking_mode = ThinkingMode.INCLUDE if show_thinking else ThinkingMode.EXCLUDE

    # Configure executor
    config = ExecutorConfig(
        user_id=user_id,
        platform=platform,
        cwd=cwd,
        session_id=session_id,
        system_prompt=system_prompt or "You are Claude Code, a helpful AI assistant powered by Claude Sonnet 4.5. You help users with code, file operations, and technical tasks.",
        allowed_tools=allowed_tools or ["Read", "Write", "Bash", "Edit"],
        response_mode=ResponseMode.BUFFER_TEXT,
        thinking_mode=thinking_mode,
        include_tool_indicators=True,
    )

    # Execute query
    executor = get_executor()
    result = await executor.execute(user_message, config)

    # Handle empty response
    response_text = result.text if result.text.strip() else "I processed your request, but I don't have a text response to show."

    # Save session for future interactions
    if result.session_id:
        save_user_session(user_id, result.session_id, cwd, platform)
        logger.info(f"Saved session for user {user_id} ({platform})")

    return response_text, result.tool_uses, result.session_id


# ==================== Message Utilities ====================

def split_long_message(text: str, max_length: int) -> List[str]:
    """
    Split a long message into chunks respecting the max length.

    Splits by lines to avoid breaking mid-sentence.

    Args:
        text: Message text to split
        max_length: Maximum length per chunk

    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Use a safety buffer: 10% of max_length, minimum 50 chars, maximum 200 chars
    buffer = min(max(int(max_length * 0.1), 50), 200)
    effective_limit = max(max_length - buffer, max_length // 2)  # At least half of max_length

    # Split by lines to avoid breaking mid-sentence
    lines = text.split("\n")

    for line in lines:
        # If adding this line would exceed limit, start new chunk
        if len(current_chunk) + len(line) + 1 > effective_limit:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                # Single line is too long, force it into a chunk
                current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def format_tool_indicators(tool_uses: List[str]) -> str:
    """
    Format tool usage indicators for display.

    Args:
        tool_uses: List of tool names used

    Returns:
        Formatted string like "🔧 READ 🔧 BASH"
    """
    if not tool_uses:
        return ""

    unique_tools = list(dict.fromkeys(tool_uses))  # Remove duplicates, preserve order
    indicators = [f"🔧 {tool.upper()}" for tool in unique_tools]
    return "\n\n" + " ".join(indicators)


# ==================== Directory Search Utilities ====================

def search_directories(query: str, max_results: int = 15, max_depth: int = 3) -> List[str]:
    """
    Search for directories matching a query.

    Args:
        query: Search query (case-insensitive)
        max_results: Maximum number of results to return
        max_depth: Maximum depth to search

    Returns:
        List of matching directory paths
    """
    query = query.lower()
    matches = []

    # Search common locations
    search_paths = []

    # Add user home directory
    home = Path.home()
    search_paths.append(home)

    # Add common Windows locations if on Windows
    if os.name == 'nt':
        search_paths.extend([
            Path("C:\\Users"),
            Path("C:\\Projects"),
            Path("D:\\") if Path("D:\\").exists() else None,
        ])
    else:
        # Add common Unix/Linux locations
        search_paths.extend([
            Path("/home"),
            Path("/opt"),
            Path("/var"),
        ])

    # Remove None values
    search_paths = [p for p in search_paths if p and p.exists()]

    # Search for matching directories
    for base_path in search_paths:
        if len(matches) >= max_results:
            break

        try:
            # Search with depth limit
            for depth in range(max_depth):
                if len(matches) >= max_results:
                    break

                # Build glob pattern for current depth
                pattern = "/".join(["*"] * depth) + "/*" if depth > 0 else "*"

                for item in base_path.glob(pattern):
                    if len(matches) >= max_results:
                        break

                    if item.is_dir() and query in item.name.lower():
                        matches.append(str(item))

        except (PermissionError, OSError):
            # Skip directories we can't access
            continue

    return matches
