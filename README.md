# BPI Demand Triage Agent

Front-door demand-triage copilot that screens incoming technology demand
strictly per the **BPI Demand Screening and Triage Manual** and produces a
ready-to-share **BTL Hand-Off Pack**. Built on the Anthropic Claude API
(Opus 4.7 + adaptive thinking + structured outputs).

## What you get for every demand

The agent ingests a demand file and writes two outputs to `outbox/`:

| File | What it is | Who uses it |
|------|------------|-------------|
| `<name>.handoff.md` | **BTL Hand-Off Pack** — a formatted Markdown brief with the G1 verdict, classification decision, required consultations, open questions, and triage note. Renders natively in the GitHub file viewer. | BTLs, PMO, service owners |
| `<name>.json` | Machine-readable record of the full 14-section triage (same data, typed). | Downstream automation, portfolio dashboards |

The hand-off pack is organized for fast BTL consumption:

1. **G1 verdict** — one-line call-out with the recommended action
2. **Demand intake & completeness** — what's present, what's missing, what was assumed
3. **Classification decision** — family, run type, subtype, program affiliation, materiality (table)
4. **Required consultations** — overlays sorted mandatory → exception → not needed
5. **Resourcing signal** — effort/cost bands with confidence and quick-estimate flag
6. **Provisional delivery path** — Agile / Waterfall / Infra Build / Innovation
7. **Recommended next owner / forum**
8. **Open questions & escalation items**
9. **Triage note** — the 5-8 sentence audit-trail narrative

## Run it in GitHub (no local setup)

The usage model is: upload a demand file to `inbox/`, the workflow runs,
the hand-off pack appears in `outbox/`.

1. **One-time: set the API key secret.** In the repo on GitHub, go to
   **Settings → Secrets and variables → Actions → New repository
   secret**. Name: `ANTHROPIC_API_KEY`. Value: your Claude API key.
2. **Upload a demand.** Commit a file to `inbox/`. Supported:
   `.txt`, `.md`, `.docx`, `.pdf`. From the GitHub web UI: click into
   `inbox/`, then **Add file → Upload files** (for PDF/DOCX) or
   **Create new file** (for text), drop your file in, commit.
3. **Wait ~15–30 seconds.** The **Triage Demand** workflow triggers
   automatically — watch it run in the **Actions** tab.
4. **Read the hand-off pack.** Refresh — two files appear in `outbox/`:
   - `outbox/your-name.handoff.md` — click it on GitHub for a formatted view.
   - `outbox/your-name.json` — the raw JSON record.
5. **Re-run on demand.** Open **Actions → Triage Demand → Run workflow**.
   Optional inputs: a specific file path, or tick **force** to reprocess
   everything.

The workflow skips files whose outputs are already up-to-date, so
pushing a batch of ten demands costs ten API calls, not twenty.

A sample PDF demand (`Post Delivery Review - Automated Risk Score.pdf`)
is already in `inbox/` — the first workflow run will triage it end-to-end
so you can see the full flow.

## Run it locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

### As a CLI

```bash
# Write the hand-off pack + JSON to a folder (one API call)
python -m triage inbox/my_demand.pdf --outdir outbox

# Print the hand-off pack (Markdown) to stdout
python -m triage inbox/my_demand.pdf --markdown

# Print the legacy plain-text report to stdout
python -m triage inbox/my_demand.txt

# Print raw JSON to stdout
python -m triage inbox/my_demand.txt --json

# From stdin (plain text only)
cat demand.txt | python -m triage -
```

Flags:

| Flag | Default | Notes |
|------|---------|-------|
| `--markdown` | off | Emit the BTL hand-off pack to stdout |
| `--json` | off | Emit raw JSON to stdout |
| `--outdir DIR` | — | Write `<stem>.handoff.md` and `<stem>.json` to `DIR` (one API call) |
| `--usage` | off | Print token usage to stderr |
| `--model` | `claude-opus-4-7` | Override the Claude model id |
| `--effort` | `high` | One of `low`, `medium`, `high`, `xhigh`, `max` |

### As a library

```python
from triage import TriageAgent
from triage.handoff import format_handoff_pack

agent = TriageAgent()

# From plain text
result = agent.triage(demand_text)

# From a file (.txt, .md, .docx, or .pdf — dispatched automatically)
result = agent.triage_file("inbox/demand-brief.pdf")

# Render the BTL hand-off pack as Markdown
print(format_handoff_pack(result.triage, source_name="demand-brief.pdf"))

# Or access structured fields directly
print(result.triage["g1_triage_recommendation"])
print(result.usage)
```

`result.triage` conforms exactly to `triage/schema.py`.
`result.raw_response` is the full Anthropic `Message` object if you
need stop reason, content blocks, or usage in typed form.

## How it works

- **Multi-format input.** `.txt` / `.md` → UTF-8; `.docx` →
  `python-docx` (paragraphs + tables); `.pdf` → Claude native document
  block, so scanned pages, diagrams, tables, and signatures are read
  via vision — no separate OCR step.
- **Cached system prompt.** The full BPI manual
  (`triage/system_prompt.py`) is sent as a cacheable system block, so
  repeated triage calls within the cache TTL pay only for the
  per-demand input.
- **Structured output.** The model is constrained to emit JSON matching
  `TRIAGE_SCHEMA` via `output_config.format` — no parsing brittleness.
- **Adaptive thinking + high effort.** Opus 4.7 reasons proportionally
  to the demand's complexity, and burns more tokens on Tier 3 / routing-
  disputed cases than on BAU.
- **No improvisation.** The system prompt explicitly forbids generic
  PMO logic and pins every step to the manual. When evidence is
  insufficient, the agent lowers confidence and recommends
  clarification rather than fabricating a verdict.

## Examples

`examples/` ships four reference demands covering the main outcomes:

| File | Expected outcome |
|------|------------------|
| `demand_complete_project.txt` | Grow / Project, Tier 3, multiple overlays |
| `demand_innovate_poc.txt` | Innovate / PoC, Innovation path |
| `demand_run_bau.txt` | Run / BAU, Tier 1, no overlay triggers |
| `demand_incomplete_clarify.txt` | Clarification required |

Use any of them locally with `python -m triage examples/<name>.txt --outdir outbox`.

## Project layout

```
triage/
  __init__.py        # public exports
  __main__.py        # `python -m triage` entry point
  agent.py           # TriageAgent class + TriageResult dataclass
  cli.py             # argparse CLI
  handoff.py         # BTL hand-off pack Markdown formatter
  loader.py          # .txt / .md / .docx / .pdf dispatch
  schema.py          # JSON schema for the 14-section output
  system_prompt.py   # BPI Demand Screening and Triage Manual (frozen)
.github/workflows/
  triage.yml         # runs the agent on inbox/, writes to outbox/
inbox/               # drop demand files here (txt/md/docx/pdf)
outbox/              # hand-off packs + JSON land here (auto-committed)
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
  reclassification but do not replace sponsor or service-owner
  accountability.
- Work is **not "started"** at G1.
- Triage **cannot close** without an accepted G1 handoff.
