import itertools
import copy
import asyncio
import aiohttp
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple
import logging
from core.mcp_tool import MCPTool
from core.mcp_message import MCPResponse, MCPStatus
from models.user_profile import UserProfile, ProfileCompleteness
from core.mcp_context import MCPContext
from config.mcp_config import config


class GuessedMatchingMCP(MCPTool):
    """MCP标准化的猜测匹配工具 - 支持异步并行调用"""

    def __init__(self):
        super().__init__(
            name="run_guessed_matching",
            description="当用户画像信息不完整时，根据已有信息猜测缺失的字段并进行并行匹配。",
            required_params=[],
            parameters_schema={
                "type": "object",
                "properties": {},  # 此工具直接使用用户画像，无需额外参数
            }
        )
        self.base_url = config.get_api_config()["base_url"]
        self.logger = logging.getLogger(self.__class__.__name__)

        # 定义猜测选项配置
        self.guess_options = {
            'gpa': [85, 87, 90],
            'region': ['美国', '英国', '加拿大', '新加坡', '香港'],
            'background_institution_rating': ['985', '211', '双非'],
            'rank_max': [10, 30, 50, 100],
            'budget_max': [1000000, 800000, 300000, 400000]
        }

    def _generate_guess_combinations(self, missing_fields: List[str]) -> List[Dict[str, Any]]:
        """根据缺失字段和预设选项，生成所有可能的猜测组合"""
        self.logger.info(f"开始生成猜测组合，缺失字段: {missing_fields}")

        # 只对在guess_options中定义的字段进行猜测
        fields_to_guess = [field for field in missing_fields if field in self.guess_options]

        self.logger.info(f"可猜测字段: {fields_to_guess}")

        if not fields_to_guess:
            self.logger.warning("没有可猜测的字段")
            return []

        # 获取这些字段的猜测值列表
        guess_values = [self.guess_options[field] for field in fields_to_guess]
        self.logger.info(f"猜测值选项: {dict(zip(fields_to_guess, guess_values))}")

        # 生成所有组合的笛卡尔积
        combinations = list(itertools.product(*guess_values))
        result = [dict(zip(fields_to_guess, combo)) for combo in combinations]

        self.logger.info(f"生成了 {len(result)} 个猜测组合")
        return result

    def _convert_profile_to_api_format(self, profile: UserProfile) -> Dict[str, Any]:
        """将UserProfile对象转换为API所需的字典格式"""
        try:
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
            filtered_data = {k: v for k, v in api_data.items() if v not in ["UNKNOWN", 0, 0.0, 0xffff, None, []]}

            self.logger.debug(f"转换后的API数据: {filtered_data}")
            return filtered_data

        except Exception as e:
            self.logger.error(f"转换用户画像到API格式时出错: {e}", exc_info=True)
            return {}

    def _print_supplement_match_details(self, data: Dict[str, Any], guess_info: str = "") -> str:
        """打印补充匹配的详细结果信息"""
        try:
            details_info = f"\n=== 补充匹配详细结果 {guess_info} ===\n"

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
            return f"\n=== 补充匹配结果 {guess_info} ===\n解析结果详情时出错: {str(e)}\n"

    def _call_supplement_match_api_sync(self, api_data: Dict[str, Any], guess_info: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """同步调用补充匹配接口"""
        try:
            self.logger.info(f"调用补充匹配API - {guess_info}，请求: {api_data}")

            import requests
            response = requests.post(
                f"{self.base_url}/api/supplement_match",
                json=api_data,
                params={
                    "strict_location": False,
                    "strict_major": False,
                    "strict_rank": False,
                    "strict_budget": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"补充匹配API调用成功 - {guess_info}")

                # 输出返回内容的详细信息
                details_info = self._print_supplement_match_details(result, guess_info)
                self.logger.info(details_info)

                return result, "success"
            else:
                error_msg = f"API调用失败，状态码: {response.status_code}, 响应: {response.text}"
                self.logger.error(f"{guess_info} - {error_msg}")
                return None, error_msg

        except Exception as e:
            error_msg = f"API调用异常: {str(e)}"
            self.logger.error(f"{guess_info} - {error_msg}", exc_info=True)
            return None, error_msg

    def _parallel_api_calls_with_threads(self, guess_combinations: List[Dict[str, Any]], base_profile_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用线程池并行执行所有API调用"""
        self.logger.info(f"开始使用线程池并行执行 {len(guess_combinations)} 个API调用")
        start_time = time.time()

        # 准备所有任务数据
        tasks_data = []
        for i, guess in enumerate(guess_combinations):
            try:
                # 创建当前猜测的用户画像副本
                temp_profile_dict = copy.deepcopy(base_profile_dict)
                temp_profile_dict.update(guess)

                temp_profile = UserProfile()
                temp_profile.upgradeProfile(temp_profile_dict)

                # 转换为API格式
                api_data = self._convert_profile_to_api_format(temp_profile)

                if api_data:
                    guess_str = ', '.join([f'{k}="{v}"' for k, v in guess.items()])
                    guess_info = f"组合{i+1}({guess_str})"

                    tasks_data.append({
                        'api_data': api_data,
                        'guess_info': guess_info,
                        'guess': guess,
                        'temp_profile_dict': temp_profile_dict
                    })
                else:
                    self.logger.warning(f"组合{i+1}的API数据为空，跳过: {guess}")

            except Exception as e:
                self.logger.error(f"处理组合{i+1}时出错: {guess}, 错误: {e}", exc_info=True)

        self.logger.info(f"准备了 {len(tasks_data)} 个有效任务")

        if not tasks_data:
            self.logger.warning("没有有效的任务可执行")
            return []

        # 使用线程池执行并行调用
        all_results = []
        successful_calls = 0
        failed_calls = 0

        # 设置最大线程数，避免过多并发
        max_workers = min(len(tasks_data), 10)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._call_supplement_match_api_sync, task['api_data'], task['guess_info']): task
                for task in tasks_data
            }

            # 收集结果
            for future in future_to_task:
                task = future_to_task[future]
                try:
                    api_result, guess_info = future.result(timeout=35)  # 稍长于单个请求超时

                    if api_result:
                        all_results.append({
                            "guess": task['guess'],
                            "profile": task['temp_profile_dict'],
                            "results": api_result,
                            "guess_info": guess_info
                        })
                        successful_calls += 1
                    else:
                        failed_calls += 1

                except Exception as e:
                    self.logger.error(f"任务执行异常 - {task['guess_info']}: {e}")
                    failed_calls += 1

        end_time = time.time()
        self.logger.info(f"线程池并行API调用完成，耗时: {end_time - start_time:.2f}秒，成功: {successful_calls}，失败: {failed_calls}")

        return all_results

    async def _call_supplement_match_api_async(self, session: aiohttp.ClientSession, supplement: dict) -> dict:
        """
        Asynchronously calls the supplement match API.
        """
        api_url = f"{self.config.get('SUPPLEMENT_MATCH_API')}/supplement_match"
        try:
            async with session.post(api_url, json=supplement, timeout=self.api_timeout) as response:
                response.raise_for_status()  # Raise an exception for bad status codes
                return await response.json()
        except Exception as e:
            self.logger.error(f"API call to {api_url} with supplement {supplement} failed: {e}")
            return {"error": str(e), "supplement": supplement}

    async def _parallel_api_calls_async(self, supplements: list) -> list:
        """
        Performs parallel API calls asynchronously using aiohttp and asyncio.gather.
        """
        successful_results = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._call_supplement_match_api_async(session, s) for s in supplements]
            api_results = await asyncio.gather(*tasks)

        for result in api_results:
            if result and not result.get("error") and result.get("code") == 0 and result.get("data"):
                successful_results.extend(result["data"])

        return successful_results

    def _generate_supplements(self, user_profile: UserProfile) -> List[Dict[str, Any]]:
        """根据缺失字段和预设选项，生成所有可能的猜测组合"""
        self.logger.info(f"开始生成猜测组合，缺失字段: {missing_fields}")

        # 只对在guess_options中定义的字段进行猜测
        fields_to_guess = [field for field in missing_fields if field in self.guess_options]

        self.logger.info(f"可猜测字段: {fields_to_guess}")

        if not fields_to_guess:
            self.logger.warning("没有可猜测的字段")
            return []

        # 获取这些字段的猜测值列表
        guess_values = [self.guess_options[field] for field in fields_to_guess]
        self.logger.info(f"猜测值选项: {dict(zip(fields_to_guess, guess_values))}")

        # 生成所有组合的笛卡尔积
        combinations = list(itertools.product(*guess_values))
        result = [dict(zip(fields_to_guess, combo)) for combo in combinations]

        self.logger.info(f"生成了 {len(result)} 个猜测组合")
        return result

    async def run(self, user_input: str) -> str:
        user_profile = self.context.get_value("user_profile")
        if not user_profile:
            return "无法获取用户画像，无法进行猜测匹配。"

        self.logger.info("开始为不完整的用户画像生成猜测组合...")
        supplements = self._generate_supplements(user_profile)
        if not supplements:
            return "无法生成任何有效的猜测组合。"

        self.logger.info(f"共生成 {len(supplements)} 个猜测组合，开始并行调用API...")
        successful_supplements = await self._parallel_api_calls_async(supplements)

        if not successful_supplements:
            return "所有猜测性补充匹配均未找到合适的结果。"

        # Sort results by rank and limit to top 3
        sorted_results = sorted(successful_supplements, key=lambda x: x.get('rank', float('inf')))
        top_3_results = sorted_results[:3]

        response_str = "我们根据您现有的信息，为您做了一些可能的猜测和补充，并找到了以下可能适合您的学校：\n"
        for item in top_3_results:
            response_str += f"- 学校: {item.get('school_name_cn', 'N/A')}, 专业: {item.get('major_name_cn', 'N/A')}, 排名: {item.get('rank', 'N/A')}\n"

        response_str += "请问您对以上哪个选项感兴趣？或者，您可以提供更详细的信息，例如您的GPA、目标专业、预算等，以便我们为您提供更精确的推荐。"

        return response_str

    def run(self, context: MCPContext, parameters: Dict[str, Any]) -> MCPResponse:
        """执行猜测匹配"""
        self.logger.info("开始执行猜测匹配工具")

        try:
            # 从上下文获取用户画像
            if context and hasattr(context, 'get_session_data'):
                user_profile = context.get_session_data('user_profile')
                self.logger.info("从上下文成功获取用户画像")
            else:
                user_profile = None
                self.logger.error("无法从上下文获取用户画像")

            if not user_profile:
                error_msg = "用户画像不存在，请先提供个人信息"
                self.logger.error(error_msg)
                return MCPResponse.error(error_msg)

            # 检查画像完整性
            self.logger.info("检查用户画像完整性")
            completeness, missing_fields = user_profile.check_profile_completeness()
            self.logger.info(f"画像完整性: {completeness.value}，缺失字段: {missing_fields}")

            # 如果信息完整，建议使用确定匹配
            if completeness == ProfileCompleteness.COMPLETE:
                error_msg = "您的信息已经完整，建议使用确定匹配工具获得更精确的结果"
                self.logger.info(error_msg)
                return MCPResponse.error(error_msg)

            # 检查缺失字段数量，超过2个不进行猜测匹配
            if len(missing_fields) > 2:
                error_msg = f"您缺失的字段过多（{len(missing_fields)}个：{', '.join(missing_fields)}），猜测匹配仅适用于缺失1-2个字段的情况。请先补充更多信息后再使用此功能。"
                self.logger.info(error_msg)
                return MCPResponse.error(error_msg)

            # 生成猜测组合
            guess_combinations = self._generate_guess_combinations(missing_fields)

            if not guess_combinations:
                error_msg = f"缺失的字段（{', '.join(missing_fields)}）无法进行有效猜测，请您补充更多信息"
                self.logger.error(error_msg)
                return MCPResponse.error(error_msg)

            self.logger.info(f"生成了 {len(guess_combinations)} 个猜测组合，准备并行调用API")

            # 获取基础画像字典
            base_profile_dict = user_profile.to_dict()
            self.logger.debug(f"基础用户画像: {base_profile_dict}")

            # 使用线程池并行调用所有API（避免事件循环冲突）
            try:
                all_results = self._parallel_api_calls_with_threads(guess_combinations, base_profile_dict)

            except Exception as e:
                self.logger.error(f"并行调用过程中出错: {e}", exc_info=True)
                return MCPResponse.error(f"并行API调用失败: {str(e)}")

            self.logger.info(f"获得 {len(all_results)} 个有效结果")

            # 生成结果摘要
            results_summary = ""

            if not all_results:
                error_msg = "所有猜测组合的API调用都失败了，请检查网络连接或稍后再试"
                self.logger.error(error_msg)
                return MCPResponse.error(error_msg)

            for result in all_results:
                guess = result["guess"]
                supplement_results = result["results"]
                guess_info = result["guess_info"]

                guess_str = ', '.join([f'{k}为"{v}"' for k, v in guess.items()])
                results_summary += f"\n--- \n**{guess_info} - 如果您的{guess_str}：**\n"

                if supplement_results and supplement_results.get('summary', {}).get('text'):
                    # 只截取部分核心结果展示给用户
                    summary_text = supplement_results['summary']['text']
                    # 简单地取第一句话作为摘要
                    short_summary = summary_text.split('。')[0] + '。'
                    results_summary += f"{short_summary}\n"
                else:
                    results_summary += "未能找到匹配的项目。\n"

            # 生成最终摘要
            final_summary = f"您的信息尚不完整，我们并行处理了 {len(guess_combinations)} 个猜测组合，成功获得 {len(all_results)} 个结果：{results_summary}"
            final_summary += "\n\n为了给您更精确的推荐，请告诉我您缺失的信息。"

            # 整合所有结果数据
            matching_summary = {
                "guessed_results": all_results,
                "missing_fields": missing_fields,
                "completeness": completeness.value,
                "match_type": "guessed_parallel_threads",
                "total_combinations": len(guess_combinations),
                "successful_combinations": len(all_results),
                "failed_combinations": len(guess_combinations) - len(all_results)
            }

            self.logger.info(f"猜测匹配执行完成，总组合: {len(guess_combinations)}，成功: {len(all_results)}")

            return MCPResponse.success(
                final_summary,
                data=matching_summary
            )

        except Exception as e:
            error_msg = f"猜测匹配过程中发生未预期错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return MCPResponse.error(error_msg)