from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
import uuid
from datetime import datetime

class MCPMessageType(Enum):
    '''
        定义内部消息类型枚举值，用于标识消息的来源和类型
        USER：用户输入
        ASSISTANT：LLM以及匹配算法回复
        SYSTEM：系统消息
        TOOL：工具调用
    '''
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class MCPStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    """MCP状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    NO_CHANGE = "no_change"
    INCOMPLETE = "incomplete"

@dataclass
class MCPMessage:
    """标准化的MCP消息格式"""
    id: str
    type: MCPMessageType
    content: Any
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, message_type: MCPMessageType, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.type = message_type
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI API 兼容的格式"""
        return {
            "role": self.type.value,
            "content": self.content
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建MCPMessage"""
        message = cls.__new__(cls)
        message.id = data["id"]
        message.type = MCPMessageType(data["type"])
        message.content = data["content"]
        message.timestamp = data["timestamp"]
        message.metadata = data.get("metadata", {})
        return message

@dataclass
class MCPResponse:
    """标准化的MCP响应格式"""
    status: MCPStatus
    message: str
    data: Optional[Any] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata or {}
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def success(cls, message: str, data: Any = None, **kwargs) -> 'MCPResponse':
        """创建成功响应"""
        return cls(MCPStatus.SUCCESS, message, data, **kwargs)

    @classmethod
    def error(cls, message: str, data: Any = None, **kwargs) -> 'MCPResponse':
        """创建错误响应"""
        return cls(MCPStatus.ERROR, message, data, **kwargs)

    @classmethod
    def no_change(cls, message: str, data: Any = None, **kwargs) -> 'MCPResponse':
        """创建无变化响应"""
        return cls(MCPStatus.NO_CHANGE, message, data, **kwargs)

@dataclass
class MCPToolCall:
    """MCP工具调用格式"""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str

    def __init__(self, tool_name: str, parameters: Dict[str, Any]):
        self.tool_name = tool_name
        self.parameters = parameters
        self.call_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "call_id": self.call_id
        }