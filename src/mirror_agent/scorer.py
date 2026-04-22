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
        """novelty_score와 final_score를 계산하여 정렬된 Critique 반환."""
        raise NotImplementedError("다음 세션에서 구현")

    def _load_history(self, document_path: str) -> list[ReportHistoryEntry]:
        """해당 문서에 대한 이전 리포트 기록 로드."""
        raise NotImplementedError("다음 세션에서 구현")