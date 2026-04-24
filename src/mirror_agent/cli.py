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
    help="리포트 저장 디렉토리. 미지정 시 data/reports/{doc_slug}/ 아래 자동 저장.",
)
@click.option(
    "--no-save",
    is_flag=True,
    default=False,
    help="파일 저장 없이 stdout만 출력.",
)
def review(document_path: Path, output: Path | None, no_save: bool) -> None:
    """문서를 검토하여 맹점 리포트 생성."""
    from mirror_agent.pipeline import run_mirror_review
    from mirror_agent.reporter import Reporter

    console.print(f"[bold cyan]Mirror Agent v0.1[/bold cyan] reviewing: {document_path}")
    report = asyncio.run(run_mirror_review(document_path))

    reporter = Reporter()
    console.print(reporter.render(report))

    if not no_save:
        project_root = Path(__file__).resolve().parent.parent.parent
        save_dir = output if output else project_root / "data" / "reports" / document_path.stem
        saved_path = reporter.save(report, save_dir)
        console.print(f"[green]리포트 저장됨:[/green] {saved_path}")


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="저장 경로. 미지정 시 data/critiques/{doc_stem}.json 자동 저장.",
)
@click.option(
    "--no-save",
    is_flag=True,
    default=False,
    help="파일 저장 없이 stdout만 출력.",
)
def extract(document_path: Path, output: Path | None, no_save: bool) -> None:
    """대화 로그에서 비판 발화를 추출한다."""
    import json

    from mirror_agent.config import DATA_DIR, Settings
    from mirror_agent.extractor import Extractor

    settings = Settings.from_env()
    extractor = Extractor(settings)

    console.print(f"[bold cyan]Extractor[/bold cyan] 추출 중: {document_path}")
    units = asyncio.run(extractor.extract(document_path))
    console.print(f"[green]{len(units)}개 비판 추출 완료[/green]")

    for u in units:
        console.print(f"  [{u.id}] {u.raw_text[:60]}...")

    if not no_save:
        out_path = output if output else DATA_DIR / "critiques" / f"{document_path.stem}.json"
        asyncio.run(extractor.save(units, out_path))
        console.print(f"[green]저장됨:[/green] {out_path}")


@main.command()
@click.argument("critiques_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="저장 디렉토리. 미지정 시 data/rules/pending/ 자동 저장.",
)
@click.option(
    "--no-save",
    is_flag=True,
    default=False,
    help="파일 저장 없이 stdout만 출력.",
)
def generalize(critiques_path: Path, output: Path | None, no_save: bool) -> None:
    """CritiqueUnit → 추상 Rule 후보 생성."""
    import json

    from mirror_agent.config import DATA_DIR, Settings
    from mirror_agent.generalizer import PENDING_DIR, Generalizer
    from mirror_agent.models import CritiqueUnit

    settings = Settings.from_env()
    generalizer = Generalizer(settings)

    raw = json.loads(critiques_path.read_text())
    units = [CritiqueUnit.model_validate(u) for u in raw]
    console.print(f"[bold cyan]Generalizer[/bold cyan] {len(units)}개 비판 → 규칙 후보 생성 중")

    candidates = asyncio.run(generalizer.generalize(units))
    console.print(f"[green]{len(candidates)}개 규칙 후보 생성 완료[/green]")

    for rule in candidates:
        console.print(f"  [{rule.rule_id}] {rule.rule_name} ({rule.confidence.value})")

    if not no_save and candidates:
        out_dir = output if output else DATA_DIR / "rules" / "pending"
        saved = asyncio.run(generalizer.save(candidates, out_dir))
        for path in saved:
            console.print(f"[green]저장됨:[/green] {path}")


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option("--no-save", is_flag=True, default=False, help="stdout만 출력.")
def socratic(document_path: Path, no_save: bool) -> None:
    """문서의 숨겨진 가정을 드러내는 질문 생성."""
    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.llm import LLMClient
    from mirror_agent.socratic import SocraticAgent

    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = SocraticAgent(llm, model=settings.model_generator)

    console.print(f"[bold cyan]Socratic Agent[/bold cyan] 분석 중: {document_path}")
    document_text = document_path.read_text()
    metadata = asyncio.run(analyzer.analyze(document_path))
    questions = asyncio.run(agent.interrogate(document_text, metadata))

    console.print(f"[green]{len(questions)}개 질문 생성 완료[/green]\n")
    for i, q in enumerate(questions, 1):
        severity_color = {"high": "red", "medium": "yellow", "low": "white"}[q.severity]
        console.print(f"[{severity_color}]#{i} [{q.angle}] {q.question}[/{severity_color}]")
        console.print(f"  가정: {q.assumption}")
        console.print(f"  근거: {q.evidence_from_document[:80]}...\n")


@main.command()
@click.argument("document_path", type=click.Path(exists=True, path_type=Path))
@click.option("--no-save", is_flag=True, default=False, help="stdout만 출력.")
def contrarian(document_path: Path, no_save: bool) -> None:
    """문서의 핵심 주장에 반대 시나리오를 구성한다."""
    from mirror_agent.analyzer import DocumentAnalyzer
    from mirror_agent.config import Settings
    from mirror_agent.contrarian import ContrarianAgent
    from mirror_agent.llm import LLMClient

    settings = Settings.from_env()
    llm = LLMClient(settings)
    analyzer = DocumentAnalyzer(llm)
    agent = ContrarianAgent(llm, model=settings.model_generator)

    console.print(f"[bold cyan]Contrarian Agent[/bold cyan] 분석 중: {document_path}")
    document_text = document_path.read_text()
    metadata = asyncio.run(analyzer.analyze(document_path))
    challenges = asyncio.run(agent.challenge(document_text, metadata))

    console.print(f"[green]{len(challenges)}개 반대 시나리오 생성 완료[/green]\n")
    for i, c in enumerate(challenges, 1):
        severity_color = {"high": "red", "medium": "yellow", "low": "white"}[c.severity]
        console.print(f"[{severity_color}]#{i} {c.challenge_question}[/{severity_color}]")
        console.print(f"  주장: {c.claim[:60]}...")
        console.print(f"  반대 전제: {c.counter_premise}")
        console.print(f"  시나리오: {c.counter_scenario[:80]}...")
        console.print(f"  함의: {c.implication[:80]}...\n")


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
