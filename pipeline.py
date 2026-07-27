"""
qClip — CLI Entry Point

Thin CLI on top of the Celery task chain. Use this for one-off local runs;
production goes through the FastAPI endpoint.

Usage:
    python pipeline.py "https://www.twitch.tv/videos/123"
    python pipeline.py ./recording.mp4 --clips 7 --preset battle_royale
    python pipeline.py ./recording.mp4 --watch  # tail the SSE stream until done
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from backend.api.schemas import CreateJobRequest
from backend.db.session import db_session
from backend.services.job_service import JobService
from backend.services.sse import stream_job_progress
from core.config import get_settings
from core.creator_options import CAPTION_STYLE_IDS, REFRAME_PRESET_IDS
from core.storage import make_storage, upload_key
from core.task_dispatch import dispatch_task
from core.tasks.pipeline_tasks import start_pipeline

console = Console()
log = structlog.get_logger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _create_and_dispatch(
    source: str,
    *,
    clips: int,
    style: str,
    preset: str,
) -> str:
    """Create a Job row, push to Celery, return the job_id."""
    cfg = get_settings()
    storage = make_storage(cfg)

    # If `source` is a local file, upload it to storage first
    storage_key: str | None = None
    source_url: str | None = None

    if Path(source).exists():
        local = Path(source).resolve()
        key = upload_key("cli", local.stem, local.name)
        console.print(f"[cyan]Uploading[/cyan] {local.name} → {key}")
        storage.upload(key, local, content_type="video/mp4")
        storage_key = key
    elif source.startswith(("http://", "https://")):
        source_url = source
    else:
        raise click.UsageError(f"Source must be a URL or existing file: {source!r}")

    async with db_session() as db:
        svc = JobService(db, cfg, storage)
        request = CreateJobRequest(
            source_url=source_url,
            source_upload_key=storage_key,
            target_clips=clips,
            caption_style=style,
            reframe_preset=preset,
        )
        job = await svc.create_job(request, owner_id=None)
        # Commit the job row so the worker sees it
        await db.commit()

        # Dispatch through the queue seam (Celery or in-process)
        task = dispatch_task(start_pipeline, args=(job.id,))
        await svc.jobs.attach_celery_task(job.id, task.id)
        await db.commit()

    return job.id


async def _watch(job_id: str) -> None:
    """Tail the SSE stream until the job ends."""
    cfg = get_settings()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
    task_id = progress.add_task("Initialising", total=100)

    with progress:
        async for chunk in stream_job_progress(job_id, cfg):
            # SSE frames are `event: ... \n data: {...}\n\n` — parse manually
            for line in chunk.splitlines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                progress.update(
                    task_id,
                    completed=data["progress"] * 100,
                    description=data.get("message") or data.get("stage", ""),
                )

                if data.get("status") in ("done", "error"):
                    await _print_summary(job_id)
                    return


async def _print_summary(job_id: str) -> None:
    async with db_session() as db:
        svc = JobService(db, get_settings(), make_storage(get_settings()))
        job = await svc.get_job(job_id, owner_id=None)

    table = Table(title=f"Job {job_id[:8]}", show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Title", min_width=24)
    table.add_column("Score", width=7)
    table.add_column("Emotion", width=10)
    table.add_column("Duration", width=9)
    table.add_column("Status", width=10)
    table.add_column("Hook", min_width=30)

    for i, clip in enumerate(job.clips, 1):
        status_style = "green" if clip.status.value == "done" else "red"
        table.add_row(
            str(i),
            (clip.title or "—")[:28],
            f"{clip.ensemble_score:.3f}",
            clip.emotion,
            f"{clip.duration_secs:.0f}s",
            f"[{status_style}]{clip.status.value}[/{status_style}]",
            (clip.hook[:55] + "…") if len(clip.hook) > 55 else clip.hook,
        )

    console.print()
    console.print(Panel(table, border_style="cyan"))
    console.print()


# ─── CLI ─────────────────────────────────────────────────────────────────────

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("source")
@click.option("--clips", default=5, show_default=True, help="Number of clips to generate")
@click.option("--style", default="gaming_impact", show_default=True,
              type=click.Choice(list(CAPTION_STYLE_IDS)),
              help="Caption style")
@click.option("--preset", default="fps_game", show_default=True,
              type=click.Choice(list(REFRAME_PRESET_IDS)),
              help="Reframe preset")
@click.option("--watch/--no-watch", default=True,
              help="Tail the progress stream until done")
def main(source: str, clips: int, style: str, preset: str, watch: bool) -> None:
    """qClip — AI video clip pipeline CLI."""

    async def _run() -> None:
        job_id = await _create_and_dispatch(
            source, clips=clips, style=style, preset=preset,
        )
        console.print(f"\n[bold green]Job created:[/bold green] {job_id}\n")

        if watch:
            await _watch(job_id)
        else:
            console.print(
                f"Tail the progress with: "
                f"[cyan]curl http://localhost:8000/api/jobs/{job_id}/progress[/cyan]\n"
            )

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
