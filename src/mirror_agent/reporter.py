"""리포트 렌더러.

Report 객체를 사용자가 읽는 마크다운으로 변환.
방어 예측은 접힌 상태로 표시 (먼저 비판에 집중, 방어 예측은 확인용).

TODO(v0.1):
- [ ] Markdown 템플릿
- [ ] 상위 N개 vs 접힌 영역 구분
- [ ] Evidence 구절 인용 포맷
- [ ] 방어 예측 섹션 (<details> 접기)
- [ ] 파일로 저장 (data/reports/{date}_{document}.md)
"""

from __future__ import annotations

from pathlib import Path

from mirror_agent.models import Report


class Reporter:
    """Report 객체를 마크다운으로 렌더링."""

    def render(self, report: Report) -> str:
        """Report → Markdown 문자열."""
        raise NotImplementedError("다음 세션에서 구현")

    def save(self, report: Report, output_dir: Path | str) -> Path:
        """렌더링된 리포트를 파일로 저장하고 경로 반환."""
        raise NotImplementedError("다음 세션에서 구현")
