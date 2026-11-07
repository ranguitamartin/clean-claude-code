# clean-claude-code

A [Claude Code](https://claude.com/claude-code) skill that cleans up the clutter Claude leaves behind in your projects: temporary files and non-final versions of **PDFs, images and videos**.

## What it does

While working, Claude often generates intermediate media: screenshots, previews, rendered frames, `report-v1.pdf` … `report-v4.pdf`, `diagram (1).png`, files in `tmp/` folders. This skill finds them and removes them safely.

1. **Scans** the current project and the Claude session scratchpad (read-only).
2. **Detects** three kinds of leftovers:
   - Files inside temporary folders (`tmp/`, `scratch/`, `renders/`, `frames/`, `previews/`, `test-results/`…)
   - Files with draft-like names (`draft`, `wip`, `copy`, `(1)`, `final-final`, `screenshot`…)
   - Superseded versions: if `report-v1.pdf`, `v2` and `v3` exist, it keeps the newest (or the one marked final) and flags the rest
3. **Shows you a dry-run** grouped by reason, with sizes and the space you would recover.
4. **Deletes only what you confirm**, moving files to the system trash so they can be recovered.

### Safety

- Nothing is deleted without your explicit confirmation
- Files go to the trash, never permanently deleted
- Never touches files tracked by git, `.git` or `node_modules`
- Never leaves the project folder or the session scratchpad
- Every path is re-validated before it is moved

## Installation

Install it globally, so it is available in all your projects:

```bash
npx skills add https://github.com/ranguitamartin/clean-claude-code
```

Then **start a new Claude Code session** (already-open sessions don't reload skills).

Manual alternative:

```bash
git clone https://github.com/ranguitamartin/clean-claude-code ~/.claude/skills/clean-claude-code
```

Requires Python 3.9+ (standard library only, no extra dependencies).

## Usage

In any project, run the slash command:

```
/clean-claude-code
```

or just ask in natural language:

- "Clean up the temp files in this project"
- "Remove old versions of the PDFs and images you generated"
- "Limpia los archivos temporales"

Claude will show the list of candidates and ask for confirmation before removing anything.

## Update

Run the install command again to get the latest version:

```bash
npx skills add https://github.com/ranguitamartin/clean-claude-code
```

## Author

Roberto Anguita Martín — info@laterretagames.com

## License

MIT
