"""Developer and operator CLI for the governed content workflow."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from zoneinfo import ZoneInfo

import typer

from .config import Settings
from .generation import OpenAIAgentsBackend
from .models import ArticleDraft, ContentJob, JobStatus, Source
from .validators import render_supraj_website_mdx
from .workflow import attach_draft, generate_validated_article, validate_job

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Supraj Content Agent operator utilities."""


@app.command()
def validate_example() -> None:
    """Run the deterministic Phase-1 gates against a synthetic article."""

    body = """## Why this workflow exists

A publishing agent should not be allowed to turn uncertain model output directly
into a production website change. The workflow therefore separates research and
writing from deterministic release gates. This example repeats enough explanatory
material to exercise the minimum-size gate while keeping the command self-contained.

## How the gate works

The draft is represented by a typed contract. Sources are explicit records rather
than URLs hidden in prose. Before publication, deterministic validators inspect
article structure, source diversity, unfinished markers, and other requirements.
A failed check moves the job to a blocked state instead of allowing publication.

""" * 8

    draft = ArticleDraft(
        title="Building a Safe Automated Publishing Workflow",
        description=(
            "A practical example of separating AI-assisted writing from deterministic "
            "validation and publication gates."
        ),
        slug="safe-automated-publishing-workflow",
        body_markdown=body,
        tags=["AI Agents", "Automation"],
        sources=[
            Source(title="Astro documentation", publisher="Astro", url="https://docs.astro.build/"),
            Source(title="Python documentation", publisher="Python", url="https://docs.python.org/3/"),
        ],
        hero_emoji="⚙️",
        reading_time="5 min read",
    )

    job = ContentJob(id=str(uuid4()), topic=draft.title, status=JobStatus.DRAFTING)
    job = attach_draft(job, draft)
    job = validate_job(job)

    typer.echo(f"status={job.status}")
    if job.validation:
        for finding in job.validation.findings:
            typer.echo(f"- {finding.code}: {finding.message}")

    if job.status is JobStatus.READY_FOR_PR:
        today = datetime.now(UTC).date().isoformat()
        typer.echo(render_supraj_website_mdx(draft, today))


@app.command()
def generate(
    topic: Annotated[str, typer.Argument(help="Technical topic to research and draft.")],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path for the validated SuprajWebsite MDX article.",
        ),
    ] = None,
) -> None:
    """Run the live research/writer/reviewer workflow for one topic."""

    if not os.getenv("OPENAI_API_KEY"):
        typer.echo(
            "OPENAI_API_KEY is not set. Live agent execution is disabled; "
            "no research call was attempted.",
            err=True,
        )
        raise typer.Exit(code=2)

    settings = Settings()
    backend = OpenAIAgentsBackend(model=settings.model)
    job = generate_validated_article(
        topic,
        backend,
        max_revision_attempts=settings.max_revision_attempts,
    )

    typer.echo(f"job_id={job.id}")
    typer.echo(f"status={job.status}")
    typer.echo(f"revision_attempt={job.attempt}")

    if job.status is not JobStatus.READY_FOR_PR or job.draft is None:
        if job.editorial_review:
            for finding in job.editorial_review.findings:
                typer.echo(f"- {finding.code}: {finding.message}", err=True)
        if job.validation:
            for finding in job.validation.findings:
                typer.echo(f"- {finding.code}: {finding.message}", err=True)
        raise typer.Exit(code=1)

    publication_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    mdx = render_supraj_website_mdx(job.draft, publication_date)

    if output is None:
        typer.echo(f"slug={job.draft.slug}")
        typer.echo("validated=true")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(mdx, encoding="utf-8")
    typer.echo(f"mdx={output}")


if __name__ == "__main__":
    app()
