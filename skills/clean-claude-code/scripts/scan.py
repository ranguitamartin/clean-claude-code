#!/usr/bin/env python3
"""clean-claude-code scanner: finds temporary / non-final PDF, image and video files.

Default mode is read-only: prints a JSON report of candidates.
Use --apply MANIFEST to move the confirmed candidates to the trash.

Safety rules (enforced here, not just documented):
  * never leaves the given roots; never follows symlinks
  * never touches files tracked by git
  * skips .git, node_modules, virtualenvs and build-tool dirs
  * build dirs (ddarch, ddn, ddv, arch + any --build-dir) are listed as whole folders,
    never if they contain git-tracked files
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
# Xcode-style build/derived-data/archive folders created by xcodebuild runs.
BUILD_DIRS = {"ddarch", "ddn", "ddv", "arch"}
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
        dns[:] = [d for d in dns if d not in SKIP_DIRS and d not in BUILD_DIRS]
        for fn in fns:
            p = Path(dp) / fn
            if p.suffix.lower() in ALL_EXT and not p.is_symlink():
                yield p


def dir_size(d: Path) -> int:
    total = 0
    for dp, _, fns in os.walk(d, followlinks=False):
        for fn in fns:
            try:
                total += os.lstat(os.path.join(dp, fn)).st_size
            except OSError:
                pass
    return total


def has_tracked(d: Path, tracked: set) -> bool:
    prefix = str(d.resolve()) + os.sep
    return any(t.startswith(prefix) for t in tracked)


def find_build_dirs(root: Path, tracked: set):
    found = []
    for dp, dns, _ in os.walk(root, followlinks=False):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for d in list(dns):
            p = Path(dp) / d
            if d.lower() in BUILD_DIRS and not p.is_symlink():
                dns.remove(d)  # do not descend; the folder is one unit
                if has_tracked(p, tracked):
                    continue
                found.append({"path": str(p.resolve()), "kind": "build-dir",
                              "size": dir_size(p), "mtime": int(p.stat().st_mtime),
                              "reasons": [f"build-dir:{d}"]})
    return found


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
    return list(cands.values()) + find_build_dirs(root, tracked)


def NAME_MATCH(stem):
    return bool(TEMP_NAME.search(stem))


TEXT_EXT = {".md", ".txt", ".json", ".js", ".ts", ".tsx", ".jsx", ".py", ".html", ".css",
            ".swift", ".kt", ".kts", ".java", ".xml", ".yml", ".yaml", ".sh", ".plist",
            ".gradle", ".toml", ".dart", ".rb", ".php", ".strings", ".pbxproj"}


def mark_references(cands, roots):
    """Add 'referenced_by' to candidates whose filename appears in a text file."""
    names = {}
    for c in cands:
        if c["kind"] == "build-dir":
            continue
        names.setdefault(Path(c["path"]).name, []).append(c)
    for r in roots:
        for dp, dns, fns in os.walk(r, followlinks=False):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                p = Path(dp) / fn
                if p.suffix.lower() not in TEXT_EXT or p.is_symlink():
                    continue
                try:
                    if p.stat().st_size > 2_000_000:
                        continue
                    txt = p.read_text(errors="ignore")
                except OSError:
                    continue
                for n, cs in names.items():
                    if n in txt:
                        for c in cs:
                            if str(p.resolve()) != c["path"]:
                                c.setdefault("referenced_by", []).append(str(p))


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
    ap.add_argument("--root", action="append", default=None,
                    help="project directory; repeat for every folder the session works in (default: cwd)")
    ap.add_argument("--scratchpad", action="append", default=[],
                    help="Claude session scratchpad dir to include (repeatable)")
    ap.add_argument("--build-dir", action="append", default=[],
                    help="extra build folder name to treat like ddarch/ddn/ddv/arch (repeatable)")
    ap.add_argument("--apply", metavar="MANIFEST",
                    help="JSON list of paths confirmed by the user; moves them to trash")
    a = ap.parse_args()

    BUILD_DIRS.update(n.lower() for n in a.build_dir)
    roots = [Path(r).resolve() for r in (a.root or ["."])]
    if a.apply:
        allowed = roots + [Path(s).resolve() for s in a.scratchpad]
        tracked = set().union(*(git_tracked(r) for r in roots))
        moved, refused = [], []
        for path in json.load(open(a.apply)):
            rp = Path(path).resolve()
            in_scope = any(rp.is_relative_to(r) for r in allowed)
            if rp.is_dir():
                ok = in_scope and rp.name.lower() in BUILD_DIRS and not Path(path).is_symlink() \
                    and not has_tracked(rp, tracked)
            else:
                ok = in_scope and rp.is_file() and rp.suffix.lower() in ALL_EXT \
                    and str(rp) not in tracked and not rp.is_symlink()
            (moved if ok else refused).append(to_trash(str(rp)) if ok else str(path))
        print(json.dumps({"trashed": len(moved), "refused": refused}, indent=2))
        return

    result = []
    for root in roots:
        result += scan(root, False)
    for s in a.scratchpad:
        sp = Path(s).resolve()
        if sp.is_dir():
            result += scan(sp, True)
    mark_references(result, roots)
    result.sort(key=lambda c: (c["kind"], c["path"]))
    print(json.dumps({"roots": [str(r) for r in roots], "count": len(result),
                      "total_bytes": sum(c["size"] for c in result),
                      "candidates": result}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
