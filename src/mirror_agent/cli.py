"""Mirror Agent CLI.

사용법:
    mirror review <document_path>
    mirror rules list
    mirror rules show <rule_id>
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mirror_agent.config import RULES_DIR
from mirror_agent.loader import load_rules

console = Console()


@click.group()
def main() -> None:
    """Mirror Agent — 자기 비판 에이전트 팀."""


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="리포트 저장 경로. 미지정 시 data/reports/ 아래 자동 생성.",
)
def review(document_path: Path, output: Path | None) -> None:
    """문서를 검토하여 맹점 리포트 생성."""
    from mirror_agent.pipeline import run_mirror_review
    from mirror_agent.reporter import Reporter

    console.print(f"[bold cyan]Mirror Agent v0.1[/bold cyan] reviewing: {document_path}")
    report = asyncio.run(run_mirror_review(document_path))

    reporter = Reporter()
    markdown = reporter.render(report)

    if output:
        output.write_text(markdown, encoding="utf-8")
        console.print(f"[green]리포트 저장됨:[/green] {output}")
    else:
        console.print(markdown)


@main.group()
def rules() -> None:
    """규칙 관리 명령."""


@rules.command("list")
def list_rules() -> None:
    """활성 규칙 목록 표시."""
    rule_list = load_rules(RULES_DIR)

    table = Table(title=f"Mirror Agent 활성 규칙 ({len(rule_list)}개)")
    table.add_column("ID", style="cyan")
    table.add_column("이름", style="white")
    table.add_column("Confidence", style="yellow")
    table.add_column("확신도", style="magenta")

    for rule in rule_list:
        table.add_row(
            rule.rule_id,
            rule.rule_name,
            rule.confidence.value,
            rule.user_conviction_level,
        )

    console.print(table)


@rules.command("show")
@click.argument("rule_id")
def show_rule(rule_id: str) -> None:
    """특정 규칙의 상세 내용 표시."""
    rule_list = load_rules(RULES_DIR)
    rule = next((r for r in rule_list if r.rule_id == rule_id), None)

    if rule is None:
        console.print(f"[red]규칙을 찾을 수 없음:[/red] {rule_id}")
        return

    console.print(f"[bold cyan]{rule.rule_name}[/bold cyan] ({rule.rule_id})")
    console.print(f"Confidence: [yellow]{rule.confidence.value}[/yellow]")
    console.print(f"\n[bold]핵심 질문:[/bold]\n  {rule.critique_template}")
    console.print("\n[bold]파생 질문:[/bold]")
    for i, q in enumerate(rule.evidence_questions, 1):
        console.print(f"  {i}. {q}")
    console.print("\n[bold]근거 비판:[/bold]")
    for src in rule.source_critiques:
        console.print(f"  - {src}")
    if rule.notes:
        console.print(f"\n[dim]{rule.notes}[/dim]")


if __name__ == "__main__":
    main()
