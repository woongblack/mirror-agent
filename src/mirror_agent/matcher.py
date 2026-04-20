"""규칙 매처.

Rule의 trigger_conditions가 현재 문서에 해당하는지 LLM으로 판정.

핵심 설계:
- Evidence 필드 강제 (환각 방지)
- "추측 금지" 프롬프트 명시
- confidence < threshold는 False로 강제

TODO(v0.1):
- [ ] 매칭 프롬프트 템플릿
- [ ] structured_call로 MatchResult 파싱
- [ ] threshold 필터링
- [ ] 규칙-문서 쌍당 1회 호출 (병렬)
"""

from __future__ import annotations

import asyncio

from mirror_agent.config import Settings
from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata, MatchResult, Rule


MATCHER_SYSTEM_PROMPT = """\
당신은 Mirror Agent의 Rule Matcher입니다.

주어진 규칙의 trigger_conditions가 현재 문서에 해당하는지 판정합니다.

엄격한 규칙:
1. 각 조건마다 문서에서 직접 인용 가능한 근거가 있어야 합니다.
2. 근거를 인용할 수 없으면 matches=False로 판정하세요.
3. 추측하지 마세요. 문서에 명시적으로 쓰여 있는 것만 근거로 삼으세요.
4. 불확실하면 confidence를 낮추세요.
5. 친절하게 "해당할 가능성이 있다"고 답하지 마세요. 명확하지 않으면 False입니다.
"""


class RuleMatcher:
    """LLM 기반 규칙 매칭기."""

    def __init__(self, llm: LLMClient, settings: Settings) -> None:
        self._llm = llm
        self._settings = settings

    async def match(
        self,
        rule: Rule,
        document_text: str,
        document_metadata: DocumentMetadata,
    ) -> MatchResult:
        """단일 규칙에 대한 매칭 판정."""
        raise NotImplementedError("다음 세션에서 구현")

    async def match_all(
        self,
        rules: list[Rule],
        document_text: str,
        document_metadata: DocumentMetadata,
    ) -> list[MatchResult]:
        """모든 규칙에 대해 병렬 매칭."""
        tasks = [
            self.match(rule, document_text, document_metadata) for rule in rules
        ]
        results = await asyncio.gather(*tasks)
        # threshold 필터링
        return [
            r
            for r in results
            if r.matches and r.confidence >= self._settings.match_confidence_threshold
        ]
