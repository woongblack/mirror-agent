"""Contrarian Agent — 문서의 핵심 주장에 반대 시나리오를 구성한다.

'크로스 셀러 룩북이 전환율이 높다'는 주장에
→ '낮을 수도 있다면 어떻게 되는가?'를 탐색.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from mirror_agent.llm import LLMClient
from mirror_agent.models import ContrarianChallenge, DocumentMetadata

logger = logging.getLogger(__name__)

_SYSTEM = """\
당신은 기획 문서의 핵심 주장에 반대 시나리오를 구성하는 비판자입니다.

## 역할
문서가 "당연히" 전제하는 것에 "정말 당연한가?"를 묻습니다.
단순 부정("아닐 수도 있다")이 아니라,
반대 전제가 성립하는 구체적 조건과 메커니즘을 제시합니다.

## 핵심 주장 유형 (여기서 찾아라)
- 사용자 수요 주장: "사용자가 X를 원한다", "X가 필요하다"
- 차별화 주장: "우리가 더 낫다", "기존과 다르다"
- 실행 가능성 주장: "기술적으로 가능하다", "구현할 수 있다"
- 수익 주장: "이렇게 수익이 난다", "수익화할 수 있다"
- 타이밍 주장: "지금이 적기다", "시장이 준비됐다"

## 반대 시나리오 작성 원칙
- counter_scenario: 반대 전제가 성립하는 구체적 조건과 경로를 설명한다 (50자 이상)
- implication: 반대 전제가 맞다면 어떤 결정을 다르게 해야 하는지 명시한다
- 단순 "아닐 수도 있다" 수준의 counter_scenario는 작성하지 않는다

## 금지
- 단순 부정만 나열하는 challenge_question
- 문서에서 인용 불가한 claim 생성
- Socratic Agent와 완전히 동일한 각도의 질문 (전제 드러내기가 아닌 반대 시나리오여야 함)
"""


class _RawChallenge(BaseModel):
    """LLM이 채우는 단순화된 중간 모델."""
    claim: str
    counter_premise: str
    counter_scenario: str
    challenge_question: str
    implication: str
    severity: str  # high / medium / low
    evidence_from_document: str


class _ContrarianOutput(BaseModel):
    challenges: list[_RawChallenge]


_VALID_SEVERITIES = {"high", "medium", "low"}


class ContrarianAgent:
    """문서의 핵심 주장에 반대 시나리오를 구성하는 에이전트."""

    def __init__(self, llm: LLMClient, model: str) -> None:
        self._llm = llm
        self._model = model

    async def challenge(
        self,
        document_text: str,
        metadata: DocumentMetadata,
    ) -> list[ContrarianChallenge]:
        """문서의 핵심 주장마다 반대 시나리오 생성."""
        user_prompt = f"""다음 문서의 핵심 주장에 반대 시나리오를 구성하세요. 최소 3개.
각 주장의 반대 전제가 성립하는 구체적 시나리오와 그 함의를 제시하세요.

=== 문서 메타데이터 ===
프로젝트 유형: {metadata.target_type}
사용자 가치 주장: {metadata.claimed_user_values}
공급자 존재: {metadata.has_supply_side}
1인 프로젝트: {metadata.is_solo_project}

=== 문서 전문 ===
{document_text[:4000]}
"""
        result = await self._llm.structured_call(
            model=self._model,
            system=_SYSTEM,
            user=user_prompt,
            response_model=_ContrarianOutput,
        )

        challenges = []
        for raw in result.challenges:
            severity = raw.severity if raw.severity in _VALID_SEVERITIES else "medium"
            challenges.append(ContrarianChallenge(
                claim=raw.claim,
                counter_premise=raw.counter_premise,
                counter_scenario=raw.counter_scenario,
                challenge_question=raw.challenge_question,
                implication=raw.implication,
                severity=severity,
                evidence_from_document=raw.evidence_from_document,
            ))

        logger.info("Contrarian: %d개 도전 생성", len(challenges))
        return challenges
