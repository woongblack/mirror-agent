"""Anthropic API 래퍼.

모든 LLM 호출의 단일 진입점. 토큰 사용량 로깅, 재시도, 구조화 출력 강제를 담당.

TODO(v0.1):
- [ ] Anthropic AsyncClient 초기화
- [ ] structured_call(): Pydantic 모델로 응답 파싱 강제
- [ ] 간단한 재시도 (rate limit 대응)
- [ ] 토큰 사용량 로깅
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from mirror_agent.config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Anthropic API 래퍼. 모든 에이전트가 이를 통해 LLM 호출."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # TODO: from anthropic import AsyncAnthropic
        # self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def structured_call(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        """구조화 출력을 강제하는 LLM 호출.

        Tool use / JSON mode를 통해 응답을 response_model로 파싱한다.
        파싱 실패 시 최대 2회 재시도.
        """
        raise NotImplementedError("다음 세션에서 구현")

    async def text_call(
        self,
        *,
        model: str,
        system: str,
        user: str,
    ) -> str:
        """일반 텍스트 응답. 자연어 질문 생성 등에 사용."""
        raise NotImplementedError("다음 세션에서 구현")
