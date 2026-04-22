"""Triage agent — wraps the Claude API call and returns parsed JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anthropic

from triage.schema import TRIAGE_SCHEMA
from triage.system_prompt import SYSTEM_PROMPT

MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000


@dataclass
class TriageResult:
    """A single triage screening result."""

    triage: dict[str, Any]
    raw_response: anthropic.types.Message

    @property
    def usage(self) -> dict[str, int | None]:
        u = self.raw_response.usage
        return {
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cache_creation_input_tokens": getattr(
                u, "cache_creation_input_tokens", None
            ),
            "cache_read_input_tokens": getattr(
                u, "cache_read_input_tokens", None
            ),
        }


class TriageAgent:
    """Front-door BPI demand-triage screener.

    The system prompt embedding the BPI manual is cached on the first call;
    subsequent calls within the cache TTL pay only for the per-demand input.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = MODEL,
        effort: str = "high",
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.effort = effort

    def triage(self, demand_text: str) -> TriageResult:
        """Screen one demand and return the parsed triage recommendation.

        `demand_text` may be free-form prose, a structured form, or a paste
        from the intake system. The agent will identify gaps via Step 2.
        """
        if not demand_text or not demand_text.strip():
            raise ValueError("demand_text must be non-empty")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={
                "effort": self.effort,
                "format": {
                    "type": "json_schema",
                    "schema": TRIAGE_SCHEMA,
                },
            },
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Screen the following demand using the BPI Demand "
                        "Screening and Triage Manual sequence. Return the "
                        "structured triage recommendation as JSON.\n\n"
                        "DEMAND:\n"
                        f"{demand_text}"
                    ),
                }
            ],
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        if not text_blocks:
            raise RuntimeError(
                f"Model returned no text block. stop_reason="
                f"{response.stop_reason!r}"
            )

        try:
            triage = json.loads(text_blocks[0])
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Model output was not valid JSON: {exc}\n"
                f"Raw output: {text_blocks[0][:500]}"
            ) from exc

        return TriageResult(triage=triage, raw_response=response)
