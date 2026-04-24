"""Socratic Agent 테스트.

단위 테스트: 모델 검증, angle/severity 정규화
통합 테스트: 실제 문서 → 질문 생성 (pytest -m integration)
"""

from pathlib import Path

import pytest

from mirror_agent.models import SocraticQuestion

# ---------------------------------------------------------------------------
# 단위 테스트
# ---------------------------------------------------------------------------


def test_socratic_question_model_valid():
    """SocraticQuestion 모델이 정상 생성되는가."""
    q = SocraticQuestion(
        assumption="사용자가 크로스 셀러 룩북을 원한다",
        question="왜 사용자가 이걸 원한다고 가정하는가?",
        angle="market",
        severity="high",
        evidence_from_document="크로스 셀러 AI 룩북 오케스트레이터",
    )
    assert q.angle == "market"
    assert q.severity == "high"


def test_socratic_question_invalid_angle():
    """angle 필드가 허용값 외의 값이면 ValidationError."""
    with pytest.raises(Exception):
        SocraticQuestion(
            assumption="test",
            question="test?",
            angle="invalid_angle",
            severity="high",
            evidence_from_document="test",
        )


def test_socratic_question_invalid_severity():
    """severity 필드가 허용값 외의 값이면 ValidationError."""
    with pytest.raises(Exception):
        SocraticQuestion(
            assumption="test",
            question="test?",
            angle="market",
            severity="extreme",
            evidence_from_document="test",
        )


def test_all_valid_angles():
    """5가지 각도가 모두 유효한가."""
    for angle in ["market", "tech", "operation", "motivation", "competition"]:
        q = SocraticQuestion(
            assumption="test",
            question="test?",
            angle=angle,
            severity="medium",
            evidence_from_document="test",
        )
        assert q.angle == angle


def test_all_valid_severities():
    """3가지 severity가 모두 유효한가."""
    for severity in ["high", "medium", "low"]:
        q = SocraticQuestion(
            assumption="test",
            question="test?",
            angle="tech",
            severity=severity,
            evidence_from_document="test",
        )
        assert q.severity == severity


# ---------------------------------------------------------------------------
# 통합 테스트 (실제 LLM 호출)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_socratic_covers_all_angles():
    """ALLBLUE README → 5가지 각도 각각 최소 1개 질문 생성."""
    import asyncio

    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.llm import LLMClient
    from mirror_agent.socratic import SocraticAgent

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = SocraticAgent(llm, model=settings.model_generator)

    document_text = fixture.read_text()
    metadata = asyncio.run(analyzer.analyze(fixture))
    questions = asyncio.run(agent.interrogate(document_text, metadata))

    assert len(questions) >= 5, f"최소 5개 질문 기대, 실제 {len(questions)}개"

    angles_covered = {q.angle for q in questions}
    required_angles = {"market", "tech", "operation", "motivation", "competition"}
    assert required_angles.issubset(angles_covered), (
        f"미커버 각도: {required_angles - angles_covered}"
    )


@pytest.mark.integration
def test_socratic_evidence_not_empty():
    """모든 질문의 evidence_from_document가 비어 있지 않은가."""
    import asyncio

    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.llm import LLMClient
    from mirror_agent.socratic import SocraticAgent

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = SocraticAgent(llm, model=settings.model_generator)

    document_text = fixture.read_text()
    metadata = asyncio.run(analyzer.analyze(fixture))
    questions = asyncio.run(agent.interrogate(document_text, metadata))

    for q in questions:
        assert len(q.evidence_from_document.strip()) > 10, (
            f"evidence 너무 짧음: '{q.evidence_from_document}'"
        )
