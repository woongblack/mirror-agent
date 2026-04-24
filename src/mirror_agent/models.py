"""
Mirror Agent 데이터 모델.

모든 I/O가 이 스키마를 통해 흐른다. LLM 응답도 여기 정의된 모델로 강제 파싱한다.

설계 원칙:
- Rule은 human-readable JSON (Git diff로 진화 추적 가능)
- CritiqueUnit은 과거 발화의 원자 단위
- MatchResult는 Evidence 필드를 강제하여 환각 방지
- Report는 최종 산출물 (Markdown 렌더링 소스)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Confidence(str, Enum):
    """규칙의 신뢰도 레벨. historical-agent-plan.md의 분류 기준."""

    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    SEED = "seed"


class TargetType(str, Enum):
    """비판 대상의 유형."""

    TEAM_PROJECT = "team_project"
    PERSONAL_PROJECT = "personal_project"
    TECH_DECISION = "tech_decision"
    MARKET_JUDGMENT = "market_judgment"
    PLATFORM = "platform"
    MARKETPLACE = "marketplace"
    TWO_SIDED_MARKET = "two_sided_market"


# ---------------------------------------------------------------------------
# Critique Unit — Stage 1 산출물 (v0.1에서는 수동 작성)
# ---------------------------------------------------------------------------


class CritiqueUnit(BaseModel):
    """과거 발화에서 추출한 비판의 원자 단위."""

    id: str = Field(..., description="예: critique_001")
    source: str = Field(..., description="출처 경로 + 앵커. 예: conversation-log.md#phase7")
    raw_text: str = Field(..., description="원문 발화")
    target_project: str = Field(..., description="비판 대상 프로젝트 이름")
    target_type: TargetType
    domain: str = Field(..., description="예: platform/marketplace")
    critique_category: str = Field(..., description="예: supplier_acquisition")
    emotional_marker: str = Field(default="neutral", description="감정 톤 마커")
    context: str = Field(..., description="이 비판이 나온 주변 맥락")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Rule — Stage 2 산출물 (v0.1에서는 수동 작성)
# ---------------------------------------------------------------------------


class TriggerConditions(BaseModel):
    """LLM이 문서에 적용할지 판정할 조건들."""

    target_type_in: list[str] = Field(default_factory=list)
    has_supply_side: bool | None = None
    has_demand_side: bool | None = None
    document_mentions_similar_product: bool | None = None
    document_has_phased_roadmap: bool | None = None
    document_claims_user_value: bool | None = None
    project_is_solo: bool | None = None
    tech_stack_complexity_high: bool | None = None
    author_is_user: bool | None = None

    # 규칙마다 필요한 조건이 다르므로 확장 가능한 자유 필드
    extra: dict[str, bool | str | list[str]] = Field(default_factory=dict)

    def describe_for_llm(self) -> str:
        """LLM 프롬프트에 삽입할 자연어 형태로 변환."""
        lines = []
        if self.target_type_in:
            lines.append(f"- 프로젝트 유형이 {self.target_type_in} 중 하나여야 함")
        if self.has_supply_side is not None:
            lines.append(f"- 공급자(supply side)의 존재: {self.has_supply_side}")
        if self.has_demand_side is not None:
            lines.append(f"- 수요자(demand side)의 존재: {self.has_demand_side}")
        if self.document_mentions_similar_product is not None:
            lines.append(f"- 유사 제품 언급: {self.document_mentions_similar_product}")
        if self.document_has_phased_roadmap is not None:
            lines.append(f"- 단계별 로드맵 존재: {self.document_has_phased_roadmap}")
        if self.document_claims_user_value is not None:
            lines.append(f"- 사용자 가치 주장: {self.document_claims_user_value}")
        if self.project_is_solo is not None:
            lines.append(f"- 1인 프로젝트: {self.project_is_solo}")
        if self.tech_stack_complexity_high is not None:
            lines.append(f"- 기술 스택 복잡도 높음: {self.tech_stack_complexity_high}")
        for key, value in self.extra.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(조건 없음)"


class Rule(BaseModel):
    """재사용 가능한 비판 규칙."""

    rule_id: str
    rule_name: str
    confidence: Confidence
    trigger_conditions: TriggerConditions
    critique_template: str = Field(
        ...,
        description="변수 슬롯 포함. 예: '{supply_side}를 어떻게 확보할 것인가?'",
    )
    evidence_questions: list[str]
    source_critiques: list[str] = Field(
        default_factory=list, description="근거 비판 유닛 ID 또는 참조 텍스트"
    )
    user_conviction_level: str = Field(..., description="예: very_high, high, medium")
    notes: str = Field(default="")
    validated_by_user: bool = Field(default=True, description="v0.1 수동 규칙은 기본 True")

    @property
    def is_active(self) -> bool:
        """SEED 상태는 비활성. 나머지는 활성."""
        return self.confidence != Confidence.SEED


# ---------------------------------------------------------------------------
# Document Metadata — Analyzer 출력
# ---------------------------------------------------------------------------


class DocumentMetadata(BaseModel):
    """문서 분석기가 추출한 메타데이터. Matcher의 입력이 된다."""

    path: str
    target_type: str | None = None
    domain: str | None = None
    has_supply_side: bool | None = None
    has_demand_side: bool | None = None
    has_phased_roadmap: bool | None = None
    mentions_similar_products: list[str] = Field(default_factory=list)
    claimed_user_values: list[str] = Field(default_factory=list)
    is_solo_project: bool | None = None
    tech_stack: list[str] = Field(default_factory=list)
    key_excerpts: dict[str, str] = Field(
        default_factory=dict, description="주요 섹션별 발췌 (Evidence용)"
    )


# ---------------------------------------------------------------------------
# Match Result — Matcher 출력 (Evidence 강제)
# ---------------------------------------------------------------------------


class MatchResult(BaseModel):
    """LLM이 규칙 적용 가능성을 판정한 결과.

    환각 방지를 위해 evidence_from_document는 필수.
    근거를 문서에서 인용할 수 없으면 matches=False로 강제.
    """

    rule_id: str
    matches: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_from_document: str = Field(
        ...,
        description="문서에서 직접 인용한 근거 구절. 인용 불가 시 '근거 없음'과 함께 matches=False",
    )
    reasoning: str = Field(..., description="판정 이유의 한 줄 요약")
    extracted_variables: dict[str, str] = Field(
        default_factory=dict,
        description="critique_template 치환에 사용할 변수. 예: {'supply_side': '카페24 셀러'}",
    )


# ---------------------------------------------------------------------------
# Defense Pattern — 방어 예측의 재료
# ---------------------------------------------------------------------------


class DefensePattern(BaseModel):
    """사용자의 과거 방어 패턴. defender.py가 참조."""

    pattern_id: str
    trigger: str = Field(..., description="어떤 비판을 받았을 때 이 방어가 나오는가")
    example_response: str = Field(..., description="실제 관찰된 방어 발화 예시")
    weakness: str = Field(..., description="이 방어의 구조적 약점")
    source: str = Field(..., description="출처")


class DefensePrediction(BaseModel):
    """특정 비판에 대한 예상 방어와 그 약점."""

    predicted_response: str
    weakness: str
    matched_pattern_id: str | None = None


# ---------------------------------------------------------------------------
# Socratic Agent — 숨겨진 가정 드러내기
# ---------------------------------------------------------------------------


class SocraticQuestion(BaseModel):
    """문서의 숨겨진 가정에서 파생된 질문."""

    assumption: str = Field(..., description="드러난 숨겨진 가정")
    question: str = Field(..., description="'왜 ~인가?' 형태의 질문")
    angle: Literal["market", "tech", "operation", "motivation", "competition"] = Field(
        ..., description="질문의 각도"
    )
    severity: Literal["high", "medium", "low"]
    evidence_from_document: str = Field(..., description="가정이 담긴 문서 인용")


# ---------------------------------------------------------------------------
# Final Critique — 사용자에게 제시되는 단위
# ---------------------------------------------------------------------------


class Critique(BaseModel):
    """최종 비판 항목. Report의 구성 요소."""

    rule_id: str
    rule_name: str
    confidence_label: Confidence
    main_question: str = Field(..., description="critique_template 치환 결과")
    evidence_questions: list[str]
    past_evidence: str = Field(
        ..., description="과거에 사용자가 타인에게 던진 비판의 인용"
    )
    document_excerpt: str = Field(
        ..., description="현재 문서의 관련 구절. 없으면 '해당 내용 없음' 명시"
    )
    defense_prediction: DefensePrediction | None = None
    novelty_score: float = Field(default=1.0, ge=0.0)
    final_score: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# Report — 최종 산출물
# ---------------------------------------------------------------------------


class Report(BaseModel):
    """Re-Applicator의 최종 산출물."""

    document_path: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    critiques_displayed: list[Critique] = Field(
        ..., description="상위 3개. 사용자에게 기본 표시"
    )
    critiques_collapsed: list[Critique] = Field(
        default_factory=list, description="추가 비판. 펼치기로 노출"
    )
    document_metadata: DocumentMetadata

    @property
    def total_critiques(self) -> int:
        return len(self.critiques_displayed) + len(self.critiques_collapsed)


# ---------------------------------------------------------------------------
# Report History — novelty_score 계산에 사용
# ---------------------------------------------------------------------------


class ReportHistoryEntry(BaseModel):
    """이전 리포트 기록. novelty_score 계산 및 중복 감지에 사용."""

    document_path: str
    generated_at: datetime
    rule_ids_fired: list[str]
    user_responded_rules: list[str] = Field(
        default_factory=list, description="사용자가 답했거나 반영한 규칙 ID"
    )