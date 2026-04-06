"""LangChain 编排服务：LCEL + 工具路由 + 本地 Qwen 适配。"""

from __future__ import annotations

import ast
import operator
import re
from datetime import datetime
from typing import Dict, Iterator, List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableBranch, RunnableLambda
from langchain_core.tools import tool

from app.core.config import settings
from app.services.inference_service import inference_service
from app.services.knowledge_base_service import knowledge_base_service


_ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


@tool("current_time")
def current_time_tool(timezone_name: str = "Asia/Shanghai") -> str:
    """获取指定时区的当前时间。"""
    tz_name = timezone_name or settings.LANGCHAIN_DEFAULT_TIMEZONE
    if ZoneInfo is None:
        now = datetime.now().astimezone()
    else:
        now = datetime.now(ZoneInfo(tz_name))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")


@tool("calculator")
def calculator_tool(expression: str) -> str:
    """安全计算简单数学表达式，仅支持 + - * / // % ** 和括号。"""
    expr = (expression or "").strip()
    if not expr:
        return "计算失败：未提供表达式"

    try:
        value = _safe_eval_expression(expr)
    except Exception as exc:  # noqa: BLE001
        return f"计算失败：{exc}"

    if float(value).is_integer():
        value_text = str(int(value))
    else:
        value_text = f"{value:.8f}".rstrip("0").rstrip(".")
    return f"{expr} = {value_text}"


def _safe_eval_expression(expression: str) -> float:
    if len(expression) > 120:
        raise ValueError("表达式过长")

    tree = ast.parse(expression, mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_BINARY_OPERATORS:
                raise ValueError("包含不支持的运算符")
            left = _eval(node.left)
            right = _eval(node.right)
            return float(_ALLOWED_BINARY_OPERATORS[op_type](left, right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_UNARY_OPERATORS:
                raise ValueError("包含不支持的一元运算")
            operand = _eval(node.operand)
            return float(_ALLOWED_UNARY_OPERATORS[op_type](operand))
        raise ValueError("表达式包含不安全或不支持的语法")

    return _eval(tree)


class LangChainChatService:
    """使用 LangChain 编排对话与工具调用。"""

    def __init__(self):
        self._answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                MessagesPlaceholder("history"),
                (
                    "system",
                    "你运行在一个 LangChain 编排链路中。"
                    "如果下方提供了工具结果，优先使用该结果进行回答；"
                    "如果工具结果为空，则正常回答。\n\n"
                    "工具结果：\n{tool_result}",
                ),
                (
                    "system",
                    "如果下方提供了知识库检索片段，请优先基于这些片段回答，"
                    "并在回答中用自然语言简要说明依据来源；"
                    "如果知识库片段为空，则基于通用能力回答。\n\n"
                    "知识库检索结果：\n{kb_context}",
                ),
                ("human", "{user_input}"),
            ]
        )

        self._tool_router = RunnableLambda(self._route_tool)
        self._tool_runner = RunnableBranch(
            (lambda x: x["tool_name"] == "current_time", RunnableLambda(self._run_current_time_tool)),
            (lambda x: x["tool_name"] == "calculator", RunnableLambda(self._run_calculator_tool)),
            RunnableLambda(self._skip_tool),
        )
        self._prompt_chain = RunnableLambda(self._render_prompt) | RunnableLambda(
            self._prompt_to_generation_payload
        )

    def generate_reply(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> tuple[str, dict]:
        """非流式回复，返回 (reply, metadata)。"""
        payload = self._prepare_payload(
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        reply = inference_service.generate_reply(
            payload["messages"],
            max_new_tokens=payload["max_new_tokens"],
            temperature=payload["temperature"],
            top_p=payload["top_p"],
        )
        return reply, payload["metadata"]

    def stream_reply(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> tuple[Iterator[str], dict]:
        """流式回复，返回 (token_iterator, metadata)。"""
        payload = self._prepare_payload(
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        def _generator() -> Iterator[str]:
            for token in inference_service.stream_reply(
                payload["messages"],
                max_new_tokens=payload["max_new_tokens"],
                temperature=payload["temperature"],
                top_p=payload["top_p"],
            ):
                yield token

        return _generator(), payload["metadata"]

    def _prepare_payload(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int],
        temperature: Optional[float],
        top_p: Optional[float],
    ) -> dict:
        if not settings.LANGCHAIN_ENABLED:
            return {
                "messages": messages,
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "metadata": {
                    "langchain_enabled": False,
                    "tool_used": False,
                    "tool_name": "none",
                    "rag_used": False,
                    "rag_hits": 0,
                    "rag_sources": [],
                },
            }

        system_prompt, history, user_input = self._split_context(messages)
        tool_event = self._resolve_tool_event(user_input)
        kb_result = knowledge_base_service.retrieve(
            user_input,
            top_k=settings.RAG_TOP_K,
            score_threshold=settings.RAG_SCORE_THRESHOLD,
        )

        chain_input = {
            "system_prompt": system_prompt,
            "history": history,
            "user_input": user_input,
            "tool_result": self._format_tool_result(tool_event),
            "kb_context": kb_result.context,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "tool_event": tool_event,
            "kb_result": {
                "used": kb_result.used,
                "hits": kb_result.hits,
                "sources": kb_result.sources,
                "error": kb_result.error,
            },
        }
        prepared = self._prompt_chain.invoke(chain_input)
        return prepared

    def _split_context(self, messages: List[Dict[str, str]]) -> tuple[str, List[tuple[str, str]], str]:
        system_prompt = settings.DEFAULT_SYSTEM_PROMPT
        dialogue: List[Dict[str, str]] = []

        for message in messages:
            role = (message.get("role") or "").strip().lower()
            content = (message.get("content") or "").strip()
            if not content:
                continue

            if role == "system":
                system_prompt = content
                continue
            if role in {"user", "assistant"}:
                dialogue.append({"role": role, "content": content})

        user_input = ""
        if dialogue and dialogue[-1]["role"] == "user":
            user_input = dialogue[-1]["content"]
            dialogue = dialogue[:-1]

        if not user_input and dialogue:
            user_input = dialogue[-1]["content"]
            dialogue = dialogue[:-1]

        if settings.LANGCHAIN_MAX_HISTORY_ROUNDS > 0:
            max_history_size = settings.LANGCHAIN_MAX_HISTORY_ROUNDS * 2
            dialogue = dialogue[-max_history_size:]

        history: List[tuple[str, str]] = []
        for item in dialogue:
            if item["role"] == "user":
                history.append(("human", item["content"]))
            elif item["role"] == "assistant":
                history.append(("ai", item["content"]))

        return system_prompt, history, user_input

    def _resolve_tool_event(self, user_input: str) -> dict:
        if not settings.LANGCHAIN_ENABLE_TOOLS:
            return self._skip_tool({})
        routed = self._tool_router.invoke({"user_input": user_input})
        return self._tool_runner.invoke(routed)

    def _route_tool(self, payload: dict) -> dict:
        user_input = (payload.get("user_input") or "").strip()
        lowered = user_input.lower()

        expr = self._extract_math_expression(user_input)
        if expr:
            return {"tool_name": "calculator", "tool_input": expr}

        time_keywords = (
            "现在几点",
            "当前时间",
            "当前日期",
            "日期",
            "星期几",
            "time",
            "date",
            "now",
        )
        if any(keyword in lowered for keyword in time_keywords):
            return {
                "tool_name": "current_time",
                "tool_input": settings.LANGCHAIN_DEFAULT_TIMEZONE,
            }

        return {"tool_name": "none", "tool_input": ""}

    def _run_current_time_tool(self, payload: dict) -> dict:
        timezone_name = payload.get("tool_input") or settings.LANGCHAIN_DEFAULT_TIMEZONE
        result = current_time_tool.invoke({"timezone_name": timezone_name})
        return {
            "tool_name": "current_time",
            "tool_input": timezone_name,
            "tool_result": result,
            "tool_used": True,
        }

    def _run_calculator_tool(self, payload: dict) -> dict:
        expression = payload.get("tool_input") or ""
        result = calculator_tool.invoke({"expression": expression})
        return {
            "tool_name": "calculator",
            "tool_input": expression,
            "tool_result": result,
            "tool_used": True,
        }

    @staticmethod
    def _skip_tool(_: dict) -> dict:
        return {
            "tool_name": "none",
            "tool_input": "",
            "tool_result": "",
            "tool_used": False,
        }

    @staticmethod
    def _extract_math_expression(user_input: str) -> str:
        expression_candidates = re.findall(r"[0-9\s\+\-\*\/\(\)\.%]{3,}", user_input)
        for candidate in sorted(expression_candidates, key=len, reverse=True):
            expr = candidate.strip()
            has_number = any(ch.isdigit() for ch in expr)
            has_operator = any(op in expr for op in ["+", "-", "*", "/", "%"])
            if has_number and has_operator:
                return expr
        return ""

    @staticmethod
    def _format_tool_result(tool_event: dict) -> str:
        if not tool_event.get("tool_used"):
            return ""
        return (
            f"tool_name: {tool_event.get('tool_name', 'none')}\n"
            f"tool_input: {tool_event.get('tool_input', '')}\n"
            f"tool_output: {tool_event.get('tool_result', '')}"
        )

    def _render_prompt(self, payload: dict) -> dict:
        prompt_value = self._answer_prompt.invoke(
            {
                "system_prompt": payload["system_prompt"],
                "history": payload["history"],
                "tool_result": payload["tool_result"],
                "kb_context": payload["kb_context"],
                "user_input": payload["user_input"],
            }
        )
        return {
            **payload,
            "prompt_value": prompt_value,
        }

    def _prompt_to_generation_payload(self, payload: dict) -> dict:
        qwen_messages: List[Dict[str, str]] = []
        for message in payload["prompt_value"].messages:
            if message.type == "system":
                role = "system"
            elif message.type == "human":
                role = "user"
            elif message.type == "ai":
                role = "assistant"
            else:
                continue
            qwen_messages.append({"role": role, "content": message.content})

        tool_event = payload.get("tool_event", {})
        kb_result = payload.get("kb_result", {})
        metadata = {
            "langchain_enabled": True,
            "tool_used": bool(tool_event.get("tool_used")),
            "tool_name": tool_event.get("tool_name", "none"),
            "tool_input": tool_event.get("tool_input", ""),
            "tool_result": tool_event.get("tool_result", "")[:300],
            "rag_used": bool(kb_result.get("used")),
            "rag_hits": int(kb_result.get("hits", 0)),
            "rag_sources": kb_result.get("sources", [])[:5],
            "rag_error": kb_result.get("error", ""),
        }

        return {
            "messages": qwen_messages,
            "max_new_tokens": payload.get("max_new_tokens"),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "metadata": metadata,
        }


langchain_chat_service = LangChainChatService()
