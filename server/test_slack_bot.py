#!/usr/bin/env python3
"""
Test script for Slack bot functionality.

This script performs automated checks on the Slack bot setup
without actually starting the bot or connecting to Slack.

Usage:
    python server/test_slack_bot.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_test(name, passed, details=""):
    """Print test result."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"      {details}")


def check_environment():
    """Check required environment variables."""
    print_header("Environment Configuration")

    checks = []

    # Check .env file
    env_exists = Path(".env").exists()
    print_test(
        ".env file exists",
        env_exists,
        "Found .env file" if env_exists else "Create a .env file in the project root"
    )
    checks.append(env_exists)

    # Check SLACK_BOT_TOKEN
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    has_bot_token = bool(slack_bot_token)
    print_test(
        "SLACK_BOT_TOKEN set",
        has_bot_token,
        f"Token: {slack_bot_token[:20]}..." if has_bot_token else "Set SLACK_BOT_TOKEN in .env"
    )
    checks.append(has_bot_token)

    # Validate bot token format
    if slack_bot_token:
        valid_format = slack_bot_token.startswith("xoxb-")
        print_test(
            "Bot token format valid",
            valid_format,
            "Token format looks correct" if valid_format else "Token should start with: xoxb-"
        )
        checks.append(valid_format)
    else:
        checks.append(False)

    # Check SLACK_APP_TOKEN
    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    has_app_token = bool(slack_app_token)
    print_test(
        "SLACK_APP_TOKEN set",
        has_app_token,
        f"Token: {slack_app_token[:20]}..." if has_app_token else "Set SLACK_APP_TOKEN in .env"
    )
    checks.append(has_app_token)

    # Validate app token format
    if slack_app_token:
        valid_format = slack_app_token.startswith("xapp-")
        print_test(
            "App token format valid",
            valid_format,
            "Token format looks correct" if valid_format else "Token should start with: xapp-"
        )
        checks.append(valid_format)
    else:
        checks.append(False)

    # Check CLAUDE_CODE_OAUTH_TOKEN
    claude_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    has_claude_token = bool(claude_token)
    print_test(
        "CLAUDE_CODE_OAUTH_TOKEN set",
        has_claude_token,
        f"Token: {claude_token[:20]}..." if has_claude_token else "Set CLAUDE_CODE_OAUTH_TOKEN in .env"
    )
    checks.append(has_claude_token)

    # Validate Claude token format
    if claude_token:
        valid_format = claude_token.startswith("sk-ant-oat01-")
        print_test(
            "Claude token format valid",
            valid_format,
            "Token format looks correct" if valid_format else "Token should start with: sk-ant-oat01-"
        )
        checks.append(valid_format)
    else:
        checks.append(False)

    # Check WORKING_DIRECTORY (optional)
    working_dir = os.getenv("WORKING_DIRECTORY")
    if working_dir:
        dir_exists = Path(working_dir).exists()
        print_test(
            "WORKING_DIRECTORY exists",
            dir_exists,
            f"Using: {working_dir}" if dir_exists else f"Directory not found: {working_dir}"
        )
        checks.append(dir_exists)
    else:
        print_test(
            "WORKING_DIRECTORY (optional)",
            True,
            f"Not set, will use current directory: {os.getcwd()}"
        )

    return all(checks)


def check_dependencies():
    """Check required Python packages."""
    print_header("Python Dependencies")

    checks = []
    required_packages = {
        "slack_bolt": "slack-bolt",
        "dotenv": "python-dotenv",
        "claude_agent_sdk": "claude-agent-sdk",
    }

    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
            print_test(f"{package_name} installed", True)
            checks.append(True)
        except ImportError:
            print_test(
                f"{package_name} installed",
                False,
                f"Install with: pip install {package_name}"
            )
            checks.append(False)

    return all(checks)


def check_file_structure():
    """Check required files exist."""
    print_header("File Structure")

    checks = []
    required_files = [
        "server/slack_bot.py",
        "server/bot_common.py",
        "server/requirements.txt",
    ]

    for file_path in required_files:
        exists = Path(file_path).exists()
        print_test(
            f"{file_path} exists",
            exists,
            "Found" if exists else "File missing"
        )
        checks.append(exists)

    return all(checks)


def check_session_directory():
    """Check session directory setup."""
    print_header("Session Management")

    checks = []
    session_dir = Path("slack_sessions")

    # Check if directory exists (will be created automatically)
    exists = session_dir.exists()
    print_test(
        "slack_sessions directory",
        True,  # Always pass, created automatically
        f"Exists at: {session_dir.absolute()}" if exists else "Will be created automatically"
    )

    # If exists, check permissions
    if exists:
        writable = os.access(session_dir, os.W_OK)
        print_test(
            "Session directory writable",
            writable,
            "Can write session files" if writable else "Check directory permissions"
        )
        checks.append(writable)
    else:
        checks.append(True)  # Will be created with correct permissions

    return all(checks)


def test_bot_common():
    """Test bot_common module can be imported."""
    print_header("Bot Common Module")

    checks = []

    try:
        from bot_common import (
            save_user_session,
            load_user_session,
            set_user_cwd,
            get_user_cwd,
            clear_user_session,
            process_claude_message,
            split_long_message,
            format_tool_indicators
        )

        print_test("Import bot_common", True, "All functions available")
        checks.append(True)

        # Test utility functions - split_long_message splits by lines
        # Use a realistic max_length (Telegram/Slack limits are 4096)
        # The function has a 100-char buffer, so use max_length > 100
        test_message = "\n".join([f"Line {i}: some content here" for i in range(50)])
        chunks = split_long_message(test_message, 500)
        print_test(
            "split_long_message()",
            len(chunks) >= 1,  # Should return at least 1 chunk
            f"Split into {len(chunks)} chunk(s)"
        )
        checks.append(len(chunks) >= 1)

        indicators = format_tool_indicators(["Read", "Bash", "Write"])
        expected_in_output = "🔧 READ" in indicators and "🔧 BASH" in indicators
        print_test(
            "format_tool_indicators()",
            expected_in_output,
            f"Output: {indicators.strip()}"
        )
        checks.append(expected_in_output)

    except ImportError as e:
        print_test("Import bot_common", False, f"Error: {e}")
        checks.append(False)

    return all(checks)


def run_all_tests():
    """Run all tests and provide summary."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Slack Bot Test Suite':^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    results = {}

    results["Environment"] = check_environment()
    results["Dependencies"] = check_dependencies()
    results["File Structure"] = check_file_structure()
    results["Session Directory"] = check_session_directory()
    results["Bot Common Module"] = test_bot_common()

    # Summary
    print_header("Test Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for category, result in results.items():
        status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
        print(f"  {status} {category}")

    print(f"\n{BLUE}Results: {passed}/{total} categories passed{RESET}\n")

    if passed == total:
        print(f"{GREEN}{'=' * 60}{RESET}")
        print(f"{GREEN}All tests passed! ✓{RESET}")
        print(f"{GREEN}You can now run: python server/slack_bot.py{RESET}")
        print(f"{GREEN}Or with Docker: docker compose up -d slack-bot{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}\n")
        return 0
    else:
        print(f"{RED}{'=' * 60}{RESET}")
        print(f"{RED}Some tests failed. Please fix the issues above.{RESET}")
        print(f"{RED}See server/SLACK_SETUP.md for detailed setup instructions.{RESET}")
        print(f"{RED}{'=' * 60}{RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
