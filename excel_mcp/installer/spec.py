from __future__ import annotations

import shutil
from dataclasses import dataclass

# The MCP server name this installer manages across every agent config.
SERVER_NAME = "excel-ops-mcp"


def resolve_uvx_path() -> str:
    found = shutil.which("uvx")
    return found if found else "uvx"


@dataclass(frozen=True)
class ServerSpec:
    name: str
    args: tuple[str, ...]
    uvx_path: str

    def command_for(self, gui: bool) -> str:
        return self.uvx_path if gui else "uvx"

    def entry(self, gui: bool) -> dict:
        return {"command": self.command_for(gui), "args": list(self.args)}


def default_spec() -> ServerSpec:
    return ServerSpec(SERVER_NAME, (SERVER_NAME,), resolve_uvx_path())
