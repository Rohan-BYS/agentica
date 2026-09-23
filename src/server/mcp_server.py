import sys
import json
import asyncio
from typing import Dict, Any, List, Optional

from src.core.router import AIBrowserRouter

class NexusMCPServer:
    """
    JSON-RPC 2.0 implementation of the Model Context Protocol (MCP) over stdio.
    Exposes the AIBrowserRouter capabilities to AI agents.
    """
    def __init__(self):
        self.router = AIBrowserRouter()
        
    def _read_message(self) -> Optional[Dict[Any, Any]]:
        line = sys.stdin.readline()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def _write_message(self, msg: Dict[Any, Any]):
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    async def _handle_request(self, req: Dict[Any, Any]):
        if "method" not in req:
            return
            
        method = req["method"]
        msg_id = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            self._write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {
                        "name": "nexus-mcp",
                        "version": "1.0.0"
                    }
                }
            })
        elif method == "notifications/initialized":
            pass # No response needed
        elif method == "tools/list":
            self._write_message({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self._get_tools()
                }
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                res = await self._call_tool(tool_name, tool_args)
                self._write_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res)}
                        ],
                        "isError": False
                    }
                })
            except Exception as e:
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
            from pathlib import Path
            p = Path("data/hermes_messages.json")
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
            from pathlib import Path
            p = Path("data/hermes_messages.json")
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
        while True:
            # Read from stdin asynchronously using executor
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            try:
                req = json.loads(line)
                await self._handle_request(req)
            except json.JSONDecodeError:
                pass

def main():
    server = NexusMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
