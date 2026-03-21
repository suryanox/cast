from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

from .store import list_runs, load_run, clear_runs
from .models import RunStatus

console = Console()

STATUS_STYLE = {
    RunStatus.DONE:    ("✓ done",    "green"),
    RunStatus.FAILED:  ("✗ failed",  "red"),
    RunStatus.RUNNING: ("⟳ running", "yellow"),
}


@click.group()
def cli():
    pass


@cli.command()
def help():
    console.print()
    console.print(Rule("[bold cyan]cast[/bold cyan]  [dim]record. replay. rewind.[/dim]"))
    console.print()

    console.print("  [bold white]commands[/bold white]")
    console.print()
    commands = [
        ("cast list",             "",              "list all recorded runs"),
        ("cast list",             "--limit 5",     "show last 5 runs"),
        ("cast show",             "<run_id>",      "inspect every step of a run"),
        ("cast last",             "",              "inspect the most recent run"),
        ("cast clear",            "",              "delete all recorded runs"),
    ]
    for cmd, arg, desc in commands:
        console.print(f"  [cyan]{cmd}[/cyan] [yellow]{arg}[/yellow]"
                      f"{'':>{28 - len(cmd) - len(arg)}}[dim]{desc}[/dim]")

    console.print()
    console.print("  [bold white]quickstart[/bold white]")
    console.print()
    console.print("  [dim]1. wrap your agent[/dim]")
    console.print()
    console.print("  [bright_black]  import[/bright_black] [cyan]cast[/cyan]")
    console.print()
    console.print("  [cyan]  @cast.record[/cyan]")
    console.print("  [white]  def[/white] [cyan]run_agent[/cyan][white](user_input):[/white]")
    console.print("  [white]      ...[/white]")
    console.print()
    console.print("  [dim]2. run it — cast records everything automatically[/dim]")
    console.print()
    console.print("  [dim]3. inspect[/dim]")
    console.print()
    console.print("  [bright_black]  $[/bright_black] [cyan]cast list[/cyan]")
    console.print("  [bright_black]  $[/bright_black] [cyan]cast last[/cyan]")
    console.print("  [bright_black]  $[/bright_black] [cyan]cast show a3f9c1e8[/cyan]")
    console.print()
    console.print(Rule(style="dim"))
    console.print()


@cli.command()
@click.option("--limit", default=20, help="Number of runs to show")
def list(limit: int):
    runs = list_runs(limit)

    if not runs:
        console.print()
        console.print("  [dim]no runs yet.[/dim]  wrap your agent with [cyan]@cast.record[/cyan] to start.")
        console.print()
        return

    console.print()
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="dim",
        show_edge=False,
        pad_edge=True,
    )
    table.add_column("run id",   style="cyan",    width=10)
    table.add_column("name",                      width=22)
    table.add_column("started",  style="dim",     width=20)
    table.add_column("steps",    justify="right", width=6)
    table.add_column("tokens",   justify="right", width=8)
    table.add_column("duration", justify="right", width=10)
    table.add_column("status",                    width=12)

    for run in runs:
        label, color = STATUS_STYLE[run.status]
        duration = f"{run.duration_ms}ms" if run.duration_ms else "—"
        name = run.name
        if run.forked_from:
            name += f" [dim](⑂ {run.forked_from})[/dim]"

        table.add_row(
            run.id,
            name,
            run.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"[white]{len(run.steps)}[/white]",
            f"[white]{run.total_tokens}[/white]",
            f"[dim]{duration}[/dim]",
            f"[{color}]{label}[/{color}]",
        )

    console.print(table)
    console.print(f"  [dim]{len(runs)} run(s) · "
                  f"cast show <run_id> to inspect[/dim]")
    console.print()


@cli.command()
@click.argument("run_id")
def show(run_id: str):
    run = load_run(run_id)
    if not run:
        console.print(f"\n  [red]✗[/red] run [cyan]{run_id}[/cyan] not found\n")
        return
    _print_run(run)


@cli.command()
def last():
    runs = list_runs(limit=1)
    if not runs:
        console.print("\n  [dim]no runs yet.[/dim]\n")
        return
    _print_run(runs[0])


@cli.command()
@click.confirmation_option(prompt="  ⚠ delete all recorded runs. are you sure?")
def clear():
    count = clear_runs()
    console.print(f"\n  [dim]deleted [white]{count}[/white] run(s). fresh start.[/dim]\n")


def _print_run(run):
    label, color = STATUS_STYLE[run.status]

    console.print()
    console.print(Rule(
        f"[bold cyan]{run.id}[/bold cyan]  "
        f"[dim]{run.name}[/dim]  "
        f"[{color}]{label}[/{color}]"
    ))
    console.print(
        f"  [dim]started[/dim] {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}  "
        f"[dim]·[/dim]  [white]{run.total_tokens}[/white] [dim]tokens[/dim]  "
        f"[dim]·[/dim]  [white]{run.duration_ms}ms[/white]  "
        + (f"[dim]·[/dim]  [dim]⑂ forked from [cyan]{run.forked_from}[/cyan] at step {run.forked_at_step}[/dim]"
           if run.forked_from else "")
    )
    console.print()

    if not run.steps:
        console.print("  [dim]no steps recorded.[/dim]")
        console.print()
        return

    for step in run.steps:
        console.print(
            f"  [bold white]step {step.index}[/bold white]  "
            f"[dim]{step.model}[/dim]  "
            f"[cyan]{step.total_tokens} tokens[/cyan]  "
            f"[dim]{step.latency_ms}ms[/dim]"
        )
        console.print()

        first_message = step.prompt[0] if step.prompt else {}
        prompt_text = str(first_message.get("content", ""))
        console.print(Panel(
            f"[dim]{prompt_text}[/dim]",
            title="[dim]prompt[/dim]",
            title_align="left",
            border_style="bright_black",
            padding=(0, 2),
        ))

        if step.tool_calls:
            for tc in step.tool_calls:
                console.print(
                    f"  [yellow]⚙[/yellow]  [bold yellow]{tc.name}[/bold yellow]  "
                    f"[dim]{tc.arguments}[/dim]"
                )
            console.print()

        console.print(Panel(
            f"[white]{step.response}[/white]",
            title="[dim]response[/dim]",
            title_align="left",
            border_style="cyan",
            padding=(0, 2),
        ))
        console.print()

    console.print(Rule(style="dim"))
    console.print()