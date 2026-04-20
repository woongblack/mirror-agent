"""비판 질문 생성기.

매칭된 규칙의 critique_template에 MatchResult의 extracted_variables를 치환하여
구체적인 비판 질문을 생성한다. evidence_questions도 동일 치환.
"""

from __future__ import annotations

import re

from mirror_agent.llm import LLMClient
from mirror_agent.models import Confidence, Critique, MatchResult, Rule


def _fill_template(template: str, variables: dict[str, str]) -> str:
    """템플릿의 {변수} 슬롯을 치환. 미치환 슬롯은 그대로 둠."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def _has_unfilled_slots(text: str) -> bool:
    return bool(re.search(r"\{[a-z_]+\}", text))


_REFINE_SYSTEM = """\
당신은 Mirror Agent의 질문 정제 담당입니다.
주어진 비판 질문을 자연스럽고 날카롭게 다듬으세요.

규칙:
- 질문의 핵심 의도와 날카로움을 유지하세요.
- 더 친절하게 만들지 마세요.
- 물음표로 끝나는 질문 형태를 유지하세요.
- 한국어로 답하세요.
- 50자 이내.
"""


class CritiqueGenerator:
    """매칭 결과를 최종 Critique로 변환."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def generate(
        self,
        rule: Rule,
        match: MatchResult,
    ) -> Critique:
        """단일 규칙-매칭 쌍에 대해 Critique 생성."""
        variables = match.extracted_variables

        main_question = _fill_template(rule.critique_template, variables)
        evidence_questions = [
            _fill_template(q, variables) for q in rule.evidence_questions
        ]

        # 미치환 슬롯이 남아있으면 LLM으로 정제
        if _has_unfilled_slots(main_question):
            main_question = await self._llm.text_call(
                model="claude-haiku-4-5-20251001",
                system=_REFINE_SYSTEM,
                user=f"다음 질문의 {{변수}} 슬롯을 문서 맥락에 맞게 채워 완성하세요:\n\n{main_question}\n\n문서 발췌: {match.evidence_from_document}",
            )

        # past_evidence: source_critiques 중 첫 번째 (수동 규칙이므로 항상 존재)
        past_evidence = rule.source_critiques[0] if rule.source_critiques else "(과거 발화 없음)"

        return Critique(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            confidence_label=rule.confidence,
            main_question=main_question,
            evidence_questions=evidence_questions,
            past_evidence=past_evidence,
            document_excerpt=match.evidence_from_document,
            defense_prediction=None,  # defender.py가 채움
            novelty_score=1.0,        # scorer.py가 재계산
            final_score=match.confidence,
        )
