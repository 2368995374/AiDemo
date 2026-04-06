"""会话与消息数据访问层（同步）"""

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.models.models import Session as SessionModel
from app.models.models import Message


# ==================== Session Repository ====================

def create_session(
    db: Session,
    title: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
) -> SessionModel:
    s = SessionModel(title=title, system_prompt=system_prompt, model_name=model_name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_sessions(db: Session) -> list[dict]:
    """返回未删除会话列表，附带 message_count"""
    stmt = (
        select(
            SessionModel,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message, Message.session_id == SessionModel.id)
        .where(SessionModel.is_deleted == False)
        .group_by(SessionModel.id)
        .order_by(SessionModel.updated_at.desc())
    )
    rows = db.execute(stmt).all()
    out = []
    for session_obj, cnt in rows:
        out.append({
            "id": session_obj.id,
            "title": session_obj.title,
            "system_prompt": session_obj.system_prompt,
            "model_name": session_obj.model_name,
            "created_at": session_obj.created_at,
            "updated_at": session_obj.updated_at,
            "message_count": cnt,
        })
    return out


def get_session_by_id(db: Session, session_id: int) -> Optional[SessionModel]:
    stmt = select(SessionModel).where(SessionModel.id == session_id, SessionModel.is_deleted == False)
    return db.execute(stmt).scalar_one_or_none()


def delete_session(db: Session, session_id: int) -> bool:
    stmt = (
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(is_deleted=True, updated_at=datetime.utcnow())
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount > 0


def touch_session(db: Session, session_id: int):
    stmt = (
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(updated_at=datetime.utcnow())
    )
    db.execute(stmt)
    db.commit()


# ==================== Message Repository ====================

def get_messages(db: Session, session_id: int) -> Sequence[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_no)
    )
    return db.execute(stmt).scalars().all()


def get_next_sequence_no(db: Session, session_id: int) -> int:
    stmt = select(func.coalesce(func.max(Message.sequence_no), 0)).where(
        Message.session_id == session_id
    )
    return db.execute(stmt).scalar() + 1


def create_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    sequence_no: int,
    token_count: Optional[int] = None,
    generation_params: Optional[dict] = None,
) -> Message:
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        sequence_no=sequence_no,
        token_count=token_count,
        generation_params=generation_params,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
