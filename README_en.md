# recommend-Agent - Personalized Study Abroad Recommendation System (MCP Version)

> **Note on Git History:**  
> The original commit history was removed using an orphan branch because an API key was accidentally committed in an earlier version.  
> All sensitive information has been removed, and the current repository contains only clean, secure commits.

---

## Project Overview

**recommend-Agent MCP** is a personalized recommendation system designed for study abroad scenarios.  
It analyzes student backgrounds, matches them with suitable programs, and generates tailored recommendations using a large language model (LLM).

Key goals of this project:

- Extract and structure student information for analysis  
- Match student profiles with relevant study abroad programs using precise and fuzzy algorithms  
- Generate LLM-based, human-readable recommendations  
- Evaluate recommendation quality against actual student choices

---

## My Role & Contributions

I developed this project **entirely by myself**, including:

- Designing the **core agent architecture** (MCPAgent) and implementing main workflows  
- Implementing **user profile extraction and management**, including JSON-based profile representation and completeness assessment  
- Integrating LLM services for **personalized recommendation generation**  
- Implementing **matching strategies**: precise matching for complete profiles, fuzzy matching for incomplete profiles  
- Designing **FastAPI endpoints** for remote recommendation access  
- Ensuring **data security**: removed sensitive API keys and cleaned Git history  
- Overall responsibility for project structure, core logic, and workflow orchestration

---

## Technology Stack

- **Python 3**: Core programming language  
- **FastAPI**: API service and endpoint management  
- **LLM API** (Deepseek-based chat model): Recommendation generation  
- **JSON / Structured Data**: User profile management and tool input/output  
- **Modular Architecture**: Core agent, tools, services, config, models, and API clearly separated

---

## Project Architecture

```
recoAgent_verMCP/
├── .env # Environment variables
├── .gitignore # Git ignore file
├── api.py # FastAPI main application
├── main_mcp.py # CLI entry point
├── test_api.py # API test scripts
├── recommendation_agent_mcp.py # Main agent implementation
│
├── config/ # Configuration
│ └── mcp_config.py # Configuration manager
│
├── core/ # Core MCP components
│ ├── mcp_agent.py # Agent base class
│ ├── mcp_context.py # Context management
│ ├── mcp_message.py # Message and response models
│ └── mcp_tool.py # Tool base class and registry
│
├── models/ # Data models
│ └── user_profile.py # User profile structure
│
├── services/ # Service layer
│ └── llm_service.py # LLM API service wrapper
│
└── tools/ # Functional tools
├── profile_updater_mcp.py # User profile updater
├── certain_matching_mcp.py # Precise matching tool
└── guessed_matching_mcp.py # Fuzzy matching tool
```

---

## Core Components

### 1. MCP Core Agent (`core/mcp_agent.py`)
- Abstract base class for all agents  
- Methods:
  - `_initialize_agent()`: Initialize agent and tools  
  - `process_user_input()`: Handle user input  
  - `execute_tool()`: Execute tool logic  
  - `register_tool()`: Register tools  

### 2. MCP Tools (`core/mcp_tool.py`)
- Base class for tools, defining standard interfaces  
- Registry manages all registered tools  
- Methods:
  - `get_schema()`: Return tool schema compatible with LLM API  
  - `run()`: Execute tool logic  

### 3. MCP Messages & Context (`core/mcp_message.py`, `core/mcp_context.py`)
- Standardized message types: USER, ASSISTANT, SYSTEM, TOOL  
- Context stores session history and metadata  
- Response structure: status codes (SUCCESS, ERROR, NO_CHANGE) and tool outputs  

### 4. Main Agent (`recommendation_agent_mcp.py`)
- Inherits from MCPAgent  
- Workflow:
  1. Update user profile via LLM extraction  
  2. Select matching strategy based on profile completeness  
  3. Generate final recommendation  
- Key methods: `run()`, `run_stream()`, `_update_user_profile()`, `_perform_matching()`, `_generate_final_response()`

### 5. Tools
- **ProfileUpdaterMCP**: Extracts and updates user profile from input  
- **CertainMatchingMCP**: Precise matching for complete profiles  
- **GuessedMatchingMCP**: Fuzzy matching for incomplete profiles  

### 6. User Profile Model (`models/user_profile.py`)
- Categories:
  - Basic info: GPA, school, language scores  
  - Academic background: major, degree, research  
  - Goals: target programs, countries, regions  
  - Preferences: budget, ranking, preferred schools  
  - Experience: work, extracurriculars  
- Methods: `upgradeProfile()`, `check_profile_completeness()`, `get_completion_summary()`

### 7. LLM Service (`services/llm_service.py`)
- Unified interface for calling LLM APIs  
- Supports async calls, streaming responses, and tool decision logic  

### 8. Configuration (`config/mcp_config.py`)
- LLM settings: API keys, model choice, base URL  
- API settings: endpoints, timeouts  
- Agent settings: name, history limits  
- Logging and run mode configuration  

### 9. API (`api.py`)
- Endpoint: `/recommend`  
- Supports session management, streaming, request validation, and error handling  
- Request/response models: `RecommendationRequest`, `RecommendationResponse`  

---

## Notes

- Entire project implemented **independently**  
- Git history cleared due to accidental API key exposure  
- Modular, production-ready architecture showcasing Python, FastAPI, LLM integration, and design of abstract agent frameworks  
- Focused on educational and research purposes
