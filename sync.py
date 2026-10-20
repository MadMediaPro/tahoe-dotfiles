#!/usr/bin/env python3
"""
Dotfiles Sync Script
Copies active configuration files from the user's system back into this repository.
"""

import os
import shutil
from pathlib import Path

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"

REPO_DIR = Path(__file__).resolve().parent
HOME_DIR = Path.home()

MAPPINGS = [
    # Source in HOME -> Destination in REPO
    (".config/darklyrc", ".config/darklyrc"),
    (".config/kdeglobals", ".config/kdeglobals"),
    (".config/kwinrc", ".config/kwinrc"),
    (".config/kwinrulesrc", ".config/kwinrulesrc"),
    (".config/klassy", ".config/klassy"),
    (".config/plasmashellrc", ".config/plasmashellrc"),
    (".config/plasma-org.kde.plasma.desktop-appletsrc", ".config/plasma-org.kde.plasma.desktop-appletsrc"),
    (".config/starship.toml", ".config/starship.toml"),
    (".config/albert/config", ".config/albert/config"),
    (".config/albert/websearch/engines.json", ".config/albert/websearch/engines.json"),
    (".config/autostart/albert.desktop", ".config/autostart/albert.desktop"),
    (".config/alacritty", ".config/alacritty"),
    (".config/cava", ".config/cava"),
    (".config/konsolerc", ".config/konsolerc"),
    (".config/dolphinrc", ".config/dolphinrc"),

    (".local/share/color-schemes/MacTahoeDark.colors", ".local/share/color-schemes/MacTahoeDark.colors"),
    (".local/share/color-schemes/MacTahoeLight.colors", ".local/share/color-schemes/MacTahoeLight.colors"),
    (".local/share/konsole", ".local/share/konsole"),
    (".local/share/plasma/plasmoids/com.github.antroids.application-title-bar", ".local/share/plasma/plasmoids/com.github.antroids.application-title-bar"),
    (".local/share/plasma/plasmoids/org.51n7.kMenu", ".local/share/plasma/plasmoids/org.51n7.kMenu"),
    (".local/share/plasma/plasmoids/org.kde.mac-tahoe-liquid-kde.trashcan", ".local/share/plasma/plasmoids/org.kde.mac-tahoe-liquid-kde.trashcan"),
    (".local/share/plasma/plasmoids/org.kde.mac-tahoe-liquid-kde.launcher", ".local/share/plasma/plasmoids/org.kde.mac-tahoe-liquid-kde.launcher"),
    (".local/share/kwin/scripts", ".local/share/kwin/scripts"),
    (".local/share/kxmlgui5/dolphin", ".local/share/kxmlgui5/dolphin"),
    (".local/share/albert/widgetsboxmodel/themes", ".local/share/albert/widgetsboxmodel/themes"),
    (".local/share/applications/albert-toggle.desktop", ".local/share/applications/albert-toggle.desktop"),

    (".zshrc", "shell/.zshrc"),
    (".p10k.zsh", "shell/.p10k.zsh"),
]

def main():
    print(f"\n{BOLD}{CYAN}=== Syncing Dotfiles from System to Repo ==={RESET}\n")

    synced_count = 0
    for home_rel, repo_rel in MAPPINGS:
        src = HOME_DIR / home_rel
        dest = REPO_DIR / repo_rel

        if not src.exists():
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)

        print(f"{GREEN}[✓]{RESET} Synced {home_rel} -> {repo_rel}")
        synced_count += 1

    print(f"\n{BOLD}{GREEN}Successfully synced {synced_count} items into dotfiles!{RESET}")
    print("You can now run: git add . && git commit -m 'update configs' && git push\n")

if __name__ == "__main__":
    main()
