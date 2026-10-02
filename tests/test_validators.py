from supraj_content_agent.models import ArticleDraft, Source
from supraj_content_agent.validators import render_supraj_website_mdx, validate_article


def make_draft(**overrides):
    data = {
        "title": "A Practical Article About Reliable Content Automation",
        "description": (
            "A detailed practical article showing how validation protects an "
            "automated technical publishing workflow."
        ),
        "slug": "reliable-content-automation",
        "body_markdown": "## Architecture\n\n" + ("Useful technical explanation. " * 320),
        "tags": ["Automation", "AI Agents"],
        "sources": [
            Source(title="Astro docs", publisher="Astro", url="https://docs.astro.build/"),
            Source(title="Python docs", publisher="Python", url="https://docs.python.org/3/"),
        ],
    }
    data.update(overrides)
    return ArticleDraft(**data)


def test_valid_article_passes():
    assert validate_article(make_draft()).passed


def test_single_source_host_is_blocking():
    draft = make_draft(
        sources=[
            Source(title="Astro one", publisher="Astro", url="https://docs.astro.build/a"),
            Source(title="Astro two", publisher="Astro", url="https://docs.astro.build/b"),
        ]
    )
    report = validate_article(draft)

    assert not report.passed
    assert "source.low_diversity" in {finding.code for finding in report.findings}


def test_todo_marker_is_blocking():
    draft = make_draft(body_markdown="## Architecture\n\n" + ("text " * 310) + "TODO")
    report = validate_article(draft)

    assert not report.passed
    assert "article.todo_marker" in {finding.code for finding in report.findings}


def test_renderer_matches_supraj_website_frontmatter():
    output = render_supraj_website_mdx(make_draft(hero_emoji="⚙️"), "2026-10-01")

    assert 'title: "A Practical Article About Reliable Content Automation"' in output
    assert "pubDate: 2026-10-01" in output
    assert 'tags: ["Automation", "AI Agents"]' in output
    assert 'heroEmoji: "⚙️"' in output
    assert "draft: false" in output


def test_source_not_approved_by_research_is_blocking():
    draft = make_draft(
        sources=[
            Source(title="Astro docs", publisher="Astro", url="https://docs.astro.build/"),
            Source(title="Unknown docs", publisher="Unknown", url="https://example.com/docs"),
        ]
    )
    report = validate_article(
        draft,
        approved_source_urls=[
            "https://docs.astro.build/",
            "https://docs.python.org/3/",
        ],
    )

    assert not report.passed
    assert "source.not_in_research" in {finding.code for finding in report.findings}
