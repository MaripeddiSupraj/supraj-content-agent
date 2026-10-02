from supraj_content_agent.models import (
    ArticleDraft,
    EditorialReview,
    JobStatus,
    ResearchClaim,
    ResearchPacket,
    ReviewFinding,
    Source,
)
from supraj_content_agent.workflow import generate_validated_article


def source(title: str, publisher: str, url: str) -> Source:
    return Source(title=title, publisher=publisher, url=url)


RESEARCH = ResearchPacket(
    topic="Agent sandboxes",
    angle="Explain why execution isolation matters for tool-using AI agents in production.",
    audience="Cloud, DevOps, platform, and AI infrastructure engineers.",
    key_points=[
        "Agents execute untrusted or model-generated actions.",
        "Isolation limits blast radius.",
        "Policy and observability remain necessary outside the sandbox.",
    ],
    claims=[
        ResearchClaim(
            statement="Execution isolation reduces the blast radius of risky agent actions.",
            source_urls=["https://docs.docker.com/"],
            confidence="high",
        )
    ],
    sources=[
        source("Docker docs", "Docker", "https://docs.docker.com/"),
        source("Python docs", "Python", "https://docs.python.org/3/"),
    ],
)


def valid_draft(body_suffix: str = "") -> ArticleDraft:
    return ArticleDraft(
        title="Why Production AI Agents Need Execution Sandboxes",
        description=(
            "A practical explanation of how execution isolation limits risk when "
            "tool-using AI agents run commands and modify systems."
        ),
        slug="why-production-ai-agents-need-execution-sandboxes",
        body_markdown="## Isolation boundary\n\n" + ("Technical explanation. " * 320) + body_suffix,
        tags=["AI Agents", "Platform Engineering"],
        sources=RESEARCH.sources,
        hero_emoji="📦",
        reading_time="7 min read",
    )


class PassingBackend:
    def research(self, topic: str) -> ResearchPacket:
        return RESEARCH.model_copy(update={"topic": topic})

    def write(self, research: ResearchPacket) -> ArticleDraft:
        return valid_draft()

    def review(self, research: ResearchPacket, draft: ArticleDraft) -> EditorialReview:
        return EditorialReview(summary="Grounded and technically suitable.", findings=[])

    def revise(
        self,
        research: ResearchPacket,
        draft: ArticleDraft,
        review: EditorialReview,
    ) -> ArticleDraft:
        raise AssertionError("Revision should not be called for a passing draft.")


class RepairingBackend(PassingBackend):
    def __init__(self) -> None:
        self.review_calls = 0
        self.revise_calls = 0

    def write(self, research: ResearchPacket) -> ArticleDraft:
        return valid_draft(" TODO")

    def review(self, research: ResearchPacket, draft: ArticleDraft) -> EditorialReview:
        self.review_calls += 1
        return EditorialReview(summary="Editorial review passes.", findings=[])

    def revise(
        self,
        research: ResearchPacket,
        draft: ArticleDraft,
        review: EditorialReview,
    ) -> ArticleDraft:
        self.revise_calls += 1
        return valid_draft()


class BlockingBackend(PassingBackend):
    def review(self, research: ResearchPacket, draft: ArticleDraft) -> EditorialReview:
        return EditorialReview(
            summary="Unsupported benchmark claim.",
            findings=[
                ReviewFinding(
                    code="evidence.unsupported",
                    message="The benchmark is not supported by the research packet.",
                    blocking=True,
                )
            ],
        )

    def revise(
        self,
        research: ResearchPacket,
        draft: ArticleDraft,
        review: EditorialReview,
    ) -> ArticleDraft:
        return draft


def test_full_workflow_reaches_ready_for_pr():
    job = generate_validated_article("Agent sandboxes", PassingBackend())

    assert job.status is JobStatus.READY_FOR_PR
    assert job.research is not None
    assert job.draft is not None
    assert job.validation is not None
    assert job.validation.passed


def test_deterministic_failure_enters_bounded_repair_loop():
    backend = RepairingBackend()

    job = generate_validated_article(
        "Agent sandboxes",
        backend,
        max_revision_attempts=2,
    )

    assert job.status is JobStatus.READY_FOR_PR
    assert job.attempt == 1
    assert backend.revise_calls == 1


def test_editorial_block_exhausts_revision_budget():
    job = generate_validated_article(
        "Agent sandboxes",
        BlockingBackend(),
        max_revision_attempts=1,
    )

    assert job.status is JobStatus.BLOCKED
    assert job.attempt == 1
