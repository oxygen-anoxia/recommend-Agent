import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

class MCPConfig:
    """MCP配置管理器"""

    def __init__(self, env_file: Optional[str] = None):
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        self._config = self._load_config()
        self._setup_logging()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            # LLM配置
            "llm": {
                "base_url": os.getenv("LLM_BASE_URL"),
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": os.getenv("LLM_MODEL")
            },

            # API配置
            "api": {
                "base_url": os.getenv("API_BASE_URL"),
                "timeout": int(os.getenv("API_TIMEOUT", "30"))
            },

            # Agent配置
            "agent": {
                "name": os.getenv("AGENT_NAME", "RecommendAgent_MCP"),
                "max_history": int(os.getenv("MAX_HISTORY", "50")),
                "enable_tool_logging": os.getenv("ENABLE_TOOL_LOGGING", "true").lower() == "true"
            },

            # 日志配置
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                "file": os.getenv("LOG_FILE", None)
            },

            # 运行模式
            "mode": {
                "test_mode": os.getenv("TEST_MODE", "false").lower() == "true",
                "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true"
            },

            # 命令配置
            "commands": {
                "quit_command": os.getenv("QUIT_COMMAND", "quit")
            }
        }

    def _setup_logging(self) -> None:
        """设置日志"""
        log_config = self._config["logging"]

        # 设置日志级别
        level = getattr(logging, log_config["level"].upper(), logging.INFO)

        # 配置日志格式
        formatter = logging.Formatter(log_config["format"])

        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # 不清除任何现有处理器，只添加我们的处理器
        # 检查是否已经有控制台处理器
        has_console_handler = any(
            isinstance(h, logging.StreamHandler) and h.stream.name in ['<stdout>', '<stderr>']
            for h in root_logger.handlers
        )

        if not has_console_handler:
            # 添加控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # 添加文件处理器（如果配置了）
        if log_config["file"]:
            file_handler = logging.FileHandler(log_config["file"], encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # 确保 uvicorn 和 fastapi 的日志也能正常输出
        logging.getLogger("uvicorn").setLevel(level)
        logging.getLogger("uvicorn.access").setLevel(level)
        logging.getLogger("fastapi").setLevel(level)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self._config["llm"]

    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self._config["api"]

    def get_agent_config(self) -> Dict[str, Any]:
        """获取Agent配置"""
        return self._config["agent"]

    def is_test_mode(self) -> bool:
        """是否为测试模式"""
        return self._config["mode"]["test_mode"]

    def is_debug_mode(self) -> bool:
        """是否为调试模式"""
        return self._config["mode"]["debug_mode"]

    def get_quit_command(self) -> str:
        """获取退出命令"""
        return self._config["commands"]["quit_command"]

    def validate_config(self) -> bool:
        """验证配置完整性"""
        required_keys = [
            "llm.api_key",
            "llm.model",
            "api.base_url"
        ]

        for key in required_keys:
            if not self.get(key):
                logging.error(f"缺少必需的配置项: {key}")
                return False

        return True

    def __str__(self) -> str:
        return f"MCPConfig(agent={self.get('agent.name')}, model={self.get('llm.model')})"

# 全局配置实例
config = MCPConfig()


def get_server_config():
    """获取服务器配置"""
    return {
        "host": os.getenv("SERVER_HOST", "127.0.0.1"),
        "port": int(os.getenv("SERVER_PORT", "25831")),
    }