#!/usr/bin/env python3
"""Stop hook: after Claude finishes a turn, run a read-only scan and, if there are
enough leftovers, ask Claude to run the clean-claude-code skill (which asks the
user to confirm with buttons). Never deletes anything itself.

Env vars:
  CLEAN_CLAUDE_MODE=run|notify|off   (default run)
      run    -> block the stop once so Claude presents the cleanup to the user
      notify -> only show a one-line message to the user, Claude does not continue
      off    -> do nothing
  CLEAN_CLAUDE_MIN=N                 minimum candidates before acting (default 3)
"""
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

SCAN = Path(__file__).resolve().parent.parent / "skills/clean-claude-code/scripts/scan.py"


def main():
    mode = os.environ.get("CLEAN_CLAUDE_MODE", "run")
    if mode == "off":
        return
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    # Claude is already continuing because of a stop hook: never loop.
    if data.get("stop_hook_active"):
        return
    cwd = data.get("cwd") or os.getcwd()
    try:
        out = subprocess.run([sys.executable, str(SCAN), "--root", cwd],
                             capture_output=True, text=True, timeout=25, check=True).stdout
        report = json.loads(out)
    except Exception:
        return  # a hook must never break the session

    cands = report.get("candidates", [])
    if len(cands) < int(os.environ.get("CLEAN_CLAUDE_MIN", "3")):
        return

    # Only nag when the set of leftovers changed since the last time in this session.
    digest = hashlib.sha1("\n".join(sorted(c["path"] for c in cands)).encode()).hexdigest()
    state = Path(tempfile.gettempdir()) / f"clean-claude-{data.get('session_id', 'x')}.seen"
    if state.exists() and state.read_text() == digest:
        return
    state.write_text(digest)

    mb = report["total_bytes"] / 1_048_576
    summary = f"{len(cands)} temporary/non-final media files found ({mb:.1f} MB)"
    if mode == "notify":
        print(json.dumps({"systemMessage": f"clean-claude-code: {summary}. Run /clean-claude-code to review."}))
    else:
        print(json.dumps({
            "decision": "block",
            "reason": (f"clean-claude-code hook: {summary}. Run the clean-claude-code skill now: "
                       "scan all folders this session works in, present the dry-run, and ask the "
                       "user to confirm with the buttons. Do not delete anything without confirmation."),
        }))


if __name__ == "__main__":
    main()
