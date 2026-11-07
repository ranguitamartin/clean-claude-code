---
name: clean-claude-code
description: Cleans up temporary files and non-final versions of PDFs, images and videos that Claude Code generates while working in a project (drafts, previews, screenshots, renders, v1/v2 copies, tmp folders, session scratchpad). Always dry-runs first and moves files to the trash only after the user confirms. Use whenever the user asks to clean up, tidy, purge or remove leftovers, temp files, old versions, drafts or generated junk in a project — in English or Spanish ("limpia", "borra temporales", "quita versiones antiguas") — or at the end of a task that produced many intermediate pdf/png/jpg/mp4 files.
license: MIT
metadata:
  author: Roberto Anguita Martín <info@laterretagames.com>
  version: 0.2.0
  repository: https://github.com/ranguitamartin/clean-claude-code
---

# clean-claude-code

Claude Code leaves intermediate media behind: screenshots, `report-v1.pdf` … `report-v4.pdf`, `render/` frames, previews. This skill finds them and removes them safely.

Deletion is the one thing here that cannot be undone, so the whole workflow is built around a human checkpoint: scan → show → confirm → trash.

## Workflow

1. **Scan (read-only).** First work out every folder this session works in, because a session often spans several sibling folders (e.g. `web_app/`, `ios_app/`, `android_app/`) and the script only sees the roots you pass it:
   - the primary working directory and every additional working directory listed in your environment;
   - any other folder you have read from or written to in this session (check the paths of the files you touched);
   - the session scratchpad directory, if there is one.

   Pass each project folder as its own `--root`, and the scratchpad with `--scratchpad`:
   ```bash
   python3 <skill-dir>/scripts/scan.py --root /path/web --root /path/ios --root /path/android --scratchpad <scratchpad-dir>
   ```
   If you are unsure whether a nearby folder belongs to the session, ask the user instead of guessing; scanning too little is harmless, scanning an unrelated project is not.
   The script returns JSON with each candidate's path, kind (pdf/image/video), size, and `reasons`:
   - `temp-dir:<name>` – inside tmp/, scratch/, renders/, frames/, previews/, test-results/ …
   - `temp-name-pattern` – draft, tmp, wip, copy, `(1)`, final-final, screenshot, preview …
   - `superseded-by:<file>` – an older version (`-v1`, `(2)`) when a newer or "final" one exists
   - `scratchpad-session-file` – anything in the Claude session scratchpad

2. **Review before presenting.** The script is heuristic, so sanity-check it:
   - The script already searches every root's text files (docs, code, configs) for each candidate's filename and reports matches in `referenced_by`. Treat any candidate with that field as an asset: drop it unless the user says otherwise. Do not rely on your own `grep` for this; the script does it for you.
   - Drop anything the user's task just asked you to produce (the deliverable is "final" even if its name matches a pattern).
   - Files with a single weak reason (only `temp-name-pattern`) deserve a second look; those with `temp-dir` or `superseded-by` are usually safe.

3. **Present the dry-run.** Group by reason, show size and total reclaimed space, and say what is kept (e.g. "keeping `report-v4.pdf`, removing v1–v3"). Then ask for confirmation with the `AskUserQuestion` tool so the user answers by clicking a button instead of typing (load it with ToolSearch first if it is deferred). Write the question and labels in the user's language.
   - **Question 1** (single choice), summarising the count and size: "Move all N files to the trash" / "Let me choose which groups" / "Cancel, keep everything".
   - If they pick "choose", **Question 2** (multi-select), one option per reason group (e.g. "Superseded versions (5)", "Temp folders (3)", "Name patterns (2)", "Scratchpad (1)"), so they tick only the groups to remove. There are at most four groups; merge the smallest if needed.
   - Treat "Other"/free text as a request to adjust the list, and ask again with the updated list.
   - If `AskUserQuestion` is unavailable, fall back to asking in plain text. Never treat silence or an ambiguous answer as a yes.

4. **Apply only what was confirmed.** Write the approved paths to a JSON array file and run:
   ```bash
   python3 <skill-dir>/scripts/scan.py --root /path/web --root /path/ios --root /path/android --scratchpad <scratchpad-dir> --apply approved.json
   ```
   Files go to the system trash, not `rm`, so a mistake is recoverable. Report how many were trashed and anything refused.

## Guarantees built into the script

- Never leaves the roots and scratchpad you pass in; never follows symlinks. Each root respects its own git repository.
- Never touches files tracked by git (those are deliberate project content).
- Skips `.git`, `node_modules`, virtualenvs and build output.
- `--apply` re-validates every path, so a bad manifest cannot delete something outside scope.

## What this skill does not do

It only handles PDF, image and video files. It does not clean code, logs, caches or git branches. If the user wants those, say so rather than extending the scope silently.
