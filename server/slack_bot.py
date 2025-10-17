"""
Slack Bot for Claude Agent SDK
================================

A Slack bot that enables users to interact with Claude Code through
direct messages and channels. Features include:
- Per-user session management
- Per-user working directory configuration
- Streaming responses from Claude
- Persistent conversation context
- Channel and DM support
- Rich message formatting with Block Kit

Usage:
    python slack_bot.py

Environment Variables:
    SLACK_BOT_TOKEN: Bot token (xoxb-...)
    SLACK_APP_TOKEN: App token for Socket Mode (xapp-...)
    CLAUDE_CODE_OAUTH_TOKEN: Claude authentication token
    WORKING_DIRECTORY: Default working directory (optional)
"""

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# Import shared bot functionality
from bot_common import (
    save_user_session,
    load_user_session,
    set_user_cwd,
    get_user_cwd,
    clear_user_session,
    set_show_thinking,
    get_show_thinking,
    process_claude_message,
    split_long_message,
    format_tool_indicators,
    search_directories
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Slack message length limit (recommended, actual is 40k but we chunk at 3k)
MAX_SLACK_MESSAGE_LENGTH = 3000

# Initialize Slack app
app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))


# ==================== Command Handlers ====================

@app.command("/start")
async def start_command(ack, command, say):
    """Handle /start command - welcome message."""
    await ack()

    user_id = command['user_id']
    logger.info(f"User {user_id} started the bot")

    welcome_message = f"""👋 Welcome to Claude Code Bot!

I'm powered by Claude Sonnet 4.5 and the Claude Agent SDK. I can help you with:
• Code analysis and development
• File operations in your working directory
• Multi-turn conversations with context
• Tool usage (Read, Write, Bash, Edit)

*Getting Started:*
1. Set your working directory: `/setcwd <path>`
2. Check your current directory: `/getcwd`
3. Start chatting! Just mention me or send a DM

*Commands:*
• `/help` - Show available commands
• `/setcwd` - Set working directory
• `/getcwd` - Show current working directory
• `/searchcwd` - Search for directories
• `/reset` - Clear conversation history

Let's get started! What would you like to do?"""

    await say(text=welcome_message)


@app.command("/help")
async def help_command(ack, command, say):
    """Handle /help command - show available commands."""
    await ack()

    help_message = """🤖 *Claude Code Bot - Commands*

*Setup Commands:*
• `/setcwd <path>` - Set your working directory for file operations
• `/getcwd` - Show your current working directory
• `/searchcwd <query>` - Search for directories matching a pattern

*Conversation Commands:*
• `/reset` - Clear your conversation history (keeps cwd setting)
• `/showthinking on/off` - Toggle thinking blocks visibility
• `/start` - Show welcome message
• `/help` - Show this help message

*How to Use:*
Just mention me (@Claude Code Bot) in a channel or send me a direct message to chat! I'll remember the context of our conversation and can perform file operations in your configured working directory.

*Examples:*
• "List all Python files in the current directory"
• "Read the contents of README.md"
• "Create a new file called test.py with a hello world function"
• "What's the difference between these two files?"

*Pro Tip:*
To send Claude Code slash commands (like `/help` or `/clear`), escape the slash with a backslash: `\/help` or `\/clear`

Your conversations are private and stored locally per user."""

    await say(text=help_message)


@app.command("/setcwd")
async def setcwd_command(ack, command, say):
    """Handle /setcwd command - set working directory."""
    await ack()

    user_id = command['user_id']
    text = command.get('text', '').strip()

    # Check if path argument provided
    if not text:
        await say(
            text="⚠️ Please provide a directory path.\n\n"
            "*Usage:* `/setcwd <path>`\n"
            "*Example:* `/setcwd /home/user/projects`"
        )
        return

    path = text

    # Validate path exists and is a directory
    if not os.path.exists(path):
        await say(
            text=f"❌ Path does not exist: `{path}`\n\n"
            "Please check the path and try again.\n"
            "*Tip:* Use `/searchcwd` to find directories"
        )
        return

    if not os.path.isdir(path):
        await say(
            text=f"❌ Path is not a directory: `{path}`\n\n"
            "Please provide a valid directory path."
        )
        return

    # Convert to absolute path
    abs_path = os.path.abspath(path)

    # Save the working directory
    set_user_cwd(user_id, abs_path, platform="slack")

    await say(
        text=f"✅ Working directory set to:\n`{abs_path}`\n\n"
        "You can now chat with me and I'll use this directory for file operations!"
    )


@app.command("/getcwd")
async def getcwd_command(ack, command, say):
    """Handle /getcwd command - show current working directory."""
    await ack()

    user_id = command['user_id']
    cwd = get_user_cwd(user_id, platform="slack")

    await say(
        text=f"📁 Your current working directory:\n`{cwd}`\n\n"
        "Use `/setcwd` to change it."
    )


@app.command("/reset")
async def reset_command(ack, command, say):
    """Handle /reset command - clear conversation session."""
    await ack()

    user_id = command['user_id']

    clear_user_session(user_id, platform="slack")

    await say(
        text="🔄 Conversation cleared!\n\n"
        "Your working directory setting has been preserved.\n"
        "We can start a fresh conversation now."
    )


@app.command("/showthinking")
async def showthinking_command(ack, command, say):
    """Handle /showthinking command - toggle thinking blocks visibility."""
    await ack()

    user_id = command['user_id']
    toggle = command.get('text', '').strip().lower()

    # Check if toggle argument provided
    if not toggle:
        # Show current status
        current = get_show_thinking(user_id, "slack")
        status = "ON" if current else "OFF"
        await say(
            text=f"💭 Thinking blocks are currently: *{status}*\n\n"
            "*Usage:*\n"
            "`/showthinking on` - Show thinking blocks\n"
            "`/showthinking off` - Hide thinking blocks\n\n"
            "Thinking blocks show Claude's reasoning process."
        )
        return

    if toggle not in ["on", "off"]:
        await say(
            text="⚠️ Invalid argument. Use 'on' or 'off'.\n\n"
            "*Examples:*\n"
            "`/showthinking on`\n"
            "`/showthinking off`"
        )
        return

    # Set preference
    show_thinking = (toggle == "on")
    set_show_thinking(user_id, show_thinking, "slack")

    status = "enabled" if show_thinking else "disabled"
    emoji = "✅" if show_thinking else "❌"

    await say(
        text=f"{emoji} Thinking blocks {status}!\n\n"
        f"{'I will now show my reasoning process in responses.' if show_thinking else 'I will now hide my thinking process.'}"
    )


@app.command("/searchcwd")
async def searchcwd_command(ack, command, say):
    """Handle /searchcwd command - search for directories."""
    await ack()

    user_id = command['user_id']
    query = command.get('text', '').strip()

    # Check if search query provided
    if not query:
        await say(
            text="⚠️ Please provide a search query.\n\n"
            "*Usage:* `/searchcwd <query>`\n"
            "*Examples:*\n"
            "  • `/searchcwd projects`\n"
            "  • `/searchcwd documents`\n"
            "  • `/searchcwd workspace`"
        )
        return

    await say(
        text=f"🔍 Searching for directories matching '{query}'...\n"
        "This may take a moment..."
    )

    try:
        # Search for matching directories
        matches = search_directories(query, max_results=15, max_depth=3)

        # Format results
        if matches:
            response = f"📁 Found {len(matches)} matching directories:\n\n"

            for i, match in enumerate(matches, 1):
                response += f"{i}. `{match}`\n"

            response += (
                "\n💡 To set one as your working directory:\n"
                "`/setcwd <path>`\n\n"
                "*Example:*\n"
                f"`/setcwd {matches[0]}`"
            )

            await say(text=response)
        else:
            await say(
                text=f"❌ No directories found matching '{query}'.\n\n"
                "*Tips:*\n"
                "• Try a shorter search term\n"
                "• Check the spelling\n"
                "• Use a more general term (e.g., 'work' instead of 'workspace2024')"
            )

    except Exception as e:
        logger.error(f"Error searching directories for user {user_id}: {e}", exc_info=True)
        await say(
            text="⚠️ An error occurred while searching for directories.\n"
            "Please try again or specify the full path using `/setcwd`"
        )


# ==================== Message Handler ====================

@app.event("message")
async def handle_message(event, say):
    """
    Handle regular messages and interface with Claude SDK.

    This function:
    1. Loads user's session and cwd configuration
    2. Processes message through Claude SDK (via bot_common)
    3. Sends response back to Slack
    """
    # Ignore bot messages and message changes
    if event.get('subtype') or event.get('bot_id'):
        return

    user_id = event['user']
    channel = event['channel']
    text = event.get('text', '')
    thread_ts = event.get('thread_ts', event.get('ts'))

    logger.info(f"Received message from user {user_id}: {text[:50]}...")

    try:
        # Send "typing" indicator
        await app.client.chat_postMessage(
            channel=channel,
            text="Processing...",
            thread_ts=thread_ts
        )

        # Process message through Claude SDK (shared logic)
        response_text, tool_uses, new_session_id = await process_claude_message(
            user_id=user_id,
            user_message=text,
            platform="slack"
        )

        # Add tool usage indicators if any tools were used
        if tool_uses:
            response_text += format_tool_indicators(tool_uses)

        # Send response to user (handle Slack message length limit)
        await send_long_message(channel, response_text, thread_ts)

    except Exception as e:
        logger.error(f"Error handling message from user {user_id}: {e}", exc_info=True)

        error_message = (
            "⚠️ Sorry, I encountered an error processing your message.\n\n"
            f"*Error:* `{str(e)}`\n\n"
            "Please try again or use `/reset` to start a fresh conversation."
        )

        await say(text=error_message, thread_ts=thread_ts)


async def send_long_message(channel: str, text: str, thread_ts: Optional[str] = None):
    """
    Send a long message, splitting it if necessary due to Slack's character limit.

    Args:
        channel: Slack channel ID
        text: Message text to send
        thread_ts: Thread timestamp (for threaded replies)
    """
    chunks = split_long_message(text, MAX_SLACK_MESSAGE_LENGTH)

    for i, chunk in enumerate(chunks):
        prefix = ""
        if i > 0:
            # Add indicator for continued messages
            prefix = f"_(continued {i+1}/{len(chunks)})_\n\n"

        await app.client.chat_postMessage(
            channel=channel,
            text=prefix + chunk,
            thread_ts=thread_ts
        )


# ==================== App Mention Handler ====================

@app.event("app_mention")
async def handle_mention(event, say):
    """
    Handle @mentions in channels.

    When the bot is mentioned in a channel, process the message.
    """
    user_id = event['user']
    channel = event['channel']
    text = event.get('text', '')
    thread_ts = event.get('thread_ts', event.get('ts'))

    # Remove bot mention from text
    # Format: "<@U123ABC> message here" -> "message here"
    import re
    text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()

    if not text:
        await say(
            text="👋 Hi! Ask me anything or use `/help` to see available commands.",
            thread_ts=thread_ts
        )
        return

    logger.info(f"Received mention from user {user_id} in channel {channel}: {text[:50]}...")

    try:
        # Process message through Claude SDK (shared logic)
        response_text, tool_uses, new_session_id = await process_claude_message(
            user_id=user_id,
            user_message=text,
            platform="slack"
        )

        # Add tool usage indicators if any tools were used
        if tool_uses:
            response_text += format_tool_indicators(tool_uses)

        # Send response to user (handle Slack message length limit)
        await send_long_message(channel, response_text, thread_ts)

    except Exception as e:
        logger.error(f"Error handling mention from user {user_id}: {e}", exc_info=True)

        error_message = (
            "⚠️ Sorry, I encountered an error processing your message.\n\n"
            f"*Error:* `{str(e)}`\n\n"
            "Please try again or use `/reset` to start a fresh conversation."
        )

        await say(text=error_message, thread_ts=thread_ts)


# ==================== Main Entry Point ====================

async def main():
    """Main entry point for the Slack bot."""
    # Get tokens from environment
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")

    if not bot_token:
        logger.error("SLACK_BOT_TOKEN not found in environment variables")
        logger.error("Please set SLACK_BOT_TOKEN in your .env file")
        return

    if not app_token:
        logger.error("SLACK_APP_TOKEN not found in environment variables")
        logger.error("Please set SLACK_APP_TOKEN in your .env file")
        logger.error("Note: Socket Mode requires an App-Level Token (xapp-...)")
        return

    # Start the bot in Socket Mode
    logger.info("Initializing Slack bot...")
    handler = AsyncSocketModeHandler(app, app_token)

    logger.info("Starting Slack bot in Socket Mode...")
    logger.info("Bot is ready to receive messages!")

    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
