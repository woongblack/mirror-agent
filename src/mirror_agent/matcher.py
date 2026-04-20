"""규칙 매처.

Rule의 trigger_conditions가 현재 문서에 해당하는지 LLM으로 판정.

핵심 설계:
- Evidence 필드 강제 (환각 방지)
- "추측 금지" 프롬프트 명시
- confidence < threshold는 False로 강제
"""

from __future__ import annotations

import asyncio

from mirror_agent.config import Settings
from mirror_agent.llm import LLMClient
from mirror_agent.models import DocumentMetadata, MatchResult, Rule


MATCHER_SYSTEM_PROMPT = """\
당신은 Mirror Agent의 Rule Matcher입니다.

주어진 규칙의 trigger_conditions가 현재 문서에 해당하는지 판정합니다.

엄격한 규칙:
1. 각 조건마다 문서에서 직접 인용 가능한 근거가 있어야 합니다.
2. 근거를 인용할 수 없으면 matches=False로 판정하세요.
3. 추측하지 마세요. 문서에 명시적으로 쓰여 있는 것만 근거로 삼으세요.
4. 불확실하면 confidence를 낮추세요.
5. 친절하게 "해당할 가능성이 있다"고 답하지 마세요. 명확하지 않으면 False입니다.
6. extracted_variables에는 critique_template의 빈칸을 채울 구체적 값을 넣으세요.
   예: template에 {supply_side}가 있으면 → "카페24 셀러" 같은 문서 속 실제 표현.
"""


class RuleMatcher:
    """LLM 기반 규칙 매칭기."""

    def __init__(self, llm: LLMClient, settings: Settings) -> None:
        self._llm = llm
        self._settings = settings

    async def match(
        self,
        rule: Rule,
        document_text: str,
        document_metadata: DocumentMetadata,
    ) -> MatchResult:
        """단일 규칙에 대한 매칭 판정."""
        conditions_desc = rule.trigger_conditions.describe_for_llm()
        excerpts_block = "\n".join(
            f"[{k}]: {v}" for k, v in document_metadata.key_excerpts.items()
        ) or "(추출된 발췌 없음)"

        user_prompt = f"""\
=== 규칙 정보 ===
rule_id: {rule.rule_id}
rule_name: {rule.rule_name}

적용 조건 (trigger_conditions):
{conditions_desc}

critique_template (변수 슬롯 포함):
{rule.critique_template}

=== 문서 메타데이터 ===
target_type: {document_metadata.target_type}
domain: {document_metadata.domain}
has_supply_side: {document_metadata.has_supply_side}
has_demand_side: {document_metadata.has_demand_side}
is_solo_project: {document_metadata.is_solo_project}
tech_stack: {document_metadata.tech_stack}

=== 문서 주요 발췌 ===
{excerpts_block}

=== 문서 전문 (참조용) ===
{document_text[:3000]}

---
위 규칙이 이 문서에 적용되는지 판정하세요.
evidence_from_document에는 판정 근거가 된 문서 원문을 직접 인용하세요.
인용할 수 없으면 matches=False로 판정하세요.
"""

        result = await self._llm.structured_call(
            model=self._settings.model_matcher,
            system=MATCHER_SYSTEM_PROMPT,
            user=user_prompt,
            response_model=MatchResult,
        )

        # Evidence 없으면 강제 False
        evidence = result.evidence_from_document.strip()
        if not evidence or evidence in ("없음", "근거 없음", "해당 없음", "N/A"):
            return result.model_copy(update={"matches": False, "confidence": 0.0})

        # rule_id는 LLM이 틀릴 수 있으므로 강제 설정
        return result.model_copy(update={"rule_id": rule.rule_id})

    async def match_all(
        self,
        rules: list[Rule],
        document_text: str,
        document_metadata: DocumentMetadata,
    ) -> list[MatchResult]:
        """모든 규칙에 대해 병렬 매칭."""
        active_rules = [r for r in rules if r.is_active]
        tasks = [
            self.match(rule, document_text, document_metadata) for rule in active_rules
        ]
        results = await asyncio.gather(*tasks)
        return [
            r
            for r in results
            if r.matches and r.confidence >= self._settings.match_confidence_threshold
        ]
