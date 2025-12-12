"""MCP 版本的推荐 Agent 包。

这个包实现了基于 Model Context Protocol (MCP) 标准的推荐系统，
提供了标准化的工具接口、消息格式和 Agent 架构。
"""

__version__ = "1.0.0"
__author__ = "MCP Team"

# 导出主要组件
from .recommendation_agent_mcp import RecommendationAgentMCP
from .config.mcp_config import MCPConfig
from .core.mcp_agent import MCPAgent
from .core.mcp_context import MCPContext
from .core.mcp_message import MCPMessage, MCPResponse, MCPToolCall
from .core.mcp_tool import MCPTool, MCPToolRegistry
from .models.user_profile import UserProfile
from .services.llm_service import MCPLLMService

__all__ = [
    "RecommendationAgentMCP",
    "MCPConfig",
    "MCPAgent",
    "MCPContext",
    "MCPMessage",
    "MCPResponse",
    "MCPToolCall",
    "MCPTool",
    "MCPToolRegistry",
    "UserProfile",
    "MCPLLMService",
]