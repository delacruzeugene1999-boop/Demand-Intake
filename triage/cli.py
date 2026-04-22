"""CLI for the BPI demand-triage agent.

Usage:
    python -m triage <path/to/demand.{txt,md,docx,pdf}>
    python -m triage -            # read plain text from stdin
    cat demand.txt | python -m triage -

Flags:
    --json       emit raw JSON instead of the formatted report
    --outdir DIR write both formatted + JSON outputs to DIR
    --usage      print token usage to stderr
    --model      override the Claude model id
    --effort     override the effort level (low|medium|high|xhigh|max)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anthropic

from triage.agent import MODEL, TriageAgent, TriageResult
from triage.loader import SUPPORTED_EXTENSIONS


def _format_report(t: dict[str, Any]) -> str:
    lines: list[str] = []

    def section(title: str) -> None:
        lines.append("")
        lines.append(title)
        lines.append("-" * len(title))

    def kv(label: str, value: Any) -> None:
        lines.append(f"  {label}: {value}")

    def bullets(label: str, items: list[Any]) -> None:
        if not items:
            lines.append(f"  {label}: (none)")
            return
        lines.append(f"  {label}:")
        for item in items:
            lines.append(f"    - {item}")

    lines.append("=" * 72)
    lines.append("BPI DEMAND TRIAGE — G1 RECOMMENDATION")
    lines.append("=" * 72)

    section("1. Demand intake status")
    kv("status", t["demand_intake_status"])

    section("2. Completeness assessment")
    ca = t["completeness_assessment"]
    bullets("mandatory_fields_present", ca["mandatory_fields_present"])
    bullets("missing_fields", ca["missing_fields"])
    bullets("assumptions_used", ca["assumptions_used"])
    kv("can_continue_safely", ca["can_continue_safely"])

    section("3. Service-family routing")
    sfr = t["service_family_routing"]
    kv("primary_family", sfr["primary_family"])
    kv("specific_subfamily", sfr["specific_subfamily"])
    kv("rationale", sfr["rationale"])
    bullets("secondary_families", sfr["secondary_families"])
    kv("routing_ambiguity", sfr["routing_ambiguity"])

    section("4. Run type")
    kv("type", t["run_type"]["type"])
    kv("rationale", t["run_type"]["rationale"])

    section("5. Subtype")
    st = t["subtype"]
    kv("type", st["type"])
    kv("rationale", st["rationale"])
    bullets("disqualifiers_or_escalators", st["disqualifiers_or_escalators"])

    section("6. Program affiliation")
    kv("type", t["program_affiliation"]["type"])
    kv("rationale", t["program_affiliation"]["rationale"])

    section("7. Materiality")
    kv("tier", t["materiality"]["tier"])
    kv("rationale", t["materiality"]["rationale"])

    section("8. Overlay triggers")
    for ov in t["overlay_triggers"]:
        flag = "TRIGGERED" if ov["triggered"] else "not triggered"
        lines.append(f"  - {ov['overlay']}: {flag}")
        lines.append(f"      consultation: {ov['consultation_type']}")
        lines.append(f"      rationale: {ov['rationale']}")

    section("9. Effort & cost bands")
    eb = t["effort_and_cost_bands"]
    kv("effort_band", eb["effort_band"])
    kv("cost_band", eb["cost_band"])
    kv("estimate_basis", eb["estimate_basis"])
    kv("confidence_level", eb["confidence_level"])
    kv("quick_estimate_huddle_needed", eb["quick_estimate_huddle_needed"])

    section("10. Provisional delivery path")
    kv("path", t["provisional_delivery_path"]["path"])
    kv("rationale", t["provisional_delivery_path"]["rationale"])

    section("11. Recommended next owner / forum")
    kv("owner_or_forum", t["recommended_next_owner_forum"]["owner_or_forum"])
    kv("rationale", t["recommended_next_owner_forum"]["rationale"])

    section("12. G1 triage recommendation")
    kv("action", t["g1_triage_recommendation"]["action"])
    kv("rationale", t["g1_triage_recommendation"]["rationale"])

    section("13. Triage note draft")
    lines.append("")
    for paragraph in t["triage_note_draft"].split("\n"):
        lines.append(f"  {paragraph}")

    section("14. Confidence & escalation")
    ce = t["confidence_and_escalation"]
    kv("overall_confidence", ce["overall_confidence"])
    bullets("uncertainty_drivers", ce["uncertainty_drivers"])
    kv("human_review_mandatory", ce["human_review_mandatory"])
    bullets("escalation_items", ce["escalation_items"])

    lines.append("")
    return "\n".join(lines)


def _print_usage(result: TriageResult) -> None:
    u = result.usage
    print(
        "[usage] input={input_tokens} output={output_tokens} "
        "cache_read={cache_read_input_tokens} "
        "cache_write={cache_creation_input_tokens}".format(**u),
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="triage",
        description="BPI demand-triage screener (front-door G1 copilot).",
    )
    parser.add_argument(
        "demand",
        help=(
            "Path to a demand file (.txt, .md, .docx, .pdf), or '-' to read "
            "plain text from stdin."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON instead of the formatted report.",
    )
    parser.add_argument(
        "--usage",
        action="store_true",
        help="Print token usage to stderr.",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Claude model id (default: {MODEL}).",
    )
    parser.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="Effort level (default: high).",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help=(
            "Write both the formatted report and raw JSON to this directory "
            "(one API call). Uses the input filename stem."
        ),
    )
    args = parser.parse_args(argv)

    agent = TriageAgent(model=args.model, effort=args.effort)

    try:
        if args.demand == "-":
            demand_text = sys.stdin.read()
            if not demand_text.strip():
                print("error: demand is empty", file=sys.stderr)
                return 2
            result = agent.triage(demand_text)
        else:
            path = Path(args.demand)
            if not path.exists():
                print(
                    f"error: demand file not found: {args.demand}",
                    file=sys.stderr,
                )
                return 2
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                print(
                    f"error: unsupported file type {path.suffix!r}. "
                    f"Supported: {sorted(SUPPORTED_EXTENSIONS)}",
                    file=sys.stderr,
                )
                return 2
            result = agent.triage_file(path)
    except anthropic.AuthenticationError:
        print(
            "error: ANTHROPIC_API_KEY missing or invalid. "
            "Set it in your environment or .env file.",
            file=sys.stderr,
        )
        return 2
    except anthropic.APIError as exc:
        print(f"error: Claude API call failed: {exc}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.outdir:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = (
            Path(args.demand).stem
            if args.demand != "-"
            else "stdin"
        )
        report_path = outdir / f"{stem}.report.txt"
        json_path = outdir / f"{stem}.json"
        report_path.write_text(_format_report(result.triage), encoding="utf-8")
        json_path.write_text(
            json.dumps(result.triage, indent=2), encoding="utf-8"
        )
        print(f"wrote {report_path}")
        print(f"wrote {json_path}")
    elif args.json:
        print(json.dumps(result.triage, indent=2))
    else:
        print(_format_report(result.triage))

    if args.usage:
        _print_usage(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
