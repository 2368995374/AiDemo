"""Qwen 本地推理服务（单例）"""

import os
import logging
from typing import Iterator, List, Dict, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_dtype(dtype: str):
    dtype = (dtype or "auto").lower()
    if dtype == "auto":
        return "auto"
    if dtype in {"fp16", "float16"}:
        return torch.float16
    if dtype in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if dtype in {"fp32", "float32"}:
        return torch.float32
    raise ValueError(f"Unsupported dtype: {dtype}")


class QwenInferenceService:
    """管理模型单例，提供同步/流式推理"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name: str = ""
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load_model(self):
        model_path = settings.MODEL_PATH
        if not model_path:
            logger.error("MODEL_PATH 未配置，无法加载模型")
            return

        # 将路径转换为绝对路径，确保被识别为本地路径
        from pathlib import Path
        model_path = str(Path(model_path).resolve())
        
        if not Path(model_path).exists():
            logger.error(f"模型路径不存在: {model_path}")
            return

        offline = settings.MODEL_OFFLINE
        if offline:
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        dtype = _parse_dtype(settings.MODEL_DTYPE)

        logger.info(f"正在加载 tokenizer: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=True
        )

        logger.info(f"正在加载模型: {model_path}")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=dtype,
            device_map=settings.MODEL_DEVICE_MAP,
            local_files_only=True,
            trust_remote_code=True,
        ).eval()

        self.model_name = os.path.basename(model_path)
        self._loaded = True
        logger.info(f"模型加载完成: {self.model_name}")

    def generate_reply(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """非流式生成完整回复"""
        if not self._loaded:
            raise RuntimeError("模型尚未加载")

        max_new_tokens = max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS
        temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else settings.DEFAULT_TOP_P

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt")
        model_inputs = {k: v.to(self.model.device) for k, v in model_inputs.items()}

        do_sample = temperature > 0
        gen_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
        )

        gen_only = gen_ids[0, model_inputs["input_ids"].shape[1]:]
        reply = self.tokenizer.decode(gen_only, skip_special_tokens=True).strip()
        return reply

    def stream_reply(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> Iterator[str]:
        """流式生成：通过 TextIteratorStreamer 逐 token 输出"""
        if not self._loaded:
            raise RuntimeError("模型尚未加载")

        max_new_tokens = max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS
        temperature = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
        top_p = top_p if top_p is not None else settings.DEFAULT_TOP_P

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt")
        model_inputs = {k: v.to(self.model.device) for k, v in model_inputs.items()}

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )

        do_sample = temperature > 0
        gen_kwargs = {
            **model_inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "temperature": temperature if do_sample else None,
            "top_p": top_p if do_sample else None,
            "streamer": streamer,
        }

        thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
        thread.start()

        for token_text in streamer:
            if token_text:
                yield token_text

        thread.join()


# 全局单例
inference_service = QwenInferenceService()
