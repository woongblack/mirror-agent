"""비판 스코어링.

final_score = confidence × (1 + novelty_bonus - repetition_penalty)

novelty는 이전 리포트 히스토리와 비교:
- 이전 리포트에 있었던 규칙이면 감점
- 사용자가 이미 답한 규칙이면 추가 감점
- 새로 매칭된 규칙이면 가점
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mirror_agent.models import Critique, ReportHistoryEntry

logger = logging.getLogger(__name__)

_NOVELTY_BONUS = 0.2
_REPETITION_PENALTY = 0.15
_RESPONDED_PENALTY = 0.3


class Scorer:
    """Critique의 final_score를 계산하고 정렬."""

    def __init__(self, reports_dir: Path | str) -> None:
        self._reports_dir = Path(reports_dir)

    def score(
        self,
        critiques: list[Critique],
        document_path: str,
    ) -> list[Critique]:
        """novelty_score와 final_score를 계산하여 정렬된 Critique 반환."""
        history = self._load_history(document_path)
        previously_fired = {rule_id for entry in history for rule_id in entry.rule_ids_fired}
        user_responded = {rule_id for entry in history for rule_id in entry.user_responded_rules}

        scored: list[Critique] = []
        for critique in critiques:
            rid = critique.rule_id

            if rid in user_responded:
                novelty = 1.0 - _RESPONDED_PENALTY
            elif rid in previously_fired:
                novelty = 1.0 - _REPETITION_PENALTY
            else:
                novelty = 1.0 + _NOVELTY_BONUS

            novelty = max(0.1, min(1.5, novelty))
            final = critique.final_score * novelty

            scored.append(
                critique.model_copy(update={"novelty_score": novelty, "final_score": final})
            )

        return sorted(scored, key=lambda c: c.final_score, reverse=True)

    def _load_history(self, document_path: str) -> list[ReportHistoryEntry]:
        """해당 문서에 대한 이전 리포트 기록 로드."""
        if not self._reports_dir.exists():
            return []

        entries: list[ReportHistoryEntry] = []
        for history_file in self._reports_dir.glob("*.history.json"):
            try:
                raw = json.loads(history_file.read_text(encoding="utf-8"))
                entry = ReportHistoryEntry.model_validate(raw)
                if entry.document_path == document_path:
                    entries.append(entry)
            except Exception:
                logger.warning("히스토리 파일 로드 실패: %s", history_file)

        return entries
