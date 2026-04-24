"""Planning Agent — 아이디어 텍스트 → Ouroboros Loop → 구조화된 기획안.

나머지 에이전트가 '비판자'라면, Planning은 '구조화자'.
Round 1: 문제 정의
Round 2: Socratic으로 숨겨진 가정 드러내기 → 반영
Round 3: Contrarian으로 반대 시나리오 탐색 → 반영
종료 조건: ambiguity_score ≤ 0.2 또는 최대 3회
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from mirror_agent.config import Settings
from mirror_agent.contrarian import ContrarianAgent
from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata, PlanningDraft, PlanningRound
from mirror_agent.socratic import SocraticAgent

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3
AMBIGUITY_THRESHOLD = 0.2

_DRAFT_SYSTEM = """\
당신은 기획 구조화 전문가입니다.

주어진 아이디어에서 다음을 추출하여 구조화된 기획안을 작성하세요:

## 기획안 구조 (필수 섹션)
1. **문제 정의** — 이 아이디어가 해결하는 문제는 무엇인가? (What)
2. **대상 사용자** — 누가 이 문제를 겪는가? (Who)
3. **해결 방식** — 어떻게 해결하는가? (How)
4. **성공 지표** — 어떻게 성공을 측정하는가? (Measure)
5. **핵심 전제** — 이 기획이 성립하려면 무엇이 사실이어야 하는가?
6. **미해결 질문** — 아직 답하지 못한 것 (있으면 [?]로 표시)

## 원칙
- 근거 없는 주장은 [가정]으로 명시한다
- 불명확한 부분은 [?]로 표시한다
- 모호함을 감추지 말고 드러낸다
"""

_AMBIGUITY_SYSTEM = """\
당신은 기획안의 명확도를 평가하는 전문가입니다.

다음 5가지 항목을 1~5점으로 평가하세요:
1. 문제 정의 명확도 — "누구의 어떤 문제인가"가 구체적인가?
2. 대상 사용자 명확도 — 타겟이 특정 가능한가?
3. 해결 방식 구체성 — "어떻게"가 실행 가능한 수준으로 기술되었는가?
4. 성공 기준 존재 여부 — 측정 가능한 지표가 있는가?
5. 핵심 전제 명시 여부 — 암묵적 가정이 드러나 있는가?

ambiguity_score = (5 - 평균점수) / 5
→ 0.0: 완전 명확, 1.0: 완전 모호, 종료 기준 0.2 이하
"""

_REFINE_SYSTEM = """\
당신은 기획안을 개선하는 전문가입니다.

외부 비판(질문/반대 시나리오)을 반영하여 기획안을 수정하세요.

## 원칙
- 비판을 무시하거나 방어하지 말고, 기획안에 반영하라
- 답하지 못한 비판은 [미해결]로 표시하고 기획안에 남겨두라
- 이전 기획안보다 더 구체적이고 명확해야 한다
- 추가된 내용과 변경된 내용을 changes_from_prev에 요약하라
"""


class _DraftOutput(BaseModel):
    draft: str
    open_questions: list[str]


class _AmbiguityOutput(BaseModel):
    scores: list[float]  # 5개 항목, 각 1~5점
    reasoning: str


class _RoundOutput(BaseModel):
    draft: str
    ambiguity_score: float
    open_questions: list[str]
    changes_from_prev: str


class PlanningAgent:
    """아이디어 → Ouroboros Loop → 구조화된 기획안 생성."""

    def __init__(self, settings: Settings) -> None:
        self._llm = LLMClient(settings)
        self._model = settings.model_generator
        self._socratic = SocraticAgent(self._llm, model=settings.model_generator)
        self._contrarian = ContrarianAgent(self._llm, model=settings.model_generator)

    async def plan(self, idea_text: str) -> PlanningDraft:
        rounds: list[PlanningRound] = []
        current_draft = ""

        for round_num in range(1, MAX_ROUNDS + 1):
            logger.info("Planning Round %d 시작", round_num)

            if round_num == 1:
                round_result = await self._round1_define(idea_text)
            elif round_num == 2:
                round_result = await self._round2_socratic(idea_text, current_draft)
            else:
                round_result = await self._round3_contrarian(idea_text, current_draft)

            rounds.append(PlanningRound(
                round_number=round_num,
                draft=round_result.draft,
                ambiguity_score=round_result.ambiguity_score,
                open_questions=round_result.open_questions,
                changes_from_prev=round_result.changes_from_prev,
            ))
            current_draft = round_result.draft
            logger.info("Round %d 완료 — ambiguity: %.2f", round_num, round_result.ambiguity_score)

            if round_result.ambiguity_score <= AMBIGUITY_THRESHOLD:
                logger.info("ambiguity_score %.2f ≤ %.2f — 조기 종료", round_result.ambiguity_score, AMBIGUITY_THRESHOLD)
                break

        final = rounds[-1]
        return PlanningDraft(
            idea_input=idea_text,
            rounds=rounds,
            final_draft=final.draft,
            final_ambiguity=final.ambiguity_score,
            converged=final.ambiguity_score <= AMBIGUITY_THRESHOLD,
        )

    async def _round1_define(self, idea_text: str) -> _RoundOutput:
        """Round 1: 문제 정의 및 기획안 초안 작성."""
        result = await self._llm.structured_call(
            model=self._model,
            system=_DRAFT_SYSTEM,
            user=f"다음 아이디어를 구조화된 기획안으로 작성하세요.\n\n---\n\n{idea_text}",
            response_model=_DraftOutput,
        )
        score = await self._measure_ambiguity(result.draft)
        return _RoundOutput(
            draft=result.draft,
            ambiguity_score=score,
            open_questions=result.open_questions,
            changes_from_prev="초안 작성",
        )

    async def _round2_socratic(self, idea_text: str, draft: str) -> _RoundOutput:
        """Round 2: Socratic으로 가정 드러내기 → 기획안 반영."""
        dummy_metadata = DocumentMetadata(path="planning_draft")
        questions = await self._socratic.interrogate(draft, dummy_metadata)
        questions_text = "\n".join(f"- [{q.angle}] {q.question}" for q in questions)

        result = await self._llm.structured_call(
            model=self._model,
            system=_REFINE_SYSTEM,
            user=f"""현재 기획안:
{draft}

---

Socratic 질문 (이 질문들을 반영하여 기획안을 개선하세요):
{questions_text}

원본 아이디어 (참고):
{idea_text}
""",
            response_model=_RoundOutput,
        )
        return result

    async def _round3_contrarian(self, idea_text: str, draft: str) -> _RoundOutput:
        """Round 3: Contrarian으로 반대 시나리오 탐색 → 기획안 반영."""
        dummy_metadata = DocumentMetadata(path="planning_draft")
        challenges = await self._contrarian.challenge(draft, dummy_metadata)
        challenges_text = "\n".join(
            f"- {c.challenge_question}\n  함의: {c.implication}" for c in challenges
        )

        result = await self._llm.structured_call(
            model=self._model,
            system=_REFINE_SYSTEM,
            user=f"""현재 기획안:
{draft}

---

Contrarian 도전 (이 반대 시나리오들을 반영하여 기획안을 개선하세요):
{challenges_text}

원본 아이디어 (참고):
{idea_text}
""",
            response_model=_RoundOutput,
        )
        return result

    async def _measure_ambiguity(self, draft: str) -> float:
        """기획안의 ambiguity_score 측정 (0=명확, 1=모호)."""
        result = await self._llm.structured_call(
            model=self._model,
            system=_AMBIGUITY_SYSTEM,
            user=f"다음 기획안의 명확도를 평가하세요.\n\n{draft}",
            response_model=_AmbiguityOutput,
        )
        if not result.scores:
            return 0.5
        avg = sum(result.scores) / len(result.scores)
        return round((5 - avg) / 5, 2)
