"""Small developer CLI for exercising deterministic gates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import typer

from .models import ArticleDraft, ContentJob, JobStatus, Source
from .validators import render_supraj_website_mdx
from .workflow import attach_draft, validate_job

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Supraj Content Agent developer utilities."""


@app.command()
def validate_example() -> None:
    """Run the Phase-1 gates against a local synthetic article."""

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


if __name__ == "__main__":
    app()
