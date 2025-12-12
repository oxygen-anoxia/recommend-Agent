import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.mcp_message import MCPResponse, MCPStatus
import logging
import json

load_dotenv()

class MCPLLMService:
    """MCP标准化的LLM服务"""

    def __init__(self):
        self.client = AsyncOpenAI(  # <--- 1. 初始化异步客户端
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model = os.getenv("LLM_MODEL")
        # 统一使用类名作为logger名称
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_tool_decision(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> MCPResponse: # <--- 2. 异步化方法
        """获取LLM的工具调用决策"""
        try:
            self.logger.info(f"请求LLM工具决策，工具数量: {len(tools)}")

            response = await self.client.chat.completions.create( # <--- 3. 使用 await
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            if message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })

                return MCPResponse.success(
                    "LLM决策完成",
                    data={
                        "content": message.content,
                        "tool_calls": tool_calls
                    }
                )
            else:
                return MCPResponse.success(
                    "LLM响应完成",
                    data={
                        "content": message.content,
                        "tool_calls": None
                    }
                )

        except Exception as e:
            error_msg = f"LLM工具决策失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return MCPResponse.error(error_msg)

    async def generate_response(self, messages: List[Dict[str, Any]]) -> MCPResponse: # <--- 2. 异步化方法
        """生成最终回复（非流式）"""
        try:
            self.logger.info("正在生成非流式回复...")
            response = await self.client.chat.completions.create( # <--- 3. 使用 await
                model=self.model,
                messages=messages,
                stream=False
            )
            content = response.choices[0].message.content
            self.logger.info("非流式回复生成成功。")
            return MCPResponse.success(content, data={"content": content})
        except Exception as e:
            error_msg = f"非流式生成回复失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return MCPResponse.error(error_msg)

    async def generate_response_stream(self, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]: # <--- 2. 异步化方法
        """为给定的消息生成流式回复。"""
        try:
            self.logger.info("正在生成流式回复...")
            stream = await self.client.chat.completions.create( # <--- 3. 使用 await
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream: # <--- 3. 使用 async for
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            self.logger.info("流式回复生成成功。")
        except Exception as e:
            error_msg = f"生成流式回复失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            yield f"[ERROR] {error_msg}"

    async def extract_information(self, user_input: str, extraction_prompt: str) -> MCPResponse: # <--- 2. 异步化方法
        """使用提示词从用户输入中提取信息"""
        messages = [
            {
                "role": "system",
                "content": extraction_prompt
            },
            {
                "role": "user",
                "content": user_input
            }
        ]

        try:
            self.logger.info("请求LLM提取信息")

            response = await self.client.chat.completions.create( # <--- 3. 使用 await
                model=self.model,
                messages=messages
            )

            content = response.choices[0].message.content

            return MCPResponse.success(
                "信息提取完成",
                data={"content": content}
            )

        except Exception as e:
            error_msg = f"信息提取失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return MCPResponse.error(error_msg)