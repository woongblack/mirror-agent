"""Orchestrator — Historical + Socratic + Contrarian 병렬 실행 + 결과 통합.

3개 에이전트를 병렬 실행하고, severity 기준으로 통합 우선순위 리스트를 만든다.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from mirror_agent.analyzer import DocumentAnalyzer
from mirror_agent.config import AUTO_RULES_DIR, DEFENSE_PATTERNS_PATH, REPORTS_DIR, RULES_DIR, Settings
from mirror_agent.contrarian import ContrarianAgent
from mirror_agent.defender import DefensePredictor
from mirror_agent.generator import CritiqueGenerator
from mirror_agent.llm import LLMClient
from mirror_agent.loader import load_defense_patterns, load_rules
from mirror_agent.matcher import RuleMatcher
from mirror_agent.models import (
    Confidence,
    ContrarianChallenge,
    Critique,
    FullReport,
    SocraticQuestion,
    UnifiedItem,
)
from mirror_agent.scorer import Scorer
from mirror_agent.socratic import SocraticAgent

logger = logging.getLogger(__name__)

_CONFIDENCE_TO_SEVERITY = {
    Confidence.HIGH: "high",
    Confidence.MEDIUM_HIGH: "medium",
    Confidence.MEDIUM: "medium",
    Confidence.SEED: "low",
}


class Orchestrator:
    """3개 에이전트를 병렬 실행하고 결과를 통합한다."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = LLMClient(settings)

    async def run(self, document_path: Path) -> FullReport:
        rules = load_rules(RULES_DIR)
        if AUTO_RULES_DIR.exists():
            rules += load_rules(AUTO_RULES_DIR)
        patterns = load_defense_patterns(DEFENSE_PATTERNS_PATH)

        analyzer = DocumentAnalyzer(self._llm)
        matcher = RuleMatcher(self._llm, self._settings)
        generator = CritiqueGenerator(self._llm)
        defender = DefensePredictor(self._llm, patterns)
        scorer = Scorer(REPORTS_DIR)
        socratic = SocraticAgent(self._llm, model=self._settings.model_generator)
        contrarian = ContrarianAgent(self._llm, model=self._settings.model_generator)

        document_text = document_path.read_text(encoding="utf-8")
        metadata = await analyzer.analyze(document_path)

        logger.info("3개 에이전트 병렬 실행 중...")
        historical_task = self._run_historical(
            rules, document_text, metadata, matcher, generator, defender, scorer, document_path
        )
        socratic_task = socratic.interrogate(document_text, metadata)
        contrarian_task = contrarian.challenge(document_text, metadata)

        historical_critiques, socratic_questions, contrarian_challenges = await asyncio.gather(
            historical_task, socratic_task, contrarian_task,
            return_exceptions=True,
        )

        # 에이전트 실패 시 빈 리스트로 대체 (graceful degradation)
        if isinstance(historical_critiques, Exception):
            logger.error("Historical Agent 실패: %s", historical_critiques)
            historical_critiques = []
        if isinstance(socratic_questions, Exception):
            logger.error("Socratic Agent 실패: %s", socratic_questions)
            socratic_questions = []
        if isinstance(contrarian_challenges, Exception):
            logger.error("Contrarian Agent 실패: %s", contrarian_challenges)
            contrarian_challenges = []

        unified = _merge_and_rank(historical_critiques, socratic_questions, contrarian_challenges)
        top_n = self._settings.display_top_n

        return FullReport(
            document_path=str(document_path),
            historical_critiques=historical_critiques,
            socratic_questions=socratic_questions,
            contrarian_challenges=contrarian_challenges,
            top_items=unified[:top_n],
            collapsed_items=unified[top_n:],
            document_metadata=metadata,
        )

    async def _run_historical(
        self, rules, document_text, metadata, matcher, generator, defender, scorer, document_path
    ) -> list[Critique]:
        from mirror_agent.models import Rule

        matches = await matcher.match_all(rules, document_text, metadata)
        rules_by_id = {r.rule_id: r for r in rules}

        async def _gen(match):
            try:
                rule = rules_by_id[match.rule_id]
                critique = await generator.generate(rule, match)
                critique.defense_prediction = await defender.predict(critique)
                return critique
            except Exception:
                logger.warning("규칙 처리 실패: %s", match.rule_id, exc_info=True)
                return None

        results = await asyncio.gather(*[_gen(m) for m in matches if m.rule_id in rules_by_id])
        critiques = [c for c in results if c is not None]
        return scorer.score(critiques, str(document_path))


def _merge_and_rank(
    critiques: list[Critique],
    questions: list[SocraticQuestion],
    challenges: list[ContrarianChallenge],
) -> list[UnifiedItem]:
    """3개 에이전트 출력을 UnifiedItem으로 변환하고 severity 기준으로 정렬."""
    items: list[UnifiedItem] = []

    for c in critiques:
        severity = _CONFIDENCE_TO_SEVERITY.get(c.confidence_label, "medium")
        context = ""
        if c.defense_prediction:
            context = f"예상 방어: {c.defense_prediction.predicted_response}"
        items.append(UnifiedItem(
            source_agent="historical",
            severity=severity,
            question=c.main_question,
            evidence=c.document_excerpt[:200],
            context=context,
        ))

    for q in questions:
        items.append(UnifiedItem(
            source_agent="socratic",
            severity=q.severity,
            question=q.question,
            evidence=q.evidence_from_document[:200],
            context=f"가정: {q.assumption}",
        ))

    for ch in challenges:
        items.append(UnifiedItem(
            source_agent="contrarian",
            severity=ch.severity,
            question=ch.challenge_question,
            evidence=ch.evidence_from_document[:200],
            context=f"함의: {ch.implication}",
        ))

    # severity 기준 정렬, 동일 severity면 historical 우선
    _agent_rank = {"historical": 0, "socratic": 1, "contrarian": 2}
    items.sort(key=lambda x: (x.severity_rank, _agent_rank[x.source_agent]))
    return items
