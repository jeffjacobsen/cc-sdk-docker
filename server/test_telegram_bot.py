#!/usr/bin/env python3
"""
Test script for Telegram bot functionality.

This script performs automated checks on the Telegram bot setup
without actually starting the bot or connecting to Telegram.

Usage:
    python server/test_telegram_bot.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import telegram_bot
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# ANSI color codes for output
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

    # Check .env file exists
    env_exists = Path(".env").exists()
    print_test(
        ".env file exists",
        env_exists,
        "Found .env file" if env_exists else "Create a .env file in the project root"
    )
    checks.append(env_exists)

    # Check TELEGRAM_BOT_API_KEY
    telegram_token = os.getenv("TELEGRAM_BOT_API_KEY")
    has_telegram_token = bool(telegram_token)
    print_test(
        "TELEGRAM_BOT_API_KEY set",
        has_telegram_token,
        f"Token: {telegram_token[:20]}..." if has_telegram_token else "Set TELEGRAM_BOT_API_KEY in .env"
    )
    checks.append(has_telegram_token)

    # Validate token format
    if telegram_token:
        valid_format = ":" in telegram_token and len(telegram_token) > 20
        print_test(
            "Telegram token format valid",
            valid_format,
            "Token format looks correct" if valid_format else "Token should be like: 1234567890:ABCdef..."
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
        "telegram": "python-telegram-bot",
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
        "server/telegram_bot.py",
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
    session_dir = Path("telegram_sessions")

    # Check if directory exists (will be created automatically)
    exists = session_dir.exists()
    print_test(
        "telegram_sessions directory",
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


def test_session_functions():
    """Test session management functions."""
    print_header("Session Functions")

    checks = []

    try:
        # Import session functions
        from telegram_bot import (
            save_user_session,
            load_user_session,
            set_user_cwd,
            get_user_cwd,
            clear_user_session,
            SESSIONS_DIR
        )

        # Create sessions directory if it doesn't exist
        SESSIONS_DIR.mkdir(exist_ok=True)

        # Test with a fake user ID
        test_user_id = 999999999
        test_session_id = "test-session-123"
        test_cwd = "/tmp"

        # Test save
        try:
            save_user_session(test_user_id, test_session_id, test_cwd)
            print_test("save_user_session()", True, "Session saved successfully")
            checks.append(True)
        except Exception as e:
            print_test("save_user_session()", False, f"Error: {e}")
            checks.append(False)

        # Test load
        try:
            loaded = load_user_session(test_user_id)
            if loaded and loaded[0] == test_session_id and loaded[1] == test_cwd:
                print_test("load_user_session()", True, f"Loaded: {loaded}")
                checks.append(True)
            else:
                print_test("load_user_session()", False, f"Mismatch: {loaded}")
                checks.append(False)
        except Exception as e:
            print_test("load_user_session()", False, f"Error: {e}")
            checks.append(False)

        # Test set_user_cwd
        try:
            new_cwd = "/home"
            set_user_cwd(test_user_id, new_cwd)
            retrieved_cwd = get_user_cwd(test_user_id)
            if retrieved_cwd == new_cwd:
                print_test("set_user_cwd() / get_user_cwd()", True, f"CWD: {retrieved_cwd}")
                checks.append(True)
            else:
                print_test("set_user_cwd() / get_user_cwd()", False, f"Mismatch: {retrieved_cwd}")
                checks.append(False)
        except Exception as e:
            print_test("set_user_cwd() / get_user_cwd()", False, f"Error: {e}")
            checks.append(False)

        # Test clear
        try:
            clear_user_session(test_user_id)
            loaded = load_user_session(test_user_id)
            if loaded is None or loaded[0] is None:
                print_test("clear_user_session()", True, "Session cleared, CWD preserved")
                checks.append(True)
            else:
                print_test("clear_user_session()", False, f"Session not cleared: {loaded}")
                checks.append(False)
        except Exception as e:
            print_test("clear_user_session()", False, f"Error: {e}")
            checks.append(False)

        # Clean up test session
        test_file = SESSIONS_DIR / f"{test_user_id}.json"
        if test_file.exists():
            test_file.unlink()
            print_test("Cleanup test session", True, "Test file removed")

    except ImportError as e:
        print_test("Import session functions", False, f"Error: {e}")
        checks.append(False)

    return all(checks)


def run_all_tests():
    """Run all tests and provide summary."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'Telegram Bot Test Suite':^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    results = {}

    results["Environment"] = check_environment()
    results["Dependencies"] = check_dependencies()
    results["File Structure"] = check_file_structure()
    results["Session Directory"] = check_session_directory()
    results["Session Functions"] = test_session_functions()

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
        print(f"{GREEN}You can now run: python server/telegram_bot.py{RESET}")
        print(f"{GREEN}{'=' * 60}{RESET}\n")
        return 0
    else:
        print(f"{RED}{'=' * 60}{RESET}")
        print(f"{RED}Some tests failed. Please fix the issues above.{RESET}")
        print(f"{RED}{'=' * 60}{RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
