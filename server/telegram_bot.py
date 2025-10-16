"""
Telegram Bot for Claude Agent SDK
==================================

A Telegram bot that enables users to interact with Claude Code through
direct messages. Features include:
- Per-user session management
- Per-user working directory configuration
- Streaming responses from Claude
- Persistent conversation context

Usage:
    python telegram_bot.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

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

# Configuration
# Telegram message length limit
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


# ==================== Command Handlers ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    welcome_message = f"""👋 Welcome to Claude Code Bot!

I'm powered by Claude Sonnet 4.5 and the Claude Agent SDK. I can help you with:
• Code analysis and development
• File operations in your working directory
• Multi-turn conversations with context
• Tool usage (Read, Write, Bash, Edit)

**Getting Started:**
1. Set your working directory: /setcwd <path>
2. Check your current directory: /getcwd
3. Start chatting! Just send me a message

**Commands:**
/help - Show available commands
/setcwd - Set working directory
/getcwd - Show current working directory
/searchcwd - Search for directories
/reset - Clear conversation history

Let's get started! What would you like to do?"""

    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show available commands."""
    help_message = """🤖 **Claude Code Bot - Commands**

**Setup Commands:**
/setcwd <path> - Set your working directory for file operations
/getcwd - Show your current working directory
/searchcwd <query> - Search for directories matching a pattern

**Conversation Commands:**
/reset - Clear your conversation history (keeps cwd setting)
/showthinking on/off - Toggle thinking blocks visibility
/start - Show welcome message
/help - Show this help message

**How to Use:**
Just send me a regular message to chat! I'll remember the context of our conversation and can perform file operations in your configured working directory.

**Examples:**
• "List all Python files in the current directory"
• "Read the contents of README.md"
• "Create a new file called test.py with a hello world function"
• "What's the difference between these two files?"

**Pro Tip:**
To send Claude Code slash commands (like /help or /clear), escape the slash with a backslash: `\/help` or `\/clear`

Your conversations are private and stored locally per user."""

    await update.message.reply_text(help_message, parse_mode='Markdown')


async def setcwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcwd command - set working directory."""
    user_id = update.effective_user.id

    # Check if path argument provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ Please provide a directory path.\n\n"
            "Usage: /setcwd <path>\n"
            "Example: /setcwd C:\\Users\\YourName\\Projects"
        )
        return

    # Get the path (join args in case path has spaces)
    path = " ".join(context.args)

    # Validate path exists and is a directory
    if not os.path.exists(path):
        await update.message.reply_text(
            f"❌ Path does not exist: {path}\n\n"
            "Please check the path and try again.\n"
            "Tip: Use /searchcwd to find directories"
        )
        return

    if not os.path.isdir(path):
        await update.message.reply_text(
            f"❌ Path is not a directory: {path}\n\n"
            "Please provide a valid directory path."
        )
        return

    # Convert to absolute path
    abs_path = os.path.abspath(path)

    # Save the working directory
    set_user_cwd(str(user_id), abs_path, "telegram")

    await update.message.reply_text(
        f"✅ Working directory set to:\n{abs_path}\n\n"
        "You can now chat with me and I'll use this directory for file operations!"
    )


async def getcwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getcwd command - show current working directory."""
    user_id = update.effective_user.id
    cwd = get_user_cwd(str(user_id), "telegram")

    await update.message.reply_text(
        f"📁 Your current working directory:\n{cwd}\n\n"
        "Use /setcwd to change it."
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reset command - clear conversation session."""
    user_id = update.effective_user.id

    clear_user_session(str(user_id), "telegram")

    await update.message.reply_text(
        "🔄 Conversation cleared!\n\n"
        "Your working directory setting has been preserved.\n"
        "We can start a fresh conversation now."
    )


async def showthinking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /showthinking command - toggle thinking blocks visibility."""
    user_id = update.effective_user.id

    # Check if toggle argument provided
    if not context.args or len(context.args) == 0:
        # Show current status
        from bot_common import get_show_thinking
        current = get_show_thinking(str(user_id), "telegram")
        status = "ON" if current else "OFF"
        await update.message.reply_text(
            f"💭 Thinking blocks are currently: *{status}*\n\n"
            "Usage:\n"
            "/showthinking on - Show thinking blocks\n"
            "/showthinking off - Hide thinking blocks\n\n"
            "Thinking blocks show Claude's reasoning process.",
            parse_mode='Markdown'
        )
        return

    # Get the toggle value
    toggle = context.args[0].lower()

    if toggle not in ["on", "off"]:
        await update.message.reply_text(
            "⚠️ Invalid argument. Use 'on' or 'off'.\n\n"
            "Examples:\n"
            "/showthinking on\n"
            "/showthinking off"
        )
        return

    # Import and use bot_common functions
    from bot_common import set_show_thinking
    show_thinking = (toggle == "on")
    set_show_thinking(str(user_id), show_thinking, "telegram")

    status = "enabled" if show_thinking else "disabled"
    emoji = "✅" if show_thinking else "❌"

    await update.message.reply_text(
        f"{emoji} Thinking blocks {status}!\n\n"
        f"{'I will now show my reasoning process in responses.' if show_thinking else 'I will now hide my thinking process.'}"
    )


async def searchcwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /searchcwd command - search for directories."""
    user_id = update.effective_user.id

    # Check if search query provided
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "⚠️ Please provide a search query.\n\n"
            "Usage: /searchcwd <query>\n"
            "Examples:\n"
            "  /searchcwd Projects\n"
            "  /searchcwd Documents\n"
            "  /searchcwd workspace"
        )
        return

    query = " ".join(context.args)

    await update.message.reply_text(
        f"🔍 Searching for directories matching '{query}'...\n"
        "This may take a moment..."
    )

    try:
        # Use shared search function
        matches = search_directories(query, max_results=15, max_depth=3)

        # Format results
        if matches:
            response = f"📁 Found {len(matches)} matching directories:\n\n"

            for i, match in enumerate(matches, 1):
                response += f"{i}. {match}\n"

            response += (
                "\n💡 To set one as your working directory:\n"
                "/setcwd <path>\n\n"
                "Example:\n"
                f"/setcwd {matches[0]}"
            )

            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                f"❌ No directories found matching '{query}'.\n\n"
                "Tips:\n"
                "• Try a shorter search term\n"
                "• Check the spelling\n"
                "• Use a more general term (e.g., 'work' instead of 'workspace2024')"
            )

    except Exception as e:
        logger.error(f"Error searching directories for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ An error occurred while searching for directories.\n"
            "Please try again or specify the full path using /setcwd"
        )


# ==================== Message Handler ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle regular text messages and interface with Claude SDK.

    This function:
    1. Processes message through unified SDK executor
    2. Gets response with observability (file logging, Sentry, PostHog)
    3. Sends response back to Telegram
    """
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text

    # Handle \/ escape for slash commands
    # If message starts with \/, replace it with / so Claude can interpret it
    if user_message.startswith("\\/"):
        user_message = "/" + user_message[2:]
        logger.info(f"Converted \\/ escape to / for command: {user_message[:50]}...")

    logger.info(f"Received message from user {user_id} ({user.username}): {user_message[:50]}...")

    try:
        # Send "typing" indicator
        await update.message.chat.send_action("typing")

        # Process message through Claude SDK (shared logic with observability)
        response_text, tool_uses, new_session_id = await process_claude_message(
            user_id=str(user_id),
            user_message=user_message,
            platform="telegram"
        )

        # Add tool usage indicators if any tools were used
        if tool_uses:
            response_text += format_tool_indicators(tool_uses)

        # Send response to user (handle Telegram message length limit)
        await send_long_message(update.message.chat_id, response_text, context)

    except Exception as e:
        logger.error(f"Error handling message from user {user_id}: {e}", exc_info=True)

        error_message = (
            "⚠️ Sorry, I encountered an error processing your message.\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or use /reset to start a fresh conversation."
        )

        await update.message.reply_text(error_message)


async def send_long_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a long message, splitting it if necessary due to Telegram's 4096 character limit.

    Args:
        chat_id: Telegram chat ID
        text: Message text to send
        context: Bot context for sending messages
    """
    # Use shared function to split message
    chunks = split_long_message(text, MAX_TELEGRAM_MESSAGE_LENGTH)

    # Send all chunks
    for i, chunk in enumerate(chunks):
        if i > 0:
            # Add indicator for continued messages
            chunk = f"(continued {i+1}/{len(chunks)})\n\n{chunk}"
        await context.bot.send_message(chat_id=chat_id, text=chunk)


def main():
    """Main entry point for the Telegram bot."""
    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_API_KEY")
    if not bot_token:
        logger.error("TELEGRAM_BOT_API_KEY not found in environment variables")
        logger.error("Please set TELEGRAM_BOT_API_KEY in your .env file")
        return

    # Build the application
    logger.info("Initializing Telegram bot...")
    application = ApplicationBuilder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setcwd", setcwd_command))
    application.add_handler(CommandHandler("getcwd", getcwd_command))
    application.add_handler(CommandHandler("searchcwd", searchcwd_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("showthinking", showthinking_command))

    # Add message handler for regular text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    logger.info("Starting Telegram bot polling...")
    logger.info("Bot is ready to receive messages!")
    application.run_polling()


if __name__ == "__main__":
    main()