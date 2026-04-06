# RemoteSAM + Qwen 前后端联调（推荐：双环境双后端）

目标：在同一套前端中稳定调用两个模型服务。

- Qwen 文本后端：独立 Python 环境（建议 `zwyAi`）
- RemoteSAM 多模态后端：独立 Python 环境（建议 `remotesam_stable`）

这种方式可避免 `transformers`、`mmcv`、`mmdet`、`torch` 互相冲突。

如果你要了解本项目的 LangChain 编排改造与工具调用机制，请阅读：`backend/docs/LANGCHAIN_INTEGRATION_GUIDE.md`。

## 1. 部署拓扑

- 前端：`http://127.0.0.1:5173`
- Qwen 后端：`http://127.0.0.1:8001`
- RemoteSAM 后端：`http://127.0.0.1:8002`

## 2. 启动 Qwen 后端（zwyAi 环境）

在 PowerShell 窗口 A：

```powershell
cd D:/zwy/zwyAi/backend
& "D:/anacona/envs/zwyAi/python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

建议在 `backend/.env` 中确保：

```ini
MODEL_PATH=D:/zwy/zwyAi/models/Qwen2.5-Coder-1.5B-Instruct
MODEL_DTYPE=float16
MODEL_DEVICE_MAP=auto
MODEL_OFFLINE=true
```

## 3. 启动 RemoteSAM 后端（remotesam_stable 环境）

在 PowerShell 窗口 B：

```powershell
cd D:/zwy/zwyAi/backend
& "D:/anacona/envs/remotesam_stable/python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

建议在 `backend/.env` 中确保：

```ini
REMOTESAM_REPO_PATH=../RemoteSAM-master/RemoteSAM-master
REMOTESAM_CHECKPOINT=D:/zwy/zwyAi/models/RemoteSAMv1.pth
REMOTESAM_DEVICE=cuda:0
REMOTESAM_USE_EPOC=false
REMOTESAM_AUTO_LOAD=false
```

说明：

- `REMOTESAM_AUTO_LOAD=false` 为懒加载，首次推理才加载模型。
- 如果需要启动即加载，可改为 `true`。

## 4. 启动前端

```powershell
cd D:/zwy/zwyAi/frontend
npm install
npm run dev
```

默认打开 `http://127.0.0.1:5173`。

## 5. 前端代理建议

若要同时接入两个后端，建议在 `frontend/vite.config.ts` 里配置两个前缀（示例）：

```ts
proxy: {
   '/api/qwen': {
      target: 'http://127.0.0.1:8001',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api\/qwen/, '/api'),
   },
   '/api/remotesam': {
      target: 'http://127.0.0.1:8002',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api\/remotesam/, '/api'),
   },
}
```

## 6. 使用方式

1. 顶部选择后端服务。
2. 选 `RemoteSAM` 时先上传图片，再输入问题。
3. 返回信息包括：前景像素占比、overlay、mask。

RemoteSAM 的问题建议使用英文短语，例如：`a long narrow road`。

## 7. 健康检查

- Qwen：`GET /api/health`
- RemoteSAM：`GET /api/remotesam/health`

可分别访问：

- `http://127.0.0.1:8001/api/health`
- `http://127.0.0.1:8002/api/remotesam/health`

## 8. 快速排错

- Qwen 显示未加载：检查 `MODEL_PATH` 是否存在、`transformers` 是否兼容。
- RemoteSAM 显示未加载但可用：这是懒加载正常现象，发一次推理后应变为已加载。
- RemoteSAM 路径错误：检查 `REMOTESAM_REPO_PATH` 与 `REMOTESAM_CHECKPOINT`。
- 依赖检查：运行 `python scripts/check_dependency_versions.py`。
- 前端请求失败：确认代理前缀与后端端口一致。
