"""Explicit Phase-1 workflow transitions.

The workflow is intentionally small before adding LangGraph execution. The
state-transition rules are ordinary Python so they remain testable even if the
agent framework changes later.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .models import ArticleDraft, ContentJob, JobStatus
from .validators import validate_article


def attach_draft(job: ContentJob, draft: ArticleDraft) -> ContentJob:
    if job.status not in {JobStatus.RESEARCHING, JobStatus.DRAFTING}:
        raise ValueError(f"Cannot attach a draft while job is {job.status}")

    return job.model_copy(
        update={
            "draft": draft,
            "status": JobStatus.VALIDATING,
            "updated_at": datetime.now(UTC),
        }
    )


def validate_job(job: ContentJob) -> ContentJob:
    if job.status is not JobStatus.VALIDATING or job.draft is None:
        raise ValueError("Job must contain a draft and be in validating state.")

    report = validate_article(job.draft)
    status = JobStatus.READY_FOR_PR if report.passed else JobStatus.BLOCKED

    return job.model_copy(
        update={
            "validation": report,
            "status": status,
            "updated_at": datetime.now(UTC),
        }
    )
