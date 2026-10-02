"""Governed Phase-1 content workflow.

Agents research, write, review, and revise. Ordinary Python owns state,
retry limits, deterministic validation, and eligibility for publication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .generation import ContentGenerationBackend
from .models import (
    ArticleDraft,
    ContentJob,
    EditorialReview,
    JobStatus,
    ReviewFinding,
    ValidationReport,
)
from .validators import validate_article


def _updated(job: ContentJob, **changes) -> ContentJob:
    changes["updated_at"] = datetime.now(UTC)
    return job.model_copy(update=changes)


def attach_draft(job: ContentJob, draft: ArticleDraft) -> ContentJob:
    if job.status not in {JobStatus.RESEARCHING, JobStatus.DRAFTING}:
        raise ValueError(f"Cannot attach a draft while job is {job.status}")

    return _updated(job, draft=draft, status=JobStatus.VALIDATING)


def validate_job(job: ContentJob) -> ContentJob:
    if job.status is not JobStatus.VALIDATING or job.draft is None:
        raise ValueError("Job must contain a draft and be in validating state.")

    approved_urls = None
    if job.research is not None:
        approved_urls = [str(source.url) for source in job.research.sources]

    report = validate_article(job.draft, approved_source_urls=approved_urls)
    status = JobStatus.READY_FOR_PR if report.passed else JobStatus.BLOCKED
    return _updated(job, validation=report, status=status)


def _validation_review(report: ValidationReport) -> EditorialReview:
    return EditorialReview(
        summary="Deterministic publication gates found blocking issues.",
        findings=[
            ReviewFinding(
                code=finding.code,
                message=finding.message,
                blocking=finding.blocking,
                suggested_fix="Revise the draft so this deterministic gate passes.",
            )
            for finding in report.findings
        ],
    )


def generate_validated_article(
    topic: str,
    backend: ContentGenerationBackend,
    *,
    max_revision_attempts: int = 2,
) -> ContentJob:
    """Run research -> writing -> review/repair -> deterministic validation.

    A return value of READY_FOR_PR is the only successful Phase-1 terminal state.
    BLOCKED means the bounded repair budget was exhausted.
    """

    if max_revision_attempts < 0:
        raise ValueError("max_revision_attempts must be non-negative")

    job = ContentJob(
        id=str(uuid4()),
        topic=topic,
        status=JobStatus.RESEARCHING,
    )

    research = backend.research(topic)
    job = _updated(job, research=research, status=JobStatus.DRAFTING)

    draft = backend.write(research)

    for attempt in range(max_revision_attempts + 1):
        job = _updated(
            job,
            draft=draft,
            attempt=attempt,
            status=JobStatus.REVIEWING,
        )

        review = backend.review(research, draft)
        job = _updated(job, editorial_review=review)

        if not review.passed:
            if attempt >= max_revision_attempts:
                return _updated(job, status=JobStatus.BLOCKED)
            draft = backend.revise(research, draft, review)
            continue

        job = _updated(job, status=JobStatus.VALIDATING)
        job = validate_job(job)
        if job.status is JobStatus.READY_FOR_PR:
            return job

        if attempt >= max_revision_attempts or job.validation is None:
            return job

        repair_review = _validation_review(job.validation)
        job = _updated(job, editorial_review=repair_review, status=JobStatus.REVIEWING)
        draft = backend.revise(research, draft, repair_review)

    return _updated(job, status=JobStatus.BLOCKED)
