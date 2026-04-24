"""Anthropic API 래퍼.

모든 LLM 호출의 단일 진입점. 토큰 사용량 로깅, 재시도, 구조화 출력 강제를 담당.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TypeVar

from anthropic import AsyncAnthropic, RateLimitError
from pydantic import BaseModel

from mirror_agent.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRY_DELAYS = [5, 15]  # rate limit 재시도 간격(초)


class LLMClient:
    """Anthropic API 래퍼. 모든 에이전트가 이를 통해 LLM 호출."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def structured_call(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_model: type[T],
        max_tokens: int = 4096,
    ) -> T:
        """구조화 출력을 강제하는 LLM 호출.

        tool_choice로 특정 tool 호출을 강제하여 response_model로 파싱.
        파싱 실패 및 rate limit 시 최대 2회 재시도.
        """
        tool_name = "structured_output"
        tool_schema = response_model.model_json_schema()

        for attempt in range(3):
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user}],
                    tools=[
                        {
                            "name": tool_name,
                            "description": f"Return structured output conforming to {response_model.__name__}",
                            "input_schema": tool_schema,
                        }
                    ],
                    tool_choice={"type": "tool", "name": tool_name},
                )

                logger.debug(
                    "structured_call [%s] input=%d output=%d cache_read=%d cache_create=%d",
                    model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    getattr(response.usage, "cache_read_input_tokens", 0),
                    getattr(response.usage, "cache_creation_input_tokens", 0),
                )

                for block in response.content:
                    if block.type == "tool_use" and block.name == tool_name:
                        return response_model.model_validate(block.input)

                raise ValueError("응답에 tool_use 블록이 없음")

            except RateLimitError:
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning("Rate limit. %d초 후 재시도 (%d/2)...", delay, attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError("structured_call: 재시도 소진")

    async def text_call(
        self,
        *,
        model: str,
        system: str,
        user: str,
    ) -> str:
        """일반 텍스트 응답. 자연어 질문 생성 등에 사용."""
        for attempt in range(3):
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=2048,
                    system=[
                        {
                            "type": "text",
                            "text": system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": user}],
                )

                logger.debug(
                    "text_call [%s] input=%d output=%d cache_read=%d cache_create=%d",
                    model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    getattr(response.usage, "cache_read_input_tokens", 0),
                    getattr(response.usage, "cache_creation_input_tokens", 0),
                )

                return response.content[0].text

            except RateLimitError:
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning("Rate limit. %d초 후 재시도 (%d/2)...", delay, attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError("text_call: 재시도 소진")
