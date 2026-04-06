# LangChain 集成说明（面试增强版）

本文档说明你当前项目是如何接入 LangChain 的、它解决了什么问题、工具如何被调用、以及后续如何扩展到向量数据库/RAG。

## 1. 为什么要在现有项目里引入 LangChain

你当前项目原本已经具备：

- FastAPI 接口层
- 会话与消息持久化（MySQL + SQLAlchemy）
- 本地 Qwen 推理（Transformers）

但是如果只停留在“直接模型调用”，面试中通常会被追问：

- 你怎么做多步骤任务编排？
- 你怎么接外部工具？
- 你怎么接知识库检索和向量库？
- 你怎么管理提示词模板与上下文？

LangChain 的价值就在这里：

1. 把 Prompt、上下文、工具调用、模型调用变成可组合的链（LCEL）。
2. 让“工具增强”“检索增强”“代理式调用”更容易扩展。
3. 让工程结构从“脚本式调用”升级为“可维护的编排层”。

## 2. 本次改造做了什么

本次改造遵循一个原则：**前端 API 不变，后端内部升级为 LangChain 编排**。

### 2.1 新增 LangChain 编排服务

新增文件：

- `backend/app/services/langchain_service.py`

核心能力：

1. 使用 `ChatPromptTemplate + RunnableLambda + RunnableBranch` 组织链路。
2. 内置两个可演示工具：
   - `current_time_tool`：获取当前时间
   - `calculator_tool`：安全计算数学表达式
3. 提供统一入口：
   - `generate_reply(...)`（非流式）
   - `stream_reply(...)`（流式）

### 2.2 替换聊天编排主入口

修改文件：

- `backend/app/services/chat_service.py`

变更点：

1. 原先 `chat_service` 直接调用 `inference_service`。
2. 现在改为调用 `langchain_chat_service`。
3. API 返回结构不变：`session_id / user_message_id / assistant_message_id / reply`。
4. 额外把 LangChain 元信息写入 `generation_params.langchain`，方便后续可观测与调试。

### 2.3 新增配置项与依赖

修改文件：

- `backend/app/core/config.py`
- `backend/requirements.txt`

新增配置项：

- `LANGCHAIN_ENABLED`：是否启用 LangChain 编排
- `LANGCHAIN_ENABLE_TOOLS`：是否启用工具调用
- `LANGCHAIN_MAX_HISTORY_ROUNDS`：编排层历史轮数
- `LANGCHAIN_DEFAULT_TIMEZONE`：时间工具默认时区

新增依赖：

- `langchain>=0.3.0`
- `langchain-core>=0.3.0`

## 3. 现在的调用链路

请求链路保持一致：

1. 前端请求 `/api/qwen/chat` 或 `/api/qwen/chat/stream`
2. 后端进入 `routes.py`
3. 跳转到 `chat_service.py`
4. `chat_service` 调 `langchain_service`
5. `langchain_service` 做：
   - 上下文拆分
   - 工具路由（可选）
   - Prompt 组装
   - 调用本地 Qwen 推理
6. 回写数据库并返回前端

## 4. 工具调用是怎么发生的

你可以把当前实现理解为“可控的工具增强链”：

1. 路由阶段：
   - 从用户输入判断是否需要工具（时间/计算）
2. 执行阶段：
   - 命中则调用工具，拿到 `tool_result`
3. 生成阶段：
   - 把 `tool_result` 注入到系统提示中
   - 再调用 Qwen 生成最终答案

这种方式有两个优势：

1. 比“纯自由 Agent”更可控，稳定性高。
2. 后续可平滑升级到函数调用模型或 AgentExecutor。

## 5. 你可以在面试中这样解释“LangChain 有什么用”

建议回答模板：

> 我在项目里把 LangChain 放在模型调用上层，专门负责对话编排和工具增强。这样做后，接口层和模型层解耦，Prompt、上下文截断、工具路由都集中在编排层管理。当前已经实现时间和计算工具，下一步可以无缝接入向量数据库检索，把它扩展为 RAG 问答系统。

如果对方追问“为什么不直接自己写”：

> 直接写当然可以，但 LangChain 的好处是组件标准化，后续接入 Retriever、Memory、Agent、Tracing 成本更低，团队协作时也更容易维护。

## 6. 如何扩展到向量数据库 / RAG（下一步路线）

你后续可以按这个顺序升级：

1. 接入 embedding 模型（本地或 API）
2. 接入向量库（FAISS / Milvus / Chroma）
3. 在 LangChain 中增加 `Retriever` 链路
4. 改造 Prompt：把检索片段注入上下文
5. 增加引用与溯源字段（source docs）

链路会变成：

`User Query -> Retriever -> Context Packing -> LLM -> Answer + Sources`

## 7. 如何扩展更多工具

在 `langchain_service.py` 新增工具函数并挂到路由分支即可。

最小步骤：

1. 用 `@tool` 定义工具
2. 在 `_route_tool` 增加路由规则
3. 在 `_tool_runner` 增加分支执行
4. 可选：在 metadata 里记录工具调用结果摘要

## 8. 环境变量建议

可在 `backend/.env` 中增加：

```ini
LANGCHAIN_ENABLED=true
LANGCHAIN_ENABLE_TOOLS=true
LANGCHAIN_MAX_HISTORY_ROUNDS=10
LANGCHAIN_DEFAULT_TIMEZONE=Asia/Shanghai

# RAG / Qdrant
RAG_ENABLED=true
RAG_TOP_K=4
RAG_SCORE_THRESHOLD=0.2
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
QDRANT_COLLECTION=project_kb

# 二选一：远程 Qdrant 或本地 Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
# QDRANT_LOCAL_PATH=./.qdrant_local
```

## 9. 把当前文档作为知识库（第一版）

你可以直接把本文件写入向量库，作为项目知识库的第一份资料。

### 9.1 安装新增依赖

```bash
cd backend
pip install -r requirements.txt
```

### 9.2 入库当前文档

```bash
cd backend
python scripts/ingest_knowledge_base.py --file docs/LANGCHAIN_INTEGRATION_GUIDE.md --recreate
```

脚本会自动完成：

1. 加载 Markdown 文档
2. 文本切分（chunk）
3. 向量化（Embedding）
4. 写入 Qdrant 集合（默认 `project_kb`）

### 9.3 对话时自动检索

当前后端已经将知识库检索接入 `langchain_service.py`：

1. 每次用户提问先进行向量检索
2. 命中片段拼接到系统上下文中
3. 再调用本地 Qwen 生成回答
4. 检索元信息写入 `generation_params.langchain`，便于调试

你可以在数据库里查看 `rag_hits`、`rag_sources`、`rag_error` 等字段确认检索行为。

## 10. 你这次改造的简历亮点（可直接使用）

你可以把项目描述为：

1. 基于 FastAPI + Qwen 本地模型构建离线对话系统，支持流式输出与会话持久化。
2. 设计并实现 LangChain 编排层（LCEL），将 Prompt 管理、上下文截断、工具调用从模型推理解耦。
3. 实现工具增强问答（时间/计算），并将调用元信息持久化，支持可观测与调试。
4. 保持前端 API 不变完成后端架构升级，为后续 RAG/向量数据库接入预留标准接口。

## 11. 注意事项

1. 你当前运行环境不在本机，本次仅完成代码改造，未执行实际启动验证。
2. 首次部署到目标环境时，请确保安装了新增依赖并同步 `.env` 配置。
3. 若需要更强的自动工具选择能力，可将当前“规则路由”升级为“模型决策 + 结构化输出”的 Tool Calling 方案。
