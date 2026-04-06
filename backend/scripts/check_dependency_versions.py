"""检查 RemoteSAM + 后端运行所需依赖版本。"""

from __future__ import annotations

import importlib
import platform
import sys
from typing import Dict


REQUIRED: Dict[str, str] = {
    "python": "3.8+ (推荐 3.10)",
    "torch": "1.13.0+ (3090 推荐 CUDA 11.8/12.x 对应轮子)",
    "torchvision": "与 torch 匹配",
    "fastapi": "0.115+",
    "uvicorn": "0.30+",
    "numpy": "1.24+",
    "PIL": "10.0+",
    "cv2": "4.8+",
    "transformers": "4.30.2+",
    "mmcv": "1.7.1 (RemoteSAM 官方建议)",
    "mmseg": "0.17.0",
    "mmdet": "2.x",
}


def get_version(module_name: str) -> str:
    try:
        module = importlib.import_module(module_name)
        return getattr(module, "__version__", "unknown")
    except Exception as exc:
        return f"NOT INSTALLED ({exc.__class__.__name__})"


def main():
    print("=== 系统信息 ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")

    checks = {
        "torch": "torch",
        "torchvision": "torchvision",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "numpy": "numpy",
        "PIL": "PIL",
        "cv2": "cv2",
        "transformers": "transformers",
        "mmcv": "mmcv",
        "mmseg": "mmseg",
        "mmdet": "mmdet",
    }

    print("\n=== 依赖版本 ===")
    for name, import_name in checks.items():
        print(f"{name:12s} -> {get_version(import_name)}")

    try:
        import torch

        print("\n=== CUDA 信息 ===")
        print(f"CUDA available: {torch.cuda.is_available()}")
        print(f"CUDA version:   {torch.version.cuda}")
        if torch.cuda.is_available():
            print(f"GPU count:      {torch.cuda.device_count()}")
            print(f"GPU[0]:         {torch.cuda.get_device_name(0)}")
    except Exception as exc:
        print(f"\nCUDA 检查失败: {exc}")

    print("\n=== 推荐版本基线 ===")
    for name, expected in REQUIRED.items():
        print(f"{name:12s} -> {expected}")


if __name__ == "__main__":
    main()
