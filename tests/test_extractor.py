"""Extractor 테스트.

단위 테스트: LLM 호출 없는 순수 함수 (_extract_user_utterances, _to_anchor, _split_by_heading)
통합 테스트: 실제 conversation-log.md → CritiqueUnit 추출 검증 (pytest -m integration)
"""

from pathlib import Path

import pytest

from mirror_agent.extractor import _extract_user_utterances, _split_by_heading, _to_anchor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LOG = """\
# 대화 로그

## Phase 1 — 초기 요청

### 사용자 입력

> "플랜에 대해서 평가해줘."
> "이 부분에서 헛점이 많을 것 같은데."

### Claude의 평가 요약

**강점:**
- 구조가 탄탄함

**우려:**
- 에이전트 5개가 필요한가?

---

## Phase 2 — 전환점

### 사용자 입력

> "솔직히 얘기하면 이 기획의 문제점이 보여."

### Claude의 분석

분석 내용...

---

## Phase 3 — 사용자 입력 없는 섹션

### Claude의 제안

제안 내용만 있는 섹션.
"""

LOG_NO_MARKERS = """\
# 일반 문서

## 섹션 A

내용 A

## 섹션 B

내용 B
"""


# ---------------------------------------------------------------------------
# _extract_user_utterances 단위 테스트
# ---------------------------------------------------------------------------


def test_extracts_only_blockquotes_from_user_input_sections():
    """사용자 입력 섹션의 blockquote만 추출한다."""
    results = _extract_user_utterances(SAMPLE_LOG)

    assert len(results) == 2  # Phase 1, Phase 2만 (Phase 3는 사용자 입력 없음)


def test_extracted_text_contains_user_words():
    """추출된 텍스트가 사용자 발화를 포함한다."""
    results = _extract_user_utterances(SAMPLE_LOG)

    phase1_text = results[0][2]
    assert "플랜에 대해서 평가해줘" in phase1_text
    assert "헛점이 많을 것 같은데" in phase1_text


def test_claude_section_content_not_included():
    """Claude 섹션 내용은 추출되지 않는다."""
    results = _extract_user_utterances(SAMPLE_LOG)

    all_text = " ".join(r[2] for r in results)
    assert "에이전트 5개가 필요한가" not in all_text
    assert "구조가 탄탄함" not in all_text
    assert "분석 내용" not in all_text


def test_skips_section_without_user_input_marker():
    """'### 사용자 입력' 마커 없는 섹션은 건너뛴다."""
    results = _extract_user_utterances(SAMPLE_LOG)

    phase_names = [r[0] for r in results]
    assert not any("Phase 3" in name for name in phase_names)


def test_returns_empty_when_no_markers():
    """'### 사용자 입력' 마커가 전혀 없으면 빈 리스트를 반환한다."""
    results = _extract_user_utterances(LOG_NO_MARKERS)
    assert results == []


def test_anchor_is_included_in_result():
    """결과에 앵커가 포함된다."""
    results = _extract_user_utterances(SAMPLE_LOG)

    for phase_name, anchor, text in results:
        assert isinstance(anchor, str)
        assert len(anchor) > 0


# ---------------------------------------------------------------------------
# _to_anchor 단위 테스트
# ---------------------------------------------------------------------------


def test_to_anchor_lowercases():
    assert _to_anchor("Phase 7") == "phase7"


def test_to_anchor_removes_special_chars():
    assert "—" not in _to_anchor("Phase 7 — 전환점")
    assert "-" not in _to_anchor("Phase 7 — 전환점")


def test_to_anchor_truncates_at_30():
    long_name = "Phase 1 매우 긴 섹션명이 여기에 있을 수 있다"
    assert len(_to_anchor(long_name)) <= 30


def test_to_anchor_preserves_korean():
    anchor = _to_anchor("Phase 6 — DEKK 공개")
    assert "dekk" in anchor or "dekk공개" in anchor or "phase6" in anchor


# ---------------------------------------------------------------------------
# _split_by_heading 단위 테스트
# ---------------------------------------------------------------------------


def test_split_by_heading_correct_count():
    sections = _split_by_heading(SAMPLE_LOG)
    # "# 대화 로그"는 ## 아니므로 제외, ## Phase 1~3 = 3개
    assert len(sections) == 3


def test_split_by_heading_no_headings():
    sections = _split_by_heading("헤딩 없는 텍스트\n내용")
    assert len(sections) == 1
    assert sections[0][0] == "document"


def test_split_preserves_content():
    sections = _split_by_heading(SAMPLE_LOG)
    phase1 = next(s for s in sections if "Phase 1" in s[0])
    assert "플랜에 대해서 평가해줘" in phase1[1]


# ---------------------------------------------------------------------------
# 통합 테스트 (실제 LLM 호출 — pytest -m integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_extractor_covers_manual_rules():
    """실제 conversation-log.md 추출 결과가 수동 규칙 3개 이상의 패턴을 포함한다."""
    import asyncio

    from mirror_agent.config import Settings
    from mirror_agent.extractor import Extractor

    conversation_log = Path(__file__).parent.parent / "docs" / "origin" / "conversation-log.md"
    assert conversation_log.exists()

    settings = Settings.from_env()
    extractor = Extractor(settings)
    units = asyncio.run(extractor.extract(conversation_log))

    assert len(units) >= 3, f"최소 3개 비판 추출 기대, 실제 {len(units)}개"

    categories = {u.critique_category for u in units}
    assert len(categories) >= 2, "최소 2가지 이상 비판 카테고리 기대"


@pytest.mark.integration
def test_extractor_no_claude_utterances_in_output():
    """추출 결과에 Claude 발화('에이전트 5개가 필요한가' 등)가 포함되지 않는다."""
    import asyncio

    from mirror_agent.config import Settings
    from mirror_agent.extractor import Extractor

    conversation_log = Path(__file__).parent.parent / "docs" / "origin" / "conversation-log.md"
    settings = Settings.from_env()
    extractor = Extractor(settings)
    units = asyncio.run(extractor.extract(conversation_log))

    claude_phrases = [
        "에이전트 5개가 정말 필요한가",
        "무한루프 위험",
        "JSON 룰셋",
        "90% 이상 공수 절감",
    ]
    for unit in units:
        for phrase in claude_phrases:
            assert phrase not in unit.raw_text, f"Claude 발화가 추출됨: {unit.raw_text}"
