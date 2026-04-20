"""방어 예측기 — Mirror Agent의 고유 가치.

각 비판에 대해 사용자가 어떻게 방어할지 예측하고, 그 방어의 약점을 선제적으로 지적한다.
DefensePattern DB를 참조하여 유사 패턴이 있으면 매칭, 없으면 LLM 추론.

이 모듈이 없으면 Historical Agent는 그냥 규칙 기반 비판 도구일 뿐이다.
방어 예측이 있어야 "당신의 과거 궤적을 아는 비판자"가 된다.

TODO(v0.1):
- [ ] 비판-방어패턴 매칭 (의미 유사도 or 카테고리)
- [ ] 매칭된 패턴으로 DefensePrediction 생성
- [ ] 매칭 없으면 LLM으로 추론 (conversation-log.md 맥락 주입)
- [ ] 매칭 pattern_id를 기록하여 추적
"""

from __future__ import annotations

from mirror_agent.llm import LLMClient
from mirror_agent.models import Critique, DefensePattern, DefensePrediction


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
        """단일 비판에 대한 방어 예측."""
        raise NotImplementedError("다음 세션에서 구현")
