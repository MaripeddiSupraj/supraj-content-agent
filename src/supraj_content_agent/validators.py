"""Deterministic publication gates.

These checks deliberately do not ask an LLM whether an article is "good".
They enforce machine-checkable requirements before a draft can enter the
website pull-request stage.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlparse

from .models import ArticleDraft, ValidationFinding, ValidationReport

ALLOWED_SOURCE_SCHEMES = {"https"}
MIN_DISTINCT_SOURCE_HOSTS = 2


def validate_article(
    draft: ArticleDraft,
    approved_source_urls: Iterable[str] | None = None,
) -> ValidationReport:
    findings: list[ValidationFinding] = []

    if len(draft.body_markdown.split()) < 300:
        findings.append(
            ValidationFinding(
                code="article.too_short",
                message="Article must contain at least 300 words before publication.",
            )
        )

    if not re.search(r"^##\s+.+", draft.body_markdown, flags=re.MULTILINE):
        findings.append(
            ValidationFinding(
                code="article.no_sections",
                message="Article must contain at least one H2 section.",
            )
        )

    hosts: set[str] = set()
    draft_urls: set[str] = set()
    for source in draft.sources:
        source_url = str(source.url)
        draft_urls.add(source_url)
        parsed = urlparse(source_url)
        if parsed.scheme not in ALLOWED_SOURCE_SCHEMES:
            findings.append(
                ValidationFinding(
                    code="source.insecure_url",
                    message=f"Source must use HTTPS: {source.url}",
                )
            )
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())

    if len(hosts) < MIN_DISTINCT_SOURCE_HOSTS:
        findings.append(
            ValidationFinding(
                code="source.low_diversity",
                message=(
                    "Use at least two distinct source hosts so one publication "
                    "does not become the sole factual basis for the article."
                ),
            )
        )

    if approved_source_urls is not None:
        approved = {str(url) for url in approved_source_urls}
        unapproved = sorted(draft_urls - approved)
        if unapproved:
            findings.append(
                ValidationFinding(
                    code="source.not_in_research",
                    message=(
                        "Draft contains sources that were not approved by research: "
                        + ", ".join(unapproved)
                    ),
                )
            )

    if "TODO" in draft.body_markdown.upper():
        findings.append(
            ValidationFinding(
                code="article.todo_marker",
                message="Draft still contains a TODO marker.",
            )
        )

    return ValidationReport(findings=findings)


def render_supraj_website_mdx(draft: ArticleDraft, pub_date: str) -> str:
    """Render frontmatter compatible with SuprajWebsite/src/content.config.ts."""

    quoted_tags = ", ".join(f'"{tag}"' for tag in draft.tags)
    hero = f'heroEmoji: "{draft.hero_emoji}"\n' if draft.hero_emoji else ""
    reading = f'readingTime: "{draft.reading_time}"\n' if draft.reading_time else ""

    return (
        "---\n"
        f'title: "{draft.title.replace(chr(34), chr(92) + chr(34))}"\n'
        f'description: "{draft.description.replace(chr(34), chr(92) + chr(34))}"\n'
        f"pubDate: {pub_date}\n"
        f"tags: [{quoted_tags}]\n"
        f"{hero}"
        "featured: false\n"
        "draft: false\n"
        f"{reading}"
        "---\n\n"
        f"{draft.body_markdown.rstrip()}\n"
    )
