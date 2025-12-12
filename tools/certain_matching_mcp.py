import requests
import json
from typing import Dict, Any
import logging
from core.mcp_tool import MCPTool
from core.mcp_message import MCPResponse, MCPStatus
from models.user_profile import UserProfile, ProfileCompleteness
from core.mcp_context import MCPContext
from config.mcp_config import config

class CertainMatchingMCP(MCPTool):
    """MCP标准化的精确匹配工具"""

    def __init__(self):
        super().__init__(
            name="run_certain_matching",
            description="当用户画像信息完整（没有缺失字段）时，为用户运行精确的留学项目和案例匹配。",
            required_params=[],
            parameters_schema={
                "type": "object",
                "properties": {},  # 此工具直接使用完整的用户画像，无需LLM提供额外参数
            }
        )
        self.base_url = config.get_api_config()["base_url"]
        self.logger = logging.getLogger(self.__class__.__name__)

    def _convert_profile_to_api_format(self, profile: UserProfile) -> Dict[str, Any]:
        """将UserProfile对象转换为API所需的字典格式"""
        major_list = []
        if profile.major and profile.major != "UNKNOWN":
            major_list = profile.major if isinstance(profile.major, list) else [profile.major]

        api_data = {
            "degree": profile.degree,
            "gpa": profile.GPA,
            "major": major_list,
            "budget_max": profile.budget_max,
            "rank_max": profile.rank_max,
            "region": profile.region,
            "background_institution_rating": profile.background_institution_rating
        }

        # 过滤掉无效值或默认值
        return {k: v for k, v in api_data.items() if v not in ["UNKNOWN", 0, 0.0, 0xffff, None, []]}

    def _print_supplement_match_details(self, data: Dict[str, Any]) -> str:
        """打印补充匹配的详细结果信息"""
        try:
            details_info = "\n=== 补充匹配详细结果 ===\n"

            # 1. 初始结果统计
            if "initial_results" in data:
                initial_results = data["initial_results"]
                stats = initial_results.get("stats", {})
                details_info += "\n1. 初始匹配结果\n" + "=" * 30 + "\n"
                details_info += f"- 初始项目数: {stats.get('initial_count', 0)}\n"
                details_info += f"- 最终项目数: {stats.get('final_count', 0)}\n"
                details_info += f"- 包含案例数: {stats.get('with_cases_count', 0)}\n"
                details_info += f"- 总处理时间: {stats.get('total_time', 0):.3f}秒\n"

                cases_summary = stats.get("cases_summary", {})
                details_info += f"- 案例占比: {cases_summary.get('cases_percentage', 0)}%\n"

            # 2. 补充结果
            if "supplementary_results" in data and data["supplementary_results"]:
                details_info += "\n2. 补充匹配结果\n" + "=" * 30 + "\n"
                details_info += f"放宽条件顺序: {', '.join(data.get('relaxed_conditions', []))}\n"
                for idx, supp_result in enumerate(data["supplementary_results"], 1):
                    details_info += f"第{idx}次放宽: {supp_result['relaxed_field']} - 新增项目数: {len(supp_result['results'])}\n"

            # 3. 总体统计
            if "summary" in data:
                summary = data["summary"]
                details_info += "\n3. 总体统计\n" + "=" * 30 + "\n"
                details_info += f"- 最终项目总数: {summary.get('total_programs', 0)}\n"
                details_info += f"- 最终案例总数: {summary.get('with_cases', 0)}\n"

            return details_info

        except Exception as e:
            self.logger.error(f"打印补充匹配详情时出错: {e}")
            return f"\n=== 补充匹配结果 ===\n解析结果详情时出错: {str(e)}\n"

    def _print_case_match_details(self, data: Dict[str, Any]) -> str:
        """打印案例匹配的详细结果"""
        try:
            details_info = "\n=== 案例匹配详细结果 ===\n"
            details_info += f"状态: {data.get('status', 'unknown')}\n"

            if data.get('status') == 'success':
                summary = data.get('summary', {})
                details_info += f"\n总览:\n"
                details_info += f"- 总项目数: {summary.get('total_programs', 0)}\n"
                details_info += f"- 总案例数: {summary.get('total_cases', 0)}\n"

                type_results = data.get('type_results', {})
                for match_type in ["stretch", "normal", "safe"]:
                    if match_type in type_results:
                        type_result = type_results[match_type]
                        details_info += f"\n{match_type.title()}级项目:\n"
                        if type_result.get("results", {}).get("matched_programs"):
                            program_scores = type_result.get("details", {}).get("program_scores", [])
                            details_info += f"- 匹配项目数: {len(program_scores)}\n"
                            for prog in program_scores[:3]:  # 只显示前3个
                                details_info += f"  项目ID: {prog.get('program_id', 'N/A')}, 综合得分: {prog.get('score', 0):.3f}\n"
                        else:
                            details_info += "  无匹配项目\n"
            else:
                details_info += f"错误信息: {data.get('error_message', '未知错误')}\n"

            return details_info

        except Exception as e:
            self.logger.error(f"打印案例匹配详情时出错: {e}")
            return f"\n=== 案例匹配结果 ===\n解析结果详情时出错: {str(e)}\n"

    def _call_supplement_match_api(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用补充匹配接口"""
        try:
            self.logger.info(f"调用补充匹配API，请求: {api_data}")

            response = requests.post(
                f"{self.base_url}/api/supplement_match",
                json=api_data,
                params={
                    "strict_location": False,
                    "strict_major": False,
                    "strict_rank": False,
                    "strict_budget": False
                }
            )
            response.raise_for_status()

            result = response.json()
            self.logger.info("补充匹配API调用成功")

            # 输出返回内容的详细信息
            details_info = self._print_supplement_match_details(result)
            self.logger.info(details_info)

            return result

        except requests.RequestException as e:
            self.logger.error(f"补充匹配API调用失败: {e}")
            raise

    def _call_case_match_api(self, match_results: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """调用案例匹配接口"""
        try:
            api_data = {
                "match_results": match_results,
                "user_info": user_info
            }
            self.logger.info(f"调用案例匹配API，请求数据大小: {len(str(api_data))} 字符")

            response = requests.post(
                f"{self.base_url}/api/case_match",
                json=api_data
            )
            response.raise_for_status()

            result = response.json()
            self.logger.info("案例匹配API调用成功")

            # 输出返回内容的详细信息
            details_info = self._print_case_match_details(result)
            self.logger.info(details_info)

            return result

        except requests.RequestException as e:
            self.logger.error(f"案例匹配API调用失败: {e}")
            raise

    def run(self, context: MCPContext, parameters: Dict[str, Any]) -> MCPResponse:
        """执行精确匹配"""
        # 从上下文获取用户画像
        if context and hasattr(context, 'get_session_data'):
            user_profile = context.get_session_data('user_profile')
        else:
            user_profile = None

        if not user_profile:
            return MCPResponse.error("用户画像不存在，请先提供个人信息")

        # 检查画像完整性
        completeness, missing_fields = user_profile.check_profile_completeness()

        if completeness == ProfileCompleteness.INCOMPLETE:
            return MCPResponse.error(
                f"用户画像信息不完整，缺少必需字段: {missing_fields}。请先补充这些信息。"
            )

        try:
            # 转换为API格式
            api_data = self._convert_profile_to_api_format(user_profile)

            if not api_data:
                return MCPResponse.error("用户画像中没有足够的有效信息进行匹配")

            # 调用补充匹配API
            supplement_result = self._call_supplement_match_api(api_data)

            # 准备案例匹配的用户信息
            user_info = {
                "gpa": user_profile.GPA,
                "background_rating": user_profile.background_institution_rating
            }

            # 调用案例匹配API
            case_result = self._call_case_match_api(supplement_result, user_info)

            # 整合结果
            matching_summary = {
                "supplement_matches": supplement_result,
                "case_matches": case_result,
                "profile_used": api_data,
                "completeness": completeness.value
            }

            # 生成用户友好的摘要
            supplement_count = len(supplement_result.get('matches', []))
            case_count = len(case_result.get('cases', []))

            summary_message = f"匹配完成！找到 {supplement_count} 个项目推荐和 {case_count} 个相似案例。"

            return MCPResponse.success(
                summary_message,
                data=matching_summary
            )

        except Exception as e:
            error_msg = f"匹配过程中发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return MCPResponse.error(error_msg)