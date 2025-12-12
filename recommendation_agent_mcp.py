from typing import Dict, Any, List, Union, Generator
from core.mcp_agent import MCPAgent
from core.mcp_message import MCPResponse, MCPStatus, MCPMessageType
from core.mcp_context import MCPContext
from models.user_profile import UserProfile, ProfileCompleteness
from services.llm_service import MCPLLMService
from tools.profile_updater_mcp import ProfileUpdaterMCP
from tools.certain_matching_mcp import CertainMatchingMCP
from tools.guessed_matching_mcp import GuessedMatchingMCP
from config.mcp_config import MCPConfig
import logging
import json

class RecommendationAgentMCP(MCPAgent):
    """
    功能 : 留学推荐智能体的主类，负责维护留学智能体的状态和行为
    继承 : MCPAgent抽象基类
    输入 : 可选的MCPContext上下文对象
    初始化内容 :

        - 调用父类构造函数，设置Agent名称为"RecommendationAgent"
        - 创建LLM服务实例用于AI对话
        - 初始化智能体工具：（这里虽然注册，但并未使用智能体工具的形式，而是固定流程，将在下面展示）
            - 注册ProfileUpdaterMCP工具用于更新用户画像
            - 注册CertainMatchingMCP工具用于Certain匹配
            - 注册GuessedMatchingMCP工具用于Guessed匹配

    """
    def __init__(self, context: MCPContext = None):
        super().__init__("RecommendationAgent", context)
        self.llm_service = MCPLLMService()

    def _initialize_agent(self):
        """初始化智能体工具"""
        # 注册三个工具
        self.profile_updater = ProfileUpdaterMCP()
        self.certain_matching = CertainMatchingMCP()
        self.guessed_matching = GuessedMatchingMCP()

        self.logger.info(f"RecommendationAgent 初始化完成，共注册 3 个工具")

    '''留学推荐主流程'''

    async def run(self, user_input: str) -> dict:
        """
        功能 : 执行完整的留学推荐流程
        输入 : 用户输入字符串
        输出 : 包含响应内容的字典
        执行流程 :
        1. 记录用户输入 : 将用户输入添加到会话上下文
        2. 更新用户画像 : 调用ProfileUpdaterMCP分析用户需求
        3. 执行匹配 : 根据画像完整度选择匹配策略
        4. 生成回复 : 基于画像和匹配结果生成最终建议
        5. 记录回复 : 将AI回复添加到会话上下文
        错误处理 : 每个步骤都有独立的错误检查和处理
        """
        try:
            # 添加用户输入到上下文
            self.add_message("user", user_input)

            # 步骤1：更新用户画像
            profile_result = await self._update_user_profile(user_input)
            if profile_result.status == MCPStatus.ERROR:
                return {"type": "response", "content": f"画像更新失败: {profile_result.message}"}

            # 步骤2：根据画像完整度选择匹配方式
            matching_result = await self._perform_matching()
            if matching_result.status == MCPStatus.ERROR:
                return {"type": "response", "content": f"匹配失败: {matching_result.message}"}

            # 步骤3：生成最终回复
            final_response = await self._generate_final_response(profile_result, matching_result, user_input)
            if final_response.status == MCPStatus.ERROR:
                return {"type": "response", "content": f"回复生成失败: {final_response.message}"}

            # 添加最终回复到上下文
            self.add_message("assistant", final_response.data["content"])

            return {"type": "response", "content": final_response.data["content"]}

        except Exception as e:
            error_msg = f"处理用户输入时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"type": "response", "content": error_msg}

    async def run_stream(self, user_input: str):
        """同上，只不过是流式输出的部分，当时没想好怎么合并，现在就先分开"""
        try:
            # 添加用户输入到上下文
            self.add_message("user", user_input)

            # 步骤1：更新用户画像
            yield "正在分析并更新用户画像...\n"
            profile_result = await self._update_user_profile(user_input)
            if profile_result.status == MCPStatus.ERROR:
                yield f"画像更新失败: {profile_result.message}\n"
                return

            # 步骤2：根据画像完整度选择匹配方式
            yield "正在进行院校匹配...\n"
            matching_result = await self._perform_matching()
            if matching_result.status == MCPStatus.ERROR:
                yield f"匹配失败: {matching_result.message}\n"
                return

            # 步骤3：生成最终回复（流式）
            yield "正在生成推荐回复...\n"
            async for chunk in self._generate_final_response_stream(profile_result, matching_result, user_input):
                yield chunk

        except Exception as e:
            error_msg = f"处理用户输入时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            yield error_msg

    async def _update_user_profile(self, user_input: str) -> MCPResponse:
        """步骤1：更新用户画像
        - 输入 ： user_input: str - 用户的原始输入文本
        - 输出 ： MCPResponse - 包含更新结果的响应对象
        - 逻辑流程 ：
            1. 调用 ProfileUpdaterMCP 工具的 run 方法
            2. 传递用户输入和上下文信息
            3. 处理工具返回的结果
        - 特点 ：异步方法，使用 await 调用工具
        """
        try:
            return await self.profile_updater.run(self.context, {"user_input": user_input})
        except Exception as e:
            return MCPResponse.error(f"用户画像更新失败: {str(e)}")

    async def _perform_matching(self) -> MCPResponse:
        """步骤2：根据画像完整度选择匹配方式
        功能 ：根据用户画像必填字段完整度选择匹配策略
        输入 ：无直接参数，从上下文获取用户画像
        输出 ： MCPResponse - 包含匹配结果的响应对象
        逻辑流程 ：
            1. 获取用户画像并检查必填字段完整性
            2. 根据必填字段状态选择匹配工具：
                - COMPLETE → 调用 CertainMatchingMCP 工具
                - MINIMAL → 调用 GuessedMatchingMCP 工具（缺失重要字段但必填字段完整）
                - INCOMPLETE → 返回提示补充必填信息
            3. 记录日志并执行相应的匹配工具
        """
        try:
            # 从上下文获取用户画像
            user_profile = self.context.get_session_data('user_profile')
            if not user_profile:
                return MCPResponse.error("用户画像不存在，请先提供个人信息")

            # 检查画像完整性（基于必填字段）
            completeness, missing_fields = user_profile.check_profile_completeness()

            # 获取完整度摘要用于日志记录
            profile_summary = user_profile.get_completion_summary()
            completion_rate = profile_summary.get("completion_rate", 0)

            # 添加调试输出
            print(f"[DEBUG] 画像完整性状态: {completeness.value}")
            print(f"[DEBUG] 缺失字段: {missing_fields}")
            print(f"[DEBUG] 总体完整度: {completion_rate:.1f}%")
            print(f"[DEBUG] 画像摘要: {profile_summary}")

            # 根据必填字段完整性选择匹配工具
            if completeness == ProfileCompleteness.COMPLETE:
                print(f"[DEBUG] 必填和重要字段都完整，使用确定匹配")
                self.logger.info(f"画像完整性: {completeness.value}，使用确定匹配")
                return self.certain_matching.run(self.context, {})
            elif completeness == ProfileCompleteness.MINIMAL:
                print(f"[DEBUG] 使用猜测匹配")
                self.logger.info(f"画像完整度 {completion_rate:.1%}，使用猜测匹配")
                return self.guessed_matching.run(self.context, {})
            else:  # INCOMPLETE - 缺失必填字段
                print(f"[DEBUG] 缺失必填字段，无法进行匹配")
                self.logger.info(f"画像完整性: {completeness.value}，缺失必填字段: {missing_fields}")
                return MCPResponse.success(
                    f"您还缺少一些必填信息：{', '.join(missing_fields)}。请先补充这些信息，我才能为您推荐合适的学校。",
                    data={"missing_essential_fields": missing_fields, "completeness": completeness.value}
                )

        except Exception as e:
            print(f"[DEBUG] 匹配过程异常: {str(e)}")
            return MCPResponse.error(f"匹配过程失败: {str(e)}")

    async def _generate_final_response(self, profile_result: MCPResponse, matching_result: MCPResponse, user_input: str) -> MCPResponse:
        """步骤3：生成最终回复
        功能 ：根据用户画像和匹配结果生成最终建议
        输入 ：
            - profile_result: MCPResponse - 用户画像更新结果
            - matching_result: MCPResponse - 院校匹配结果
            - user_input: str - 用户原始输入
        输出 ： MCPResponse - 包含最终建议的响应对象
        逻辑流程 ：
            1. 构建上下文消息，包含用户画像、匹配结果和用户输入
            2. 调用LLM生成回复
            3. 处理LLM返回结果：
                - 成功：返回LLM生成的回复
                - 失败：使用备用回复
        特点 ：异步方法，使用 await 调用LLM服务
        """
        try:
            # 构建上下文消息
            messages = self._build_response_context(profile_result, matching_result, user_input)

            # 调用LLM生成回复
            response = await self.llm_service.generate_response(messages)

            if response.status == MCPStatus.SUCCESS:
                return MCPResponse.success(
                    "最终回复生成成功",
                    data={"content": response.data["content"]}
                )
            else:
                # 如果LLM调用失败，返回备用回复
                fallback_content = self._generate_fallback_response(profile_result, matching_result)
                return MCPResponse.success(
                    "使用备用回复",
                    data={"content": fallback_content}
                )

        except Exception as e:
            return MCPResponse.error(f"最终回复生成失败: {str(e)}")

    async def _generate_final_response_stream(self, profile_result: MCPResponse, matching_result: MCPResponse, user_input: str):
        """步骤3：流式生成最终回复
            同上，只不过是流式版本
        """
        try:
            # 构建上下文消息
            messages = self._build_response_context(profile_result, matching_result, user_input)

            # 流式调用LLM
            async for chunk in self.llm_service.generate_response_stream(messages):
                yield chunk

        except Exception as e:
            yield f"流式回复生成失败: {str(e)}"

    def _build_response_context(self, profile_result: MCPResponse, matching_result: MCPResponse, user_input: str) -> List[Dict[str, Any]]:
        """构建最终回复的上下文
        功能 ：构建 LLM 调用所需的上下文消息
        - 输入 ：画像结果、匹配结果、用户输入
        - 输出 ： List[Dict[str, Any]] - 格式化的消息列表
        - 消息结构 ：
            - 系统消息 ：定义 AI 角色为专业留学顾问
            - 用户消息 ：包含用户问题、画像更新结果、院校匹配结果
        - 数据格式 ：使用 JSON 格式化，确保中文显示正确
        """
        return [
            {
                "role": "system",
                "content": "你是一个专业的留学顾问，请根据用户画像和匹配结果，为用户提供个性化的留学建议。"
            },
            {
                "role": "user",
                "content": f"用户问题: {user_input}\n\n用户画像更新结果: {json.dumps(profile_result.data, ensure_ascii=False, indent=2)}\n\n院校匹配结果: {json.dumps(matching_result.data, ensure_ascii=False, indent=2)}"
            }
        ]

    def _generate_fallback_response(self, profile_result: MCPResponse, matching_result: MCPResponse) -> str:
        """生成备用回复
            之前是打算返回用户画像和匹配结果的，但是现在因为数据库信息敏感，现在只返回这个。
        """
        return f"""系统繁忙，请稍后再试"""

    def get_user_profile_summary(self) -> Dict[str, Any]:
        """获取用户画像摘要
        功能 ：获取用户画像的完整性摘要
        输入 ：无参数，从上下文获取画像
        输出 ： Dict[str, Any] - 包含完整度信息的字典
        逻辑流程 ：
        1. 从上下文获取用户画像（ get_session_data('user_profile') ）
        2. 检查画像是否存在：
            - 存在：调用画像对象的 get_completion_summary() 方法获取摘要
            - 不存在：返回默认的空状态
        3. 返回摘要信息
        异常处理：返回默认的空状态
        - 返回格式 ：包含 status 、 completion_rate 等字段
        """
        try:
            # 从上下文中获取最新的用户画像
            user_profile = self.context.get_session_data('user_profile')
            if user_profile:
                return user_profile.get_completion_summary()
            return {"status": "empty", "completion_rate": 0}
        except Exception:
            return {"status": "empty", "completion_rate": 0}

    def process_user_input(self, user_input: str) -> MCPResponse:
        """处理用户输入（同步版本，兼容基类），原版功能，现因为流式回复的设计，导致接口难以统一，已废弃，但在main_mcp.py中的命令行方法中仍有调用，不建议删掉"""

        # 这里可以调用异步版本或提供简化实现
        return MCPResponse.success("请使用 run() 或 run_stream() 方法")