from recommendation_agent_mcp import RecommendationAgentMCP
from config.mcp_config import MCPConfig
import asyncio
import sys
import os


# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- MCP 控制开关 ---
# 设置为 True 以运行预设的测试对话
# 设置为 False 以启动交互式命令行会话
TEST_MODE = True

# 设置为 True 以启用详细日志
DEBUG_MODE = False

async def run_test_scenario(agent: RecommendationAgentMCP):
    """运行一个预设的多轮对话测试。"""
    print("--- [MCP 测试模式]：开始运行预设对话场景 ---")

    test_inputs = [
        "我是一名中山大学的学生，目前是本科计算机专业，我想申请计算机科学与技术专业的硕士，",
        "想去美国的哥伦比亚大学，现在绩点78分，托福95分，预算约40万，",
        "我想报全球排名前50的学校。请你为我推荐一些学校？",
    ]

    for i, user_input in enumerate(test_inputs):
        print(f"\n--- 对话轮次 {i+1} ---")
        print(f"> 用户: {user_input}")

        try:
            reply = agent.run_once(user_input)
            print(f"< MCP Agent: {reply}")
        except Exception as e:
            print(f"< MCP Agent: 抱歉，处理您的请求时遇到了一个错误: {e}")
            if DEBUG_MODE:
                import traceback
                traceback.print_exc()

    print("\n--- [MCP 测试模式]：对话场景运行结束 ---")

async def run_interactive_session(agent: RecommendationAgentMCP):
    """启动交互式命令行会话。"""
    print("--- [MCP 交互模式]：智能推荐 MCP Agent 已启动 --- (输入 '退出' 来结束对话)")

    while True:
        try:
            user_input = input("> 用户: ")
            if user_input.lower() in ["退出", "exit", "quit"]:
                print("< MCP Agent: 感谢您的使用，再见！")
                break

            reply = agent.run_once(user_input)
            print(f"< MCP Agent: {reply}")

        except KeyboardInterrupt:
            print("\n< MCP Agent: 检测到中断，感谢您的使用，再见！")
            break
        except Exception as e:
            print(f"< MCP Agent: 抱歉，处理您的请求时遇到了一个错误: {e}")
            if DEBUG_MODE:
                import traceback
                traceback.print_exc()

def main():
    """主函数，初始化 MCP Agent 并根据 TEST_MODE 决定运行模式。"""
    try:
        # 初始化 MCP 配置
        config = MCPConfig()

        print("[MCP 系统] 正在初始化 MCP 推荐 Agent...")

        # 创建 MCP Agent 实例
        agent = RecommendationAgentMCP()

        print("[MCP 系统] MCP 推荐 Agent 初始化完成")
        print(f"[MCP 系统] 使用模型: {config.get_llm_config()['model']}")
        print(f"[MCP 系统] 已注册工具数量: {len(agent.context.tool_registry.list_tools())}")

        # 根据 TEST_MODE 选择运行模式
        if TEST_MODE:
            # 同步运行测试场景
            import asyncio
            asyncio.run(run_test_scenario(agent))
        else:
            # 同步运行交互会话
            import asyncio
            asyncio.run(run_interactive_session(agent))

    except Exception as e:
        print(f"[MCP 系统] 启动失败: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()