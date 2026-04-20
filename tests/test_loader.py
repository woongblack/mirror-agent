"""로더의 기본 동작 검증."""

from pathlib import Path

import pytest

from mirror_agent.loader import load_defense_patterns, load_rules
from mirror_agent.models import Confidence


@pytest.fixture
def rules_dir() -> Path:
    return Path(__file__).parent.parent / "data" / "rules" / "manual-v0.1"


@pytest.fixture
def patterns_path() -> Path:
    return Path(__file__).parent.parent / "data" / "defense-patterns" / "patterns.json"


def test_rules_load_without_error(rules_dir: Path) -> None:
    """모든 수동 규칙 JSON이 Pydantic 스키마에 맞게 파싱되는가."""
    rules = load_rules(rules_dir)
    assert len(rules) == 8, f"활성 규칙 8개 기대, 실제 {len(rules)}개"


def test_rules_have_expected_ids(rules_dir: Path) -> None:
    """예상된 규칙 ID가 모두 존재하는가."""
    rules = load_rules(rules_dir)
    rule_ids = {r.rule_id for r in rules}
    expected = {
        "rule_supplier_first",
        "rule_differentiation_explicit",
        "rule_post_mvp_concreteness",
        "rule_user_need_evidence",
        "rule_solo_operability",
        "rule_hypothetical_language_detector",
        "rule_defensive_response_check",
        "rule_motivation_honesty",
    }
    assert rule_ids == expected


def test_critical_hit_rule_is_high_confidence(rules_dir: Path) -> None:
    """Critical Hit 대상 규칙(rule_supplier_first)이 HIGH confidence여야 함."""
    rules = load_rules(rules_dir)
    critical = next(r for r in rules if r.rule_id == "rule_supplier_first")
    assert critical.confidence == Confidence.HIGH
    assert critical.user_conviction_level == "very_high"


def test_defense_patterns_load(patterns_path: Path) -> None:
    """방어 패턴이 스키마대로 로드되는가."""
    patterns = load_defense_patterns(patterns_path)
    assert len(patterns) >= 4, "최소 4개 방어 패턴 기대"


def test_all_rules_have_evidence_questions(rules_dir: Path) -> None:
    """모든 규칙이 evidence_questions를 갖고 있어야 함."""
    rules = load_rules(rules_dir)
    for rule in rules:
        assert len(rule.evidence_questions) > 0, f"{rule.rule_id}: evidence_questions 비어있음"


def test_trigger_conditions_describe(rules_dir: Path) -> None:
    """trigger_conditions의 LLM용 describe 메서드가 동작하는가."""
    rules = load_rules(rules_dir)
    for rule in rules:
        desc = rule.trigger_conditions.describe_for_llm()
        assert isinstance(desc, str)
        assert len(desc) > 0
