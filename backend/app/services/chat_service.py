"""聊天编排服务：组合推理 + 数据持久化（同步版）"""

import json
from typing import Optional, Iterator, List, Dict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import repository as repo
from app.services.langchain_service import langchain_chat_service


def _build_context(
    system_prompt: str,
    history_messages,
    max_rounds: int = 10,
) -> List[Dict[str, str]]:
    """将数据库消息记录转为 Transformers messages 格式"""
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]
    pairs = []
    for m in history_messages:
        if m.role in ("user", "assistant"):
            pairs.append({"role": m.role, "content": m.content})
    if len(pairs) > max_rounds * 2:
        pairs = pairs[-(max_rounds * 2):]
    messages.extend(pairs)
    return messages


def chat(
    db: Session,
    session_id: int,
    user_text: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
) -> dict:
    """非流式聊天"""
    session = repo.get_session_by_id(db, session_id)
    if session is None:
        raise ValueError(f"会话 {session_id} 不存在")

    system_prompt = session.system_prompt or settings.DEFAULT_SYSTEM_PROMPT
    history = repo.get_messages(db, session_id)
    seq = repo.get_next_sequence_no(db, session_id)

    user_msg = repo.create_message(db, session_id, "user", user_text, seq)
    context = _build_context(system_prompt, list(history) + [user_msg])

    reply, langchain_meta = langchain_chat_service.generate_reply(
        context,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    assistant_msg = repo.create_message(
        db, session_id, "assistant", reply, seq + 1,
        generation_params={
            "temperature": temperature or settings.DEFAULT_TEMPERATURE,
            "top_p": top_p or settings.DEFAULT_TOP_P,
            "max_new_tokens": max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS,
            "langchain": langchain_meta,
        },
    )

    repo.touch_session(db, session_id)

    return {
        "session_id": session_id,
        "user_message_id": user_msg.id,
        "assistant_message_id": assistant_msg.id,
        "reply": reply,
    }


def chat_stream(
    db: Session,
    session_id: int,
    user_text: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_new_tokens: Optional[int] = None,
) -> Iterator[str]:
    """流式聊天"""
    session = repo.get_session_by_id(db, session_id)
    if session is None:
        yield f"data: {json.dumps({'type': 'error', 'content': '会话不存在'})}\n\n"
        return

    system_prompt = session.system_prompt or settings.DEFAULT_SYSTEM_PROMPT
    history = repo.get_messages(db, session_id)
    seq = repo.get_next_sequence_no(db, session_id)

    user_msg = repo.create_message(db, session_id, "user", user_text, seq)
    context = _build_context(system_prompt, list(history) + [user_msg])

    yield f"data: {json.dumps({'type': 'start', 'user_message_id': user_msg.id})}\n\n"

    full_reply = ""
    token_iterator, langchain_meta = langchain_chat_service.stream_reply(
        context,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    for token in token_iterator:
        full_reply += token
        yield f"data: {json.dumps({'type': 'delta', 'content': token})}\n\n"

    assistant_msg = repo.create_message(
        db, session_id, "assistant", full_reply, seq + 1,
        generation_params={
            "temperature": temperature or settings.DEFAULT_TEMPERATURE,
            "top_p": top_p or settings.DEFAULT_TOP_P,
            "max_new_tokens": max_new_tokens or settings.DEFAULT_MAX_NEW_TOKENS,
            "langchain": langchain_meta,
        },
    )

    repo.touch_session(db, session_id)

    yield f"data: {json.dumps({'type': 'end', 'assistant_message_id': assistant_msg.id})}\n\n"
    yield "data: [DONE]\n\n"
