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
def help():
    """Show cast commands and usage."""
    console.print()
    console.print("[bold cyan]cast[/bold cyan]  [dim]record. replay. rewind. time-travel debugger for AI agents.[/dim]")
    console.print()
    console.print("[bold]usage[/bold]")
    console.print("  wrap your agent with [cyan]@cast.record[/cyan] to start recording runs.")
    console.print()
    console.print("[bold]commands[/bold]")
    console.print()
    console.print(f"  [cyan]cast list[/cyan]              list all recorded runs")
    console.print(f"  [cyan]cast list --limit 5[/cyan]    list last 5 runs")
    console.print(f"  [cyan]cast show <run_id>[/cyan]     inspect every step of a run")
    console.print(f"  [cyan]cast last[/cyan]              inspect the most recent run")
    console.print()
    console.print("[bold]example[/bold]")
    console.print()
    console.print("  [dim]# wrap your agent[/dim]")
    console.print("  [cyan]@cast.record[/cyan]")
    console.print("  [cyan]def run_agent(user_input):[/cyan]")
    console.print("  [cyan]    ...[/cyan]")
    console.print()
    console.print("  [dim]# then inspect[/dim]")
    console.print("  [cyan]$ cast list[/cyan]")
    console.print("  [cyan]$ cast last[/cyan]")
    console.print("  [cyan]$ cast show a3f9c1e8[/cyan]")
    console.print()


@cli.command()
@click.option("--limit", default=20, help="Number of runs to show")
def list(limit: int):
    """List all recorded runs."""
    runs = list_runs(limit)

    if not runs:
        console.print("[dim]no runs yet. wrap your agent with @cast.record to start.[/dim]")
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
def show(run_id: str):
    """Inspect every step of a run."""
    run = load_run(run_id)
    if not run:
        console.print(f"[red]run {run_id} not found[/red]")
        return
    _print_run(run)


@cli.command()
def last():
    """Inspect the most recent run."""
    runs = list_runs(limit=1)
    if not runs:
        console.print("[dim]no runs yet.[/dim]")
        return
    _print_run(runs[0])


def _print_run(run):
    console.print(f"\n[bold cyan]run {run.id}[/bold cyan]  "
                  f"[dim]{run.name} · {run.started_at.strftime('%Y-%m-%d %H:%M:%S')} · "
                  f"{run.total_tokens} tokens · {run.duration_ms}ms[/dim]\n")

    if not run.steps:
        console.print("[dim]no steps recorded.[/dim]")
        return

    for step in run.steps:
        first_message = step.prompt[0] if step.prompt else {}
        prompt_preview = str(first_message.get("content", ""))[:120]

        console.print(f"[bold]step {step.index}[/bold]  "
                      f"[dim]{step.model} · {step.total_tokens} tokens · {step.latency_ms}ms[/dim]")

        console.print(Panel(
            f"[dim]prompt:[/dim] {prompt_preview}\n\n"
            f"[dim]response:[/dim] {step.response}",
            border_style="dim",
            padding=(0, 1),
        ))

        if step.tool_calls:
            for tc in step.tool_calls:
                console.print(f"  [yellow]⚙ tool_call[/yellow] [bold]{tc.name}[/bold]  "
                               f"[dim]{tc.arguments}[/dim]")

        console.print()