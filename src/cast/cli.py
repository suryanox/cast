from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .store import list_runs, load_run
from .models import RunStatus

console = Console()


@click.group()
def cli():
    """cast — record. replay. rewind. time-travel debugger for AI agents."""
    pass


@cli.command()
@click.option("--limit", default=20, help="Number of runs to show")
def list(limit: int):
    """List all recorded runs."""
    runs = list_runs(limit)

    if not runs:
        console.print("[dim]no runs recorded yet. wrap your agent with @record to start.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("run id", style="cyan", width=10)
    table.add_column("name", width=20)
    table.add_column("started", width=20)
    table.add_column("steps", justify="right", width=6)
    table.add_column("tokens", justify="right", width=8)
    table.add_column("duration", justify="right", width=10)
    table.add_column("status", width=10)

    for run in runs:
        status_style = {
            RunStatus.DONE: "[green]✓ done[/green]",
            RunStatus.FAILED: "[red]✗ failed[/red]",
            RunStatus.RUNNING: "[yellow]⟳ running[/yellow]",
        }[run.status]

        duration = f"{run.duration_ms}ms" if run.duration_ms else "—"
        forked = f" [dim](fork of {run.forked_from})[/dim]" if run.forked_from else ""

        table.add_row(
            run.id,
            run.name + forked,
            run.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            str(len(run.steps)),
            str(run.total_tokens),
            duration,
            status_style,
        )

    console.print(table)


@cli.command()
@click.argument("run_id")
def inspect(run_id: str):
    """Inspect every step of a run."""
    run = load_run(run_id)
    if not run:
        console.print(f"[red]run {run_id} not found[/red]")
        return

    console.print(f"\n[bold cyan]run {run.id}[/bold cyan]  "
                  f"[dim]{run.name} · {run.started_at.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{run.total_tokens} tokens · {run.duration_ms}ms[/dim]\n")

    for step in run.steps:
        first_message = step.prompt[0] if step.prompt else {}
        prompt_preview = str(first_message.get("content", ""))[:120]

        console.print(f"[bold]step {step.index}[/bold]  "
                      f"[dim]{step.model} · {step.total_tokens} tokens · {step.latency_ms}ms[/dim]")

        console.print(Panel(
            f"[dim]prompt:[/dim] {prompt_preview}\n\n"
            f"[dim]response:[/dim] {step.response[:300]}",
            border_style="dim",
            padding=(0, 1),
        ))

        if step.tool_calls:
            for tc in step.tool_calls:
                console.print(f"  [yellow]⚙ tool_call[/yellow] [bold]{tc.name}[/bold]  "
                               f"[dim]{tc.arguments}[/dim]")

        console.print()


@cli.command()
@click.argument("run_id_a")
@click.argument("run_id_b")
def diff(run_id_a: str, run_id_b: str):
    """Diff two runs step by step."""
    run_a = load_run(run_id_a)
    run_b = load_run(run_id_b)

    if not run_a:
        console.print(f"[red]run {run_id_a} not found[/red]")
        return
    if not run_b:
        console.print(f"[red]run {run_id_b} not found[/red]")
        return

    console.print(f"\n[bold]diff[/bold]  "
                  f"[cyan]{run_id_a}[/cyan] vs [cyan]{run_id_b}[/cyan]\n")

    max_steps = max(len(run_a.steps), len(run_b.steps))
    diverged = False

    for i in range(max_steps):
        step_a = run_a.steps[i] if i < len(run_a.steps) else None
        step_b = run_b.steps[i] if i < len(run_b.steps) else None

        if not step_a:
            console.print(f"  step {i}  [yellow]+ only in {run_id_b}[/yellow]  {step_b.response[:80]}")
            continue
        if not step_b:
            console.print(f"  step {i}  [yellow]- only in {run_id_a}[/yellow]  {step_a.response[:80]}")
            continue

        if step_a.response == step_b.response and step_a.model == step_b.model:
            console.print(f"  step {i}  [green]identical[/green]")
        else:
            diverged = True
            console.print(f"  step {i}  [red]✗ diverged[/red]")
            console.print(f"    [dim]{run_id_a}:[/dim] {step_a.response[:100]}")
            console.print(f"    [dim]{run_id_b}:[/dim] {step_b.response[:100]}")

    console.print()
    if not diverged:
        console.print("[green]runs are identical[/green]")
    else:
        console.print("[dim]tip: use [bold]cast fork[/bold] to explore a diverged branch[/dim]")