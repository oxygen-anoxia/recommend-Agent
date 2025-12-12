import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, Generator
from recommendation_agent_mcp import RecommendationAgentMCP
from core.mcp_context import MCPContext
from core.mcp_message import MCPResponse
import logging
from fastapi.responses import JSONResponse
from inspect import isgenerator
from fastapi.responses import StreamingResponse
import sys
import os
from config.mcp_config import config, get_server_config  # 导入服务器配置

# 将当前目录添加到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 使用统一的日志配置（移除 basicConfig，使用模块名）
logger = logging.getLogger(__name__)

# --- FastAPI 应用初始化 ---
'''
    功能 : 创建FastAPI应用实例
    输入 : 无
    输出 : FastAPI应用对象
    作用 : 定义API的基本信息和元数据
'''
app = FastAPI(
    title="留学推荐智能体 API",
    description="一个基于MCP（模型-上下文协议）的留学推荐智能体API。",
    version="1.0.0"
)

# --- 全局Agent实例 ---
'''
    功能 : 创建单例的推荐智能体实例
    输入 : 无
    输出 : RecommendationAgentMCP实例
    作用 : 避免每次请求都重新初始化Agent，提高性能
    异常处理 : 如果初始化失败，抛出RuntimeError
'''
try:
    logger.info("正在创建全局Agent实例...")
    agent_instance = RecommendationAgentMCP()
    logger.info("全局Agent实例创建成功。")
except Exception as e:
    logger.error(f"创建全局Agent实例失败: {e}", exc_info=True)
    raise RuntimeError(f"无法初始化全局Agent: {e}") from e

# --- 请求和响应模型 ---
# Pydantic模型，用于请求和响应体的数据验证

class RecommendationRequest(BaseModel):
    '''
        功能 : 定义API请求的数据结构
        - user_id : 用户唯一标识符
        - session_id : 会话唯一标识符
        - user_input : 用户输入的问题或需求
        - stream : 是否启用流式响应（默认False）
    '''
    user_id: str
    session_id: str
    user_input: str
    stream: bool = False

class RecommendationResponse(BaseModel):
    '''
        功能 : 定义API响应的数据结构
        - status : 响应状态（成功/失败）
        - message : 响应消息
        - data : 响应数据（可选）
    '''
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

# 全局会话存储
'''
    功能 : 存储用户会话上下文
    数据结构 : 字典，键为"user_id:session_id"格式的字符串，值为MCPContext对象

'''
sessions: Dict[str, MCPContext] = {}

# 依赖注入函数，用于获取或创建会话上下文
def get_session_context(request: RecommendationRequest) -> MCPContext:
    """
    功能 : 依赖注入函数，获取或创建会话上下文
    输入 : RecommendationRequest对象
    输出 : MCPContext对象
    逻辑流程 :
        1. 验证user_id和session_id是否存在
        2. 构造会话键（user_id:session_id）
        3. 如果会话不存在，创建新的MCPContext
        4. 返回对应的会话上下文 异常处理 : 如果缺少必要参数，抛出HTTP 400错误
    """
    if not request.user_id or not request.session_id:
        raise HTTPException(status_code=400, detail="user_id and session_id are required")

    session_key = f"{request.user_id}:{request.session_id}"
    if session_key not in sessions:
        sessions[session_key] = MCPContext(user_id=request.user_id, session_id=request.session_id)
        logger.info(f"为 user_id: {request.user_id}, session_id: {request.session_id} 创建了新的会话上下文。")
    return sessions[session_key]

@app.post("/recommendation", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest, context: MCPContext = Depends(get_session_context)):
    """
    功能 : 处理留学推荐请求的主要API端点
    HTTP方法 : POST
    路径 : /recommendation
    输入 : RecommendationRequest对象
    输出 : JSON响应
    处理流程 :
        1.获取或创建会话上下文
        2.将上下文设置到Agent实例
        3.调用Agent的run方法处理用户输入
        4.返回处理结果
    异常处理 : 捕获所有异常，返回HTTP 500错误和错误信息
    """
    try:
        # 添加请求日志
        print(f"[DEBUG] 收到推荐请求: user_id={request.user_id}, session_id={request.session_id}")
        print(f"[DEBUG] 请求内容: {request.user_input[:100]}...")
        logger.info(f"收到推荐请求: user_id={request.user_id}, session_id={request.session_id}")
        
        # 不再需要手动调用 get_session_context，因为已经通过依赖注入获得
        agent_instance.set_context(context)

        # 根据stream参数选择不同的处理方式
        if request.stream:
            print(f"[DEBUG] 使用流式响应")
            # 流式响应
            async def generate_stream():
                async for chunk in agent_instance.run_stream(request.user_input):
                    yield f"data: {chunk}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            print(f"[DEBUG] 使用非流式响应")
            # 非流式响应（现有逻辑）
            response_data = await agent_instance.run(request.user_input)
            print(f"[DEBUG] 响应数据: {str(response_data)[:200]}...")
            return JSONResponse(content=response_data)

    except Exception as e:
        print(f"[DEBUG] 处理请求时发生异常: {e}")
        logger.error(f"An error occurred while processing input for session {request.session_id}: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"处理用户输入时发生异常: {e}"})

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "reco-agent"}

# 应用启动
if __name__ == "__main__":
    server_config = get_server_config()
    logger.info(f"使用 uvicorn 启动 FastAPI 服务器在 {server_config['host']}:{server_config['port']}...")
    uvicorn.run(
        app,
        host=server_config["host"],
        port=server_config["port"]
    )