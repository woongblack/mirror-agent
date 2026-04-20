"""Mirror Agent 파이프라인.

전체 플로우:
    문서 경로 입력
        → Analyzer: 문서 → DocumentMetadata
        → Matcher: 규칙 × 문서 → MatchResult[] (병렬)
        → Generator: Match → Critique[] (병렬)
        → Defender: Critique → DefensePrediction 첨부 (병렬)
        → Scorer: novelty + final_score 계산, 정렬
        → Reporter: Report → Markdown
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from mirror_agent.analyzer import DocumentAnalyzer
from mirror_agent.config import (
    DEFENSE_PATTERNS_PATH,
    REPORTS_DIR,
    RULES_DIR,
    Settings,
)
from mirror_agent.defender import DefensePredictor
from mirror_agent.generator import CritiqueGenerator
from mirror_agent.llm import LLMClient
from mirror_agent.loader import load_defense_patterns, load_rules
from mirror_agent.matcher import RuleMatcher
from mirror_agent.models import Critique, MatchResult, Report, Rule
from mirror_agent.reporter import Reporter
from mirror_agent.scorer import Scorer

logger = logging.getLogger(__name__)
console = Console()


async def _generate_with_defense(
    rule: Rule,
    match: MatchResult,
    generator: CritiqueGenerator,
    defender: DefensePredictor,
) -> Critique | None:
    """단일 규칙에 대해 Critique 생성 + 방어 예측. 실패 시 None 반환."""
    try:
        critique = await generator.generate(rule, match)
        critique.defense_prediction = await defender.predict(critique)
        return critique
    except Exception:
        logger.warning("규칙 처리 실패, 건너뜀: %s", rule.rule_id, exc_info=True)
        return None


async def run_mirror_review(document_path: Path | str) -> Report:
    """Mirror Agent의 메인 파이프라인 진입점.

    Args:
        document_path: 검토할 마크다운 문서 경로

    Returns:
        Report 객체 (final_score 내림차순, 상위 N개 표시)
    """
    settings = Settings.from_env()
    llm = LLMClient(settings)

    rules = load_rules(RULES_DIR)
    patterns = load_defense_patterns(DEFENSE_PATTERNS_PATH)

    analyzer = DocumentAnalyzer(llm)
    matcher = RuleMatcher(llm, settings)
    generator = CritiqueGenerator(llm)
    defender = DefensePredictor(llm, patterns)
    scorer = Scorer(REPORTS_DIR)

    document_text = Path(document_path).read_text(encoding="utf-8")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("문서 분석 중...", total=None)
        metadata = await analyzer.analyze(document_path)

        progress.update(task, description=f"규칙 {len(rules)}개 매칭 중...")
        matches = await matcher.match_all(rules, document_text, metadata)

        console.print(f"[green]매칭된 규칙: {len(matches)}개[/green]")

        progress.update(task, description="비판 생성 + 방어 예측 중...")
        rules_by_id = {r.rule_id: r for r in rules}
        tasks = [
            _generate_with_defense(rules_by_id[m.rule_id], m, generator, defender)
            for m in matches
            if m.rule_id in rules_by_id
        ]
        results = await asyncio.gather(*tasks)

    critiques = [c for c in results if c is not None]

    scored = scorer.score(critiques, str(document_path))

    top_n = settings.display_top_n
    return Report(
        document_path=str(document_path),
        critiques_displayed=scored[:top_n],
        critiques_collapsed=scored[top_n:],
        document_metadata=metadata,
    )
