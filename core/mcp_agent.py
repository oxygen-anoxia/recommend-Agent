from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .mcp_message import MCPMessage, MCPMessageType, MCPResponse, MCPStatus
from .mcp_context import MCPContext
from .mcp_tool import MCPTool, MCPToolRegistry  # 确保MCPToolRegistry被导入
import logging
from core.mcp_context import MCPContext
from services.llm_service import MCPLLMService

class MCPAgent(ABC):
    """MCP Agent标准接口，所有Agent都应继承此类，并且此类应当只有一个实例即RecommendationAgentMCP"""

    def __init__(self, agent_name: str, context: MCPContext = None):
        """
        初始化MCP Agent
        :param agent_name: Agent的名称
        :param context: MCPContext实例，如果为None则创建新的
        """
        self.agent_name = agent_name
        self.context = context if context is not None else MCPContext()
        self.logger = logging.getLogger(f"MCPAgent.{self.agent_name}")
        self.tools: Dict[str, Any] = {}
        self._initialize_agent()

    @abstractmethod
    def _initialize_agent(self) -> None:
        """抽象方法，由子类实现初始化Agent，注册工具等"""

        pass

    @abstractmethod
    def process_user_input(self, user_input: str) -> MCPResponse:
        """抽象方法，由子类实现处理用户输入，返回标准化响应，该方法信息详见recommendation_agent_mcp.py的内容"""
        pass

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """执行工具，这里涉及LLM选择并调用工具使用的部分，在当前版本内暂不使用"""
        # 工具执行时需要访问当前上下文
        return self.tool_registry.execute_tool(tool_name, self.context, parameters)

    def add_message(self, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """添加消息到上下文
        - message_type: str - 消息类型（如 "USER_INPUT", "AGENT_RESPONSE"，详见mcp_message.py）
        - content: str - 消息内容
        - metadata: Optional[Dict[str, Any]] - 可选的元数据信息
        - 输出 ： None
        - 作用 ：将字符串消息包装成项目内部的标准MCPMessage形式，并添加到该对话的上下文的消息历史中
        """

        # 使用位置参数，确保与 __init__ 定义一致
        message = MCPMessage(MCPMessageType(message_type), content, metadata)
        self.context.add_message(message)

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """获取一个已注册的工具，暂留接口，暂时不实现"""
        return message

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史
        功能 ：获取当前会话的完整对话历史记录
        输入参数 ：无
        输出 ： List[Dict[str, Any]] - 对话历史列表，每个元素包含消息的详细信息
        作用 ：委托给上下文对象获取格式化的对话历史记录
        """
        return self.context.get_conversation_history()

    def run_once(self, user_input: str) -> str:
        """处理一轮对话，兼容旧版命令行实现的接口，在api版本中废弃"""

        # 添加用户输入到上下文
        self.add_message(MCPMessageType.USER, user_input)

        # 处理用户输入
        response = self.process_user_input(user_input)

        # 添加Agent响应到上下文
        self.add_message(MCPMessageType.ASSISTANT, response.message, {

            "status": response.status.value,
            "data": response.data
        })

        return response.message

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息
        功能 ：获取当前Agent的基本信息和状态
        输入参数 ：无
        输出 ： Dict[str, Any] - 包含Agent名称、注册工具列表、消息数量和会话数据键的字典
        作用 ：提供Agent的基本配置和运行状态，方便调试和监控
        """
        return {
            "name": self.agent_name,
            "tools": self.tool_registry.list_tools(), # 从Agent的注册表获取工具
            "message_count": len(self.context.messages),
            "session_data_keys": list(self.context.session_data.keys())
        }

    def reset_context(self) -> None:
        """重置上下文
        功能 ：重置当前Agent和当前用户的会话上下文，清空对话历史和会话数据
        输入参数 ：无
        输出 ： None
        作用 ：在需要重新开始会话或清除旧会话数据时使用
        """
        self.context = MCPContext(self.context.user_id)
        self._initialize_agent()
        self.logger.info(f"Agent {self.agent_name} 上下文已重置")

    def __str__(self) -> str:
        '''功能 ：返回Agent的字符串表示 输入参数 ：无 输出 ： str - Agent的字符串描述 用途 ：用于打印和调试'''

        return f"MCPAgent({self.agent_name})"

    def __repr__(self) -> str:
        '''功能 ：返回Agent的详细字符串表示 输入参数 ：无 输出 ： str - 包含名称和工具数量的详细描述 用途 ：用于开发调试和对象检查'''
        return f"MCPAgent(name='{self.agent_name}', tools={len(self.context.tool_registry.list_tools())})"

    def set_context(self, context: MCPContext):
        """设置或更新Agent的当前会话上下文
        功能 ：动态切换Agent的会话上下文，支持多会话管理 输入参数 ：

        - context: MCPContext - 新的上下文对象
        输出 ： None
        作用 ：实现单Agent实例处理多个会话的核心机制
        """
        self.context = context

    def register_tool(self, tool_name: str, tool: Any):
        """注册一个工具到Agent，在当前版本，暂时只注册，不使用。
        功能 ：将外部工具注册到Agent，使Agent能够在对话中调用该工具 输入参数 ：
        - tool_name: str - 工具的唯一名称
        - tool: Any - 工具的实现对象，通常是一个函数或类实例
        输出 ： None
        作用 ：扩展Agent的功能，使其能够执行特定任务
        """
        if tool_name in self.tools:
            self.logger.warning(f"工具 {tool_name} 已存在，将被覆盖。")
        self.tools[tool_name] = tool
        self.logger.info(f"工具 {tool_name} 已注册到Agent {self.agent_name}")