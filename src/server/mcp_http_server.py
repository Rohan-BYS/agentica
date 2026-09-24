import asyncio
import json
import uuid
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

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

LOG_FILE = PROJECT_DIR / "data" / "mcp_server.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log_event(text: str):
    """Log to console and file so discovery failures are never silent."""
    msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Agentica MCP-HTTP] {text}\n"
    sys.stderr.write(msg)
    sys.stderr.flush()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass

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
    },
    {
        "name": "talk_to_developer",
        "description": "Send a direct message or bug report to the human developer/Antigravity and receive the latest developer response.",
        "inputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"]
        }
    },
    {
        "name": "get_developer_messages",
        "description": "Get all messages and replies from the developer/Antigravity.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

async def dispatch_tool(name: str, args: Dict[str, Any]) -> Any:
    log_event(f"Dispatching tool '{name}' with args {list(args.keys())}")
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
    elif name == "talk_to_developer":
        msg = args.get("message", "")
        p = PROJECT_DIR / "data" / "hermes_messages.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if p.exists():
            try:
                history = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append({
            "timestamp": time.time(),
            "sender": "Hermes",
            "message": msg
        })
        p.write_text(json.dumps(history, indent=2), encoding="utf-8")
        dev_replies = [m for m in history if m.get("sender") != "Hermes"]
        latest_reply = dev_replies[-1]["message"] if dev_replies else "Message received! The developer is working on it."
        return {
            "status": "delivered",
            "reply": latest_reply
        }
    elif name == "get_developer_messages":
        p = PROJECT_DIR / "data" / "hermes_messages.json"
        history = []
        if p.exists():
            try:
                history = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"messages": history}
    return {"error": f"Tool '{name}' not found"}

async def handle_single_jsonrpc(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    msg_id = req.get("id")
    params = req.get("params", {})

    log_event(f"Handling method: '{method}' (id={msg_id})")

    if method == "initialize":
        client_proto = params.get("protocolVersion", "2024-11-05")
        log_event(f"Client initialize accepted (protocolVersion={client_proto})")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": client_proto,
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "agentica",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "notifications/initialized":
        log_event("Client confirmed notifications/initialized")
        return None
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        }
    elif method == "tools/list":
        log_event(f"Returning {len(TOOLS)} tools to client")
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
                    "content": [
                        {"type": "text", "text": json.dumps(res) if isinstance(res, (dict, list)) else str(res)}
                    ],
                    "isError": False
                }
            }
        except Exception as e:
            log_event(f"Error executing tool '{tool_name}': {e}")
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

async def handle_jsonrpc(req: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Handle both single JSON-RPC requests and batch request arrays."""
    if isinstance(req, list):
        results = []
        for item in req:
            res = await handle_single_jsonrpc(item)
            if res is not None:
                results.append(res)
        return results
    return await handle_single_jsonrpc(req)

# -------------------------------------------------------------------------
# Standard MCP SSE Transport Endpoints
# -------------------------------------------------------------------------

@app.get("/sse")
async def sse_endpoint(request: Request):
    """MCP SSE endpoint for remote MCP clients (Hermes, Claude, etc.)"""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue
    log_event(f"New SSE connection opened (session_id={session_id})")

    async def event_generator():
        # First event informs client of the endpoint to send POST messages to
        yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    log_event(f"SSE client disconnected (session_id={session_id})")
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
    
    if resp is not None:
        if session_id and session_id in sessions:
            await sessions[session_id].put(resp)
        return JSONResponse(content=resp)
    return Response(status_code=204)

# -------------------------------------------------------------------------
# Direct JSON-RPC Endpoint (Standard HTTP POST)
# -------------------------------------------------------------------------

@app.post("/mcp")
async def direct_mcp_endpoint(request: Request):
    """Direct HTTP POST JSON-RPC 2.0 endpoint (used by Hermes local HTTP)"""
    body = await request.json()
    resp = await handle_jsonrpc(body)
    if resp is not None:
        return JSONResponse(content=resp)
    return Response(status_code=204)

# -------------------------------------------------------------------------
# Status & Health Check Endpoint
# -------------------------------------------------------------------------

@app.get("/health")
@app.get("/status")
async def status_endpoint():
    """Health check endpoint for bootstrap verification"""
    return {
        "status": "healthy",
        "server": "agentica",
        "version": "1.0.0",
        "tool_count": len(TOOLS),
        "tools": [t["name"] for t in TOOLS]
    }

if __name__ == "__main__":
    log_event("Starting Agentica MCP HTTP Server on 0.0.0.0:8000...")
    uvicorn.run("src.server.mcp_http_server:app", host="0.0.0.0", port=8000, reload=False)
