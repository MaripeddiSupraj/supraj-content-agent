# Supraj Content Agent

Automation for publishing high-quality technical content to [supraj.dev](https://supraj.dev).

## Phase 1 goal

Prove one safe, repeatable path:

```text
Topic
  -> research
  -> draft
  -> validate
  -> render SuprajWebsite-compatible MDX
  -> create a website pull request
  -> run website CI
  -> publish only after the normal repository/deployment gates pass
```

LinkedIn computer-use automation and recurring scheduling are intentionally **not** part of Phase 1. They are added only after the website publishing path is reliable.

## Design rules

- The workflow owns state and gates; agents cannot skip publication checks.
- Research must preserve source URLs and distinguish sourced facts from author explanation.
- A failed gate produces a blocked job, never a "publish anyway" result.
- Website publication is idempotent: a retry must not duplicate an already-created article/PR.
- Secrets never belong in the repository.
- The target website is `MaripeddiSupraj/SuprajWebsite`.
- Generated blog files must conform to that site's Astro content collection schema.

## Development

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are recommended.

```bash
uv sync --dev
uv run pytest
uv run supraj-content-agent validate-example
```

## Current repository layout

```text
src/supraj_content_agent/
  config.py       Environment-backed application configuration
  models.py       Durable job/article/source contracts
  validators.py   Deterministic publication gates
  workflow.py     Explicit Phase-1 state machine
tests/
  test_validators.py
```

The next implementation slice adds the research/writer agents and GitHub publisher behind these contracts.
