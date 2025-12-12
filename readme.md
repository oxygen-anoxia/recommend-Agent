# 留学项目智能推荐系统 - MCP版本

## 项目介绍
本项目是一个面向留学场景下，针对学生背景的个性化留学项目智能推荐系统。该系统基于全面的留学经验数据库，以及较为精确的项目和补充信息匹配算法，并将其接入目前已有的大语言模型，为学生提供定制化的留学项目推荐。

## 功能介绍
- 学生背景分析：根据学生的个人信息、学习经历、学术成绩等，对学生进行背景分析，为后续的推荐提供基础。
- 项目匹配：基于学生的背景分析结果，利用项目和补充信息匹配算法，从数据库中筛选出符合学生需求的留学项目。
- 推荐生成：将学生的背景分析结果和项目匹配结果，输入到大语言模型中，生成定制化的留学项目推荐。
- 推荐评估：为了评估推荐系统的效果，我们将推荐结果与学生的实际选择进行对比，分析推荐系统的准确性和个性化程度。

## 技术栈
- 后端：Python、FastAPI
- 大语言模型：目前是基于Deepseek的chat模型，后续推进可能会更改。

## 项目架构

```
recoAgent_verMCP/
├── .env                    # 环境变量配置
├── .gitignore             # Git忽略文件
├── api.py                 # FastAPI主应用入口（远程调用入口，与main_mcp.py入口独立）
├── main_mcp.py           # 命令行入口（本地命令行运行入口）
├── test_api.py           # API测试文件
├── recommendation_agent_mcp.py  # 主要智能体实现
│
├── config/               # 配置模块
│   ├── __init__.py
│   └── mcp_config.py    # MCP配置管理器
│
├── core/                # 核心MCP组件
│   ├── __init__.py
│   ├── mcp_agent.py     # MCP智能体基类
│   ├── mcp_context.py   # 上下文管理
│   ├── mcp_message.py   # 消息和响应模型
│   └── mcp_tool.py      # 工具基类和注册器
│
├── models/              # 数据模型
│   ├── __init__.py
│   └── user_profile.py  # 用户画像模型
│
├── services/            # 服务层
│   ├── __init__.py
│   └── llm_service.py   # LLM服务封装
│
└── tools/               # 功能工具
    ├── __init__.py
    ├── profile_updater_mcp.py    # 画像更新工具
    ├── certain_matching_mcp.py   # 确定匹配工具
    └── guessed_matching_mcp.py   # 猜测匹配工具
```


## 核心组件详解
### 1. 核心架构 (core/) MCPAgent (mcp_agent.py)
- 作用 ：所有智能体的抽象基类
- 主要方法 ：
  - _initialize_agent() : 初始化智能体和工具
  - process_user_input() : 处理用户输入
  - execute_tool() : 执行工具调用
  - register_tool() : 注册工具 MCPTool (mcp_tool.py)
- 作用 ：工具的抽象基类和注册器
- 主要组件 ：
  - MCPTool : 工具基类，定义标准接口
  - MCPToolRegistry : 工具注册和管理器
- 核心方法 ：
  - get_schema() : 返回符合OpenAI API格式的工具schema
  - run() : 执行工具逻辑 MCPMessage & MCPResponse (mcp_message.py)
- MCPMessage : 标准化消息格式
  - 支持USER、ASSISTANT、SYSTEM、TOOL等类型
  - 包含唯一ID、时间戳、元数据
- MCPResponse : 统一响应格式
  - 状态码：SUCCESS、ERROR、NO_CHANGE等
  - 支持工具调用和元数据
- MCPStatus : 状态枚举定义 MCPContext (mcp_context.py)
- 作用 ：会话上下文管理
- 功能 ：消息历史、会话数据存储
### 2. 主智能体 (recommendation_agent_mcp.py) RecommendationAgentMCP
- 继承 ：MCPAgent
- 核心流程 ：
  1. 1.
     画像更新 ：使用LLM提取用户信息更新画像
  2. 2.
     匹配选择 ：根据画像完整度选择匹配策略
  3. 3.
     结果生成 ：生成最终推荐结果
- 主要方法 ：
  - run() : 标准处理流程
  - run_stream() : 流式处理
  - _update_user_profile() : 更新用户画像
  - _perform_matching() : 执行匹配
  - _generate_final_response() : 生成最终响应
### 3. 功能工具 (tools/) ProfileUpdaterMCP (profile_updater_mcp.py)
- 功能 ：使用LLM从用户输入中提取信息并更新画像
- 特性 ：
  - 智能信息提取
  - JSON格式解析
  - 画像完整性评估
- 输出 ：更新的字段列表和完整性摘要 CertainMatchingMCP (certain_matching_mcp.py)
- 功能 ：基于完整画像的精确匹配
- 适用 ：画像完整度高的用户
- 策略 ：精确匹配算法 GuessedMatchingMCP (guessed_matching_mcp.py)
- 功能 ：基于不完整画像的推测匹配
- 适用 ：画像完整度低的用户
- 策略 ：模糊匹配和推测算法
### 4. 数据模型 (models/) UserProfile (user_profile.py)
- 字段分类 ：
  - 基本信息 ：GPA、学校、语言成绩等
  - 学术背景 ：专业、学位、研究经历
  - 申请目标 ：目标专业、国家、地区
  - 偏好设置 ：预算范围、排名要求、偏好院校
  - 背景经历 ：工作经验、课外活动
- 核心方法 ：
  - upgradeProfile() : 更新画像字段
  - check_profile_completeness() : 检查完整性
  - get_completion_summary() : 获取完整性摘要
### 5. 服务层 (services/) MCPLLMService (llm_service.py)
- 功能 ：LLM服务的统一封装
- 支持 ：
  - 异步调用
  - 工具决策
  - 信息提取
  - 流式响应
- 配置 ：支持多种LLM提供商（OpenRouter等）
### 6. 配置管理 (config/) MCPConfig (mcp_config.py)
- 配置项 ：
  - LLM配置 ：API密钥、模型选择、基础URL
  - API配置 ：外部API设置、超时配置
  - Agent配置 ：名称、历史记录限制
  - 日志配置 ：级别、格式、输出文件
  - 运行模式 ：测试模式、调试模式
### 7. API接口 (api.py) FastAPI应用
- 端点 ： /recommend - 获取推荐
- 特性 ：
  - 会话管理
  - 流式响应支持
  - 错误处理
  - 请求验证
- 模型 ：
  - RecommendationRequest : 请求模型
  - RecommendationResponse : 响应模型
 
## 提示
- 前端开发请在浏览器查看根地址下的/docs资源，该资源详细介绍了API调用方式。目前只有recommendation一个接口。
