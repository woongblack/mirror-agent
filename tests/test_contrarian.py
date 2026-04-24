"""Contrarian Agent 테스트.

단위 테스트: 모델 검증, severity 정규화
통합 테스트: 실제 문서 → 반대 시나리오 생성 (pytest -m integration)
"""

from pathlib import Path

import pytest

from mirror_agent.models import ContrarianChallenge


# ---------------------------------------------------------------------------
# 단위 테스트
# ---------------------------------------------------------------------------


def test_contrarian_challenge_model_valid():
    """ContrarianChallenge 모델이 정상 생성되는가."""
    c = ContrarianChallenge(
        claim="크로스 셀러 룩북이 전환율을 높인다",
        counter_premise="오히려 낮출 수도 있다",
        counter_scenario="결제 경로가 분기되면 인지 부하가 증가하여 이탈률이 높아진다",
        challenge_question="룩북 내 결제 경로 분기가 전환율을 낮추지 않는가?",
        implication="Phase 1 검증 지표를 아이템별 CTR로 바꿔야 한다",
        severity="high",
        evidence_from_document="크로스 셀러 AI 룩북 오케스트레이터",
    )
    assert c.severity == "high"
    assert len(c.counter_scenario) > 10


def test_contrarian_challenge_invalid_severity():
    """severity가 허용값 외의 값이면 ValidationError."""
    with pytest.raises(Exception):
        ContrarianChallenge(
            claim="test claim",
            counter_premise="test premise",
            counter_scenario="test scenario",
            challenge_question="test question?",
            implication="test implication",
            severity="extreme",
            evidence_from_document="test",
        )


def test_contrarian_all_valid_severities():
    """3가지 severity가 모두 유효한가."""
    for severity in ["high", "medium", "low"]:
        c = ContrarianChallenge(
            claim="test",
            counter_premise="test",
            counter_scenario="충분히 긴 구체적 시나리오 텍스트",
            challenge_question="test?",
            implication="test",
            severity=severity,
            evidence_from_document="test",
        )
        assert c.severity == severity


def test_contrarian_counter_scenario_required():
    """counter_scenario 없으면 ValidationError."""
    with pytest.raises(Exception):
        ContrarianChallenge(
            claim="test",
            counter_premise="test",
            challenge_question="test?",
            implication="test",
            severity="high",
            evidence_from_document="test",
        )


# ---------------------------------------------------------------------------
# 통합 테스트 (실제 LLM 호출)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_contrarian_generates_minimum_challenges():
    """ALLBLUE README → 최소 3개 반대 시나리오 생성."""
    import asyncio

    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.contrarian import ContrarianAgent
    from mirror_agent.llm import LLMClient

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = ContrarianAgent(llm, model=settings.model_generator)

    document_text = fixture.read_text()
    metadata = asyncio.run(analyzer.analyze(fixture))
    challenges = asyncio.run(agent.challenge(document_text, metadata))

    assert len(challenges) >= 3, f"최소 3개 기대, 실제 {len(challenges)}개"


@pytest.mark.integration
def test_contrarian_scenario_is_concrete():
    """각 반대 시나리오가 구체적인가 (counter_scenario 50자 이상)."""
    import asyncio

    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.contrarian import ContrarianAgent
    from mirror_agent.llm import LLMClient

    fixture = Path(__file__).parent / "fixtures" / "allblue-readme-snapshot.md"
    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = ContrarianAgent(llm, model=settings.model_generator)

    document_text = fixture.read_text()
    metadata = asyncio.run(analyzer.analyze(fixture))
    challenges = asyncio.run(agent.challenge(document_text, metadata))

    for c in challenges:
        assert len(c.counter_scenario) >= 50, (
            f"counter_scenario 너무 짧음 ({len(c.counter_scenario)}자): '{c.counter_scenario}'"
        )
        assert len(c.implication) > 10, "implication이 비어 있음"
