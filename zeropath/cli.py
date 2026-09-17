from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from zeropath.ops import kill_run
from zeropath.orchestrator import Orchestrator
from zeropath.paths import lab_dir as _lab_dir, triads_dir
from zeropath.rooms import all_rooms, get_room, rooms_dir
from zeropath.util import new_run_id, runs_dir
from zeropath.replay import iter_jsonl


app = typer.Typer(add_completion=False, no_args_is_help=True)
rooms_app = typer.Typer(add_completion=False, no_args_is_help=True)
triads_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(rooms_app, name="rooms")
app.add_typer(triads_app, name="triads")

console = Console()


@rooms_app.command("list")
def rooms_list() -> None:
    rooms = all_rooms()
    t = Table(title="ZeroPath Rooms (local lab)")
    t.add_column("room_id", style="bold")
    t.add_column("title")
    t.add_column("start_path")
    t.add_column("max_steps", justify="right")
    for r in rooms.values():
        t.add_row(r.room_id, r.title, r.start_path, str(r.max_steps))
    console.print(t)
    console.print(f"[dim]Configs:[/dim] {rooms_dir().resolve()}")


@app.command()
def run(
    room_id: str = typer.Argument(..., help="Room ID (see: zeropath rooms list)"),
    agent: str = typer.Option("heuristic", help="Agent to use (heuristic | llm)"),
    keep_env: bool = typer.Option(False, help="Keep the Docker container running after the run."),
    live: bool = typer.Option(True, help="Print live step updates during the run."),
    backend: str = typer.Option("auto", help="Lab backend: auto | local | docker."),
) -> None:
    run_id = new_run_id()
    room = get_room(room_id)
    lab_dir = _lab_dir()

    console.print(f"[bold]run_id[/bold]: {run_id}")
    console.print(f"[bold]room[/bold]: {room.room_id} — {room.title}")

    orch = Orchestrator(run_id=run_id, room=room, lab_dir=lab_dir, backend=backend)
    try:
        def _update(ev: dict) -> None:
            if not live:
                return
            if "error" in ev:
                console.print(f"[red]step {ev.get('step')}[/red] [{ev.get('phase')}] {ev.get('tool')}: {ev.get('error')}")
                return
            if "flag" in ev:
                console.print(f"[green]flag[/green] {ev.get('flag')}")
                return
            if "status" in ev:
                console.print(
                    f"[dim]step {ev.get('step')}[/dim] [{ev.get('phase')}] {ev.get('tool')} {ev.get('path')} -> {ev.get('status')}"
                )

        res = orch.run(agent_name=agent, on_update=_update, keep_env=keep_env)
        if res.ok:
            console.print(f"[green]SUCCESS[/green] in {res.steps} steps")
            console.print(f"[bold]flag[/bold]: {res.flag}")
        else:
            console.print(f"[red]FAILED[/red] after {res.steps} steps: {res.error}")
        console.print(f"[dim]Logs:[/dim] {(runs_dir() / run_id).resolve()}")
        if not res.ok:
            raise typer.Exit(code=1)
    finally:
        if not keep_env:
            orch.kill()


@app.command()
def demo(
    agent: str = typer.Option("heuristic", help="Agent to use (heuristic | llm)"),
    max_rooms: int = typer.Option(6, help="How many rooms to run (in listing order)."),
) -> None:
    rooms = list(all_rooms().values())[: int(max_rooms)]
    t = Table(title="ZeroPath Demo Run")
    t.add_column("room_id", style="bold")
    t.add_column("ok")
    t.add_column("steps", justify="right")
    t.add_column("flag")

    for room in rooms:
        run_id = new_run_id()
        orch = Orchestrator(run_id=run_id, room=room, lab_dir=_lab_dir())
        try:
            res = orch.run(agent_name=agent, on_update=None)
            t.add_row(room.room_id, "yes" if res.ok else "no", str(res.steps), str(res.flag or ""))
        finally:
            orch.kill()

    console.print(t)


@app.command("benchmark")
def capability_benchmark(
    agent: str = typer.Option("heuristic", help="heuristic | llm"),
    backend: str = typer.Option("local", help="local | docker | auto"),
    repeats: int = typer.Option(1, min=1, max=100),
    output: Path = typer.Option(Path("runs/benchmark.json"), help="Aggregate JSON report."),
) -> None:
    """Measure all synthetic local rooms and retain per-run evidence reports."""
    from zeropath.benchmark import benchmark

    result = benchmark(list(all_rooms().values()), lab_dir=_lab_dir(),
                       agent=agent, backend=backend, repeats=repeats, output=output)
    table = Table(title="ZeroPath Local Capability Benchmark")
    for name in ("Room", "Repeat", "Result", "Attempts", "Seconds"):
        table.add_column(name)
    for row in result["runs"]:
        table.add_row(row["room_id"], str(row["repeat"]), "PASS" if row["ok"] else "FAIL",
                      str(row["steps"]), f"{row['duration_s']:.3f}")
    console.print(table)
    console.print(f"Passed {result['passed']}/{result['total']}; report: {output.resolve()}")
    console.print("Synthetic local lab only. TryHackMe and human-time milestones remain unverified.")
    if result["failed"]:
        raise typer.Exit(code=1)


@app.command()
def replay(run_id: str = typer.Argument(..., help="Run ID to replay (from runs/<run_id>)")) -> None:
    run_dir = runs_dir() / run_id
    events = run_dir / "events.jsonl"
    summary = run_dir / "summary.json"
    if not events.exists():
        raise typer.BadParameter(f"Missing events file: {events}")

    console.print(f"[bold]Replaying[/bold] {run_id}")
    if summary.exists():
        console.print(f"[dim]Summary:[/dim] {summary.resolve()}")

    for e in iter_jsonl(events):
        kind = e.get("kind")
        data = e.get("data") or {}
        if kind == "step":
            console.print(
                f"[cyan]step[/cyan] {data.get('n')} [{data.get('phase','?')}] {data.get('tool')}: {data.get('path')}"
            )
        elif kind == "http_response":
            console.print(f"  -> {data.get('status')} ({data.get('len')} bytes)")
        elif kind == "flag_found":
            console.print(f"[green]flag_found[/green]: {data.get('flag')}")


@app.command()
def metrics(limit: int = typer.Option(50, help="Max number of runs to include.")) -> None:
    base = runs_dir()
    if not base.exists():
        console.print("[yellow]No runs directory yet.[/yellow]")
        return

    summaries: list[dict] = []
    for p in sorted(base.glob("*/summary.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            summaries.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
        if len(summaries) >= limit:
            break

    if not summaries:
        console.print("[yellow]No run summaries found.[/yellow]")
        return

    ok = sum(1 for s in summaries if s.get("ok"))
    total = len(summaries)

    t = Table(title=f"Recent Runs (success {ok}/{total} = {ok/total:.0%})")
    t.add_column("run_id", style="bold")
    t.add_column("room_id")
    t.add_column("ok")
    t.add_column("steps", justify="right")
    t.add_column("flag")

    for s in summaries:
        t.add_row(
            str(s.get("run_id", "")),
            str(s.get("room_id", "")),
            "yes" if s.get("ok") else "no",
            str(s.get("steps", "")),
            str(s.get("flag") or ""),
        )
    console.print(t)


@app.command()
def kill(run_id: str = typer.Argument(..., help="Run ID to terminate (kills its Docker container)")) -> None:
    kill_run(run_id)
    console.print(f"[yellow]Killed[/yellow] run {run_id} (if it was running).")


@app.command("harvest")
def harvest(
    url: Optional[str] = typer.Option(None, help="Direct writeup URL to scrape and document."),
    limit: int = typer.Option(5, help="Number of rooms to harvest from curated source list."),
) -> None:
    """Scrape and document TryHackMe rooms from Medium/blogs into the knowledge base."""
    from zeropath.scrapers.thm_scraper import THMScraper
    from zeropath.scrapers.sync_kb import save_room_yaml, sync_room_to_kb, save_room_catalog
    from zeropath.db import KnowledgeBase

    console.print("[bold cyan]ZeroPath Ingestion Agent[/bold cyan]: Harvesting TryHackMe rooms...")
    kb = KnowledgeBase()
    kb.init()

    # Import default seeds from runner
    import importlib.util
    import scripts.run_thm_agent as _runner

    seeds = _runner.DEFAULT_TARGET_ROOMS

    scraper = THMScraper()
    items = [{"name": "Custom", "url": url}] if url else seeds[:limit]
    profiles = []

    for item in items:
        target_url = item.get("url", "")
        hint_name = item.get("name", "")
        console.print(f"[*] Fetching: {hint_name or target_url} ...")
        prof = scraper.scrape_and_parse(target_url, room_hint=hint_name)
        if item.get("code"):
            prof.code = item["code"]
        if item.get("difficulty"):
            prof.difficulty = item["difficulty"]
        if item.get("category"):
            prof.category = item["category"]

        save_room_yaml(prof)
        sync_room_to_kb(prof, kb)
        profiles.append(prof)
        console.print(f"    [green]✓[/green] Documented [bold]{prof.code}[/bold] ({len(prof.attack_chain)} attack steps)")

    cat_path = save_room_catalog(profiles)
    console.print(f"[bold green]Harvesting complete![/bold green] Catalog: {cat_path}")


@triads_app.command("validate")
def triads_validate(
    path: Path = typer.Option(triads_dir(), help="Directory containing triad YAML files."),
    require_reviewed: bool = typer.Option(False, help="Fail when any record is still a draft."),
) -> None:
    """Validate triad schemas, sourcing, and operational quality gates."""
    from scripts.validate_triads import validate_directory

    triads, issues = validate_directory(path, require_reviewed=require_reviewed)
    if issues:
        for issue in issues:
            console.print(f"[red]ERROR[/red] {issue.path}: {issue.message}")
        raise typer.Exit(code=1)
    console.print(f"[green]PASS[/green] {len(triads)} triad(s)")


@triads_app.command("fetch")
def triads_fetch(
    refresh: bool = typer.Option(False, help="Replace cached official data."),
    skip_nvd: bool = typer.Option(False, help="Skip the rate-limited NVD API feed."),
) -> None:
    """Fetch official ATT&CK, D3FEND, and NVD data into the local cache."""
    from scripts.fetch_official_data import DEFAULT_OUTPUT, fetch_official_data

    for filename, state in fetch_official_data(
        DEFAULT_OUTPUT, refresh=refresh, include_nvd=not skip_nvd
    ).items():
        console.print(f"{state:9} {filename}")


@triads_app.command("skeleton")
def triads_skeleton(
    limit: int = typer.Option(50, min=1, help="Maximum number of draft skeletons to create."),
) -> None:
    """Create draft YAML skeletons from the cached ATT&CK bundle."""
    from scripts.make_skeleton_triads import DEFAULT_ATTACK, DEFAULT_OUTPUT, make_skeletons

    written = make_skeletons(DEFAULT_ATTACK, DEFAULT_OUTPUT, limit=limit)
    console.print(f"[green]Created[/green] {len(written)} draft triad(s)")


@triads_app.command("sync")
def triads_sync(
    path: Path = typer.Option(triads_dir(), help="Reviewed triad source directory."),
) -> None:
    """Validate and load reviewed triads into SQLite and the local graph."""
    from scripts.validate_triads import validate_directory
    from zeropath.scrapers.sync_triads import sync_triads

    triads, issues = validate_directory(path)
    if issues:
        for issue in issues:
            console.print(f"[red]ERROR[/red] {issue.path}: {issue.message}")
        raise typer.Exit(code=1)
    synced = sync_triads(path)
    console.print(f"[green]Synced[/green] {len(synced)} reviewed triad(s)")


@triads_app.command("list")
def triads_list() -> None:
    """List reviewed triads stored in SQLite."""
    from zeropath.db import KnowledgeBase

    kb = KnowledgeBase()
    kb.init()
    rows = kb.list_triads(status="reviewed")
    table = Table(title="ZeroPath Reviewed Triads")
    table.add_column("ATT&CK ID", style="bold")
    table.add_column("Technique")
    table.add_column("Kill Chain")
    table.add_column("Platforms")
    for row in rows:
        table.add_row(
            row["technique_id"],
            row["name"],
            ", ".join(row["kill_chain"]),
            ", ".join(row["platforms"]),
        )
    console.print(table)


@triads_app.command("show")
def triads_show(technique_id: str = typer.Argument(..., help="ATT&CK technique ID, such as T1003.001")) -> None:
    """Display a complete stored triad as JSON."""
    from zeropath.db import KnowledgeBase

    kb = KnowledgeBase()
    kb.init()
    payload = kb.get_triad(technique_id.upper())
    if payload is None:
        console.print(f"[red]Not found:[/red] {technique_id}")
        raise typer.Exit(code=1)
    console.print_json(data=payload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()



