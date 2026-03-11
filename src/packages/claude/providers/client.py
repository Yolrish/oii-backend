"""
Claude API 客户端

封装 Anthropic SDK，提供同步/异步/流式调用。
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import anthropic

from ..configs.config import ClaudeConfig
from ..models.messages import ToolCall


class ClaudeClient:
    """
    Anthropic Claude API 客户端

    封装底层 SDK 调用，提供统一的消息发送接口。
    """

    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config or ClaudeConfig.from_env()
        self._client: Optional[anthropic.Anthropic] = None
        self._async_client: Optional[anthropic.AsyncAnthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        """懒加载同步客户端"""
        if self._client is None:
            kwargs: Dict[str, Any] = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.timeout:
                kwargs["timeout"] = self.config.timeout
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    @property
    def async_client(self) -> anthropic.AsyncAnthropic:
        """懒加载异步客户端"""
        if self._async_client is None:
            kwargs: Dict[str, Any] = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.timeout:
                kwargs["timeout"] = self.config.timeout
            self._async_client = anthropic.AsyncAnthropic(**kwargs)
        return self._async_client

    def _build_tools_param(self, tools: Optional[List[dict]]) -> Optional[List[dict]]:
        """
        将 OpenAI 格式的 tools 转为 Anthropic 格式

        OpenAI: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        Anthropic: {"name": ..., "description": ..., "input_schema": ...}
        """
        if not tools:
            return None
        result = []
        for t in tools:
            func = t.get("function", t)
            result.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return result

    def _parse_tool_calls(self, content_blocks: list) -> tuple[str, List[ToolCall]]:
        """从响应 content blocks 中提取文本和 tool_use"""
        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input or {},
                ))
        return "\n".join(text_parts), tool_calls

    def send_message(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """
        同步发送消息

        Args:
            messages: Anthropic 格式的消息列表
            system: 系统提示词
            tools: OpenAI 格式的 tools 列表（自动转换）
            model: 模型名称，默认使用配置
            max_tokens: 最大输出 token
            temperature: 温度

        Returns:
            {"content": str, "tool_calls": List[ToolCall], "stop_reason": str,
             "input_tokens": int, "output_tokens": int, "raw_content": list}
        """
        kwargs = self._build_request_kwargs(
            messages, system=system, tools=tools,
            model=model, max_tokens=max_tokens, temperature=temperature,
        )
        response = self.client.messages.create(**kwargs)
        return self._parse_response(response)

    async def send_message_async(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """异步发送消息，参数同 send_message"""
        kwargs = self._build_request_kwargs(
            messages, system=system, tools=tools,
            model=model, max_tokens=max_tokens, temperature=temperature,
        )
        response = await self.async_client.messages.create(**kwargs)
        return self._parse_response(response)

    def _build_request_kwargs(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict:
        """构造请求参数"""
        kwargs: Dict[str, Any] = {
            "model": model or self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        elif self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if system or self.config.system_prompt:
            kwargs["system"] = system or self.config.system_prompt
        anthropic_tools = self._build_tools_param(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
        return kwargs

    async def stream_message_async(
        self,
        messages: List[dict],
        *,
        system: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[dict]:
        """
        异步流式发送消息

        yield 的事件类型：
        - {"type": "content_delta", "text": "..."}
        - {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
        - {"type": "message_end", "stop_reason": "...", "input_tokens": ..., "output_tokens": ..., "raw_content": [...]}
        """
        kwargs = self._build_request_kwargs(
            messages, system=system, tools=tools,
            model=model, max_tokens=max_tokens, temperature=temperature,
        )

        async with self.async_client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"type": "content_delta", "text": event.delta.text}
                elif event.type == "content_block_start":
                    if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                        pass  # tool_use 的 input 在后续 delta 中逐步拼出，最终从 final_message 获取

            # 流结束后获取完整消息
            final = await stream.get_final_message()
            text, tool_calls = self._parse_tool_calls(final.content)
            yield {
                "type": "message_end",
                "content": text,
                "tool_calls": tool_calls,
                "stop_reason": final.stop_reason,
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
                "raw_content": final.content,
            }

    def _parse_response(self, response) -> dict:
        """统一解析响应"""
        text, tool_calls = self._parse_tool_calls(response.content)
        return {
            "content": text,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "raw_content": response.content,
        }
