from typing import List, Dict, Any, Optional
from .mcp_message import MCPMessage, MCPMessageType, MCPResponse
from .mcp_tool import MCPToolRegistry
import logging
import json

class MCPContext:
    """管理Agent运行时的上下文信息
    功能 ：维护Agent在对话过程中的状态信息，包括用户ID、会话ID、消息历史、会话数据等
    输入参数 ：
        - user_id: str - 用户唯一标识符，默认值为"default_user"
        - session_id: str - 会话唯一标识符，默认值为"default_session"
    本地变量 ：
        - user_id: str - 用户唯一标识符
        - session_id: str - 会话唯一标识符
        - messages: List[MCPMessage] - 消息历史列表
        - session_data: Dict[str, Any] - 会话数据字典，存储该用户的用户画像等全局性信息，后期还会考虑添加
        - logger: logging.Logger - 上下文日志记录器，用于记录上下文相关的日志信息
    输出 ： None
    作用 ：提供上下文管理功能，支持多用户、多会话的Agent运行

    """

    def __init__(self, user_id: str = "default_user", session_id: str = "default_session"):
        self.user_id = user_id
        self.session_id = session_id
        self.messages: List[MCPMessage] = []
        self.session_data: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"MCPContext.{user_id}.{session_id}")

    def add_message(self, message: MCPMessage) -> None:
        """添加消息到上下文
        功能 ：将新消息添加到上下文的消息历史列表中
        输入参数 ：
            - message: MCPMessage - 要添加的消息对象
        输出 ： None
        作用 ：将新消息添加到上下文的消息历史列表中，用于维护对话历史
        """
        self.messages.append(message)
        self.logger.debug(f"添加消息: {message.type.value} - {message.id}")

    def get_messages(self, message_type: Optional[MCPMessageType] = None, limit: Optional[int] = None) -> List[MCPMessage]:
        """获取消息历史
        功能 ：根据指定条件获取上下文的消息历史列表
        输入参数 ：
            - message_type: Optional[MCPMessageType] - 消息类型筛选条件，默认值为None，即全选
            - limit: Optional[int] - 消息数量限制，默认值为None，即全选
        输出 ： List[MCPMessage] - 符合条件的消息列表
        作用 ：根据指定条件获取上下文的消息历史列表，用于对话历史的查询和分析
        """
        messages = self.messages

        if message_type:
            messages = [msg for msg in messages if msg.type == message_type]

        if limit:
            messages = messages[-limit:]

        return messages

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史，格式化为LLM可用的格式
        功能 ：将上下文的消息历史列表格式化为LLM可用的格式，包含用户输入和Agent回复
        输入参数 ： None
        输出 ： List[Dict[str, Any]] - 格式化后的对话历史列表
        作用 ：将上下文的消息历史列表格式化为LLM可用的格式，用于对话历史的查询和分析
        """
        history = []

        for message in self.messages:
            if message.type == MCPMessageType.USER:
                history.append({
                    "role": "user",
                    "content": message.content
                })
            elif message.type == MCPMessageType.ASSISTANT:
                history.append({
                    "role": "assistant",
                    "content": message.content
                })
            elif message.type == MCPMessageType.SYSTEM:
                history.append({
                    "role": "system",
                    "content": message.content
                })

        return history

    def set_session_data(self, key: str, value: Any) -> None:
        """设置会话数据
        功能 ：将键值对存储到会话数据字典中
        输入参数 ：
            - key: str - 会话数据键
            - value: Any - 会话数据值
        输出 ： None
        作用 ：将键值对存储到会话数据字典中，用于在会话过程中存储和共享数据
        """
        self.session_data[key] = value
        self.logger.debug(f"设置会话数据: {key}")

    def get_session_data(self, key: str, default: Any = None) -> Any:
        """获取会话数据"""
        return self.session_data.get(key, default)

    def clear_session_data(self) -> None:
        """清空会话数据"""
        self.session_data.clear()
        self.logger.info("会话数据已清空")

    def register_tool(self, tool) -> None:
        """注册工具到上下文，暂不使用"""
        self.tool_registry.register_tool(tool)

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """在当前上下文中执行工具，暂不使用"""

        return self.tool_registry.execute_tool(tool_name, parameters, context=self)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具定义，暂不使用"""

        return self.tool_registry.get_tool_definitions()

    def export_context(self) -> Dict[str, Any]:
        """导出上下文数据"""
        return {
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "session_data": self.session_data,
            #"tools": self.tool_registry.list_tools()
        }

    def import_context(self, context_data: Dict[str, Any]) -> None:
        """导入上下文数据"""
        self.user_id = context_data.get("user_id", self.user_id)

        # 导入消息历史
        self.messages = []
        for msg_data in context_data.get("messages", []):
            self.messages.append(MCPMessage.from_dict(msg_data))

        # 导入会话数据
        self.session_data = context_data.get("session_data", {})

        self.logger.info(f"上下文数据导入完成，消息数: {len(self.messages)}")

    def __str__(self) -> str:
        return f"MCPContext(user_id={self.user_id}, messages={len(self.messages)}, tools={len(self.tool_registry.list_tools())})"