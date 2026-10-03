#!/usr/bin/env python3
"""Install a stable copy, preserving the previous installation and command links."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil


def backup(path):
    if path.exists() or path.is_symlink():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        saved = path.with_name(path.name + ".backup-" + stamp)
        path.rename(saved)
        print(f"Backed up {path} to {saved}")


def link(target, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() and dest.resolve() == target.resolve():
        return
    backup(dest)
    dest.symlink_to(target)
    print(f"Linked {dest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="installation home (also useful for testing)")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    dest = args.home.expanduser().resolve() / ".agents/skills/pr-green"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source != dest.resolve():
        backup(dest)
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (dest / "scripts/pr-green").chmod(0o755)
    link(dest, args.home / ".codex/skills/pr-green")
    link(dest / "scripts/pr-green", args.home / ".local/bin/pr-green")
    print(f"Installed {dest}")


if __name__ == "__main__":
    main()
