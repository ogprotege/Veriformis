"""Event-loop-independent MCP test harnesses."""
from __future__ import annotations

import asyncio
import inspect
from mcp.types import CallToolResult, TextContent


def call_registered(fn, *args, **kwargs):
    result = fn(*args, **kwargs)
    if inspect.isawaitable(result):
        async def resolve():
            return await result
        return asyncio.run(resolve())
    return result


def tool_map(server):
    return {tool.name: tool.fn for tool in server._tool_manager.list_tools()}


async def call_tool_async(server, name: str, arguments: dict[str, str]) -> str:
    result = await server.call_tool(name, arguments)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def call_tool(server, name: str, arguments: dict[str, str]) -> str:
    return asyncio.run(call_tool_async(server, name, arguments))
