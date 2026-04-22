"""Triage agent — wraps the Claude API call and returns parsed JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic

from triage.loader import load_demand
from triage.schema import TRIAGE_SCHEMA
from triage.system_prompt import SYSTEM_PROMPT

MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000

_TEXT_INSTRUCTION = (
    "Screen the following demand using the BPI Demand Screening and Triage "
    "Manual sequence. Return the structured triage recommendation as JSON.\n\n"
    "DEMAND:\n"
)

_DOC_INSTRUCTION = (
    "Screen the attached demand document using the BPI Demand Screening and "
    "Triage Manual sequence. The document contains the full demand brief — "
    "read it in full (including any scanned pages, tables, diagrams, or "
    "signatures) before classifying. Return the structured triage "
    "recommendation as JSON."
)


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
        """Screen a demand supplied as plain text."""
        if not demand_text or not demand_text.strip():
            raise ValueError("demand_text must be non-empty")
        return self._run(_TEXT_INSTRUCTION + demand_text)

    def triage_file(self, path: Path | str) -> TriageResult:
        """Screen a demand from a file (.txt, .md, .docx, or .pdf).

        Text-based formats are read as UTF-8 or extracted to text. PDFs are
        sent to Claude as a native document block, so scanned pages, tables,
        and diagrams are understood — not just embedded text.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        loaded = load_demand(path)
        if isinstance(loaded, str):
            return self.triage(loaded)
        # loaded is a list of Claude content blocks (PDF case). Append the
        # instruction as a text block so the model knows what to do with
        # the attachment.
        return self._run([*loaded, {"type": "text", "text": _DOC_INSTRUCTION}])

    def _run(
        self, user_content: str | list[dict[str, Any]]
    ) -> TriageResult:
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
            messages=[{"role": "user", "content": user_content}],
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
