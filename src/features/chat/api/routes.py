"""
Chat HTTP API
"""

from dataclasses import asdict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.mongodb import get_database
from ..services.service import ChatService, create_chat_service
from features.auth.api.deps import get_current_user
from features.auth.models.models import User


chat_router = APIRouter(prefix="/chat", tags=["Chat"])


# ==================== 依赖注入 ====================


def _get_chat_service() -> ChatService:
    db = get_database()
    return create_chat_service(db)


# ==================== 请求/响应模型 ====================


class CreateSessionRequest(BaseModel):
    title: str = ""
    system_prompt: str = ""
    prompt_name: str = Field(default="", description="预定义 prompt 模板名称，优先级低于 system_prompt")
    prompt_vars: Dict[str, Any] = Field(default_factory=dict, description="prompt 模板变量")
    use_tools: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    use_tools: Optional[bool] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="消息内容")
    stream: bool = Field(default=False, description="是否使用 SSE 流式输出")


class MessageResponse(BaseModel):
    content: str
    tool_calls: List[Dict[str, Any]] = []
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0


# ==================== Session 端点 ====================


@chat_router.post("/sessions", summary="Create chat session")
async def create_session(
    req: CreateSessionRequest,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    session = await service.create_session(
        title=req.title,
        system_prompt=req.system_prompt,
        prompt_name=req.prompt_name,
        prompt_vars=req.prompt_vars,
        use_tools=req.use_tools,
        user_id=user.id,
        metadata=req.metadata,
    )
    return _session_to_dict(session)


@chat_router.get("/sessions", summary="List chat sessions")
async def list_sessions(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    sessions = await service.list_sessions(user_id=user.id, status=status, limit=limit, offset=offset)
    return {
        "sessions": [_session_to_dict(s) for s in sessions],
        "count": len(sessions),
    }


@chat_router.get("/sessions/{session_id}", summary="Get chat session")
async def get_session(
    session_id: str,
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_dict(session)


@chat_router.patch("/sessions/{session_id}", summary="Update session settings")
async def update_session(
    session_id: str,
    req: UpdateSessionRequest,
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    session = await service.update_session_settings(
        session_id,
        title=req.title,
        system_prompt=req.system_prompt,
        use_tools=req.use_tools,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_dict(session)


@chat_router.delete("/sessions/{session_id}", summary="Delete chat session")
async def delete_session(
    session_id: str,
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    ok = await service.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


# ==================== Message 端点 ====================


@chat_router.post(
    "/sessions/{session_id}/messages",
    summary="Send message",
)
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    service: ChatService = Depends(_get_chat_service),
):
    """
    发送消息

    stream=false: 等待完整响应后返回 JSON
    stream=true: SSE 流式输出（Content-Type: text/event-stream）
    """
    if req.stream:
        return StreamingResponse(
            service.send_message_stream(session_id, req.content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        resp = await service.send_message(session_id, req.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    tool_calls_data = [
        {"id": tc.id, "name": tc.name, "input": tc.input}
        for tc in resp.tool_calls_history
    ]
    return MessageResponse(
        content=resp.content,
        tool_calls=tool_calls_data,
        stop_reason=resp.stop_reason,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
    )


@chat_router.get(
    "/sessions/{session_id}/messages",
    summary="Get message history",
)
async def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    service: ChatService = Depends(_get_chat_service),
) -> dict:
    messages = await service.get_messages(session_id, limit=limit, offset=offset)
    return {
        "messages": [_message_to_dict(m) for m in messages],
        "count": len(messages),
    }


# ==================== 工具方法 ====================


def _session_to_dict(session) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "system_prompt": session.system_prompt,
        "use_tools": session.use_tools,
        "status": session.status,
        "message_count": session.message_count,
        "total_input_tokens": session.total_input_tokens,
        "total_output_tokens": session.total_output_tokens,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "metadata": session.metadata,
    }


def _message_to_dict(msg) -> dict:
    return {
        "id": msg.id,
        "session_id": msg.session_id,
        "role": msg.role,
        "content": msg.content,
        "tool_calls": msg.tool_calls or [],
        "token_count": msg.token_count,
        "seq": msg.seq,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
