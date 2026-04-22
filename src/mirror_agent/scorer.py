"""비판 스코어링.

final_score = confidence × (1 + novelty_bonus - repetition_penalty)

novelty는 이전 리포트 히스토리와 비교:
- 이전 리포트에 있었던 규칙이면 감점
- 사용자가 이미 답한 규칙이면 추가 감점
- 새로 매칭된 규칙이면 가점

TODO(v0.1):
- [ ] 리포트 히스토리 로더 (data/reports/ 탐색)
- [ ] novelty_score 계산
- [ ] final_score 계산 및 Critique 업데이트
- [ ] 정렬 + 상위 N개 선택
"""

from __future__ import annotations

from pathlib import Path

from mirror_agent.models import Critique, ReportHistoryEntry


class Scorer:
    """Critique의 final_score를 계산하고 정렬."""

    def __init__(self, reports_dir: Path | str) -> None:
        self._reports_dir = Path(reports_dir)

    def score(
        self,
        critiques: list[Critique],
        document_path: str,
    ) -> list[Critique]:
        """confidence_label 기준 정렬. novelty 계산은 v0.2에서 구현."""
        _ORDER = {"high": 0, "medium_high": 1, "medium": 2, "seed": 3}
        return sorted(critiques, key=lambda c: _ORDER.get(c.confidence_label.value, 9))

    def _load_history(self, document_path: str) -> list[ReportHistoryEntry]:
        """해당 문서에 대한 이전 리포트 기록 로드."""
        return []  # v0.2에서 구현