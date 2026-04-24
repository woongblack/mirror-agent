"""Orchestrator 테스트.

단위 테스트: UnifiedItem 정렬, graceful degradation, 모델 검증
통합 테스트: 3개 에이전트 병렬 실행 (pytest -m integration)
"""

import pytest

from mirror_agent.models import ContrarianChallenge, Critique, SocraticQuestion, UnifiedItem
from mirror_agent.orchestrator import _merge_and_rank


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_unified(source: str, severity: str, question: str = "test?") -> UnifiedItem:
    return UnifiedItem(
        source_agent=source,
        severity=severity,
        question=question,
        evidence="test evidence",
    )


# ---------------------------------------------------------------------------
# UnifiedItem 단위 테스트
# ---------------------------------------------------------------------------


def test_unified_item_severity_rank():
    """`high` < `medium` < `low` 순서로 rank가 낮아야 한다."""
    high = _make_unified("historical", "high")
    medium = _make_unified("socratic", "medium")
    low = _make_unified("contrarian", "low")

    assert high.severity_rank < medium.severity_rank
    assert medium.severity_rank < low.severity_rank


def test_unified_item_invalid_severity():
    """허용되지 않는 severity는 ValidationError."""
    with pytest.raises(Exception):
        UnifiedItem(
            source_agent="historical",
            severity="critical",
            question="test?",
            evidence="test",
        )


def test_unified_item_invalid_source_agent():
    """허용되지 않는 source_agent는 ValidationError."""
    with pytest.raises(Exception):
        UnifiedItem(
            source_agent="unknown_agent",
            severity="high",
            question="test?",
            evidence="test",
        )


# ---------------------------------------------------------------------------
# _merge_and_rank 단위 테스트
# ---------------------------------------------------------------------------


def test_merge_rank_severity_order():
    """high가 medium보다 앞에 정렬되어야 한다."""
    from mirror_agent.models import Confidence, Critique, DefensePrediction

    critique_medium = Critique(
        rule_id="rule_a",
        rule_name="Rule A",
        confidence_label=Confidence.MEDIUM,
        main_question="medium question?",
        evidence_questions=[],
        past_evidence="past",
        document_excerpt="excerpt",
        novelty_score=1.0,
        final_score=0.5,
    )

    question_high = SocraticQuestion(
        assumption="high assumption",
        question="high question?",
        angle="market",
        severity="high",
        evidence_from_document="evidence",
    )

    items = _merge_and_rank([critique_medium], [question_high], [])

    assert items[0].severity == "high"
    assert items[1].severity == "medium"


def test_merge_same_severity_historical_first():
    """동일 severity면 historical이 socratic보다 앞에 온다."""
    from mirror_agent.models import Confidence, Critique

    critique_high = Critique(
        rule_id="rule_b",
        rule_name="Rule B",
        confidence_label=Confidence.HIGH,
        main_question="historical high?",
        evidence_questions=[],
        past_evidence="past",
        document_excerpt="excerpt",
        novelty_score=1.0,
        final_score=0.9,
    )
    question_high = SocraticQuestion(
        assumption="assumption",
        question="socratic high?",
        angle="tech",
        severity="high",
        evidence_from_document="evidence",
    )

    items = _merge_and_rank([critique_high], [question_high], [])

    assert items[0].source_agent == "historical"
    assert items[1].source_agent == "socratic"


def test_merge_empty_agents():
    """모든 에이전트 결과가 비어 있어도 빈 리스트 반환."""
    items = _merge_and_rank([], [], [])
    assert items == []


def test_merge_single_agent():
    """하나의 에이전트 결과만 있어도 정상 동작."""
    question = SocraticQuestion(
        assumption="solo assumption",
        question="solo question?",
        angle="market",
        severity="high",
        evidence_from_document="evidence",
    )
    items = _merge_and_rank([], [question], [])
    assert len(items) == 1
    assert items[0].source_agent == "socratic"


# ---------------------------------------------------------------------------
# 통합 테스트
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_orchestrator_runs_all_agents():
    """3개 에이전트 모두 결과를 반환하고 FullReport를 생성한다."""
    import asyncio
    from pathlib import Path

    from mirror_agent.config import Settings
    from mirror_agent.orchestrator import Orchestrator

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    orch = Orchestrator(settings)
    report = asyncio.run(orch.run(fixture))

    assert len(report.historical_critiques) > 0
    assert len(report.socratic_questions) > 0
    assert len(report.contrarian_challenges) > 0
    assert len(report.top_items) == settings.display_top_n
    assert report.total_items == (
        len(report.top_items) + len(report.collapsed_items)
    )


@pytest.mark.integration
def test_orchestrator_top_items_are_high_severity():
    """상위 3개가 high severity 항목을 우선 포함하는가."""
    import asyncio
    from pathlib import Path

    from mirror_agent.config import Settings
    from mirror_agent.orchestrator import Orchestrator

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    orch = Orchestrator(settings)
    report = asyncio.run(orch.run(fixture))

    severities = [item.severity for item in report.top_items]
    assert "high" in severities, "상위 3개에 high severity 항목이 없음"
