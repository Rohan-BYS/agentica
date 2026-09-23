import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.router import AIBrowserRouter

app = FastAPI(title="Agentica Remote MCP & HTTP Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = AIBrowserRouter()
sessions: Dict[str, asyncio.Queue] = {}

TOOLS = [
    {
        "name": "browse",
        "description": "Fetch URL with auto-escalation (Text/Structural/Visual)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "mode": {"type": "string", "enum": ["auto", "text", "struct", "visual"]}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browse_batch",
        "description": "Fetch multiple URLs concurrently with RAM safety",
        "inputSchema": {
            "type": "object",
            "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
            "required": ["urls"]
        }
    },
    {
        "name": "snapshot",
        "description": "Get current page AXTree with @eN interactive references",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "click",
        "description": "Click element by @eN reference handle",
        "inputSchema": {
            "type": "object",
            "properties": {"ref": {"type": "string"}},
            "required": ["ref"]
        }
    },
    {
        "name": "fill",
        "description": "Type text into form input by @eN reference handle",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string"},
                "text": {"type": "string"}
            },
            "required": ["ref", "text"]
        }
    },
    {
        "name": "screenshot",
        "description": "Capture page screenshot (returns file_path and image_base64)",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    },
    {
        "name": "get_human_active_tab",
        "description": "Inspect and extract content from the user's active tab in the desktop Agentica browser",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_memory_status",
        "description": "Check real-time RAM usage and safe concurrency limits",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

async def dispatch_tool(name: str, args: Dict[str, Any]) -> Any:
    if name == "browse":
        mode = args.get("mode", "auto")
        return await router.browse(args["url"], mode=mode)
    elif name == "browse_batch":
        return await router.browse_batch(args["urls"])
    elif name == "snapshot":
        return await router.snapshot()
    elif name == "click":
        return await router.click(args["ref"])
    elif name == "fill":
        return await router.fill(args["ref"], args["text"])
    elif name == "screenshot":
        return await router.screenshot(args["url"])
    elif name == "get_memory_status":
        return await router.get_memory_status()
    elif name == "get_human_active_tab":
        return await router.get_human_active_tab()
    return {"error": f"Tool '{name}' not found"}

async def handle_jsonrpc(req: Dict[str, Any]) -> Dict[str, Any]:
    method = req.get("method")
    msg_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentica-mcp-remote", "version": "1.0.0"}
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS}
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        try:
            res = await dispatch_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res)}],
                    "isError": False
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True
                }
            }
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"}
    }

# -------------------------------------------------------------------------
# Standard MCP SSE Transport Endpoints
# -------------------------------------------------------------------------

@app.get("/sse")
async def sse_endpoint(request: Request):
    """MCP SSE endpoint for remote MCP clients (Hermes, Claude, etc.)"""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue

    async def event_generator():
        # First event informs the client of the endpoint to send POST messages to
        yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": ping\n\n"
        finally:
            sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/messages")
async def messages_endpoint(request: Request, session_id: Optional[str] = None):
    """Receives JSON-RPC messages from the remote MCP client"""
    body = await request.json()
    resp = await handle_jsonrpc(body)
    
    if resp:
        # If this request is tied to an active SSE session, send it down the stream
        if session_id and session_id in sessions:
            await sessions[session_id].put(resp)
        return JSONResponse(content=resp)
    return Response(status_code=202)

# -------------------------------------------------------------------------
# Direct JSON-RPC Endpoint (Standard HTTP POST)
# -------------------------------------------------------------------------

@app.post("/mcp")
async def direct_mcp_endpoint(request: Request):
    """Direct HTTP POST JSON-RPC 2.0 endpoint"""
    body = await request.json()
    resp = await handle_jsonrpc(body)
    return JSONResponse(content=resp if resp else {"status": "ok"})

# -------------------------------------------------------------------------
# Health Check / Status
# -------------------------------------------------------------------------

@app.get("/")
async def root():
    mem = await router.get_memory_status()
    return {
        "status": "online",
        "service": "Agentica Remote MCP & Browser Gateway",
        "mcp_sse_endpoint": "/sse",
        "mcp_post_endpoint": "/mcp",
        "memory_status": mem,
        "available_tools": [t["name"] for t in TOOLS]
    }

if __name__ == "__main__":
    uvicorn.run("src.server.mcp_http_server:app", host="0.0.0.0", port=8000, reload=False)
