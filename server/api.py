#!/usr/bin/env python3

"""
FastAPI server for testing Claude Agent SDK in Docker
Provides HTTP endpoints for interacting with Claude Code
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from claude_agent_sdk import query, ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ToolUseBlock, ResultMessage, ThinkingBlock

# Load environment variables from .env file
load_dotenv()

# Import unified SDK executor
from sdk_executor import (
    get_executor,
    ExecutorConfig,
    ResponseMode,
    ThinkingMode
)


# Global session storage
active_sessions: Dict[str, ClaudeSDKClient] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app"""
    # Startup
    print("🚀 Claude Code SDK Server starting...")
    print(f"📅 Time: {datetime.now().isoformat()}")

    # Check authentication
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    session_token = os.getenv('CLAUDE_CODE_SESSION')

    if oauth_token:
        print(f"✓ OAuth token found: {oauth_token[:20]}...")
    elif session_token:
        print(f"✓ Session token found: {session_token[:20]}...")
    else:
        print("⚠️  WARNING: No authentication token found!")
        print("   Set CLAUDE_CODE_OAUTH_TOKEN environment variable")

    yield

    # Shutdown
    print("\n🛑 Shutting down server...")
    for session_id, client in active_sessions.items():
        print(f"   Closing session: {session_id}")
        try:
            await client.disconnect()
        except Exception as e:
            print(f"   Error closing session {session_id}: {e}")
    active_sessions.clear()
    print("✓ Cleanup complete")


app = FastAPI(
    title="Claude Agent SDK API",
    description="HTTP API for testing Claude Agent SDK in Docker",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QueryRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to Claude")
    model: Optional[str] = Field(None, description="Model to use (e.g., claude-3-5-sonnet-20241022)")
    allowed_tools: Optional[List[str]] = Field(None, description="List of allowed tools")
    permission_mode: Optional[str] = Field(None, description="Permission mode: default, acceptEdits, plan, bypassPermissions")
    max_turns: Optional[int] = Field(None, description="Maximum conversation turns")
    stream: bool = Field(False, description="Stream the response using Server-Sent Events")
    include_thinking: bool = Field(False, description="Include thinking blocks in response")
    cwd: Optional[str] = Field(None, description="Working directory for file operations")


class SessionStartRequest(BaseModel):
    initial_prompt: Optional[str] = Field(None, description="Optional initial prompt")
    model: Optional[str] = Field(None, description="Model to use")
    allowed_tools: Optional[List[str]] = Field(None, description="List of allowed tools")
    permission_mode: Optional[str] = Field(None, description="Permission mode")


class SessionQueryRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send in this session")


class QueryResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    num_turns: Optional[int] = None
    total_cost_usd: Optional[float] = None


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    active: bool


# Helper functions
def build_options(
    model: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None,
    permission_mode: Optional[str] = None,
    max_turns: Optional[int] = None
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from request parameters"""
    options_dict = {}

    if model:
        options_dict['model'] = model
    if allowed_tools:
        options_dict['allowed_tools'] = allowed_tools
    if permission_mode:
        options_dict['permission_mode'] = permission_mode
    if max_turns:
        options_dict['max_turns'] = max_turns

    return ClaudeAgentOptions(**options_dict) if options_dict else ClaudeAgentOptions()


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Claude Code SDK API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "query": "POST /query",
            "session_start": "POST /session/start",
            "session_query": "POST /session/{session_id}/query",
            "session_info": "GET /session/{session_id}",
            "session_list": "GET /sessions",
            "session_close": "DELETE /session/{session_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    session_token = os.getenv('CLAUDE_CODE_SESSION')

    return {
        "status": "healthy",
        "authenticated": bool(oauth_token or session_token),
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/query")
async def create_query(request: QueryRequest):
    """
    One-off query to Claude (no conversation context)
    Each call starts fresh with no memory of previous interactions

    Uses the unified SDK executor with observability support.
    """
    # Build executor configuration
    thinking_mode = ThinkingMode.INCLUDE if request.include_thinking else ThinkingMode.EXCLUDE

    config = ExecutorConfig(
        user_id="api_user",
        platform="api",
        cwd=request.cwd or os.getcwd(),
        allowed_tools=request.allowed_tools,
        response_mode=ResponseMode.STREAM if request.stream else ResponseMode.BUFFER_ALL,
        thinking_mode=thinking_mode,
        include_tool_indicators=False,  # API doesn't need tool indicators
        metadata={
            "model": request.model,
            "permission_mode": request.permission_mode,
            "max_turns": request.max_turns,
        }
    )

    # Stream response if requested
    if request.stream:
        async def stream_response():
            """Stream responses using Server-Sent Events format"""
            try:
                executor = get_executor()
                async for message, final_result in executor.execute_stream(request.prompt, config):
                    if message:
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    yield f"data: {{'type': 'text', 'text': {repr(block.text)}}}\n\n"
                                elif isinstance(block, ToolUseBlock):
                                    yield f"data: {{'type': 'tool_use', 'name': '{block.name}', 'id': '{block.id}'}}\n\n"
                                elif isinstance(block, ThinkingBlock) and request.include_thinking:
                                    yield f"data: {{'type': 'thinking', 'text': {repr(block.thinking)}}}\n\n"
                        elif isinstance(message, ResultMessage):
                            result_data = {
                                'type': 'result',
                                'subtype': message.subtype,
                                'duration_ms': message.duration_ms,
                                'num_turns': message.num_turns,
                                'total_cost_usd': message.total_cost_usd
                            }
                            yield f"data: {result_data}\n\n"
                    elif final_result:
                        # Stream final metrics
                        yield f"data: {{'type': 'metrics', 'duration_ms': {final_result.metrics.get('duration_ms', 0)}}}\n\n"

                yield "data: {'type': 'done'}\n\n"
            except Exception as e:
                error_data = {'type': 'error', 'message': str(e)}
                yield f"data: {error_data}\n\n"

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    # Otherwise, collect full response using executor
    try:
        executor = get_executor()
        result = await executor.execute(request.prompt, config)

        return QueryResponse(
            response=result.text,
            duration_ms=result.metrics.get("duration_ms"),
            num_turns=None,  # Not available without ResultMessage
            total_cost_usd=None  # Not available without ResultMessage
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/start")
async def start_session(request: SessionStartRequest):
    """
    Start a new conversation session with Claude
    The session maintains context across multiple queries
    """
    session_id = str(uuid.uuid4())

    options = build_options(
        model=request.model,
        allowed_tools=request.allowed_tools,
        permission_mode=request.permission_mode
    )

    try:
        client = ClaudeSDKClient(options=options)

        # Connect to the CLI process
        await client.connect()

        # Give the process a moment to initialize
        await asyncio.sleep(0.1)

        # Store session
        active_sessions[session_id] = client

        response_text = ""

        # If there was an initial prompt, send it and get the response
        if request.initial_prompt:
            try:
                await client.query(request.initial_prompt)
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text
            except Exception as query_error:
                # If query fails, clean up the client
                await client.disconnect()
                del active_sessions[session_id]
                raise query_error

        return {
            "session_id": session_id,
            "status": "started",
            "initial_response": response_text if request.initial_prompt else None,
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/query")
async def session_query(session_id: str, request: SessionQueryRequest):
    """
    Send a query in an existing session
    Claude will remember previous context from this session
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    client = active_sessions[session_id]

    try:
        await client.query(request.prompt)

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        return {
            "session_id": session_id,
            "response": response_text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    """Interrupt the current task in a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    client = active_sessions[session_id]

    try:
        await client.interrupt()
        return {"status": "interrupted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionInfo(
        session_id=session_id,
        created_at=datetime.now().isoformat(),  # We could track this properly
        active=True
    )


@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "active_sessions": list(active_sessions.keys()),
        "count": len(active_sessions)
    }


@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    """Close and cleanup a session

    Note: The SDK's disconnect() method has known issues with TaskGroup cleanup.
    We handle this gracefully by catching all exceptions during disconnect.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    client = active_sessions[session_id]

    # Try to disconnect gracefully, but ignore any errors
    # The SDK has issues with TaskGroup._exceptions during cleanup
    try:
        await client.disconnect()
    except Exception as disconnect_error:
        # This is expected - SDK has cleanup issues, but session is still closed
        pass

    # Always remove from active sessions
    del active_sessions[session_id]
    return {"status": "closed", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 3000))
    print(f"\n🚀 Starting Claude Code SDK Server on port {port}")
    print(f"📖 API docs: http://localhost:{port}/docs")
    print(f"💡 Health check: http://localhost:{port}/health\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
