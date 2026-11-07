# clean-claude-code

A Claude Code skill that finds and removes temporary files and non-final versions of PDFs, images and videos generated during a project.

- Dry-run first, deletion only after you confirm
- Files go to the system trash (recoverable)
- Never touches git-tracked files, `node_modules`, `.git`, or anything outside the project / session scratchpad
- Requires Python 3.9+ (stdlib only)

## Install (global)

```bash
npx skills add https://github.com/ranguitamartin/clean-claude-code
```

Or manually:

```bash
git clone https://github.com/ranguitamartin/clean-claude-code ~/.claude/skills/clean-claude-code
```

## Use

Start a new Claude Code session and run `/clean-claude-code`, or just ask: "clean up the temp files in this project".

## Author

Roberto Anguita Martín — info@laterretagames.com

## License

MIT
