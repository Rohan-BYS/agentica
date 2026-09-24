import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path regardless of where the command was invoked
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Ensure UTF-8 I/O for stdio transport
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.core.router import AIBrowserRouter

class NexusMCPServer:
    """
    JSON-RPC 2.0 implementation of the Model Context Protocol (MCP) over stdio.
    Exposes Agentica's AIBrowserRouter capabilities to AI agents (like Hermes).
    """
    def __init__(self):
        self._log("Initializing Agentica MCP Stdio Server...")
        self.router = AIBrowserRouter()
        self._log("Router ready.")

    def _log(self, text: str):
        """MCP specification: All server logging must go to stderr."""
        sys.stderr.write(f"[Agentica MCP] {text}\n")
        sys.stderr.flush()

    def _write_message(self, msg: Dict[Any, Any]):
        """MCP specification: Stdout is strictly reserved for single-line JSON-RPC messages."""
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    async def _handle_request(self, req: Dict[Any, Any]):
        if "method" not in req:
            return
            
        method = req["method"]
        msg_id = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            client_proto = params.get("protocolVersion", "2024-11-05")
            self._log(f"Received 'initialize' (protocolVersion: {client_proto})")
            self._write_message({
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
            })
        elif method == "notifications/initialized":
            self._log("Client confirmed initialization (notifications/initialized)")
        elif method == "ping":
            self._write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            })
        elif method == "tools/list":
            tools = self._get_tools()
            self._log(f"Serving tools/list ({len(tools)} tools registered)")
            self._write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": tools
                }
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            self._log(f"Executing tools/call: {tool_name}")
            try:
                res = await self._call_tool(tool_name, tool_args)
                self._write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res) if isinstance(res, (dict, list)) else str(res)}
                        ],
                        "isError": False
                    }
                })
            except Exception as e:
                self._log(f"Error in tools/call {tool_name}: {e}")
                self._write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": str(e)}
                        ],
                        "isError": True
                    }
                })

    def _get_tools(self) -> List[Dict]:
        return [
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
                "description": "Fetch multiple URLs concurrently",
                "inputSchema": {
                    "type": "object",
                    "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
                    "required": ["urls"]
                }
            },
            {
                "name": "snapshot",
                "description": "Get current page AXTree with @eN refs",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "click",
                "description": "Click element by @eN ref",
                "inputSchema": {
                    "type": "object",
                    "properties": {"ref": {"type": "string"}},
                    "required": ["ref"]
                }
            },
            {
                "name": "fill",
                "description": "Fill element by @eN ref",
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
                "description": "Capture page screenshot",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"]
                }
            },
            {
                "name": "get_memory_status",
                "description": "Check RAM usage",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_human_active_tab",
                "description": "Inspect and extract content from the user's currently open tab in the Agentica Human Browser (port 9222) so the AI can summarize it or answer questions about it.",
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

    async def _call_tool(self, name: str, args: Dict) -> Any:
        if name == "browse":
            mode = args.get("mode", "auto")
            return await self.router.browse(args["url"], mode=mode)
        elif name == "browse_batch":
            return await self.router.browse_batch(args["urls"])
        elif name == "snapshot":
            return await self.router.snapshot()
        elif name == "click":
            return await self.router.click(args["ref"])
        elif name == "fill":
            return await self.router.fill(args["ref"], args["text"])
        elif name == "screenshot":
            return await self.router.screenshot(args["url"])
        elif name == "get_memory_status":
            return await self.router.get_memory_status()
        elif name == "get_human_active_tab":
            return await self.router.get_human_active_tab()
        elif name == "talk_to_developer":
            msg = args.get("message", "")
            import time
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
        
        return {"error": f"Tool {name} not implemented"}

    async def run(self):
        loop = asyncio.get_running_loop()
        self._log("Stdio listener loop active. Waiting for JSON-RPC messages from client...")
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                self._log("Stdin closed (EOF). Shutting down.")
                break
            stripped = line.strip()
            if not stripped:
                continue
            try:
                req = json.loads(stripped)
                await self._handle_request(req)
            except json.JSONDecodeError as err:
                self._log(f"Invalid JSON received on stdin: {err}")

def main():
    server = NexusMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
