"""
Claude 对话服务

支持普通对话、Tool Calling 自动循环和流式输出。
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from ..configs.config import ClaudeConfig
from ..models.messages import ChatResponse, Message, Role, ToolCall, ToolResult
from ..providers.client import ClaudeClient


class ClaudeService:
    """
    Claude 对话服务

    使用方式：
        service = create_claude_service()

        # 简单对话
        resp = await service.chat("你好")

        # 带工具的对话（自动从 tool_call 模块获取已注册工具）
        resp = await service.chat("帮我查看当前目录", use_tools=True)

        # 多轮对话
        resp = await service.chat_with_history(messages, use_tools=True)
    """

    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or ClaudeConfig.from_env()
        self.client = ClaudeClient(self.config)

    # ==================== 对外接口 ====================

    async def chat(
        self,
        user_message: str,
        *,
        system: Optional[str] = None,
        use_tools: bool = False,
        tools: Optional[List[dict]] = None,
    ) -> ChatResponse:
        """
        单轮对话

        Args:
            user_message: 用户消息
            system: 系统提示词（覆盖配置）
            use_tools: 是否启用 tool calling（自动获取 tool_call 模块的工具）
            tools: 自定义工具列表（OpenAI 格式），覆盖自动获取
        """
        messages = [{"role": "user", "content": user_message}]
        return await self.chat_with_history(
            messages, system=system, use_tools=use_tools, tools=tools,
        )

    async def chat_with_history(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        use_tools: bool = False,
        tools: Optional[List[dict]] = None,
    ) -> ChatResponse:
        """
        多轮对话（含 tool calling 自动循环）

        Args:
            messages: 消息历史（Anthropic 格式）
            system: 系统提示词
            use_tools: 是否启用 tool calling
            tools: 自定义工具列表（OpenAI 格式）
        """
        resolved_tools = self._resolve_tools(tools, use_tools)
        return await self._chat_loop(
            messages=list(messages),
            system=system,
            tools=resolved_tools,
        )

    def chat_sync(
        self,
        user_message: str,
        *,
        system: Optional[str] = None,
        use_tools: bool = False,
        tools: Optional[List[dict]] = None,
    ) -> ChatResponse:
        """
        单轮对话（同步版本）
        """
        messages = [{"role": "user", "content": user_message}]
        resolved_tools = self._resolve_tools(tools, use_tools)
        return self._chat_loop_sync(
            messages=messages,
            system=system,
            tools=resolved_tools,
        )

    # ==================== 流式对话 ====================

    async def chat_stream(
        self,
        user_message: str,
        *,
        system: Optional[str] = None,
        use_tools: bool = False,
        tools: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """单轮流式对话，yield SSE 格式字符串"""
        messages = [{"role": "user", "content": user_message}]
        async for chunk in self.chat_with_history_stream(
            messages, system=system, use_tools=use_tools, tools=tools,
        ):
            yield chunk

    async def chat_with_history_stream(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        use_tools: bool = False,
        tools: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """
        多轮流式对话（含 tool calling 自动循环）

        yield SSE 格式字符串，事件类型见 models/sse.py
        """
        from ..models.sse import (
            sse_content_delta,
            sse_tool_use_start,
            sse_tool_use_result,
            sse_message_end,
            sse_error,
        )

        resolved_tools = self._resolve_tools(tools, use_tools)
        current_messages = list(messages)
        all_tool_calls: List[ToolCall] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for _ in range(self.config.max_tool_rounds):
            final_event = None

            async for event in self.client.stream_message_async(
                current_messages, system=system, tools=resolved_tools,
            ):
                if event["type"] == "content_delta":
                    yield sse_content_delta(event["text"])
                elif event["type"] == "message_end":
                    final_event = event

            if not final_event:
                yield sse_error("No response from Claude")
                return

            total_input_tokens += final_event["input_tokens"]
            total_output_tokens += final_event["output_tokens"]
            tool_calls: List[ToolCall] = final_event.get("tool_calls", [])

            # 无工具调用，输出结束事件
            if not tool_calls:
                yield sse_message_end(
                    stop_reason=final_event["stop_reason"],
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
                return

            # 有工具调用：推送 tool 事件，执行工具，继续循环
            all_tool_calls.extend(tool_calls)
            current_messages.append({"role": "assistant", "content": final_event["raw_content"]})

            tool_result_content = []
            for tc in tool_calls:
                yield sse_tool_use_start(tc.id, tc.name, tc.input)
                try:
                    from packages.tool_call import execute_tool_async
                    result = await execute_tool_async(tc.name, tc.input)
                    content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                    yield sse_tool_use_result(tc.id, tc.name, result, is_error=False)
                    tool_result_content.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": content,
                    })
                except Exception as e:
                    yield sse_tool_use_result(tc.id, tc.name, str(e), is_error=True)
                    tool_result_content.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            current_messages.append({"role": "user", "content": tool_result_content})

        # 超过最大轮数
        yield sse_message_end(
            stop_reason="max_tool_rounds",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )

    # ==================== 内部实现 ====================

    def _resolve_tools(
        self, tools: Optional[List[dict]], use_tools: bool,
    ) -> Optional[List[dict]]:
        """解析工具列表"""
        if tools:
            return tools
        if use_tools:
            from packages.tool_call import get_tools_for_llm
            t = get_tools_for_llm()
            return t if t else None
        return None

    async def _chat_loop(
        self,
        messages: List[dict],
        system: Optional[str],
        tools: Optional[List[dict]],
    ) -> ChatResponse:
        """异步 tool calling 循环"""
        all_tool_calls: List[ToolCall] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for _ in range(self.config.max_tool_rounds):
            resp = await self.client.send_message_async(
                messages, system=system, tools=tools,
            )
            total_input_tokens += resp["input_tokens"]
            total_output_tokens += resp["output_tokens"]

            tool_calls: List[ToolCall] = resp["tool_calls"]

            # 无工具调用，直接返回
            if not tool_calls:
                return ChatResponse(
                    content=resp["content"],
                    tool_calls_history=all_tool_calls,
                    stop_reason=resp["stop_reason"],
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

            all_tool_calls.extend(tool_calls)

            # 构造 assistant 消息（保留原始 content blocks）
            messages.append({"role": "assistant", "content": resp["raw_content"]})

            # 执行工具，构造 tool_result 消息
            tool_result_content = await self._execute_tool_calls(tool_calls)
            messages.append({"role": "user", "content": tool_result_content})

        # 超过最大轮数
        return ChatResponse(
            content=resp["content"] if resp else "",
            tool_calls_history=all_tool_calls,
            stop_reason="max_tool_rounds",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )

    def _chat_loop_sync(
        self,
        messages: List[dict],
        system: Optional[str],
        tools: Optional[List[dict]],
    ) -> ChatResponse:
        """同步 tool calling 循环"""
        all_tool_calls: List[ToolCall] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for _ in range(self.config.max_tool_rounds):
            resp = self.client.send_message(
                messages, system=system, tools=tools,
            )
            total_input_tokens += resp["input_tokens"]
            total_output_tokens += resp["output_tokens"]

            tool_calls: List[ToolCall] = resp["tool_calls"]

            if not tool_calls:
                return ChatResponse(
                    content=resp["content"],
                    tool_calls_history=all_tool_calls,
                    stop_reason=resp["stop_reason"],
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

            all_tool_calls.extend(tool_calls)
            messages.append({"role": "assistant", "content": resp["raw_content"]})

            tool_result_content = self._execute_tool_calls_sync(tool_calls)
            messages.append({"role": "user", "content": tool_result_content})

        return ChatResponse(
            content=resp["content"] if resp else "",
            tool_calls_history=all_tool_calls,
            stop_reason="max_tool_rounds",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )

    async def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> list:
        """异步执行工具调用，返回 Anthropic 格式的 tool_result content blocks"""
        from packages.tool_call import execute_tool_async

        results = []
        for tc in tool_calls:
            try:
                result = await execute_tool_async(tc.name, tc.input)
                content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": content,
                })
            except Exception as e:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": f"Error: {e}",
                    "is_error": True,
                })
        return results

    def _execute_tool_calls_sync(self, tool_calls: List[ToolCall]) -> list:
        """同步执行工具调用"""
        from packages.tool_call import execute_tool

        results = []
        for tc in tool_calls:
            try:
                result = execute_tool(tc.name, tc.input)
                content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": content,
                })
            except Exception as e:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": f"Error: {e}",
                    "is_error": True,
                })
        return results


def create_claude_service(config: Optional[ClaudeConfig] = None) -> ClaudeService:
    """创建 Claude 对话服务"""
    return ClaudeService(config or ClaudeConfig.from_env())
