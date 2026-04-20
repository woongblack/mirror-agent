"""문서 분석기.

마크다운 문서를 읽어 DocumentMetadata로 변환.
LLM을 사용해 프로젝트 유형, 공급/수요 구조, 로드맵 유무 등을 추출.
"""

from __future__ import annotations

import re
from pathlib import Path

from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata

_ANALYZER_SYSTEM = """\
당신은 기술 문서(README, PRD, 기획안)를 분석하는 전문가입니다.
주어진 마크다운 문서를 읽고, 지정된 필드를 추출하세요.

엄격한 규칙:
- 문서에 명시적으로 쓰인 내용만 추출하세요.
- 추론하거나 추측하지 마세요.
- 문서에 없는 내용은 null 또는 빈 리스트로 두세요.
- key_excerpts는 각 주제와 직접 관련된 문서 원문 구절을 그대로 복사하세요 (요약 금지).
"""


def _split_sections(text: str) -> dict[str, str]:
    """마크다운을 H2/H3 섹션으로 분리하여 {헤더: 내용} 반환."""
    sections: dict[str, str] = {}
    current_header = "__preamble__"
    current_lines: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+", line):
            sections[current_header] = "\n".join(current_lines).strip()
            current_header = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_header] = "\n".join(current_lines).strip()
    return {k: v for k, v in sections.items() if v}


class DocumentAnalyzer:
    """마크다운 문서에서 메타데이터 추출."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(self, document_path: Path | str) -> DocumentMetadata:
        """문서를 읽어 메타데이터를 반환."""
        path = Path(document_path)
        text = path.read_text(encoding="utf-8")
        sections = _split_sections(text)

        # 섹션 요약을 LLM에 전달 (토큰 절약 + 섹션별 근거 추적)
        sections_block = "\n\n---\n\n".join(
            f"[섹션: {header}]\n{content}" for header, content in sections.items()
        )

        user_prompt = f"""\
다음 마크다운 문서를 분석하여 structured_output 도구를 호출하세요.

문서 경로: {path}

=== 문서 내용 ===
{sections_block}
=================

key_excerpts에는 다음 주제별 원문 구절을 넣으세요 (해당 내용이 있을 때만):
- "supply_side": 공급자/셀러/파트너 확보 관련 구절
- "demand_side": 수요자/사용자/고객 관련 구절
- "differentiation": 차별화/경쟁우위 주장 구절
- "roadmap": 단계별 계획/로드맵 구절
- "motivation": 왜 만드는가/문제 정의 구절
- "tech_stack": 기술 스택 구절
"""

        metadata = await self._llm.structured_call(
            model="claude-haiku-4-5-20251001",
            system=_ANALYZER_SYSTEM,
            user=user_prompt,
            response_model=DocumentMetadata,
        )

        # path는 LLM이 채우지 못하므로 직접 설정
        return metadata.model_copy(update={"path": str(path)})
