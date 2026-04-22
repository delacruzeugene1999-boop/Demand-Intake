# BPI Demand Triage Agent

Front-door demand-triage copilot that screens incoming technology demand
strictly per the **BPI Demand Screening and Triage Manual**. Built on the
Anthropic Claude API (Opus 4.7 + adaptive thinking + structured outputs).

## What it does

Feed it a demand (free-form text, email paste, or structured form) and it
returns a 14-section G1 triage recommendation:

1. Demand intake status
2. Completeness assessment
3. Service-family routing (DCG / ISG-Apps / ISG-Infra / CEDA)
4. Run type (Run / Grow / Innovate)
5. Subtype (BAU / MR / Project / PoC / Pilot)
6. Program affiliation (only if Project)
7. Materiality tier (Tier 1 / 2 / 3)
8. Overlay triggers (Architecture, Cyber, Data/Privacy, Reg, AI/Model, Vendor, PMO)
9. Effort and cost bands (E0–E5 / C0–C5)
10. Provisional delivery path (Agile / Waterfall / Infra Build / Innovation)
11. Recommended next owner / forum
12. G1 triage recommendation
13. Triage note draft (5–8 sentences, audit-friendly)
14. Confidence and escalation flags

## Run it in GitHub (no local setup needed)

If you just want to feed demands in and read outputs out, use the
GitHub flow:

1. **One-time: set the API key secret.** In the repo on GitHub, go to
   **Settings → Secrets and variables → Actions → New repository
   secret**, name it `ANTHROPIC_API_KEY`, paste your key.
2. **Upload a demand.** Commit a file to `inbox/` (any `.txt` or
   `.md`). You can do this from the GitHub web UI: click **Add file
   → Create new file**, put it under `inbox/your-name.txt`, commit.
3. **Wait ~15–30 seconds.** The **Triage Demand** workflow runs
   automatically (watch it in the **Actions** tab).
4. **Read the output.** Pull or refresh — two files appear in
   `outbox/`:
   - `outbox/your-name.report.txt` — formatted 14-section report
   - `outbox/your-name.json` — machine-readable JSON
5. **Re-run on demand.** Open **Actions → Triage Demand → Run
   workflow** for a manual trigger. You can pass a specific file path
   or tick **force** to reprocess everything.

The workflow skips files whose outputs are already up-to-date, so
pushing a batch of ten demands only costs ten API calls (not twenty).

## Run it locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Use as a CLI

```bash
# From a file
python -m triage examples/demand_complete_project.txt

# From stdin
cat examples/demand_innovate_poc.txt | python -m triage -

# Raw JSON output
python -m triage examples/demand_run_bau.txt --json

# Show token usage on stderr
python -m triage examples/demand_run_bau.txt --usage
```

Flags:

| Flag | Default | Notes |
|------|---------|-------|
| `--json` | off | Emit raw JSON instead of the formatted report |
| `--outdir DIR` | — | Write both `<stem>.report.txt` and `<stem>.json` to `DIR` from one API call |
| `--usage` | off | Print token usage to stderr |
| `--model` | `claude-opus-4-7` | Override the Claude model id |
| `--effort` | `high` | One of `low`, `medium`, `high`, `xhigh`, `max` |

## Use as a library

```python
from triage import TriageAgent

agent = TriageAgent()
result = agent.triage(demand_text)

print(result.triage["g1_triage_recommendation"])
print(result.triage["triage_note_draft"])
print(result.usage)
```

`result.triage` is a Python dict that conforms exactly to the schema in
`triage/schema.py`. `result.raw_response` is the full Anthropic
`Message` object if you need finer-grained access (stop reason, content
blocks, etc.).

## How it works

- **Cached system prompt.** The full BPI manual (`triage/system_prompt.py`)
  is sent as a cacheable system block. Repeated triage calls within the
  cache TTL pay only for the per-demand input, not the manual.
- **Structured output.** The model is constrained to emit JSON matching
  `TRIAGE_SCHEMA` via `output_config.format` — no parsing brittleness,
  no markdown fences.
- **Adaptive thinking + high effort.** Triage decisions are layered
  (intent → materiality → thresholds), so adaptive thinking lets Opus
  4.7 reason proportionally to the demand's complexity.
- **No improvisation.** The system prompt explicitly forbids generic
  PMO logic and pins every step to the manual. When evidence is
  insufficient, the agent lowers confidence and recommends clarification
  instead of fabricating a verdict.

## Examples

The `examples/` folder ships four reference demands covering the main
classification outcomes:

| File | Expected outcome |
|------|------------------|
| `demand_complete_project.txt` | Grow / Project, Tier 3, multiple overlays |
| `demand_innovate_poc.txt` | Innovate / PoC, Innovation path |
| `demand_run_bau.txt` | Run / BAU, Tier 1, no overlay triggers |
| `demand_incomplete_clarify.txt` | Clarification required |

## Project layout

```
triage/
  __init__.py        # public exports
  __main__.py        # `python -m triage` entry point
  agent.py           # TriageAgent class + TriageResult dataclass
  cli.py             # argparse CLI + report formatter
  schema.py          # JSON schema for the 14-section output
  system_prompt.py   # BPI Demand Screening and Triage Manual (frozen)
.github/workflows/
  triage.yml         # runs the agent on inbox/, writes to outbox/
inbox/               # drop demand files here
outbox/              # triage outputs land here (auto-committed)
examples/            # reference demands
requirements.txt
```

## Operating principles encoded in the agent

- Service family tells *where* the work belongs.
- Run type tells *how much governance* it needs.
- Subtype tells *which operating route* applies within that governance level.
- Program affiliation is assessed **only after** Project is identified.
- Delivery path is **provisional at G1** and confirmed later.
- Overlays are **additive** — they may force stronger governance or
  reclassification but do not replace sponsor or service-owner accountability.
- Work is **not "started"** at G1.
- Triage **cannot close** without an accepted G1 handoff.
