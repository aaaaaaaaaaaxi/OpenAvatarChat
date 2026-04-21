# OpenAvatarChat - 项目指南

## 项目概述

OpenAvatarChat (v0.6.0) 是一个模块化的交互数字人对话系统。支持文本、语音、视频等多种交互方式，ASR、LLM、TTS、Avatar 等核心组件均可灵活替换。系统针对低延迟实时对话进行了优化，平均响应时间约 2.2 秒。

**远程服务器**：`connect.westb.seetacloud.com:37411` (AutoDL GPU 云)
**项目路径**：`/root/OpenAvatarChat`
**Python**：3.11.x | **PyTorch**：2.8.0 (CUDA 12.8)

## 架构

### 入口
- `src/demo.py` — 主入口，解析命令行参数，加载配置，启动 uvicorn+FastAPI 服务器并挂载 Gradio 前端
- 默认配置：`--config config/chat_with_openai_compatible_bailian_cosyvoice.yaml`

### 核心引擎 (`src/chat_engine/`)
- `chat_engine.py` — `ChatEngine` 类：初始化处理器和逻辑管理器，管理会话生命周期
- `core/chat_session.py` — `ChatSession`：每个会话的信号/流路由，连接各处理器
- `core/handler_manager.py` — 从 `handler_search_path` 动态发现并加载处理器模块
- `core/signal_manager.py` / `stream_manager.py` — 信号与流生命周期管理
- `contexts/` — 会话上下文、处理器上下文、逻辑上下文

### 数据流模型
数据通过**类型化流**在**处理器**之间传递：
- **ChatDataType** (`data_models/chat_data_type.py`)：MIC_AUDIO → HUMAN_AUDIO → HUMAN_TEXT → AVATAR_TEXT → AVATAR_AUDIO → AVATAR_VIDEO
- **ChatSignalType**：STREAM_BEGIN, STREAM_END, INTERRUPT 等
- **EngineChannelType**：TEXT, AUDIO, VIDEO, EVENT, MOTION_DATA, DATA

### 处理器系统 (`src/handlers/`)
所有处理器继承 `HandlerBase`，通过 `get_handler_info()` 声明输入输出。生命周期：`load → create_context → warmup_context → start_context → handle → destroy_context`

| 处理器类型 | 目录 | 实现方案 |
|---|---|---|
| **Client** | `client/` | `rtc_client` (WebRTC), `ws_client` (WebSocket), `ws_lam_client` |
| **VAD** | `vad/` | `silerovad` (Silero VAD), `smart_turn_eou` (智能轮次检测) |
| **ASR** | `asr/` | `sensevoice` (SenseVoice), `bailian_asr` (百炼 ASR) |
| **LLM** | `llm/` | `openai_compatible` (OpenAI 兼容接口), `qwen_omni` (通义千问多模态), `dify`, `semantic_turn_detector` |
| **TTS** | `tts/` | `bailian_tts` (CosyVoice 百炼 API), `cosyvoice` (本地部署), `edgetts` (Edge TTS) |
| **Avatar** | `avatar/` | `liteavatar`, `lam` (LAM Audio2Expression), `musetalk`, `flashhead` (SoulX), `without_avatar` |
| **Agent** | `agent/` | `chat_agent_handler`，含工具调用、记忆、感知、OC 桥接 |
| **Analyzer** | `analyzer/` | VAD/EOU 分析与导出 |
| **Logic** | `logic/` | `interrupt_handler` (打断处理) |
| **Manager** | `manager/` | 处理器数据工具管理 |

### 配置系统 (Dynaconf)
- 配置文件位于 `config/`，YAML 格式，支持环境分区（`default:` 段）
- `service_config_loader.py` 将配置解析为：LoggerConfig、ServiceConfig、ChatEngineConfig
- 处理器配置在 YAML 的 `chat_engine.handler_configs` 下指定
- 每个配置文件对应一种 Avatar/ASR/TTS/LLM 组合（如 `chat_with_lam.yaml`、`chat_with_openai_compatible_bailian_cosyvoice_flashhead_duplex.yaml`）

### 双工模式
文件名含 `duplex` 的配置启用全双工对话，支持打断功能。使用 `HUMAN_DUPLEX_AUDIO`、`HUMAN_DUPLEX_TEXT` 数据类型。

### 服务层 (`src/service/`)
- `frontend_service/` — 前端服务
- `rtc_service/` — WebRTC 流处理（`rtc_provider.py`、`rtc_stream.py`）
- `manager_service/` — 处理器数据工具注册

### 模型 (`models/`)
已下载的模型：`LAM_audio2exp`、`iic` (SenseVoice)、`wav2vec2-base-960h`

## 常用命令

```bash
# 启动服务（在远程服务器上手动执行）
cd ~/OpenAvatarChat && python src/demo.py --config config/<配置文件>.yaml

# 下载模型
python scripts/download_models.py
python scripts/download_avatar_model.py --model "<模型ID>"

# 安装依赖（海外源需加速）
source /etc/network_turbo && pip install -e .
```

## 开发约定
- 配置使用 Dynaconf，以 `default:` 环境段为默认
- 处理器通过配置中的 module 路径从 `src/handlers/` 动态发现和加载
- 处理器之间通过类型化流（ChatDataType）通信，不直接调用
- 基于信号的生命周期管理：STREAM_BEGIN/END 控制流，INTERRUPT 用于双工模式打断
- 虚拟环境位于 `.venv/`，由 `uv` 管理
