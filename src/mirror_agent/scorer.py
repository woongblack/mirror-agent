"""비판 스코어링.

final_score = confidence_value × novelty_score
novelty_score = 1 + novelty_bonus - repetition_penalty

novelty 계산:
- 직전 3회 리포트에 없던 규칙 → novelty_bonus +0.2
- 직전 3회 리포트에 이미 있던 규칙 → repetition_penalty -0.3
- 히스토리 없으면 모두 신규로 처리
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mirror_agent.models import Critique, ReportHistoryEntry

logger = logging.getLogger(__name__)

_CONFIDENCE_SCORES: dict[str, float] = {
    "high": 0.95,
    "medium_high": 0.75,
    "medium": 0.55,
    "seed": 0.25,
}

NOVELTY_BONUS = 0.2
REPETITION_PENALTY = 0.3
HISTORY_WINDOW = 3


class Scorer:
    """Critique의 final_score를 계산하고 정렬."""

    def __init__(self, reports_dir: Path | str) -> None:
        self._reports_dir = Path(reports_dir)

    def score(
        self,
        critiques: list[Critique],
        document_path: str,
    ) -> list[Critique]:
        """novelty_score + final_score 계산 후 final_score 내림차순 정렬."""
        history = self._load_history(document_path)

        # 직전 HISTORY_WINDOW회에 등장한 rule_id 집합
        recent: set[str] = set()
        for entry in history[-HISTORY_WINDOW:]:
            recent.update(entry.rule_ids_fired)

        if recent:
            logger.debug("히스토리 %d개 로드 — 반복 규칙 %d개", len(history), len(recent))

        scored: list[Critique] = []
        for c in critiques:
            conf = _CONFIDENCE_SCORES.get(c.confidence_label.value, 0.5)

            if c.rule_id in recent:
                novelty = 1.0 - REPETITION_PENALTY  # 0.7
            else:
                novelty = 1.0 + NOVELTY_BONUS  # 1.2

            final = round(conf * novelty, 4)
            scored.append(c.model_copy(update={
                "novelty_score": novelty,
                "final_score": final,
            }))

        return sorted(scored, key=lambda c: c.final_score, reverse=True)

    def _load_history(self, document_path: str) -> list[ReportHistoryEntry]:
        """해당 문서에 대한 이전 리포트 기록 로드."""
        doc_stem = Path(document_path).stem
        history_dir = self._reports_dir / doc_stem

        if not history_dir.exists():
            return []

        entries: list[ReportHistoryEntry] = []
        for path in sorted(history_dir.glob("*.history.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entries.append(ReportHistoryEntry.model_validate(data))
            except Exception:
                logger.warning("히스토리 파일 파싱 실패: %s", path)

        return entries
