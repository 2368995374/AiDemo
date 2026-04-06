"""FastAPI 路由（同步版本）"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.schemas.schemas import (
    SessionCreate, SessionOut, MessageOut,
    ChatRequest, ChatResponse, HealthResponse,
)
from app.repositories import repository as repo
from app.services import chat_service
from app.services.inference_service import inference_service
from app.services.remotesam_service import remotesam_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 健康检查 ====================

@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if inference_service.is_loaded and db_ok else "degraded",
        model_loaded=inference_service.is_loaded,
        database_connected=db_ok,
        model_name=inference_service.model_name or "N/A",
    )


# ==================== 会话 ====================

@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    rows = repo.get_sessions(db)
    return rows


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    s = repo.create_session(
        db,
        title=body.title,
        system_prompt=body.system_prompt or settings.DEFAULT_SYSTEM_PROMPT,
        model_name=inference_service.model_name,
    )
    return SessionOut(
        id=s.id,
        title=s.title,
        system_prompt=s.system_prompt,
        model_name=s.model_name,
        created_at=s.created_at,
        updated_at=s.updated_at,
        message_count=0,
    )


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    ok = repo.delete_session(db, session_id)
    if not ok:
        raise HTTPException(404, "会话不存在")
    return {"success": True}


# ==================== 消息 ====================

@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: int, db: Session = Depends(get_db)):
    session = repo.get_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(404, "会话不存在")
    msgs = repo.get_messages(db, session_id)
    return msgs


# ==================== 聊天 ====================

@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    if not inference_service.is_loaded:
        raise HTTPException(503, "模型尚未加载，请稍后重试")
    try:
        result = chat_service.chat(
            db,
            session_id=body.session_id,
            user_text=body.message,
            temperature=body.temperature,
            top_p=body.top_p,
            max_new_tokens=body.max_new_tokens,
        )
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, db: Session = Depends(get_db)):
    if not inference_service.is_loaded:
        raise HTTPException(503, "模型尚未加载，请稍后重试")

    session = repo.get_session_by_id(db, body.session_id)
    if session is None:
        raise HTTPException(404, "会话不存在")

    return StreamingResponse(
        chat_service.chat_stream(
            db,
            session_id=body.session_id,
            user_text=body.message,
            temperature=body.temperature,
            top_p=body.top_p,
            max_new_tokens=body.max_new_tokens,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== RemoteSAM 多模态 ====================

@router.get("/remotesam/health")
def remotesam_health():
    return {
        "status": "ok" if remotesam_service.is_loaded else "not_loaded",
        "model_name": remotesam_service.model_name,
        "loaded": remotesam_service.is_loaded,
    }


@router.post("/remotesam/infer")
async def remotesam_infer(
    image: UploadFile = File(...),
    question: str = Form(...),
    task: str = Form("referring_seg"),
    classnames: str = Form("airplane,vehicle"),
):
    try:
        data = await image.read()
        if not data:
            raise HTTPException(400, "图片为空")

        if task == "detection":
            parsed = [x.strip() for x in classnames.split(",") if x.strip()]
            if not parsed:
                parsed = ["airplane"]
            result = remotesam_service.infer_detection(data, parsed)
        else:
            result = remotesam_service.infer_referring_seg(data, question)

        return {
            "service": "remotesam",
            "question": question,
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RemoteSAM 推理失败")
        raise HTTPException(500, f"RemoteSAM 推理失败: {e}")
