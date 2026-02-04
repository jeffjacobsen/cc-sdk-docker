#!/usr/bin/env python3

"""
Example client for testing the Claude Code SDK FastAPI server
Demonstrates all available endpoints
"""

import requests
import json
from typing import Optional


class ClaudeServerClient:
    """Client for interacting with Claude Code SDK Server"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip('/')

    def health_check(self):
        """Check if the server is healthy and authenticated"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def query(self, prompt: str, model: Optional[str] = None, stream: bool = False):
        """Send a one-off query (no conversation context)"""
        data = {"prompt": prompt, "stream": stream}
        if model:
            data["model"] = model

        if stream:
            # Handle streaming response
            with requests.post(
                f"{self.base_url}/query",
                json=data,
                stream=True
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            print(line[6:])  # Remove 'data: ' prefix
        else:
            response = requests.post(f"{self.base_url}/query", json=data)
            response.raise_for_status()
            return response.json()

    def start_session(self, initial_prompt: Optional[str] = None, model: Optional[str] = None):
        """Start a new conversation session

        Note: Using initial_prompt may cause race condition issues.
        Recommended pattern:
        1. Start session without initial_prompt
        2. Use session_query() for first message
        """
        data = {}
        if initial_prompt:
            data["initial_prompt"] = initial_prompt
        if model:
            data["model"] = model

        response = requests.post(f"{self.base_url}/session/start", json=data)
        response.raise_for_status()
        return response.json()

    def session_query(self, session_id: str, prompt: str):
        """Send a query in an existing session (maintains context)"""
        data = {"prompt": prompt}
        response = requests.post(
            f"{self.base_url}/session/{session_id}/query",
            json=data
        )
        response.raise_for_status()
        return response.json()

    def interrupt_session(self, session_id: str):
        """Interrupt the current task in a session"""
        response = requests.post(f"{self.base_url}/session/{session_id}/interrupt")
        response.raise_for_status()
        return response.json()

    def get_session_info(self, session_id: str):
        """Get information about a session"""
        response = requests.get(f"{self.base_url}/session/{session_id}")
        response.raise_for_status()
        return response.json()

    def list_sessions(self):
        """List all active sessions"""
        response = requests.get(f"{self.base_url}/sessions")
        response.raise_for_status()
        return response.json()

    def close_session(self, session_id: str):
        """Close and cleanup a session"""
        response = requests.delete(f"{self.base_url}/session/{session_id}")
        response.raise_for_status()
        return response.json()


def main():
    """Demonstrate all server features"""
    print("=" * 60)
    print("Claude Code SDK Server - Client Example")
    print("=" * 60)

    client = ClaudeServerClient()

    # 1. Health Check
    print("\n1️⃣  Health Check")
    print("-" * 60)
    health = client.health_check()
    print(f"Status: {health['status']}")
    print(f"Authenticated: {health['authenticated']}")
    print(f"Active Sessions: {health['active_sessions']}")

    if not health['authenticated']:
        print("\n⚠️  WARNING: No authentication token found!")
        print("Set CLAUDE_CODE_OAUTH_TOKEN environment variable")
        return

    # 2. One-off Query
    print("\n2️⃣  One-off Query (No Context)")
    print("-" * 60)
    result = client.query("What is 2 + 2? Answer very briefly.")
    print(f"Response: {result['response']}")
    print(f"Duration: {result.get('duration_ms', 'N/A')} ms")
    print(f"Cost: ${result.get('total_cost_usd', 0):.6f}")

    # 3. Start a Session
    print("\n3️⃣  Starting Conversation Session")
    print("-" * 60)
    # Note: Start session without initial_prompt to avoid race condition
    session = client.start_session()
    session_id = session['session_id']
    print(f"Session ID: {session_id}")

    # Send first query after session is ready
    first_query = client.session_query(
        session_id,
        "What is the capital of France?"
    )
    print(f"Response: {first_query['response']}")

    # 4. Continue the Conversation
    print("\n4️⃣  Continuing Conversation (Remembers Context)")
    print("-" * 60)
    followup = client.session_query(
        session_id,
        "What's the population of that city?"
    )
    print(f"Response: {followup['response']}")

    # 5. Another Follow-up
    print("\n5️⃣  Another Follow-up")
    print("-" * 60)
    followup2 = client.session_query(
        session_id,
        "Name three famous landmarks there."
    )
    print(f"Response: {followup2['response']}")

    # 6. List Sessions
    print("\n6️⃣  Active Sessions")
    print("-" * 60)
    sessions = client.list_sessions()
    print(f"Total Sessions: {sessions['count']}")
    print(f"Session IDs: {sessions['active_sessions']}")

    # 7. Session Info
    print("\n7️⃣  Session Information")
    print("-" * 60)
    info = client.get_session_info(session_id)
    print(f"Session ID: {info['session_id']}")
    print(f"Active: {info['active']}")

    # 8. Close Session
    print("\n8️⃣  Closing Session")
    print("-" * 60)
    close_result = client.close_session(session_id)
    print(f"Status: {close_result['status']}")

    print("\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)


def example_streaming():
    """Example of using streaming responses"""
    print("\n📡 Streaming Example")
    print("=" * 60)

    client = ClaudeServerClient()

    print("Sending query with streaming enabled...")
    print("-" * 60)
    client.query(
        "Write a haiku about Docker containers",
        stream=True
    )


if __name__ == "__main__":
    try:
        main()

        # Uncomment to test streaming
        # example_streaming()

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the server is running:")
        print("  docker compose exec python python /app/server/api.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
