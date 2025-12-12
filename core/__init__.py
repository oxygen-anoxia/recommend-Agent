"""MCP 核心组件模块。

包含 MCP 架构的核心组件：
- MCPAgent: Agent 基类
- MCPContext: 上下文管理
- MCPMessage: 消息格式
- MCPTool: 工具基类和注册表
"""

from .mcp_agent import MCPAgent
from .mcp_context import MCPContext
from .mcp_message import MCPMessage, MCPResponse, MCPToolCall
from .mcp_tool import MCPTool, MCPToolRegistry

__all__ = [
    "MCPAgent",
    "MCPContext",
    "MCPMessage",
    "MCPResponse",
    "MCPToolCall",
    "MCPTool",
    "MCPToolRegistry",
]