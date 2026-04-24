"""CritiqueUnit 클러스터 → 추상 Rule 후보 자동 생성.

입력: data/critiques/{source}.json
출력: data/rules/pending/rule_candidate_{slug}.json
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from mirror_agent.config import RULES_DIR, Settings
from mirror_agent.llm import LLMClient
from mirror_agent.loader import load_rules
from mirror_agent.models import Confidence, CritiqueUnit, Rule, TriggerConditions

logger = logging.getLogger(__name__)

PENDING_DIR = Path("data/rules/pending")

_RULE_EXAMPLE = """\
{
  "rule_id": "rule_supplier_first",
  "rule_name": "공급자 확보 전략 선행 원칙",
  "confidence": "high",
  "trigger_conditions": {
    "target_type_in": ["platform", "marketplace", "two_sided_market"],
    "has_supply_side": true,
    "has_demand_side": true
  },
  "critique_template": "이 플랫폼이 {supply_side}를 어떻게 확보할 것인가?",
  "evidence_questions": [
    "{supply_side}가 이 플랫폼에 참여할 경제적 동기가 있는가?",
    "초기 N개의 {supply_side}를 어떻게 확보할 구체적 계획이 있는가?"
  ],
  "user_conviction_level": "very_high",
  "notes": "사용자가 DEKK 팀에게 반복적으로 던진 질문에서 파생된 규칙."
}"""

_SYSTEM = f"""\
당신은 구체적인 비판 발화들에서 재사용 가능한 추상 규칙을 생성하는 전문가입니다.

## 목표

특정 프로젝트에 대한 비판 → 어떤 기획 문서에도 적용 가능한 규칙으로 추상화.

예시:
- L1 (구체): "DEKK에서 셀러를 어떻게 구할 건데?"
- L2 (추상): "플랫폼 프로젝트에서 {{supply_side}}를 어떻게 확보할 것인가?"

## 규칙 생성 원칙

- trigger_conditions: 이 규칙이 발동해야 하는 최소 조건
  - target_type_in: 해당 프로젝트 유형 목록 (platform/marketplace/team_project/personal_project 등)
  - has_supply_side / has_demand_side / has_phased_roadmap / project_is_solo / document_claims_user_value 등 bool 조건
  - 조건이 없으면 null로 둔다 (false가 아님)
- critique_template: {{변수}} 슬롯 포함, 어떤 문서에도 치환 가능해야 함
- evidence_questions: 구체적이고 답 가능한 질문 3~5개 (추상적 질문 금지)
- confidence: high / medium_high / medium / seed
- user_conviction_level: very_high / high / medium

## 출력 형식 예시

{_RULE_EXAMPLE}
"""


class _CandidateOutput(BaseModel):
    """LLM이 직접 채우는 규칙 후보."""

    rule_id: str
    rule_name: str
    confidence: Literal["high", "medium_high", "medium", "seed"]
    trigger_target_types: list[str]
    trigger_has_supply_side: bool | None = None
    trigger_has_demand_side: bool | None = None
    trigger_has_phased_roadmap: bool | None = None
    trigger_project_is_solo: bool | None = None
    trigger_document_claims_user_value: bool | None = None
    critique_template: str
    evidence_questions: list[str]
    user_conviction_level: Literal["very_high", "high", "medium"]
    notes: str


class Generalizer:
    """CritiqueUnit 클러스터 → Rule 후보 생성."""

    def __init__(self, settings: Settings) -> None:
        self._llm = LLMClient(settings)
        self._model = settings.model_generator  # sonnet — 추상화 품질이 핵심

    async def generalize(self, units: list[CritiqueUnit]) -> list[Rule]:
        existing = load_rules(RULES_DIR)
        existing_ids = {r.rule_id for r in existing}

        clusters = _cluster_by_category(units)
        logger.info("클러스터 %d개: %s", len(clusters), list(clusters.keys()))

        candidates: list[Rule] = []
        for category, cluster_units in clusters.items():
            logger.info("규칙 생성 중: %s (%d개 비판)", category, len(cluster_units))
            output = await self._generate(cluster_units, category)
            if output is None:
                continue

            rule = _to_rule(output, cluster_units)

            if rule.rule_id in existing_ids:
                logger.info("기존 규칙과 중복 (id): %s — 건너뜀", rule.rule_id)
                continue

            if _is_template_duplicate(rule, existing):
                logger.info("기존 규칙과 템플릿 유사: %s — 건너뜀", rule.rule_id)
                continue

            candidates.append(rule)
            logger.info("후보 생성 완료: %s", rule.rule_id)

        return candidates

    async def _generate(
        self, units: list[CritiqueUnit], category: str
    ) -> _CandidateOutput | None:
        critiques_text = "\n".join(
            f"- [{u.target_project}] {u.raw_text}\n  맥락: {u.context}"
            for u in units
        )
        user_prompt = f"""다음 비판 발화들을 추상 규칙으로 일반화하세요.

카테고리: {category}

비판 발화:
{critiques_text}
"""
        try:
            return await self._llm.structured_call(
                model=self._model,
                system=_SYSTEM,
                user=user_prompt,
                response_model=_CandidateOutput,
            )
        except Exception as e:
            logger.error("규칙 생성 실패 (%s): %s", category, e)
            return None

    async def save(self, candidates: list[Rule], output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for rule in candidates:
            path = output_dir / f"{rule.rule_id}.json"
            data = {
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "confidence": rule.confidence.value,
                "trigger_conditions": {
                    k: v
                    for k, v in rule.trigger_conditions.model_dump().items()
                    if k != "extra" and v is not None and v != []
                },
                "critique_template": rule.critique_template,
                "evidence_questions": rule.evidence_questions,
                "source_critiques": rule.source_critiques,
                "user_conviction_level": rule.user_conviction_level,
                "notes": rule.notes,
                "validated_by_user": False,
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            saved.append(path)
            logger.info("저장됨: %s", path)
        return saved


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _cluster_by_category(units: list[CritiqueUnit]) -> dict[str, list[CritiqueUnit]]:
    """critique_category 기준으로 클러스터링."""
    clusters: dict[str, list[CritiqueUnit]] = {}
    for unit in units:
        clusters.setdefault(unit.critique_category, []).append(unit)
    return clusters


def _to_rule(output: _CandidateOutput, source_units: list[CritiqueUnit]) -> Rule:
    trigger = TriggerConditions(
        target_type_in=output.trigger_target_types,
        has_supply_side=output.trigger_has_supply_side,
        has_demand_side=output.trigger_has_demand_side,
        has_phased_roadmap=output.trigger_has_phased_roadmap,
        project_is_solo=output.trigger_project_is_solo,
        document_claims_user_value=output.trigger_document_claims_user_value,
    )
    return Rule(
        rule_id=output.rule_id,
        rule_name=output.rule_name,
        confidence=Confidence(output.confidence),
        trigger_conditions=trigger,
        critique_template=output.critique_template,
        evidence_questions=output.evidence_questions,
        source_critiques=[f"{u.source}: {u.raw_text[:60]}" for u in source_units],
        user_conviction_level=output.user_conviction_level,
        notes=output.notes,
        validated_by_user=False,
    )


def _is_template_duplicate(candidate: Rule, existing: list[Rule]) -> bool:
    """critique_template이 기존 규칙과 70% 이상 유사하면 중복으로 간주."""
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z가-힣]+", text.lower()))

    cand_tokens = _tokens(candidate.critique_template)
    for rule in existing:
        exist_tokens = _tokens(rule.critique_template)
        if not cand_tokens or not exist_tokens:
            continue
        overlap = len(cand_tokens & exist_tokens) / len(cand_tokens | exist_tokens)
        if overlap >= 0.7:
            return True
    return False
