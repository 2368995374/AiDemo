"""RemoteSAM 直接推理示例（无需前后端）

使用前只改下方 4 个配置项：
1. REMOTESAM_REPO_PATH
2. CHECKPOINT_PATH
3. IMAGE_PATH
4. QUESTION
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import cv2
import numpy as np

# ====== 在这里改成你自己的路径 ======
REMOTESAM_REPO_PATH = r"D:\zwy\zwyAi\RemoteSAM-master/RemoteSAM-master"
CHECKPOINT_PATH = r"D:/zwy/zwyAi/models/RemoteSAMv1.pth"
IMAGE_PATH = r"D:\zwy\data\过程数据\浅层滑坡训练_voc\JPEGImages\tile_00010_00075.png"
QUESTION = "Circle the road, the road should be narrow and long"
DEVICE = "cuda:0"
USE_EPOC = False
# ==================================


def ensure_path(path: str, name: str):
    if not Path(path).exists():
        raise FileNotFoundError(f"{name} 不存在: {path}")


def make_overlay(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    overlay = image_rgb.copy()
    overlay[mask > 0] = [255, 64, 64]
    return cv2.addWeighted(image_rgb, 0.65, overlay, 0.35, 0)


def load_image_bgr(image_path: str) -> np.ndarray:
    """Unicode-safe OpenCV image loader for Windows paths.

    cv2.imread can fail on non-ASCII paths on some Windows/OpenCV builds.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"IMAGE_PATH 不存在: {image_path}")

    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(
            f"无法读取影像: {image_path}。请检查文件是否损坏，或扩展名与真实格式是否一致。"
        )
    return image


def main():
    ensure_path(REMOTESAM_REPO_PATH, "REMOTESAM_REPO_PATH")
    ensure_path(CHECKPOINT_PATH, "CHECKPOINT_PATH")
    ensure_path(IMAGE_PATH, "IMAGE_PATH")

    if REMOTESAM_REPO_PATH not in sys.path:
        sys.path.insert(0, REMOTESAM_REPO_PATH)

    from tasks.code.model import RemoteSAM, init_demo_model

    print("[1/4] 加载模型...")
    core = init_demo_model(CHECKPOINT_PATH, DEVICE)
    model = RemoteSAM(core, DEVICE, use_EPOC=USE_EPOC)

    print("[2/4] 读取影像...")
    image_bgr = load_image_bgr(IMAGE_PATH)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    print("[3/4] 执行 referring_seg 推理...")
    mask = model.referring_seg(image=image_rgb, sentence=QUESTION)

    print("[4/4] 保存结果...")
    out_dir = Path("./outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    mask_path = out_dir / "mask.png"
    overlay_path = out_dir / "overlay.png"

    cv2.imwrite(str(mask_path), (mask * 255).astype(np.uint8))
    overlay_bgr = cv2.cvtColor(make_overlay(image_rgb, mask), cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(overlay_path), overlay_bgr)

    pos = int((mask > 0).sum())
    ratio = pos / max(int(mask.size), 1)

    print(f"前景像素占比: {ratio:.4f} ({pos}/{int(mask.size)})")
    print(f"mask 输出: {mask_path.resolve()}")
    print(f"overlay 输出: {overlay_path.resolve()}")


if __name__ == "__main__":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    main()
