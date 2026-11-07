#!/usr/bin/env python3
"""clean-claude-code scanner: finds temporary / non-final PDF, image and video files.

Default mode is read-only: prints a JSON report of candidates.
Use --apply MANIFEST to move the confirmed candidates to the trash.

Safety rules (enforced here, not just documented):
  * never leaves the given roots; never follows symlinks
  * never touches files tracked by git
  * skips .git, node_modules, virtualenvs and build-tool dirs
  * nothing is permanently deleted: files go to the OS trash
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from collections import defaultdict
from pathlib import Path

MEDIA = {
    "pdf": {".pdf"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg", ".heic"},
    "video": {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".gif"},
}
ALL_EXT = set().union(*MEDIA.values())
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist",
             "build", ".idea", ".vscode", "target", "Pods", ".gradle"}
TEMP_DIRS = {"tmp", "temp", ".tmp", "scratch", "scratchpad", "renders", "frames",
             "previews", "preview", ".cache", "screenshots-tmp", "playwright-report",
             "test-results"}
# name patterns that mark a file as non-final (matched against the stem, lowercase)
TEMP_NAME = re.compile(
    r"(^|[-_. ])(draft|tmp|temp|wip|old|bak|backup|copy|test|preview|scratch|"
    r"untitled|screenshot|capture|render)([-_. ]|\d|$)"
    r"|\(\d+\)$|[-_ ]copy( \d+)?$|final[-_ ]?final|[-_]\d{8,}$"
)
VERSION = re.compile(r"^(?P<base>.+?)[-_ ]?v(?P<n>\d+)$|^(?P<base2>.+?)[-_ ]\((?P<n2>\d+)\)$")
FINAL_MARK = re.compile(r"(^|[-_ ])(final|definitivo|release)([-_ ]|$)")


def git_tracked(root: Path) -> set:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                             capture_output=True, check=True).stdout
        return {str((root / p).resolve()) for p in out.decode().split("\0") if p}
    except Exception:
        return set()


def walk(root: Path):
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = Path(dp) / fn
            if p.suffix.lower() in ALL_EXT and not p.is_symlink():
                yield p


def kind(p: Path) -> str:
    e = p.suffix.lower()
    return next(k for k, v in MEDIA.items() if e in v)


def scan(root: Path, is_scratch: bool):
    tracked = git_tracked(root)
    cands, files = {}, list(walk(root))

    def add(p, reason):
        rp = str(p.resolve())
        if rp in tracked:
            return
        c = cands.setdefault(rp, {"path": rp, "kind": kind(p), "size": p.stat().st_size,
                                  "mtime": int(p.stat().st_mtime), "reasons": []})
        c["reasons"].append(reason)

    for p in files:
        parts = {x.lower() for x in p.relative_to(root).parts[:-1]}
        if is_scratch:
            add(p, "scratchpad-session-file")
        elif parts & TEMP_DIRS:
            add(p, f"temp-dir:{sorted(parts & TEMP_DIRS)[0]}")
        if NAME_MATCH(p.stem.lower()):
            add(p, "temp-name-pattern")

    # superseded versions: same dir + same base, keep the newest / the one marked final
    groups = defaultdict(list)
    for p in files:
        m = VERSION.match(p.stem)
        base = (m.group("base") or m.group("base2")) if m else p.stem
        groups[(p.parent, base.lower(), p.suffix.lower())].append(p)
    for (_, base, _), g in groups.items():
        if len(g) < 2:
            continue
        finals = [p for p in g if FINAL_MARK.search(p.stem.lower())]
        keep = max(finals or g, key=lambda p: p.stat().st_mtime)
        for p in g:
            if p != keep:
                add(p, f"superseded-by:{keep.name}")
    return list(cands.values())


def NAME_MATCH(stem):
    return bool(TEMP_NAME.search(stem))


def to_trash(path: str) -> str:
    p = Path(path)
    trash = Path.home() / ".Trash"
    if not trash.is_dir():  # Linux fallback
        trash = Path.home() / ".local/share/Trash/files"
        trash.mkdir(parents=True, exist_ok=True)
    dest = trash / p.name
    if dest.exists():
        dest = trash / f"{p.stem}-{int(time.time())}{p.suffix}"
    shutil.move(str(p), str(dest))
    return str(dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--root", default=".", help="project directory (default: cwd)")
    ap.add_argument("--scratchpad", action="append", default=[],
                    help="Claude session scratchpad dir to include (repeatable)")
    ap.add_argument("--apply", metavar="MANIFEST",
                    help="JSON list of paths confirmed by the user; moves them to trash")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if a.apply:
        allowed = [root] + [Path(s).resolve() for s in a.scratchpad]
        tracked = git_tracked(root)
        moved, refused = [], []
        for path in json.load(open(a.apply)):
            rp = Path(path).resolve()
            ok = any(rp.is_relative_to(r) for r in allowed) and rp.is_file() \
                and rp.suffix.lower() in ALL_EXT and str(rp) not in tracked and not rp.is_symlink()
            (moved if ok else refused).append(to_trash(str(rp)) if ok else str(path))
        print(json.dumps({"trashed": len(moved), "refused": refused}, indent=2))
        return

    result = scan(root, False)
    for s in a.scratchpad:
        sp = Path(s).resolve()
        if sp.is_dir():
            result += scan(sp, True)
    result.sort(key=lambda c: (c["kind"], c["path"]))
    print(json.dumps({"root": str(root), "count": len(result),
                      "total_bytes": sum(c["size"] for c in result),
                      "candidates": result}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
