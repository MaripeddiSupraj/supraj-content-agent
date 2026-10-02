"""Core durable contracts for the content publishing workflow.

These Pydantic models are the boundary between agents and deterministic code.
Keeping the boundary explicit makes it possible to validate, persist, replay,
and audit each publication run without trusting free-form model text.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(StrEnum):
    QUEUED = "queued"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    VALIDATING = "validating"
    READY_FOR_PR = "ready_for_pr"
    PR_CREATED = "pr_created"
    PUBLISHED = "published"
    BLOCKED = "blocked"


class Source(BaseModel):
    title: str = Field(min_length=3)
    url: HttpUrl
    publisher: str = Field(min_length=2)
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResearchClaim(BaseModel):
    statement: str = Field(min_length=12)
    source_urls: list[HttpUrl] = Field(min_length=1)
    confidence: Literal["high", "medium", "low"] = "medium"


class ResearchPacket(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    angle: str = Field(min_length=20, max_length=500)
    audience: str = Field(min_length=10, max_length=300)
    key_points: list[str] = Field(min_length=3, max_length=12)
    claims: list[ResearchClaim] = Field(min_length=1, max_length=30)
    sources: list[Source] = Field(min_length=2, max_length=20)
    caveats: list[str] = Field(default_factory=list, max_length=12)


class ArticleDraft(BaseModel):
    title: str = Field(min_length=8, max_length=120)
    description: str = Field(min_length=40, max_length=220)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    body_markdown: str = Field(min_length=500)
    tags: list[str] = Field(min_length=1, max_length=8)
    sources: list[Source] = Field(min_length=1)
    hero_emoji: str | None = None
    reading_time: str | None = None


class ReviewFinding(BaseModel):
    code: str = Field(min_length=3)
    message: str = Field(min_length=8)
    blocking: bool = True
    suggested_fix: str | None = None


class EditorialReview(BaseModel):
    summary: str = Field(min_length=10, max_length=1000)
    findings: list[ReviewFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(item.blocking for item in self.findings)


class ValidationFinding(BaseModel):
    code: str
    message: str
    blocking: bool = True


class ValidationReport(BaseModel):
    findings: list[ValidationFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(item.blocking for item in self.findings)


class ContentJob(BaseModel):
    id: str
    topic: str = Field(min_length=3, max_length=200)
    status: JobStatus = JobStatus.QUEUED
    attempt: int = Field(default=0, ge=0)
    research: ResearchPacket | None = None
    draft: ArticleDraft | None = None
    editorial_review: EditorialReview | None = None
    validation: ValidationReport | None = None
    website_pr_url: HttpUrl | None = None
    published_url: HttpUrl | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
