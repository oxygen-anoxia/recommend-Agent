from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .mcp_message import MCPResponse
# 确保 MCPContext 的导入，即使只是用于类型提示
try:
    from .mcp_context import MCPContext
except ImportError:
    MCPContext = Any

class MCPTool(ABC):
    """工具的抽象基类"""
    def __init__(self, name: str, description: str, required_params: List[str], parameters_schema: Dict[str, Any]):
        self._name = name
        self._description = description
        self.required_params = required_params
        self.parameters_schema = parameters_schema

    @property
    def name(self) -> str:
        return self._name

    def get_schema(self) -> Dict[str, Any]:
        """返回工具的完整 schema 信息，符合 OpenAI API 格式"""
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": self._description,
                "parameters": self.parameters_schema
            }
        }

    @abstractmethod
    def run(self, context: MCPContext, parameters: Dict[str, Any]) -> MCPResponse:
        """执行工具的核心逻辑"""
        pass

class MCPToolRegistry:
    """工具注册表，管理和执行工具"""
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}

    def register_tool(self, tool: MCPTool):
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已被注册。")
        self._tools[tool.name] = tool

    def execute_tool(self, name: str, context: 'MCPContext', parameters: Dict[str, Any]) -> MCPResponse:
        if name not in self._tools:
            return MCPResponse.error(f"工具 '{name}' 未找到。")

        tool = self._tools[name]

        # 验证参数
        missing_params = [p for p in tool.required_params if p not in parameters]
        if missing_params:
            return MCPResponse.error(f"执行工具 '{name}' 缺少必要参数: {', '.join(missing_params)}")

        try:
            # 将上下文和参数传递给工具的run方法
            return tool.run(context, parameters)
        except Exception as e:
            return MCPResponse.error(f"执行工具 '{name}' 时发生错误: {str(e)}")

    def list_tools(self) -> list[Dict[str, Any]]:
        """列出所有工具名称"""
        return list(self._tools.keys())