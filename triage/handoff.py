"""BTL hand-off pack formatter.

Produces a GitHub-flavored Markdown document that presents a triage result
as an actionable brief for the Business Technology Lead (BTL): the one-line
verdict, the classification decision, required consultations, open questions,
delivery path, and the audit-trail note. Renders natively in the GitHub
file viewer — no local tooling required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_INTAKE_STATUS_LABEL = {
    "complete_for_triage": "Complete for triage",
    "incomplete_for_triage": "Incomplete for triage (provisional)",
    "clarification_required": "Clarification required",
}

_ACTION_LABEL = {
    "proceed_to_receiving_queue": "Proceed to receiving queue",
    "proceed_to_shaping_lane": "Proceed to shaping lane",
    "hold_for_clarification": "Hold for clarification",
    "escalate_routing_dispute": "Escalate — routing dispute",
    "escalate_materiality_overlay_review": (
        "Escalate — materiality / overlay review"
    ),
    "exception_memo_required": "Exception memo required",
    "retroactive_fast_track_regularization": (
        "Retroactive fast-track regularization"
    ),
}

_PROGRAM_LABEL = {
    "stand_alone": "Stand-alone project",
    "under_existing_program": "Project under an existing program",
    "recommend_program": "Recommend program umbrella",
    "not_applicable": "Not applicable",
}


def _yesno(value: bool) -> str:
    return "**Yes**" if value else "No"


def _bullets(items: list[str]) -> str:
    if not items:
        return "_(none)_"
    return "\n".join(f"- {item}" for item in items)


def _verdict_line(t: dict[str, Any]) -> str:
    intake = t["demand_intake_status"]
    if intake == "clarification_required":
        return (
            "**Hold for clarification.** Minimum completeness is not met — "
            "the demand cannot be triaged safely until the missing fields "
            "below are supplied."
        )

    run = t["run_type"]["type"]
    sub = t["subtype"]["type"]
    family = t["service_family_routing"]["primary_family"]
    tier = t["materiality"]["tier"]
    action = _ACTION_LABEL.get(
        t["g1_triage_recommendation"]["action"],
        t["g1_triage_recommendation"]["action"],
    )

    triggered = [
        o["overlay"] for o in t["overlay_triggers"] if o["triggered"]
    ]
    if triggered:
        overlay_clause = (
            f"{len(triggered)} overlay "
            f"{'consultation' if len(triggered) == 1 else 'consultations'} "
            f"required ({', '.join(triggered)})."
        )
    else:
        overlay_clause = "No overlay consultations triggered."

    return (
        f"**{action}** as **{run} / {sub}** routed to **{family}**. "
        f"Materiality **{tier}**. {overlay_clause}"
    )


def _classification_table(t: dict[str, Any]) -> str:
    sfr = t["service_family_routing"]
    family_cell = sfr["primary_family"]
    if sfr["specific_subfamily"] and sfr["specific_subfamily"] != "not specified":
        family_cell = f"{family_cell} — {sfr['specific_subfamily']}"

    program = t["program_affiliation"]
    program_label = _PROGRAM_LABEL.get(program["type"], program["type"])

    rows: list[tuple[str, str, str]] = [
        ("Service family", family_cell, sfr["rationale"]),
        ("Run type", t["run_type"]["type"], t["run_type"]["rationale"]),
        ("Subtype", t["subtype"]["type"], t["subtype"]["rationale"]),
        ("Program affiliation", program_label, program["rationale"]),
        (
            "Materiality",
            t["materiality"]["tier"],
            t["materiality"]["rationale"],
        ),
    ]

    lines = [
        "| Decision | Value | Rationale |",
        "|---|---|---|",
    ]
    for label, value, rationale in rows:
        lines.append(
            f"| {label} | **{value}** | {_escape_cell(rationale)} |"
        )
    return "\n".join(lines)


def _overlay_table(overlays: list[dict[str, Any]]) -> str:
    lines = [
        "| Overlay | Status | Consultation | Rationale |",
        "|---|---|---|---|",
    ]
    # Sort mandatory first, then by_exception, then not_needed / not triggered
    order = {"mandatory": 0, "by_exception": 1, "not_needed": 2}
    for ov in sorted(
        overlays,
        key=lambda o: (order.get(o["consultation_type"], 3), o["overlay"]),
    ):
        status = ":warning: **Triggered**" if ov["triggered"] else "Not triggered"
        consult = ov["consultation_type"].replace("_", " ")
        if ov["consultation_type"] == "mandatory":
            consult = f"**{consult}**"
        lines.append(
            f"| {ov['overlay']} | {status} | {consult} | "
            f"{_escape_cell(ov['rationale'])} |"
        )
    return "\n".join(lines)


def _escape_cell(text: str) -> str:
    # Keep it single-line and pipe-safe for the markdown table cell.
    return text.replace("|", "\\|").replace("\n", " ")


def format_handoff_pack(
    triage: dict[str, Any],
    source_name: str,
    json_sibling: str | None = None,
) -> str:
    """Render a triage result as a BTL hand-off pack in Markdown.

    `source_name` is the original demand filename (e.g. ``demand.pdf``) —
    surfaced in the header so the BTL can trace the record.

    `json_sibling` is the filename of the accompanying JSON record in the
    same folder, e.g. ``demand.json``. Omit for stdout-only output.
    """
    t = triage
    ce = t["confidence_and_escalation"]
    ca = t["completeness_assessment"]
    eb = t["effort_and_cost_bands"]
    pdp = t["provisional_delivery_path"]
    nof = t["recommended_next_owner_forum"]
    g1 = t["g1_triage_recommendation"]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    intake_label = _INTAKE_STATUS_LABEL.get(
        t["demand_intake_status"], t["demand_intake_status"]
    )
    action_label = _ACTION_LABEL.get(g1["action"], g1["action"])

    sections: list[str] = []

    # Header
    sections.append(f"# BTL Hand-Off Pack")
    sections.append(f"**Source file:** `{source_name}`")
    sections.append(
        f"**Generated (UTC):** {now_iso}  |  **Intake status:** "
        f"{intake_label}"
    )
    sections.append(
        f"**Overall confidence:** {ce['overall_confidence']}  |  "
        f"**Human review mandatory:** {_yesno(ce['human_review_mandatory'])}"
    )

    # Verdict callout
    sections.append("---")
    sections.append("## :dart: G1 verdict")
    sections.append(f"> {_verdict_line(t)}")
    sections.append(f"> ")
    sections.append(f"> **Recommended action:** **{action_label}**.")
    sections.append(f"> ")
    sections.append(f"> {g1['rationale']}")

    # 1. Demand intake & completeness
    sections.append("## 1. Demand intake & completeness")
    sections.append("**Mandatory fields present**")
    sections.append(_bullets(ca["mandatory_fields_present"]))
    sections.append("")
    sections.append("**Missing fields**")
    sections.append(_bullets(ca["missing_fields"]))
    sections.append("")
    sections.append("**Assumptions used by the triage agent**")
    sections.append(_bullets(ca["assumptions_used"]))
    sections.append("")
    sections.append(
        f"**Can continue safely at G1:** {_yesno(ca['can_continue_safely'])}"
    )

    # 2. Classification
    sections.append("## 2. Classification decision")
    sections.append(_classification_table(t))
    sfr = t["service_family_routing"]
    if sfr["secondary_families"] or sfr["routing_ambiguity"]:
        sections.append("")
        if sfr["secondary_families"]:
            sections.append(
                "**Secondary families / dependencies:** "
                + ", ".join(sfr["secondary_families"])
            )
        if sfr["routing_ambiguity"]:
            sections.append(
                ":warning: **Routing ambiguity flagged** — a triage huddle is "
                "recommended before handoff."
            )
    sub = t["subtype"]
    if sub["disqualifiers_or_escalators"]:
        sections.append("")
        sections.append("**Hard disqualifiers / escalators found**")
        sections.append(_bullets(sub["disqualifiers_or_escalators"]))

    # 3. Consultations
    sections.append("## 3. Required consultations (overlays)")
    sections.append(_overlay_table(t["overlay_triggers"]))

    # 4. Resourcing
    sections.append("## 4. Resourcing signal")
    sections.append(
        f"- **Effort band:** `{eb['effort_band']}`"
    )
    sections.append(f"- **Cost band:** `{eb['cost_band']}`")
    sections.append(f"- **Estimate basis:** {eb['estimate_basis']}")
    sections.append(f"- **Estimate confidence:** {eb['confidence_level']}")
    if eb["quick_estimate_huddle_needed"]:
        sections.append(
            "- :warning: **Quick-estimate huddle recommended** before handoff "
            "(both bands currently unknown)."
        )

    # 5. Delivery path
    sections.append("## 5. Provisional delivery path")
    sections.append(f"**Path:** **{pdp['path']}** _(provisional at G1)_  ")
    sections.append(pdp["rationale"])

    # 6. Next owner / forum
    sections.append("## 6. Recommended next owner / forum")
    sections.append(f"**Owner / forum:** {nof['owner_or_forum']}  ")
    sections.append(nof["rationale"])

    # 7. Open questions
    sections.append("## 7. Open questions & escalation items")
    sections.append("**Uncertainty drivers**")
    sections.append(_bullets(ce["uncertainty_drivers"]))
    sections.append("")
    sections.append("**Escalation items**")
    sections.append(_bullets(ce["escalation_items"]))

    # 8. Triage note
    sections.append("## 8. Triage note (audit trail)")
    for paragraph in t["triage_note_draft"].strip().split("\n"):
        sections.append(paragraph)

    # Footer
    sections.append("---")
    if json_sibling:
        sections.append(
            f"**Machine-readable record:** see `{json_sibling}` in this "
            "folder for the full structured JSON (same 14 sections)."
        )
    sections.append(
        "*Generated by the BPI Demand Triage Agent — "
        "Claude Opus 4.7, adaptive thinking, effort=high.*"
    )
    sections.append(
        "*This is a G1 triage recommendation. Work is not \"started\" at G1; "
        "delivery path and subtype may be refined after shaping.*"
    )

    return "\n\n".join(sections) + "\n"
