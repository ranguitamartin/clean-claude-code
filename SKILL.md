---
name: clean-claude-code
description: Cleans up temporary files and non-final versions of PDFs, images and videos that Claude Code generates while working in a project (drafts, previews, screenshots, renders, v1/v2 copies, tmp folders, session scratchpad). Always dry-runs first and moves files to the trash only after the user confirms. Use whenever the user asks to clean up, tidy, purge or remove leftovers, temp files, old versions, drafts or generated junk in a project — in English or Spanish ("limpia", "borra temporales", "quita versiones antiguas") — or at the end of a task that produced many intermediate pdf/png/jpg/mp4 files.
license: MIT
metadata:
  author: Roberto Anguita Martín <info@laterretagames.com>
  version: 0.1.0
  repository: https://github.com/ranguitamartin/clean-claude-code
---

# clean-claude-code

Claude Code leaves intermediate media behind: screenshots, `report-v1.pdf` … `report-v4.pdf`, `render/` frames, previews. This skill finds them and removes them safely.

Deletion is the one thing here that cannot be undone, so the whole workflow is built around a human checkpoint: scan → show → confirm → trash.

## Workflow

1. **Scan (read-only).** Run from the project root, adding the current session scratchpad directory from your environment if there is one:
   ```bash
   python3 <skill-dir>/scripts/scan.py --root . --scratchpad <scratchpad-dir>
   ```
   The script returns JSON with each candidate's path, kind (pdf/image/video), size, and `reasons`:
   - `temp-dir:<name>` – inside tmp/, scratch/, renders/, frames/, previews/, test-results/ …
   - `temp-name-pattern` – draft, tmp, wip, copy, `(1)`, final-final, screenshot, preview …
   - `superseded-by:<file>` – an older version (`-v1`, `(2)`) when a newer or "final" one exists
   - `scratchpad-session-file` – anything in the Claude session scratchpad

2. **Review before presenting.** The script is heuristic, so sanity-check it:
   - `grep -r` the project (README, markdown, HTML, code) for each candidate's filename; if something references it, drop it from the list — it is probably an asset, not junk.
   - Drop anything the user's task just asked you to produce (the deliverable is "final" even if its name matches a pattern).
   - Files with a single weak reason (only `temp-name-pattern`) deserve a second look; those with `temp-dir` or `superseded-by` are usually safe.

3. **Present the dry-run.** Group by reason, show size and total reclaimed space, and say what is kept (e.g. "keeping `report-v4.pdf`, removing v1–v3"). Ask for explicit confirmation. Let the user remove items from the list.

4. **Apply only what was confirmed.** Write the approved paths to a JSON array file and run:
   ```bash
   python3 <skill-dir>/scripts/scan.py --root . --scratchpad <scratchpad-dir> --apply approved.json
   ```
   Files go to the system trash, not `rm`, so a mistake is recoverable. Report how many were trashed and anything refused.

## Guarantees built into the script

- Never leaves the project root or the scratchpad you pass in; never follows symlinks.
- Never touches files tracked by git (those are deliberate project content).
- Skips `.git`, `node_modules`, virtualenvs and build output.
- `--apply` re-validates every path, so a bad manifest cannot delete something outside scope.

## What this skill does not do

It only handles PDF, image and video files. It does not clean code, logs, caches or git branches. If the user wants those, say so rather than extending the scope silently.
