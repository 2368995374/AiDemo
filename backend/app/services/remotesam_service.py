"""RemoteSAM 本地推理服务（单例，懒加载）"""

from __future__ import annotations

import base64
import io
import logging
import sys
from pathlib import Path
from threading import Lock
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class RemoteSAMService:
    def __init__(self):
        self._model = None
        self._loaded = False
        self._lock = Lock()
        self.model_name = "RemoteSAM"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _resolve_repo_path(self) -> Path:
        if settings.REMOTESAM_REPO_PATH:
            return Path(settings.REMOTESAM_REPO_PATH).resolve()
        backend_root = Path(__file__).resolve().parents[2]
        return (backend_root.parent / "RemoteSAM-master" / "RemoteSAM-master").resolve()

    def load_model(self):
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return

            checkpoint = Path(settings.REMOTESAM_CHECKPOINT).resolve() if settings.REMOTESAM_CHECKPOINT else None
            if not checkpoint or not checkpoint.exists():
                raise FileNotFoundError(
                    "未找到 REMOTESAM_CHECKPOINT，请在 backend/.env 配置有效权重路径"
                )

            repo_path = self._resolve_repo_path()
            if not repo_path.exists():
                raise FileNotFoundError(f"RemoteSAM 仓库路径不存在: {repo_path}")

            if str(repo_path) not in sys.path:
                sys.path.insert(0, str(repo_path))

            from tasks.code.model import RemoteSAM, init_demo_model  # pylint: disable=import-outside-toplevel

            logger.info("加载 RemoteSAM 模型中... checkpoint=%s", checkpoint)
            core = init_demo_model(str(checkpoint), settings.REMOTESAM_DEVICE)
            self._model = RemoteSAM(
                core,
                settings.REMOTESAM_DEVICE,
                use_EPOC=settings.REMOTESAM_USE_EPOC,
            )
            self._loaded = True
            logger.info("RemoteSAM 模型加载完成")

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.asarray(pil)

    @staticmethod
    def _to_png_base64(image_np: np.ndarray) -> str:
        ok, buffer = cv2.imencode(".png", cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
        if not ok:
            raise RuntimeError("PNG 编码失败")
        return base64.b64encode(buffer.tobytes()).decode("utf-8")

    @staticmethod
    def _make_overlay(image_np: np.ndarray, mask_np: np.ndarray) -> np.ndarray:
        mask_u8 = (mask_np > 0).astype(np.uint8)
        overlay = image_np.copy()
        overlay[mask_u8 == 1] = [255, 64, 64]
        mixed = cv2.addWeighted(image_np, 0.65, overlay, 0.35, 0)
        return mixed

    def infer_referring_seg(self, image_bytes: bytes, question: str) -> Dict:
        self.load_model()
        image = self._decode_image(image_bytes)

        mask = self._model.referring_seg(image=image, sentence=question)
        overlay = self._make_overlay(image, mask)

        pos = int((mask > 0).sum())
        total = int(mask.size)
        ratio = pos / max(total, 1)

        return {
            "task": "referring_seg",
            "answer": f"前景像素占比: {ratio:.4f} ({pos}/{total})",
            "mask_png_base64": self._to_png_base64((mask * 255).astype(np.uint8).repeat(3).reshape(mask.shape[0], mask.shape[1], 3)),
            "overlay_png_base64": self._to_png_base64(overlay),
        }

    def infer_detection(self, image_bytes: bytes, classnames: List[str]) -> Dict:
        self.load_model()
        image = self._decode_image(image_bytes)
        result = self._model.detection(image=image, classnames=classnames)

        summary = []
        for name in classnames:
            boxes = result.get(name) or []
            summary.append(f"{name}: {len(boxes)}")

        return {
            "task": "detection",
            "answer": "检测结果数量 -> " + ", ".join(summary),
            "boxes": result,
        }


remotesam_service = RemoteSAMService()
