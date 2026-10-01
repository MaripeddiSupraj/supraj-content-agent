# Phase 1 architecture

The system is a governed workflow with bounded agent autonomy.

## Deterministic control plane

The workflow owns job state, retry limits, validation gates, target repository paths,
and publication transitions. Agent output cannot directly mark a job as published.

## Agent plane

Phase 1 will add two model-backed capabilities:

1. **Researcher** — uses live web search, prefers primary/official sources, and returns
   structured source records plus research notes.
2. **Writer** — consumes the approved research packet and produces a typed article draft.

A separate review pass may propose revisions, but the deterministic validator decides
whether the draft is eligible for a website pull request.

## Website delivery

The target repository is `MaripeddiSupraj/SuprajWebsite`. The publisher will create
`src/content/blog/<slug>.mdx` on a dedicated branch and open a PR. Website CI and
deployment remain the final release authority.

## Safety and reliability properties

- no direct model-to-main writes
- no publish on failed validation
- explicit source records
- bounded revision attempts
- idempotent article identity/slug
- resumable durable job state
- secrets supplied only at runtime
- LinkedIn automation isolated to a later phase
