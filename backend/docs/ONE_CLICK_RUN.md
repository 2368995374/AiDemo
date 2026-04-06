# RemoteSAM 一键本地跑通（无前后端）

适用目标：只需要在一台新电脑上直接跑通 RemoteSAM 推理。

说明：

- 本文档只覆盖 `RemoteSAM` 单模型推理。
- 若你已有 `Qwen` 与 `RemoteSAM` 两套稳定环境，推荐使用双后端方案，请参考 `backend/docs/FULLSTACK_RUN.md`。

## 1. 环境建议

- GPU: RTX 3090（你的配置可用）
- Python: 3.8 或 3.10
- CUDA: 与 torch 版本匹配

## 2. 安装依赖

在 RemoteSAM 仓库环境内安装（建议单独 conda 环境）：

```powershell
cd RemoteSAM-master/RemoteSAM-master
pip install -r requirements.txt
```

如果缺少 torch / mmcv，请按 RemoteSAM 官方 README 的版本安装。

## 3. 修改脚本内路径

编辑 [backend/scripts/run_remotesam_infer.py](backend/scripts/run_remotesam_infer.py)：

- REMOTESAM_REPO_PATH
- CHECKPOINT_PATH
- IMAGE_PATH
- QUESTION

你当前 checkpoint 可以填：

```text
D:/zwy/zwyAi/models/RemoteSAMv1.pth
```

## 4. 直接运行

```powershell
cd backend
python scripts/run_remotesam_infer.py
```

输出：

- outputs/mask.png
- outputs/overlay.png

## 5. 依赖版本检查

```powershell
python scripts/check_dependency_versions.py
```

该脚本会打印 torch/fastapi/mmcv/mmdet/mmseg 等版本与 CUDA 可用性。
