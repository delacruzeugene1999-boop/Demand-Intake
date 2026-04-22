# inbox/

Drop your demand files here — one per file.

- Supported extensions: `.txt`, `.md`
- Any filename is fine (e.g. `DMD-2026-0417.txt`, `iso-20022-migration.md`)
- Free-form text is accepted; richer demands yield tighter triage

## What happens when you add a file

1. You commit a file to `inbox/` and push (or open a PR and merge it).
2. The **Triage Demand** GitHub Actions workflow runs automatically.
3. Two outputs appear in `outbox/`:
   - `<your-filename>.report.txt` — the formatted 14-section report
   - `<your-filename>.json` — the raw structured JSON
4. The workflow commits those outputs back to the branch you pushed to.

## Manual re-run

To re-triage an existing file without editing it, go to the repo's
**Actions** tab, pick **Triage Demand**, click **Run workflow**, and
optionally supply a specific file path.

## Example

See the files in `../examples/` for four reference demands covering
Project, PoC, BAU, and clarification-required outcomes.
