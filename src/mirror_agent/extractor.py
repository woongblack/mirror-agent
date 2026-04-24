"""conversation-log.md 등 과거 대화 로그에서 비판 발화를 자동 추출.

출력: data/critiques/{source_slug}.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from mirror_agent.config import Settings
from mirror_agent.llm import LLMClient
from mirror_agent.models import CritiqueUnit, TargetType

logger = logging.getLogger(__name__)

_SYSTEM = """\
당신은 사용자 발화에서 비판 패턴을 추출하는 전문가입니다.

입력은 이미 사용자(정재웅)의 발화만 전처리된 텍스트입니다. Claude의 발화는 포함되지 않습니다.

## 비판 발화의 정의 (이 조건을 모두 충족해야 추출)

- 특정 프로젝트·결정·주장의 구조적 결함, 논리적 모순, 검증 부재를 지적한 발화
- 지적의 대상이 명확하다 (어떤 프로젝트의 어떤 결정인지 특정 가능)
- 다른 기획 문서에도 적용 가능한 패턴을 담고 있다

## 추출 제외 기준 (하나라도 해당하면 제외)

- 단순 정보 요청, 파일 공유, 배경 설명 (비판 의도 없는 사실 전달)
- 칭찬, 동의, 감사 발화
- "~맞아?", "~인 거야?" 형태의 확인 질문
- 용어 재정의 또는 명칭 변경 요청
- 비판 의도가 불분명하거나 추측이 필요한 발화

## 원칙

- raw_text는 원문 그대로 인용한다. 요약하지 않는다.
- 비판이 없으면 빈 리스트를 반환한다.
- 확신이 없으면 추출하지 않는다. False Positive가 False Negative보다 나쁘다.
"""


class _RawCritique(BaseModel):
    raw_text: str
    target_project: str
    target_type: Literal[
        "team_project",
        "personal_project",
        "tech_decision",
        "market_judgment",
        "platform",
        "marketplace",
        "two_sided_market",
    ]
    domain: str
    critique_category: str
    emotional_marker: Literal["neutral", "sharp", "frustrated", "curious", "skeptical"]
    context: str


class _RawCritiqueList(BaseModel):
    critiques: list[_RawCritique]


class Extractor:
    """과거 대화 로그에서 비판 발화를 추출한다."""

    def __init__(self, settings: Settings) -> None:
        self._llm = LLMClient(settings)
        self._model = settings.model_matcher

    async def extract(self, document_path: Path) -> list[CritiqueUnit]:
        text = document_path.read_text()
        utterances = _extract_user_utterances(text)

        if not utterances:
            # 사용자 입력 마커 없으면 ## 섹션 단위로 fallback
            logger.warning("'### 사용자 입력' 마커 없음. 섹션 단위로 fallback 처리.")
            utterances = [
                (section_name, _to_anchor(section_name), section_text)
                for section_name, section_text in _split_by_heading(text)
            ]

        all_raw: list[tuple[str, str, _RawCritique]] = []
        for phase_name, anchor, utterance_text in utterances:
            logger.info("추출 중: %s", phase_name)
            result = await self._llm.structured_call(
                model=self._model,
                system=_SYSTEM,
                user=f"Phase: {phase_name}\n\n---\n\n{utterance_text}",
                response_model=_RawCritiqueList,
            )
            for raw in result.critiques:
                all_raw.append((document_path.name, anchor, raw))

        units = [
            CritiqueUnit(
                id=f"critique_{i + 1:03d}",
                source=f"{filename}#{anchor}",
                raw_text=raw.raw_text,
                target_project=raw.target_project,
                target_type=TargetType(raw.target_type),
                domain=raw.domain,
                critique_category=raw.critique_category,
                emotional_marker=raw.emotional_marker,
                context=raw.context,
                extracted_at=datetime.utcnow(),
            )
            for i, (filename, anchor, raw) in enumerate(all_raw)
        ]

        logger.info("총 %d개 비판 추출 완료", len(units))
        return units

    async def save(self, units: list[CritiqueUnit], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [u.model_dump(mode="json") for u in units]
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info("%d개 비판 저장 → %s", len(units), output_path)


def _extract_user_utterances(text: str) -> list[tuple[str, str, str]]:
    """'### 사용자 입력' 하위 blockquote만 추출.

    Returns: list of (phase_name, anchor, utterance_text)
    """
    phase_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    user_input_pattern = re.compile(r"^### 사용자[^\n]*$", re.MULTILINE)
    next_heading_pattern = re.compile(r"^###", re.MULTILINE)

    phase_matches = list(phase_pattern.finditer(text))
    results = []

    for i, phase_match in enumerate(phase_matches):
        phase_name = phase_match.group(1).strip()
        phase_start = phase_match.start()
        phase_end = phase_matches[i + 1].start() if i + 1 < len(phase_matches) else len(text)
        phase_text = text[phase_start:phase_end]

        user_input_match = user_input_pattern.search(phase_text)
        if not user_input_match:
            continue

        after_header = phase_text[user_input_match.end():]
        next_heading_match = next_heading_pattern.search(after_header)
        user_section = after_header[: next_heading_match.start()] if next_heading_match else after_header

        utterance_lines = []
        for line in user_section.splitlines():
            stripped = line.strip()
            if stripped.startswith("> "):
                utterance_lines.append(stripped[2:])
            elif stripped == ">":
                utterance_lines.append("")

        utterance_text = "\n".join(utterance_lines).strip()
        if utterance_text:
            results.append((phase_name, _to_anchor(phase_name), utterance_text))

    return results


def _split_by_heading(text: str) -> list[tuple[str, str]]:
    """## 기준으로 섹션 분리. fallback용."""
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        return [("document", text)]

    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[start:end]))

    return sections


def _to_anchor(section_name: str) -> str:
    """섹션명 → URL-safe 앵커."""
    anchor = section_name.lower()
    anchor = re.sub(r"[^a-z0-9가-힣\s]", "", anchor)
    anchor = re.sub(r"\s+", "", anchor)
    return anchor[:30]
