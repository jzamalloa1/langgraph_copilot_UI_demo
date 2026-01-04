"""
Restricted filesystem middleware - only exposes ls tool for listing files.
"""

from typing import Callable
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain.tools.tool_node import ToolCallRequest
from deepagents.middleware.filesystem import FilesystemMiddleware


ALLOWED_TOOLS = {"ls"}


class RestrictedFilesystemMiddleware(AgentMiddleware):
    """Middleware that wraps FilesystemMiddleware but only exposes ls tool."""

    def __init__(self, **kwargs):
        """Initialize with same arguments as FilesystemMiddleware."""
        restricted_system_prompt = """## Filesystem Tools

You have access to:
- ls: List files in a directory (e.g., ls("/tmp/plots"))

All file paths must start with a /."""

        kwargs['system_prompt'] = restricted_system_prompt
        self._inner = FilesystemMiddleware(**kwargs)

        # Filter tools to only ls
        self.tools = [
            tool for tool in self._inner.tools
            if tool.name in ALLOWED_TOOLS
        ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Delegate to inner middleware after filtering tools."""
        filtered_tools = [
            tool for tool in request.tools
            if (tool.name if hasattr(tool, "name") else tool.get("name")) in ALLOWED_TOOLS
            or (tool.name if hasattr(tool, "name") else tool.get("name")) not in
               {"execute", "read_file", "write_file", "edit_file", "glob", "grep"}
        ]

        filtered_request = request.override(tools=filtered_tools)
        return self._inner.wrap_model_call(filtered_request, handler)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Async version - delegate to inner middleware."""
        filtered_tools = [
            tool for tool in request.tools
            if (tool.name if hasattr(tool, "name") else tool.get("name")) in ALLOWED_TOOLS
            or (tool.name if hasattr(tool, "name") else tool.get("name")) not in
               {"execute", "read_file", "write_file", "edit_file", "glob", "grep"}
        ]

        filtered_request = request.override(tools=filtered_tools)
        return await self._inner.awrap_model_call(filtered_request, handler)

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ):
        """Delegate tool calls to inner middleware."""
        return self._inner.wrap_tool_call(request, handler)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ):
        """Async tool call delegation."""
        return await self._inner.awrap_tool_call(request, handler)
