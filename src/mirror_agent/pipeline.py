"""Mirror Agent 파이프라인.

전체 플로우:
    문서 경로 입력
        → Analyzer: 문서 → DocumentMetadata
        → Matcher: 규칙 × 문서 → MatchResult[] (병렬)
        → Generator: Match → Critique[] (병렬)
        → Defender: Critique → DefensePrediction 첨부 (병렬)
        → Scorer: novelty + final_score 계산, 정렬
        → Reporter: Report → Markdown

TODO(v0.1):
- [ ] 각 단계 조립
- [ ] 에러 처리 (한 규칙 실패해도 다른 규칙은 진행)
- [ ] 진행 상황 Rich progress bar
- [ ] 토큰 사용량 요약 출력
"""

from __future__ import annotations

from pathlib import Path

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
from mirror_agent.models import Report
from mirror_agent.reporter import Reporter
from mirror_agent.scorer import Scorer


async def run_mirror_review(document_path: Path | str) -> Report:
    """Mirror Agent의 메인 파이프라인 진입점.

    Args:
        document_path: 검토할 마크다운 문서 경로

    Returns:
        Report 객체 (final_score 내림차순, 상위 N개 표시)
    """
    settings = Settings.from_env()
    llm = LLMClient(settings)

    # 1. 규칙 + 방어 패턴 로드
    rules = load_rules(RULES_DIR)
    patterns = load_defense_patterns(DEFENSE_PATTERNS_PATH)

    # 2. 파이프라인 구성
    analyzer = DocumentAnalyzer(llm)
    matcher = RuleMatcher(llm, settings)
    generator = CritiqueGenerator(llm)
    defender = DefensePredictor(llm, patterns)
    scorer = Scorer(REPORTS_DIR)

    # 3. 실행
    document_text = Path(document_path).read_text(encoding="utf-8")
    metadata = await analyzer.analyze(document_path)
    matches = await matcher.match_all(rules, document_text, metadata)

    # 매칭된 규칙에 대해서만 Critique 생성 + 방어 예측
    rules_by_id = {r.rule_id: r for r in rules}
    critiques = []
    for match in matches:
        rule = rules_by_id[match.rule_id]
        critique = await generator.generate(rule, match)
        critique.defense_prediction = await defender.predict(critique)
        critiques.append(critique)

    # 4. 스코어링 & 정렬
    scored = scorer.score(critiques, str(document_path))

    # 5. 상위 N개 / 접힌 영역 분리
    top_n = settings.display_top_n
    return Report(
        document_path=str(document_path),
        critiques_displayed=scored[:top_n],
        critiques_collapsed=scored[top_n:],
        document_metadata=metadata,
    )
