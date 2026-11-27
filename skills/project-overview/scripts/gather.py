"""Print a capped, token-cheap digest of project status for the project-overview skill.

Usage: python gather.py project|branch [--lines N]
  project: branch digest + recent history + the top of the status docs
  branch:  branch digest only (commits ahead of the base branch, changed files, uncommitted work)
"""
import subprocess
import sys
from pathlib import Path

STATUS_DOCS = ["PROJECT_MASTER.md", "ROADMAP.md", "docs/HANDOFF.md", "HANDOFF.md", "STATUS.md", "README.md"]
WIDTH = 280  # truncate long lines: dense status docs pack whole paragraphs into one line


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def cut(text, n):
    lines = [l[:WIDTH] + ("…" if len(l) > WIDTH else "") for l in text.splitlines() if l.strip()]
    extra = f"\n… ({len(lines) - n} more lines)" if len(lines) > n else ""
    return "\n".join(lines[:n]) + extra


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    scope = sys.argv[1] if len(sys.argv) > 1 else "project"
    n = int(sys.argv[sys.argv.index("--lines") + 1]) if "--lines" in sys.argv else 40
    root = git("rev-parse", "--show-toplevel")
    if not root:
        print("Not a git repository.")
        return
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    base = next((b for b in ("main", "master") if git("rev-parse", "--verify", "-q", b)), "")

    print(f"## Repo {Path(root).name} · branch {branch} · base {base or '?'}")

    if base and branch != base:
        counts = git("rev-list", "--left-right", "--count", f"{base}...HEAD").split()
        if counts:
            print(f"Behind {base}: {counts[0]} · ahead: {counts[1]}")
        print("\n## Commits on this branch (newest first)")
        print(cut(git("log", "--date=short", "--format=%ad %s", f"{base}..HEAD"), 15) or "(none)")
        print("\n## Files changed vs base")
        print(cut(git("diff", "--stat=100", f"{base}...HEAD"), 15) or "(none)")
    print("\n## Uncommitted")
    print(cut(git("status", "--short"), 20) or "(clean)")

    if scope == "project":
        print("\n## Recent history (all branches merged into HEAD)")
        print(cut(git("log", "-15", "--date=short", "--format=%ad %s"), 15))
        for doc in STATUS_DOCS:
            p = Path(root, doc)
            if p.exists():
                print(f"\n## {doc} (top {n} non-empty lines)")
                print(cut(p.read_text(encoding="utf-8", errors="replace"), n))


if __name__ == "__main__":
    main()
