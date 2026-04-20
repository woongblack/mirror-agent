"""규칙 JSON 파일 로더.

data/rules/manual-v0.1/ 하위의 모든 JSON을 읽어 Rule 객체로 파싱한다.
SEED 상태 규칙은 기본적으로 제외한다 (historical-agent-plan.md 정책).
"""

from __future__ import annotations

import json
from pathlib import Path

from mirror_agent.models import DefensePattern, Rule


DEFAULT_RULES_DIR = Path("data/rules/manual-v0.1")
DEFAULT_PATTERNS_PATH = Path("data/defense-patterns/patterns.json")


def load_rules(
    rules_dir: Path | str = DEFAULT_RULES_DIR,
    include_seed: bool = False,
) -> list[Rule]:
    """규칙 디렉토리에서 모든 JSON을 Rule 객체로 로드.

    Args:
        rules_dir: 규칙 JSON이 담긴 디렉토리
        include_seed: SEED 상태 규칙 포함 여부. 기본 False (활성 규칙만)

    Returns:
        Rule 객체 리스트. 활성 규칙만 기본 포함.

    Raises:
        FileNotFoundError: 디렉토리 자체가 없을 때
        ValidationError: JSON 구조가 스키마와 맞지 않을 때
    """
    rules_dir = Path(rules_dir)
    if not rules_dir.exists():
        raise FileNotFoundError(f"규칙 디렉토리 없음: {rules_dir}")

    rules: list[Rule] = []
    for json_file in sorted(rules_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        rule = Rule.model_validate(data)
        if rule.is_active or include_seed:
            rules.append(rule)

    return rules


def load_defense_patterns(
    patterns_path: Path | str = DEFAULT_PATTERNS_PATH,
) -> list[DefensePattern]:
    """방어 패턴 JSON을 로드.

    Args:
        patterns_path: patterns.json 경로

    Returns:
        DefensePattern 리스트
    """
    patterns_path = Path(patterns_path)
    if not patterns_path.exists():
        # 방어 패턴은 없어도 동작해야 함 (빈 리스트 반환)
        return []

    with open(patterns_path, encoding="utf-8") as f:
        data = json.load(f)

    patterns_data = data.get("patterns", [])
    return [DefensePattern.model_validate(p) for p in patterns_data]
