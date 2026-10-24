#!/usr/bin/env python3
"""
Dotfiles Sync Script
Copies active configuration files from the user's system back into this repository.
"""

import argparse
import os
import shutil
from pathlib import Path

from manifest import GLOBAL_MAPPINGS, SYNC_IGNORE, theme_mappings

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"

REPO_DIR = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home()


def detect_theme() -> str:
    kdeglobals = HOME_DIR / ".config/kdeglobals"
    try:
        for line in kdeglobals.read_text().splitlines():
            if line.startswith("ColorScheme="):
                return "light" if "light" in line.lower() else "dark"
    except OSError:
        pass
    return "light"


def copy_item(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)

    if src.is_symlink():
        target = os.readlink(src)
        if os.path.isabs(target):
            target = os.path.relpath(target, src.parent)
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
        dest.symlink_to(target)
        return

    if src.is_dir():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns(*SYNC_IGNORE))
        return

    if dest.is_symlink():
        dest.unlink()
    shutil.copy2(src, dest)


def main():
    parser = argparse.ArgumentParser(description="Sync active system configs back into this repository.")
    parser.add_argument("--theme", choices=("auto", "light", "dark"), default="auto",
                        help="Theme folder to sync into: light, dark, or auto-detect (Default: auto)")
    args = parser.parse_args()

    theme = detect_theme() if args.theme == "auto" else args.theme

    print(f"\n{BOLD}{CYAN}=== Syncing Dotfiles from System to Repo ==={RESET}\n")
    print(f"{BLUE}[*]{RESET} Syncing color theme: {theme}\n")

    mappings = [(home_rel, repo_rel) for repo_rel, home_rel in GLOBAL_MAPPINGS]
    mappings += [(home_rel, repo_rel) for repo_rel, home_rel in theme_mappings(theme)]

    synced_count = 0
    for home_rel, repo_rel in mappings:
        src = HOME_DIR / home_rel
        dest = REPO_DIR / repo_rel

        if not src.exists():
            continue

        copy_item(src, dest)

        print(f"{GREEN}[✓]{RESET} Synced {home_rel} -> {repo_rel}")
        synced_count += 1

    print(f"\n{BOLD}{GREEN}Successfully synced {synced_count} items into dotfiles!{RESET}")
    print("You can now run: git add . && git commit -m 'update configs' && git push\n")


if __name__ == "__main__":
    main()
