
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class MCPServerConfig:
    command: str
    args: list[str]
    env: Optional[Dict[str, str]] = None

class MCPConfig:
    """
    Handles loading MCP configuration from files.
    Follows Claude Desktop format compatibility.
    """
    
    @staticmethod
    def load(path: Optional[str] = None) -> Dict[str, MCPServerConfig]:
        """
        Load configuration from a path.
        If path is None, tries:
        1. .retriever/mcp.json (project local)
        2. ~/.retriever/mcp.json (global)
        """
        if path:
             return MCPConfig._read_file(Path(path))
        
        # Try local
        local_path = Path(".retriever/mcp.json")
        if local_path.exists():
            return MCPConfig._read_file(local_path)
            
        # Try global
        global_path = Path.home() / ".retriever" / "mcp.json"
        if global_path.exists():
            return MCPConfig._read_file(global_path)
            
        return {}

    @staticmethod
    def _read_file(path: Path) -> Dict[str, MCPServerConfig]:
        try:
            with open(path, "r") as f:
                data = json.load(f)
                
            servers = {}
            # Claude Desktop format: {"mcpServers": { "name": { "command": ... } } }
            server_dict = data.get("mcpServers", {})
            
            for name, config in server_dict.items():
                servers[name] = MCPServerConfig(
                    command=config.get("command"),
                    args=config.get("args", []),
                    env=config.get("env")
                )
            return servers
        except Exception as e:
            print(f"Error loading MCP config from {path}: {e}")
            return {}
