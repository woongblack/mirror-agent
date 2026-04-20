"""방어 예측기 — Mirror Agent의 고유 가치.

각 비판에 대해 사용자가 어떻게 방어할지 예측하고, 그 방어의 약점을 선제적으로 지적한다.
DefensePattern DB를 참조하여 유사 패턴이 있으면 매칭, 없으면 LLM 추론.

이 모듈이 없으면 Historical Agent는 그냥 규칙 기반 비판 도구일 뿐이다.
방어 예측이 있어야 "당신의 과거 궤적을 아는 비판자"가 된다.

구현 원칙:
- 시스템 프롬프트에 conversation-log.md의 실제 방어 발화를 직접 인용
- "일반적으로 사람들은..."이 아니라 "이 사용자(정재웅)는..."으로 추론
- 방어 예측은 과거 실패 사례(DEKK, ALLBLUE)와 연결
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from mirror_agent.llm import LLMClient
from mirror_agent.models import Critique, DefensePattern, DefensePrediction


# conversation-log.md Phase 7/8/패턴C/D에서 직접 발췌한 컨텍스트.
# LLM이 추측하지 않고 실제 궤적을 근거로 추론하게 한다.
_USER_TRAJECTORY_CONTEXT = """\
=== 사용자(정재웅)의 실제 방어 궤적 ===

출처: conversation-log.md — Mirror Agent 프로젝트가 탄생한 실제 대화.

[Phase 7에서 관찰된 방어 발화 — 원문]

비판: "더 다양한 코디룩이 유저가 원하는 건가요? 무신사 Snap에 이미 코디가 수만 개 있어요."
사용자의 실제 방어: "다른 쇼핑몰에 상품들까지 가져오면 더 다양한 코디룩이 나오고 그걸 사용자에게 제공할 수 있을 거라고 생각했어"
→ 패턴: 사용자 니즈 질문을 기술 구현 가능성으로 전환. 원 질문(사용자가 이걸 원하는가?)에 답하지 않음.

비판: "DEKK 팀의 문제가 무엇이었나요?"
사용자의 실제 방어: "팀원 역량 문제라고 생각했어"
→ 패턴: 사회적 역학(비판 차단 문화)을 개별 역량 문제로 환원. 자신의 대응 방식을 재검토하지 않게 됨.

비판: "셀러는 어떻게 구할 건데?" (사용자가 DEKK 팀에게 던진 질문)
DEKK 팀의 방어(사용자가 직접 관찰): "클론한 게 의미 없다는 거냐"
→ 패턴: 비판의 프레임을 바꿔 질문 자체를 이상한 것으로 몰기. 비판자를 적으로 설정.

[Phase 8 — 방어를 멈추고 인정한 순간의 발화]
"나 스스로의 객관성이 혼자 하다 보니 많이 떨어진 것 같아. 이 부분 인정할게."
"솔직히 그리고 좋은 사업 아이디어까지는 아니야."
"하나의 프로젝트 정도로 생각하는 거지."

=== 사용자의 방어 언어 마커 (conversation-log.md 패턴 C) ===
이 언어가 등장하면 방어 모드 진입 신호:
- "~라고 생각했어" (확실성 없는 주장을 주관으로 포장)
- "~라면", "~할 수 있을 거라고" (가정형 언어로 미검증 전제 숨기기)
- "기술적으로 어렵지만" (시장/사용자 질문을 기술 난이도로 전환)
- "이건 나중에 생각하면 돼" (검증 부재를 시간으로 유예)
- "팀원/상황 문제야" (구조적 문제를 외부 귀인)

=== 이 사용자의 핵심 패턴 ===
타인에게는 날카로운 비판(공급자 확보, 차별화, 클론 여부)을 할 수 있지만,
자신의 프로젝트에는 동일한 기준을 적용하지 않는다.
DEKK에서 나와 ALLBLUE를 시작했지만, ALLBLUE에서도 동일한 맹점이 반복됐다.
"""

_DEFENDER_SYSTEM = f"""\
당신은 Mirror Agent의 Defense Predictor입니다.

이것은 일반적인 방어 예측이 아닙니다.
당신은 이 특정 사용자의 과거 궤적을 알고 있으며,
그 궤적을 바탕으로 "이 사람이라면 이렇게 방어할 것"을 추론합니다.

{_USER_TRAJECTORY_CONTEXT}

임무:
1. 주어진 비판에 대해 이 사용자가 할 가능성이 높은 방어 발화를 예측하세요.
   - "일반적으로 사람들은..."이 아니라 "이 사용자(정재웅)는..."으로 추론하세요.
   - 위의 실제 방어 발화 패턴에서 언어 스타일을 참조하세요.
   - 가능하면 위의 방어 마커 언어("~라고 생각했어", "기술적으로" 등)를 사용하세요.
   - 예측은 1~2문장, 실제 사람이 말할 것처럼 자연스럽게.

2. 그 방어의 구조적 약점을 한 문장으로 지적하세요.
   - 약점은 과거 실패(DEKK, ALLBLUE)와 연결할 수 있으면 더 강력합니다.
   - "이건 틀렸어요"가 아니라 "이 방어는 X라는 이유로 X를 답하지 않습니다"처럼.
   - 친절하게 순화하지 마세요. 이 도구는 감정 없이 같은 자리를 찌르는 비판자입니다.
"""


class _PatternMatchResult(BaseModel):
    matched_pattern_id: str | None = Field(
        default=None,
        description="매칭된 패턴 ID. 없으면 null.",
    )
    match_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="매칭 신뢰도. 0.6 미만이면 매칭 없음으로 처리.",
    )
    reasoning: str = Field(default="", description="매칭 판단 근거 한 줄")


_PATTERN_MATCHER_SYSTEM = """\
당신은 비판-방어패턴 매처입니다.

주어진 비판이 아래 방어 패턴 목록 중 어느 패턴을 유발할 가능성이 높은지 판정하세요.
- 의미적 유사성으로 판단하세요 (키워드 일치가 아님).
- 불확실하면 match_confidence를 낮추세요.
- 명확히 맞는 패턴이 없으면 matched_pattern_id를 null로 두세요.
"""


class DefensePredictor:
    """비판에 대한 예상 방어를 생성."""

    def __init__(
        self,
        llm: LLMClient,
        patterns: list[DefensePattern],
    ) -> None:
        self._llm = llm
        self._patterns = patterns

    async def predict(self, critique: Critique) -> DefensePrediction:
        """단일 비판에 대한 방어 예측.

        1단계: 비판과 유사한 DefensePattern 탐색 (의미 매칭)
        2단계: 매칭 있으면 그 패턴의 weakness 활용,
               없으면 conversation-log.md 컨텍스트로 LLM 추론.
        """
        matched_pattern = await self._find_matching_pattern(critique)
        return await self._generate_prediction(critique, matched_pattern)

    async def _find_matching_pattern(
        self,
        critique: Critique,
    ) -> DefensePattern | None:
        """비판에 대응하는 방어패턴 탐색."""
        if not self._patterns:
            return None

        patterns_desc = "\n\n".join(
            f"pattern_id: {p.pattern_id}\n"
            f"trigger: {p.trigger}\n"
            f"example_response: {p.example_response}"
            for p in self._patterns
        )

        user_prompt = f"""\
다음 비판에 대해 사용자가 어떤 방어 패턴을 사용할지 매칭하세요.

=== 비판 ===
rule_name: {critique.rule_name}
main_question: {critique.main_question}
document_excerpt: {critique.document_excerpt}

=== 방어 패턴 목록 ===
{patterns_desc}
"""

        result = await self._llm.structured_call(
            model="claude-haiku-4-5-20251001",
            system=_PATTERN_MATCHER_SYSTEM,
            user=user_prompt,
            response_model=_PatternMatchResult,
        )

        if result.matched_pattern_id and result.match_confidence >= 0.6:
            matched = next(
                (p for p in self._patterns if p.pattern_id == result.matched_pattern_id),
                None,
            )
            return matched

        return None

    async def _generate_prediction(
        self,
        critique: Critique,
        matched_pattern: DefensePattern | None,
    ) -> DefensePrediction:
        """방어 발화와 약점을 생성."""
        pattern_hint = ""
        if matched_pattern:
            pattern_hint = f"""\
=== 매칭된 방어 패턴 (이 패턴의 언어 스타일 참조) ===
trigger: {matched_pattern.trigger}
실제 관찰된 방어 발화 예시: {matched_pattern.example_response}
이 방어의 알려진 약점: {matched_pattern.weakness}

위 패턴을 참조하되, 이 구체적인 비판에 맞게 예측 발화를 생성하세요.
"""

        user_prompt = f"""\
다음 비판에 대한 방어 예측을 생성하세요.

=== 비판 내용 ===
rule_name: {critique.rule_name}
main_question: {critique.main_question}
past_evidence (사용자가 과거 타인에게 던진 비판): {critique.past_evidence}
document_excerpt (현재 문서의 관련 구절): {critique.document_excerpt}

{pattern_hint}

predicted_response: 이 사용자가 이 비판을 받았을 때 실제로 할 법한 방어 발화 (1~2문장)
weakness: 그 방어의 구조적 약점 (1문장, 과거 실패와 연결)
"""

        prediction = await self._llm.structured_call(
            model="claude-sonnet-4-6",
            system=_DEFENDER_SYSTEM,
            user=user_prompt,
            response_model=DefensePrediction,
        )
        # matched_pattern_id는 LLM이 아닌 패턴 매칭 결과에서 설정
        matched_id = matched_pattern.pattern_id if matched_pattern else None
        return prediction.model_copy(update={"matched_pattern_id": matched_id})
