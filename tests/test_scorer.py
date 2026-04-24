"""Scorer novelty 테스트."""

from pathlib import Path

import pytest

from mirror_agent.models import Confidence, Critique
from mirror_agent.scorer import NOVELTY_BONUS, REPETITION_PENALTY, Scorer


def _make_critique(rule_id: str, confidence: Confidence) -> Critique:
    return Critique(
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        confidence_label=confidence,
        main_question="test?",
        evidence_questions=[],
        past_evidence="past",
        document_excerpt="excerpt",
    )


def test_no_history_all_novel(tmp_path: Path):
    """히스토리 없으면 모든 규칙이 novelty_bonus 적용."""
    scorer = Scorer(tmp_path)
    critiques = [
        _make_critique("rule_a", Confidence.HIGH),
        _make_critique("rule_b", Confidence.MEDIUM),
    ]
    scored = scorer.score(critiques, "test_doc.md")

    for c in scored:
        assert c.novelty_score == pytest.approx(1.0 + NOVELTY_BONUS)


def test_repeated_rule_gets_penalty(tmp_path: Path):
    """이전 리포트에 있던 규칙은 repetition_penalty 적용."""
    import json
    from datetime import datetime

    doc_dir = tmp_path / "test_doc"
    doc_dir.mkdir()
    history = {
        "document_path": "test_doc.md",
        "generated_at": datetime.utcnow().isoformat(),
        "rule_ids_fired": ["rule_a"],
        "user_responded_rules": [],
    }
    (doc_dir / "20260101_000000_test_doc.history.json").write_text(
        json.dumps(history)
    )

    scorer = Scorer(tmp_path)
    critiques = [
        _make_critique("rule_a", Confidence.HIGH),  # 이전 리포트에 있음
        _make_critique("rule_b", Confidence.HIGH),  # 신규
    ]
    scored = scorer.score(critiques, "test_doc.md")

    rule_a = next(c for c in scored if c.rule_id == "rule_a")
    rule_b = next(c for c in scored if c.rule_id == "rule_b")

    assert rule_a.novelty_score == pytest.approx(1.0 - REPETITION_PENALTY)
    assert rule_b.novelty_score == pytest.approx(1.0 + NOVELTY_BONUS)


def test_novel_rule_scores_higher_than_repeated(tmp_path: Path):
    """신규 규칙이 반복 규칙보다 final_score가 높다 (동일 confidence 기준)."""
    import json
    from datetime import datetime

    doc_dir = tmp_path / "test_doc"
    doc_dir.mkdir()
    history = {
        "document_path": "test_doc.md",
        "generated_at": datetime.utcnow().isoformat(),
        "rule_ids_fired": ["rule_old"],
        "user_responded_rules": [],
    }
    (doc_dir / "20260101_000000_test_doc.history.json").write_text(
        json.dumps(history)
    )

    scorer = Scorer(tmp_path)
    critiques = [
        _make_critique("rule_old", Confidence.HIGH),
        _make_critique("rule_new", Confidence.HIGH),
    ]
    scored = scorer.score(critiques, "test_doc.md")

    assert scored[0].rule_id == "rule_new"
    assert scored[0].final_score > scored[1].final_score


def test_sorted_by_final_score_descending(tmp_path: Path):
    """결과가 final_score 내림차순으로 정렬된다."""
    scorer = Scorer(tmp_path)
    critiques = [
        _make_critique("rule_low", Confidence.MEDIUM),
        _make_critique("rule_high", Confidence.HIGH),
        _make_critique("rule_mid", Confidence.MEDIUM_HIGH),
    ]
    scored = scorer.score(critiques, "test_doc.md")

    scores = [c.final_score for c in scored]
    assert scores == sorted(scores, reverse=True)


def test_history_window_only_last_3(tmp_path: Path):
    """직전 3회 히스토리만 반복 판정에 사용한다."""
    import json
    from datetime import datetime

    doc_dir = tmp_path / "test_doc"
    doc_dir.mkdir()

    # 4회 히스토리: 오래된 것에만 rule_old 존재
    for i, rule_ids in enumerate([["rule_old"], ["rule_a"], ["rule_b"], ["rule_c"]]):
        h = {
            "document_path": "test_doc.md",
            "generated_at": datetime.utcnow().isoformat(),
            "rule_ids_fired": rule_ids,
            "user_responded_rules": [],
        }
        (doc_dir / f"2026010{i}_000000_test_doc.history.json").write_text(
            json.dumps(h)
        )

    scorer = Scorer(tmp_path)
    critiques = [_make_critique("rule_old", Confidence.HIGH)]
    scored = scorer.score(critiques, "test_doc.md")

    # rule_old는 4번째 히스토리(window 밖)에만 있으므로 novelty bonus
    assert scored[0].novelty_score == pytest.approx(1.0 + NOVELTY_BONUS)
