from core.mcp_tool import MCPTool
from core.mcp_message import MCPResponse, MCPStatus
from models.user_profile import UserProfile
from services.llm_service import MCPLLMService
from core.mcp_context import MCPContext
from typing import Dict, Any
import json
import logging

class ProfileUpdaterMCP(MCPTool):
    """使用LLM更新用户画像的工具"""
    def __init__(self):
        super().__init__(
            name="update_user_profile",
            description="根据用户输入，使用LLM提取或更新用户画像中的字段（如GPA, 目标国家, 专业等）。",
            required_params=["user_input"],
            parameters_schema={
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "用户的原始输入文本。"
                    }
                },
                "required": ["user_input"]
            }
        )
        self.llm_service = MCPLLMService()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extraction_prompt = """请从下面的用户输入中提取所有与UserProfile相关的信息，以JSON格式返回（只包含有提及的字段）：

             可能的字段包括：
             - 基本信息：GPA、SCHOOL、GRE、TOFLE、ITELS、major、degree（最高学位，如本科、硕士、博士等）
             - 科研经历：research（数组）、if_research（是否已了解科研情况）
             - 申请目标：target_major、target_country、level（申请学位类型：本科/硕士/博士/短期课程）
             - 地区偏好：region（目标地区列表精确到洲，如["北美洲", "南美洲", "欧洲", "亚洲", "非洲", "大洋洲", "南极洲"]）
             - 院校偏好：preferred_universities（偏好大学列表）
             - 预算要求：budget_min（最小预算）、budget_max（最大预算）（返回的值请均以元为单位展开，如40万->400000）
             - 排名要求：rank_max（最大排名要求，数字越小排名越高）
             - 背景评级：background_institution_rating（背景院校评级，如"985"、"211"、"双一流"、"普通本科"等，这里请你通过提供的背景院校和你的知识推断。）
             - 经历背景：work_experience（工作经历数组）、extracurricular（课外活动数组）

             特别注意：
             1. 如果用户却说自己没有科研经历，请把if_research设置为true（表示已经了解过用户的科研情况）
             2. 预算单位请统一为人民币（元）
             3. 排名要求：rank_max（最大排名要求，数字越小排名越高）
             4. 地区和大学名称请使用中文。
             5. 请返回扁平的JSON格式，不要嵌套分类
             6. 用户输入的专业可能会比较多样，请你根据用户的输入，将major和target_major的输出限制在以下几类：“农业与林业”，“应用科学与职业”，“艺术、设计与建筑”，“商业与管理”，“计算机科学与信息技术”，“教育与培训”，“工程与技术”，“环境研究与地球科学”，“酒店、休闲与体育”，“人文学科”，“新闻与媒体”，“法律”，“医学与健康”，“自然科学与数学”，“社会科学”。

             示例输出格式：
             {{
                 "GPA": 3.5,
                 "SCHOOL": "中山大学",
                 "major": "计算机科学与技术",
                 "degree": "硕士",
                 "budget_max": 400000,
                 "rank_max": 50,
                 "region": ["北美洲"],
                 "preferred_universities": ["哥伦比亚大学"]
             }}

             请只返回JSON格式，不要其他内容。"""

    async def run(self, context: MCPContext, parameters: Dict[str, Any]) -> MCPResponse:
        """执行画像更新"""
        user_input = parameters.get("user_input")
        if not user_input:
            return MCPResponse.error("用户输入不能为空")

        # 从上下文获取用户画像
        user_profile = None
        if context and hasattr(context, 'get_session_data'):
            user_profile = context.get_session_data('user_profile')

        # 如果上下文中没有画像，则创建一个新的，并将其存入上下文
        if user_profile is None:
            user_profile = UserProfile()
            if context and hasattr(context, 'set_session_data'):
                context.set_session_data('user_profile', user_profile)

        self.logger.info(f"开始处理用户输入: {user_input}")

        # 使用LLM提取信息 - 添加 await
        extraction_result = await self.llm_service.extract_information(user_input, self.extraction_prompt)

        if extraction_result.status != MCPStatus.SUCCESS:
            return MCPResponse.error(f"信息提取失败: {extraction_result.message}")

        try:
            # 解析提取的信息
            extracted_content = extraction_result.data["content"].strip()

            # 尝试解析JSON
            if extracted_content.startswith('{') and extracted_content.endswith('}'):
                updates = json.loads(extracted_content)
            else:
                # 如果不是标准JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', extracted_content, re.DOTALL)
                if json_match:
                    updates = json.loads(json_match.group())
                else:
                    updates = {}

            if not updates:
                return MCPResponse.no_change("用户的输入未涉及任何可用于更新画像的信息")

            # 更新用户画像
            updated_fields = user_profile.upgradeProfile(updates)

            if not updated_fields:
                return MCPResponse.no_change(
                    f"提取到的信息与现有画像一致，无需更新。涉及字段: {list(updates.keys())}"
                )

            # 获取完整性摘要
            completion_summary = user_profile.get_completion_summary()

            return MCPResponse.success(
                f"用户画像已成功更新。更新字段: {updated_fields}",
                data={
                    "updated_fields": updated_fields,
                    "extracted_info": updates,
                    "completion_summary": completion_summary,
                    "profile": user_profile.to_dict()
                }
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}, 内容: {extracted_content}")
            return MCPResponse.error(f"信息提取格式错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"画像更新异常: {e}", exc_info=True)
            return MCPResponse.error(f"画像更新失败: {str(e)}")