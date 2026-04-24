"""Planning Agent 테스트.

단위 테스트: 모델 검증, 조기 종료 로직
통합 테스트: 실제 아이디어 → 기획안 생성 (pytest -m integration)
"""

from pathlib import Path

import pytest

from mirror_agent.models import PlanningDraft, PlanningRound


# ---------------------------------------------------------------------------
# 단위 테스트
# ---------------------------------------------------------------------------


def test_planning_round_model_valid():
    """PlanningRound 모델이 정상 생성되는가."""
    r = PlanningRound(
        round_number=1,
        draft="## 기획안\n내용",
        ambiguity_score=0.4,
        open_questions=["왜?", "어떻게?"],
        changes_from_prev="초안 작성",
    )
    assert r.round_number == 1
    assert r.ambiguity_score == 0.4


def test_planning_round_ambiguity_range():
    """ambiguity_score가 0~1 범위를 벗어나면 ValidationError."""
    with pytest.raises(Exception):
        PlanningRound(
            round_number=1,
            draft="draft",
            ambiguity_score=1.5,
        )

    with pytest.raises(Exception):
        PlanningRound(
            round_number=1,
            draft="draft",
            ambiguity_score=-0.1,
        )


def test_planning_draft_model_valid():
    """PlanningDraft 모델이 정상 생성되는가."""
    rounds = [
        PlanningRound(round_number=1, draft="draft1", ambiguity_score=0.4),
        PlanningRound(round_number=2, draft="draft2", ambiguity_score=0.15),
    ]
    d = PlanningDraft(
        idea_input="원본 아이디어",
        rounds=rounds,
        final_draft="최종 기획안",
        final_ambiguity=0.15,
        converged=True,
    )
    assert d.converged is True
    assert len(d.rounds) == 2


def test_planning_draft_converged_false():
    """ambiguity가 수렴하지 않으면 converged=False."""
    rounds = [
        PlanningRound(round_number=i, draft=f"draft{i}", ambiguity_score=0.5)
        for i in range(1, 4)
    ]
    d = PlanningDraft(
        idea_input="아이디어",
        rounds=rounds,
        final_draft="최종",
        final_ambiguity=0.5,
        converged=False,
    )
    assert d.converged is False


def test_max_rounds_not_exceeded():
    """MAX_ROUNDS를 초과해서 순환하지 않는가 (모델 레벨)."""
    rounds = [
        PlanningRound(round_number=i, draft=f"draft{i}", ambiguity_score=0.3)
        for i in range(1, 4)
    ]
    d = PlanningDraft(
        idea_input="아이디어",
        rounds=rounds,
        final_draft="최종",
        final_ambiguity=0.3,
        converged=False,
    )
    assert len(d.rounds) <= 3


# ---------------------------------------------------------------------------
# 통합 테스트
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_planner_produces_structured_draft():
    """아이디어 파일 입력 → 구조화된 기획안 생성."""
    import asyncio

    from mirror_agent.config import Settings
    from mirror_agent.planner import PlanningAgent

    fixture = Path(__file__).parent / "fixtures" / "mirror-agent-idea.md"
    settings = Settings.from_env()
    agent = PlanningAgent(settings)

    idea_text = fixture.read_text()
    draft = asyncio.run(agent.plan(idea_text))

    assert len(draft.rounds) >= 1
    assert len(draft.rounds) <= 3
    assert len(draft.final_draft) > 100

    required_sections = ["문제", "사용자", "해결"]
    for section in required_sections:
        assert section in draft.final_draft, f"필수 섹션 누락: {section}"


@pytest.mark.integration
def test_planner_ambiguity_decreases_or_converges():
    """라운드가 진행될수록 ambiguity가 감소하거나 수렴한다."""
    import asyncio

    from mirror_agent.config import Settings
    from mirror_agent.planner import PlanningAgent

    fixture = Path(__file__).parent / "fixtures" / "mirror-agent-idea.md"
    settings = Settings.from_env()
    agent = PlanningAgent(settings)

    idea_text = fixture.read_text()
    draft = asyncio.run(agent.plan(idea_text))

    if len(draft.rounds) > 1:
        first = draft.rounds[0].ambiguity_score
        last = draft.rounds[-1].ambiguity_score
        assert last <= first, f"ambiguity가 증가함: {first} → {last}"

    if draft.converged:
        assert draft.final_ambiguity <= 0.2
