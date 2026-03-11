"""
Chat MongoDB 持久化

两张集合：chat_sessions（会话元数据）、chat_messages（消息记录）
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.models import Session, ChatMessage, SessionStatus


# ==================== Session 表 ====================


def _session_to_doc(s: Session) -> Dict[str, Any]:
    return {
        "_id": s.id,
        "user_id": s.user_id,
        "title": s.title,
        "system_prompt": s.system_prompt,
        "use_tools": s.use_tools,
        "status": s.status,
        "message_count": s.message_count,
        "total_input_tokens": s.total_input_tokens,
        "total_output_tokens": s.total_output_tokens,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "metadata": s.metadata or {},
    }


def _doc_to_session(doc: Dict[str, Any]) -> Session:
    return Session(
        id=str(doc.get("_id", "")),
        user_id=doc.get("user_id", ""),
        title=doc.get("title", ""),
        system_prompt=doc.get("system_prompt", ""),
        use_tools=doc.get("use_tools", False),
        status=doc.get("status", SessionStatus.ACTIVE),
        message_count=doc.get("message_count", 0),
        total_input_tokens=doc.get("total_input_tokens", 0),
        total_output_tokens=doc.get("total_output_tokens", 0),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        metadata=doc.get("metadata") or {},
    )


async def save_session(db: Any, collection: str, session: Session) -> bool:
    doc = _session_to_doc(session)
    await db[collection].replace_one({"_id": session.id}, doc, upsert=True)
    return True


async def load_session(db: Any, collection: str, session_id: str) -> Optional[Session]:
    doc = await db[collection].find_one({"_id": session_id})
    if not doc:
        return None
    return _doc_to_session(doc)


async def update_session(db: Any, collection: str, session: Session) -> bool:
    session.updated_at = datetime.utcnow()
    doc = _session_to_doc(session)
    res = await db[collection].replace_one({"_id": session.id}, doc)
    return res.matched_count > 0


async def delete_session(db: Any, collection: str, session_id: str) -> bool:
    res = await db[collection].delete_one({"_id": session_id})
    return res.deleted_count > 0


async def list_sessions(
    db: Any,
    collection: str,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Session]:
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    cursor = (
        db[collection]
        .find(query)
        .sort("updated_at", -1)
        .skip(offset)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [_doc_to_session(d) for d in docs]


# ==================== Message 表 ====================


def _message_to_doc(m: ChatMessage) -> Dict[str, Any]:
    doc = {
        "_id": m.id,
        "session_id": m.session_id,
        "role": m.role,
        "content": m.content,
        "tool_calls": m.tool_calls or [],
        "token_count": m.token_count,
        "seq": m.seq,
        "created_at": m.created_at,
    }
    # raw_content 可能包含 Anthropic SDK 对象，需要序列化
    if m.raw_content is not None:
        doc["raw_content"] = _serialize_raw_content(m.raw_content)
    return doc


def _serialize_raw_content(raw: list) -> list:
    """将 Anthropic SDK content blocks 序列化为可存储的 dict 列表"""
    result = []
    for block in raw:
        if isinstance(block, dict):
            result.append(block)
        elif hasattr(block, "model_dump"):
            result.append(block.model_dump())
        elif hasattr(block, "__dict__"):
            result.append({"type": getattr(block, "type", "unknown"), **block.__dict__})
        else:
            result.append({"type": "text", "text": str(block)})
    return result


def _doc_to_message(doc: Dict[str, Any]) -> ChatMessage:
    return ChatMessage(
        id=str(doc.get("_id", "")),
        session_id=doc.get("session_id", ""),
        role=doc.get("role", "user"),
        content=doc.get("content", ""),
        raw_content=doc.get("raw_content"),
        tool_calls=doc.get("tool_calls") or [],
        token_count=doc.get("token_count", 0),
        seq=doc.get("seq", 0),
        created_at=doc.get("created_at"),
    )


async def save_message(db: Any, collection: str, message: ChatMessage) -> bool:
    doc = _message_to_doc(message)
    await db[collection].replace_one({"_id": message.id}, doc, upsert=True)
    return True


async def load_messages(
    db: Any,
    collection: str,
    session_id: str,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[ChatMessage]:
    """按 seq 升序加载消息"""
    cursor = (
        db[collection]
        .find({"session_id": session_id})
        .sort("seq", 1)
        .skip(offset)
    )
    if limit:
        cursor = cursor.limit(limit)
    docs = await cursor.to_list(length=limit or 10000)
    return [_doc_to_message(d) for d in docs]


async def delete_messages_by_session(db: Any, collection: str, session_id: str) -> int:
    res = await db[collection].delete_many({"session_id": session_id})
    return res.deleted_count


async def get_message_count(db: Any, collection: str, session_id: str) -> int:
    return await db[collection].count_documents({"session_id": session_id})
