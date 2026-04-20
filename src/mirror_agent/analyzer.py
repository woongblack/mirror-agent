"""문서 분석기.

마크다운 문서를 읽어 DocumentMetadata로 변환.
LLM을 사용해 프로젝트 유형, 공급/수요 구조, 로드맵 유무 등을 추출.

TODO(v0.1):
- [ ] 마크다운 파싱 (섹션 분리)
- [ ] LLM 호출로 메타데이터 추출
- [ ] key_excerpts 수집 (Evidence용 원문 보관)
"""

from __future__ import annotations

from pathlib import Path

from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata


class DocumentAnalyzer:
    """마크다운 문서에서 메타데이터 추출."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(self, document_path: Path | str) -> DocumentMetadata:
        """문서를 읽어 메타데이터를 반환."""
        raise NotImplementedError("다음 세션에서 구현")
