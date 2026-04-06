"""Pydantic 请求/响应模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---- 会话 ----
class SessionCreate(BaseModel):
    title: str = "新会话"
    system_prompt: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    title: str
    system_prompt: Optional[str] = None
    model_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


# ---- 消息 ----
class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    sequence_no: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---- 聊天 ----
class ChatRequest(BaseModel):
    session_id: int
    message: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_new_tokens: Optional[int] = None
    stream: bool = False


class ChatResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    reply: str


# ---- 健康检查 ----
class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool
    model_name: str
