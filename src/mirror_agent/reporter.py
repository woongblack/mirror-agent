"""리포트 렌더러.

Report 객체를 사용자가 읽는 마크다운으로 변환.
방어 예측은 접힌 상태로 표시 (먼저 비판에 집중, 방어 예측은 확인용).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mirror_agent.models import Critique, FullReport, Report, ReportHistoryEntry, UnifiedItem


def _render_critique(critique: Critique, rank: int) -> str:
    lines: list[str] = []

    label_map = {"high": "🔴 HIGH", "medium_high": "🟠 MEDIUM-HIGH", "medium": "🟡 MEDIUM", "seed": "⚪ SEED"}
    label = label_map.get(critique.confidence_label.value, critique.confidence_label.value)

    lines.append(f"### {rank}. {critique.rule_name} {label}")
    lines.append("")
    lines.append(f"> **{critique.main_question}**")
    lines.append("")

    # 근거: 과거 발화 → 현재 문서
    lines.append("**과거 발화 (당신이 타인에게 던진 비판):**")
    lines.append(f"> {critique.past_evidence}")
    lines.append("")
    lines.append("**현재 문서의 관련 구절:**")
    lines.append(f"> {critique.document_excerpt}")
    lines.append("")

    # 세부 질문
    if critique.evidence_questions:
        lines.append("**확인이 필요한 질문들:**")
        for q in critique.evidence_questions:
            lines.append(f"- {q}")
        lines.append("")

    # 방어 예측 — 접힌 상태
    if critique.defense_prediction:
        dp = critique.defense_prediction
        lines.append("<details>")
        lines.append("<summary>당신이 이 비판을 받았을 때 할 것 같은 방어 (클릭하여 확인)</summary>")
        lines.append("")
        lines.append(f"**예상 방어:** {dp.predicted_response}")
        lines.append("")
        lines.append(f"**그 방어의 약점:** {dp.weakness}")
        if dp.matched_pattern_id:
            lines.append(f"<sub>패턴 참조: `{dp.matched_pattern_id}`</sub>")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append(f"<sub>score: {critique.final_score:.3f} | novelty: {critique.novelty_score:.2f}</sub>")

    return "\n".join(lines)


class Reporter:
    """Report 객체를 마크다운으로 렌더링."""

    def render(self, report: Report) -> str:
        lines: list[str] = []

        ts = report.generated_at.strftime("%Y-%m-%d %H:%M")
        doc_name = Path(report.document_path).name

        lines.append(f"# Mirror Agent Report — {doc_name}")
        lines.append(f"생성: {ts} | 문서: `{report.document_path}`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "이 비판들은 당신이 과거에 타인에게 던진 질문에서 파생됐습니다. "
            "타인에게 할 수 있는 비판을 자신에게도 적용합니다."
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # 상위 N개 (기본 표시)
        lines.append("## 핵심 비판")
        lines.append("")
        for i, critique in enumerate(report.critiques_displayed, start=1):
            lines.append(_render_critique(critique, i))
            lines.append("")
            lines.append("---")
            lines.append("")

        # 나머지 (접힌 상태)
        if report.critiques_collapsed:
            lines.append("<details>")
            lines.append(f"<summary>추가 비판 {len(report.critiques_collapsed)}개 (클릭하여 펼치기)</summary>")
            lines.append("")
            base_rank = len(report.critiques_displayed) + 1
            for i, critique in enumerate(report.critiques_collapsed, start=base_rank):
                lines.append(_render_critique(critique, i))
                lines.append("")
                lines.append("---")
                lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            f"총 {report.total_critiques}개 비판 생성 | "
            f"표시 {len(report.critiques_displayed)}개 | "
            f"접힘 {len(report.critiques_collapsed)}개"
        )

        return "\n".join(lines)

    def render_full(self, report: FullReport) -> str:
        """FullReport → 통합 마크다운."""
        lines: list[str] = []
        ts = report.generated_at.strftime("%Y-%m-%d %H:%M")
        doc_name = Path(report.document_path).name
        agent_badge = {"historical": "📜 Historical", "socratic": "🔍 Socratic", "contrarian": "⚔️ Contrarian"}
        severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}

        lines.append(f"# Mirror Agent Full Report — {doc_name}")
        lines.append(f"생성: {ts} | 에이전트: Historical + Socratic + Contrarian")
        lines.append(f"비판 {len(report.historical_critiques)}개 | 질문 {len(report.socratic_questions)}개 | 시나리오 {len(report.contrarian_challenges)}개")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 핵심 질문 (통합 우선순위)")
        lines.append("")

        def _render_item(item: UnifiedItem, rank: int) -> str:
            badge = agent_badge.get(item.source_agent, item.source_agent)
            icon = severity_icon.get(item.severity, "")
            result = [f"### {rank}. [{badge}] {item.question} {icon}"]
            result.append("")
            result.append(f"**근거:** {item.evidence}")
            if item.context:
                result.append(f"\n{item.context}")
            return "\n".join(result)

        for i, item in enumerate(report.top_items, 1):
            lines.append(_render_item(item, i))
            lines.append("")
            lines.append("---")
            lines.append("")

        if report.collapsed_items:
            lines.append("<details>")
            lines.append(f"<summary>추가 질문 {len(report.collapsed_items)}개 (클릭하여 펼치기)</summary>")
            lines.append("")
            base = len(report.top_items) + 1
            for i, item in enumerate(report.collapsed_items, base):
                lines.append(_render_item(item, i))
                lines.append("")
                lines.append("---")
                lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append(f"총 {report.total_items}개 | 표시 {len(report.top_items)}개 | 접힘 {len(report.collapsed_items)}개")
        return "\n".join(lines)

    def save(self, report: Report, output_dir: Path | str) -> Path:
        """렌더링된 리포트를 파일로 저장하고 경로 반환."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = report.generated_at.strftime("%Y%m%d_%H%M%S")
        doc_stem = Path(report.document_path).stem
        report_path = out_dir / f"{ts}_{doc_stem}.md"
        report_path.write_text(self.render(report), encoding="utf-8")

        # 히스토리 기록 저장
        history = ReportHistoryEntry(
            document_path=report.document_path,
            generated_at=report.generated_at,
            rule_ids_fired=[c.rule_id for c in report.critiques_displayed + report.critiques_collapsed],
        )
        history_path = out_dir / f"{ts}_{doc_stem}.history.json"
        history_path.write_text(
            json.dumps(history.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return report_path
