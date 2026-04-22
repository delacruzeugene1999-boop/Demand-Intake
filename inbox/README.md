# inbox/

Drop your demand files here — one per file.

- Supported extensions: `.txt`, `.md`, `.docx`, `.pdf`
- Any filename is fine (e.g. `DMD-2026-0417.txt`, `demand-brief.pdf`,
  `iso-20022-migration.docx`)
- Free-form text is accepted; richer demands yield tighter triage

### How each format is handled

| Extension | Handling |
|-----------|----------|
| `.txt`, `.md` | Read as UTF-8 text |
| `.docx` | Text + tables extracted via `python-docx` and fed to the agent |
| `.pdf` | Sent directly to Claude as a native document — scanned pages, diagrams, tables, and signatures are all read via vision |

If a PDF is a scanned image-only document, the agent still reads it —
no separate OCR step is required.

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
