"""Socratic Agent — 문서의 숨겨진 가정을 드러내어 '왜?'를 묻는다.

Historical이 '과거에 이런 비판을 했었다'면,
Socratic은 '이 주장의 전제가 맞는가?'를 묻는다.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata, SocraticQuestion

logger = logging.getLogger(__name__)

_SYSTEM = """\
당신은 기획 문서에서 암묵적 전제를 드러내는 소크라테스식 질문자입니다.

## 역할
문서의 "~이다", "~할 것이다", "~가 필요하다" 형태의 주장에서
그 주장이 성립하기 위해 필요한 전제를 추출하고,
"왜 그 전제가 성립하는가?"를 묻습니다.

## 5가지 각도 (각각 최소 1개 질문)
- market: 시장 수요, 경쟁 환경, 타이밍 — "사용자가 이걸 원한다는 근거는?"
- tech: 기술 실행 가능성, 의존성, 병목 — "이게 기술적으로 가능하다는 근거는?"
- operation: 운영 지속 가능성, 리소스 — "혼자 이걸 계속 운영할 수 있는가?"
- motivation: 프로젝트 동기, 진짜 이유 — "왜 이걸 만드는가?"
- competition: 대안 솔루션, 차별점 — "경쟁 제품이 이미 이걸 하고 있지 않은가?"

## 금지
- "~인지 확인이 필요합니다" 식의 추상적 질문
- 문서에서 인용 불가한 가정 생성
- 단순 사실 확인 질문 ("Phase 1이 몇 주인가?" 등)
- 동일한 각도에서 중복 질문

## 원칙
- evidence_from_document는 반드시 문서 원문을 직접 인용한다
- assumption은 "~이다" 형태로 명시한다 (의문문 금지)
- question은 "왜 ~인가?" 또는 "~라는 것이 사실인가?" 형태로 작성한다
"""


class _RawQuestion(BaseModel):
    """LLM이 채우는 단순화된 중간 모델. Literal 제약 없이 string 사용."""
    assumption: str
    question: str
    angle: str   # market / tech / operation / motivation / competition
    severity: str  # high / medium / low
    evidence_from_document: str


class _SocraticOutput(BaseModel):
    questions: list[_RawQuestion]


_VALID_ANGLES = {"market", "tech", "operation", "motivation", "competition"}
_VALID_SEVERITIES = {"high", "medium", "low"}


class SocraticAgent:
    """문서의 숨겨진 가정을 드러내는 에이전트."""

    def __init__(self, llm: LLMClient, model: str) -> None:
        self._llm = llm
        self._model = model

    async def interrogate(
        self,
        document_text: str,
        metadata: DocumentMetadata,
    ) -> list[SocraticQuestion]:
        """문서에서 숨겨진 가정을 드러내는 질문 생성."""
        user_prompt = f"""다음 문서에서 숨겨진 가정을 드러내는 질문을 생성하세요.
5가지 각도(market/tech/operation/motivation/competition) 각각 최소 1개.

=== 문서 메타데이터 ===
프로젝트 유형: {metadata.target_type}
1인 프로젝트: {metadata.is_solo_project}
사용자 가치 주장: {metadata.claimed_user_values}
기술 스택: {metadata.tech_stack}

=== 문서 전문 ===
{document_text[:4000]}
"""
        result = await self._llm.structured_call(
            model=self._model,
            system=_SYSTEM,
            user=user_prompt,
            response_model=_SocraticOutput,
        )

        questions = []
        for raw in result.questions:
            angle = raw.angle if raw.angle in _VALID_ANGLES else "market"
            severity = raw.severity if raw.severity in _VALID_SEVERITIES else "medium"
            questions.append(SocraticQuestion(
                assumption=raw.assumption,
                question=raw.question,
                angle=angle,
                severity=severity,
                evidence_from_document=raw.evidence_from_document,
            ))

        logger.info("Socratic: %d개 질문 생성", len(questions))
        return questions
