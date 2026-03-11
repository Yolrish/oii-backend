"""
Chat 对话服务

整合 SessionManager + ClaudeService，提供完整的对话流程：
- session 级别的上下文管理
- 自动 token 截断
- tool calling 支持
- SSE 流式输出
"""

import json
from dataclasses import asdict
from typing import Any, AsyncIterator, Dict, List, Optional

from ..configs.config import ChatConfig
from ..models.models import Session, ChatMessage
from .session import SessionManager

from packages.claude import ClaudeConfig, ClaudeService, create_claude_service
from packages.claude.models.messages import ChatResponse


class ChatService:
    """
    Chat 对话服务

    使用方式（HTTP API）：
        service = create_chat_service(db)
        session = await service.create_session(title="新对话")
        resp = await service.send_message(session.id, "你好")

    使用方式（内部调用）：
        resp = await service.send_message(session_id, "帮我处理视频")
    """

    def __init__(
        self,
        db: Any,
        chat_config: Optional[ChatConfig] = None,
        claude_config: Optional[ClaudeConfig] = None,
    ):
        self.config = chat_config or ChatConfig.from_env()
        self.session_mgr = SessionManager(db, self.config)
        self.claude = create_claude_service(claude_config)

    # ==================== Session 代理方法 ====================

    async def create_session(
        self,
        title: str = "",
        system_prompt: str = "",
        prompt_name: str = "",
        prompt_vars: Optional[Dict[str, Any]] = None,
        use_tools: bool = False,
        user_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        创建会话

        system prompt 组装：[安全底线] + [业务 prompt]
        业务 prompt 优先级：system_prompt 直接传入 > prompt_name 渲染
        """
        from features.prompt import create_prompt_service
        prompt_svc = create_prompt_service(self.session_mgr.db)
        resolved_prompt = await prompt_svc.build_system_prompt(
            prompt_name=prompt_name,
            prompt_vars=prompt_vars,
            raw_system_prompt=system_prompt,
        )
        return await self.session_mgr.create_session(
            title=title,
            system_prompt=resolved_prompt,
            use_tools=use_tools,
            user_id=user_id,
            metadata=metadata,
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        return await self.session_mgr.get_session(session_id)

    async def list_sessions(
        self, user_id: Optional[str] = None, status: Optional[str] = None,
        limit: int = 20, offset: int = 0,
    ) -> List[Session]:
        return await self.session_mgr.list_sessions(
            user_id=user_id, status=status, limit=limit, offset=offset,
        )

    async def update_session_settings(
        self,
        session_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None,
        use_tools: Optional[bool] = None,
    ) -> Optional[Session]:
        """更新会话设置"""
        session = await self.session_mgr.get_session(session_id)
        if not session:
            return None
        if title is not None:
            session.title = title
        if system_prompt is not None:
            session.system_prompt = system_prompt
        if use_tools is not None:
            session.use_tools = use_tools
        await self.session_mgr.update_session(session)
        return session

    async def archive_session(self, session_id: str) -> bool:
        return await self.session_mgr.archive_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        return await self.session_mgr.delete_session(session_id)

    async def get_messages(
        self, session_id: str, limit: int = 20, offset: int = 0,
    ) -> List[ChatMessage]:
        return await self.session_mgr.get_messages_paginated(
            session_id, limit=limit, offset=offset,
        )

    # ==================== 核心对话 ====================

    async def send_message(
        self,
        session_id: str,
        content: str,
    ) -> ChatResponse:
        """
        发送消息并获取回复

        流程：
        1. 获取 session
        2. 加载历史消息（缓存优先）
        3. 追加 user 消息
        4. token 截断
        5. 调用 Claude（含 tool calling 循环）
        6. 保存 assistant 消息
        7. 更新 session token 统计
        """
        session = await self.session_mgr.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # 1. 加载历史消息
        history = await self.session_mgr.get_messages(session_id)

        # 2. 创建并保存 user 消息
        user_msg = ChatMessage(
            role="user",
            content=content,
            token_count=self._estimate_tokens(content),
        )
        await self.session_mgr.append_message(session, user_msg)

        # 3. 构建发给 Claude 的消息列表（含截断）
        all_messages = history + [user_msg]
        api_messages = self._build_api_messages(all_messages)
        api_messages = self._truncate_messages(api_messages)

        # 4. 调用 Claude
        resp = await self.claude.chat_with_history(
            messages=api_messages,
            system=session.system_prompt or None,
            use_tools=session.use_tools,
        )

        # 5. 保存 assistant 消息
        tool_calls_data = [
            {"id": tc.id, "name": tc.name, "input": tc.input}
            for tc in resp.tool_calls_history
        ]
        assistant_msg = ChatMessage(
            role="assistant",
            content=resp.content,
            tool_calls=tool_calls_data,
            token_count=resp.output_tokens,
        )
        await self.session_mgr.append_message(session, assistant_msg)

        # 6. 更新 token 统计
        await self.session_mgr.update_session_tokens(
            session, resp.input_tokens, resp.output_tokens,
        )

        return resp

    # ==================== 流式对话 ====================

    async def send_message_stream(
        self,
        session_id: str,
        content: str,
    ) -> AsyncIterator[str]:
        """
        流式发送消息（SSE）

        流程与 send_message 一致，但通过 yield SSE 事件实时推送给调用方。
        文本增量、工具调用过程、最终结果都会实时推送。
        """
        from packages.claude.models.sse import (
            sse_message_start,
            sse_message_end,
            sse_error,
            EVENT_MESSAGE_END,
        )

        session = await self.session_mgr.get_session(session_id)
        if not session:
            yield sse_error("Session not found", code="not_found")
            return

        # 1. 加载历史 + 保存 user 消息
        history = await self.session_mgr.get_messages(session_id)
        user_msg = ChatMessage(
            role="user",
            content=content,
            token_count=self._estimate_tokens(content),
        )
        await self.session_mgr.append_message(session, user_msg)

        # 2. 构建 API 消息列表（含截断）
        all_messages = history + [user_msg]
        api_messages = self._build_api_messages(all_messages)
        api_messages = self._truncate_messages(api_messages)

        # 3. 推送开始事件
        yield sse_message_start(session_id=session.id, message_id=user_msg.id)

        # 4. 流式调用 Claude（含 tool calling）
        collected_text = []
        collected_tool_calls = []
        final_input_tokens = 0
        final_output_tokens = 0
        final_stop_reason = "end_turn"

        async for sse_chunk in self.claude.chat_with_history_stream(
            messages=api_messages,
            system=session.system_prompt or None,
            use_tools=session.use_tools,
        ):
            yield sse_chunk

            # 从 SSE 文本中解析关键数据（用于保存到 DB）
            parsed = self._parse_sse_for_persistence(sse_chunk)
            if parsed:
                if parsed["type"] == "content_delta":
                    collected_text.append(parsed["text"])
                elif parsed["type"] == "tool_use_start":
                    collected_tool_calls.append({
                        "id": parsed["tool_call_id"],
                        "name": parsed["name"],
                        "input": parsed["input"],
                    })
                elif parsed["type"] == "message_end":
                    final_input_tokens = parsed.get("input_tokens", 0)
                    final_output_tokens = parsed.get("output_tokens", 0)
                    final_stop_reason = parsed.get("stop_reason", "end_turn")

        # 5. 保存 assistant 消息
        full_content = "".join(collected_text)
        assistant_msg = ChatMessage(
            role="assistant",
            content=full_content,
            tool_calls=collected_tool_calls,
            token_count=final_output_tokens or self._estimate_tokens(full_content),
        )
        await self.session_mgr.append_message(session, assistant_msg)

        # 6. 更新 token 统计
        await self.session_mgr.update_session_tokens(
            session, final_input_tokens, final_output_tokens,
        )

    def _parse_sse_for_persistence(self, sse_text: str) -> Optional[dict]:
        """从 SSE 文本中提取 event 和 data，用于持久化"""
        event_type = None
        data_str = None
        for line in sse_text.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
        if not event_type or not data_str:
            return None
        try:
            data = json.loads(data_str)
            data["type"] = event_type
            return data
        except json.JSONDecodeError:
            return None

    # ==================== 内部方法 ====================

    def _build_api_messages(self, messages: List[ChatMessage]) -> List[dict]:
        """将 ChatMessage 列表转为 Anthropic API 的 messages 格式"""
        result = []
        for m in messages:
            if m.raw_content:
                # 有原始 content blocks（assistant 带 tool_use 时需要）
                result.append({"role": m.role, "content": m.raw_content})
            else:
                result.append({"role": m.role, "content": m.content})
        return result

    def _truncate_messages(self, messages: List[dict]) -> List[dict]:
        """
        token 截断：从最早的消息开始丢弃，直到总 token 量在上限内。
        始终保留最后一条 user 消息。
        """
        max_tokens = self.config.max_context_tokens
        if not messages:
            return messages

        # 估算每条消息的 token
        token_counts = []
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, str):
                token_counts.append(self._estimate_tokens(content))
            elif isinstance(content, list):
                # content blocks，粗估
                text = json.dumps(content, ensure_ascii=False)
                token_counts.append(self._estimate_tokens(text))
            else:
                token_counts.append(0)

        total = sum(token_counts)
        if total <= max_tokens:
            return messages

        # 从前面开始丢弃，但至少保留最后一条
        trimmed = list(messages)
        trimmed_tokens = list(token_counts)
        while len(trimmed) > 1 and sum(trimmed_tokens) > max_tokens:
            trimmed.pop(0)
            trimmed_tokens.pop(0)

        return trimmed

    def _estimate_tokens(self, text: str) -> int:
        """粗估 token 数量"""
        if not text:
            return 0
        return max(1, int(len(text) / self.config.chars_per_token))


def create_chat_service(
    db: Any,
    chat_config: Optional[ChatConfig] = None,
    claude_config: Optional[ClaudeConfig] = None,
) -> ChatService:
    """创建 Chat 对话服务"""
    return ChatService(db, chat_config, claude_config)
