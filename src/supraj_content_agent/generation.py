"""Model-backed research, writing, review, and revision capabilities.

The OpenAI Agents SDK is intentionally contained in this module. The rest of the
application depends on the ContentGenerationBackend protocol, which keeps tests
offline and prevents an agent implementation from owning publication state.
"""

from __future__ import annotations

import json
from typing import Protocol

from .models import ArticleDraft, EditorialReview, ResearchPacket


class ContentGenerationBackend(Protocol):
    def research(self, topic: str) -> ResearchPacket: ...

    def write(self, research: ResearchPacket) -> ArticleDraft: ...

    def review(self, research: ResearchPacket, draft: ArticleDraft) -> EditorialReview: ...

    def revise(
        self,
        research: ResearchPacket,
        draft: ArticleDraft,
        review: EditorialReview,
    ) -> ArticleDraft: ...


class OpenAIAgentsBackend:
    """OpenAI Agents SDK implementation.

    Research is the only stage with web-search capability. Writing, review, and
    revision are grounded in the typed research packet and cannot independently
    browse for unsupported facts.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model

    def _agent(self, **kwargs):
        from agents import Agent

        if self.model:
            kwargs["model"] = self.model
        return Agent(**kwargs)

    def research(self, topic: str) -> ResearchPacket:
        from agents import Runner, WebSearchTool

        agent = self._agent(
            name="Supraj.dev Researcher",
            instructions=(
                "Research one technical topic for a senior Cloud/DevOps/AI engineering audience. "
                "Use web search. Prefer official documentation, standards, source repositories, "
                "or primary engineering material. Preserve exact source URLs. Separate facts from "
                "interpretation. Flag uncertainty and version sensitivity. Do not invent personal "
                "experience, benchmarks, incidents, clients, or test results. Return only the "
                "structured research packet requested by the output schema."
            ),
            tools=[WebSearchTool()],
            output_type=ResearchPacket,
        )
        result = Runner.run_sync(agent, topic, max_turns=8)
        output = result.final_output
        if not isinstance(output, ResearchPacket):
            raise TypeError("Research agent returned an unexpected output type.")
        return output

    def write(self, research: ResearchPacket) -> ArticleDraft:
        from agents import Runner

        prompt = (
            "Write a practical, technically deep supraj.dev article from this approved research "
            "packet. Explain concepts clearly with concrete examples and trade-offs. Do not claim "
            "the author personally deployed, measured, or observed anything unless it appears in "
            "the packet. Do not add factual claims that are unsupported by the packet. Copy the "
            "packet's source records into the article sources. Markdown body should be useful as "
            "a standalone article and use meaningful H2 sections.\n\nRESEARCH PACKET:\n"
            + research.model_dump_json(indent=2)
        )
        agent = self._agent(
            name="Supraj.dev Technical Writer",
            instructions=(
                "Turn an approved research packet into an accurate technical article. "
                "Be explanatory rather than promotional. Never fabricate first-person experience."
            ),
            output_type=ArticleDraft,
        )
        result = Runner.run_sync(agent, prompt, max_turns=5)
        output = result.final_output
        if not isinstance(output, ArticleDraft):
            raise TypeError("Writer agent returned an unexpected output type.")
        return output

    def review(self, research: ResearchPacket, draft: ArticleDraft) -> EditorialReview:
        from agents import Runner

        prompt = (
            "Review this draft strictly against the approved research packet. Mark blocking issues "
            "for unsupported factual claims, contradictions, invented experience/results, weak "
            "technical explanation, missing caveats that change meaning, or source mismatch. "
            "Do not block purely for personal style preferences.\n\nRESEARCH:\n"
            + research.model_dump_json(indent=2)
            + "\n\nDRAFT:\n"
            + draft.model_dump_json(indent=2)
        )
        agent = self._agent(
            name="Supraj.dev Technical Reviewer",
            instructions=(
                "Act as an evidence-focused technical editor. Review only; do not publish."
            ),
            output_type=EditorialReview,
        )
        result = Runner.run_sync(agent, prompt, max_turns=4)
        output = result.final_output
        if not isinstance(output, EditorialReview):
            raise TypeError("Reviewer agent returned an unexpected output type.")
        return output

    def revise(
        self,
        research: ResearchPacket,
        draft: ArticleDraft,
        review: EditorialReview,
    ) -> ArticleDraft:
        from agents import Runner

        prompt = (
            "Revise the draft to resolve every blocking finding while staying inside the evidence "
            "in the research packet. Preserve valid material. Do not invent new facts, sources, "
            "personal experience, benchmarks, or test results.\n\nRESEARCH:\n"
            + research.model_dump_json(indent=2)
            + "\n\nCURRENT DRAFT:\n"
            + draft.model_dump_json(indent=2)
            + "\n\nREVIEW:\n"
            + review.model_dump_json(indent=2)
        )
        agent = self._agent(
            name="Supraj.dev Revision Writer",
            instructions=(
                "Repair a technical article using only the supplied evidence and review findings."
            ),
            output_type=ArticleDraft,
        )
        result = Runner.run_sync(agent, prompt, max_turns=5)
        output = result.final_output
        if not isinstance(output, ArticleDraft):
            raise TypeError("Revision agent returned an unexpected output type.")
        return output


def research_packet_json(packet: ResearchPacket) -> str:
    """Stable pretty JSON for diagnostics and future durable storage."""

    return json.dumps(packet.model_dump(mode="json"), indent=2, sort_keys=True)
