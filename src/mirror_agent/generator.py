"""비판 질문 생성기.

매칭된 규칙의 critique_template에 MatchResult의 extracted_variables를 치환하여
구체적인 비판 질문을 생성한다. evidence_questions도 동일 치환.

TODO(v0.1):
- [ ] 템플릿 변수 치환 (단순 format)
- [ ] LLM을 통한 자연스러운 질문 정제 (선택)
- [ ] past_evidence는 규칙의 source_critiques에서 1개 선택
- [ ] document_excerpt는 MatchResult의 evidence_from_document 재사용
"""

from __future__ import annotations

from mirror_agent.llm import LLMClient
from mirror_agent.models import Critique, MatchResult, Rule


class CritiqueGenerator:
    """매칭 결과를 최종 Critique로 변환."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate(
        self,
        rule: Rule,
        match: MatchResult,
    ) -> Critique:
        """단일 규칙-매칭 쌍에 대해 Critique 생성."""
        raise NotImplementedError("다음 세션에서 구현")
