# clean-claude-code

A [Claude Code](https://claude.com/claude-code) plugin that cleans up the clutter Claude leaves behind in your projects: temporary files and non-final versions of **PDFs, images and videos**.

## What it does

While working, Claude often generates intermediate media: screenshots, previews, rendered frames, `report-v1.pdf` … `report-v4.pdf`, `diagram (1).png`, files in `tmp/` folders. This plugin finds them and removes them safely.

1. **Scans** every folder the session works in (several projects at once) plus the Claude session scratchpad. Read-only.
2. **Detects** these kinds of leftovers:
   - Files inside temporary folders (`tmp/`, `scratch/`, `renders/`, `frames/`, `previews/`, `test-results/`…)
   - Files with draft-like names (`draft`, `wip`, `copy`, `(1)`, `final-final`, `screenshot`…)
   - Superseded versions: if `report-v1.pdf`, `v2` and `v3` exist, it keeps the newest (or the one marked final) and flags the rest
   - Build folders `ddarch`, `ddn`, `ddv` and `arch` (Xcode derived data / archives), listed as whole folders with their size. Folders containing git-tracked files are never listed. Add more names with `--build-dir`.
3. **Skips referenced files**: anything whose name appears in your code, docs or configs is treated as an asset.
4. **Shows a dry-run** with sizes, then asks you to confirm **by clicking a button** (move all / choose groups / cancel).
5. **Moves the confirmed files to the system trash**, so they can be recovered.

### Automatic scan after each turn

The plugin includes a `Stop` hook. When Claude finishes a response and there are enough leftovers (3 or more, and a different set from the last time it asked), it asks Claude to run the cleanup flow. It never deletes anything by itself; you always confirm.

Configure it with environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `CLEAN_CLAUDE_MODE` | `run` | `run`: Claude presents the cleanup; `notify`: only a one-line message; `off`: disabled |
| `CLEAN_CLAUDE_MIN` | `3` | Minimum number of candidates before the hook acts |

### Safety

- Nothing is deleted without your explicit confirmation
- Files go to the trash, never permanently deleted
- Never touches files tracked by git, `.git` or `node_modules`
- Never leaves the project folders or the session scratchpad
- Every path is re-validated before it is moved
- The hook never loops (it ignores its own follow-up turns)

## Installation

### As a plugin (skill + automatic hook)

Inside Claude Code:

```
/plugin marketplace add ranguitamartin/clean-claude-code
/plugin install clean-claude-code@clean-claude-code
```

Then start a new session.

### As a skill only (no hook)

```bash
npx skills add https://github.com/ranguitamartin/clean-claude-code
```

Select **Claude Code** in the agent list and choose a global install. Start a new session afterwards.

Requires Python 3.9+ (standard library only, no extra dependencies).

## Usage

Run the slash command in any project:

```
/clean-claude-code
```

or ask in natural language:

- "Clean up the temp files in this project"
- "Remove old versions of the PDFs and images you generated"
- "Limpia los archivos temporales"

## Author

Roberto Anguita Martín — info@laterretagames.com

## License

MIT
