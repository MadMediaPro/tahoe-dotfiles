#!/usr/bin/env python3
"""
Dotfiles Installer for KDE Plasma 6 (macOS Tahoe Rice)
Author: labubu
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

REPO_DIR = Path(__file__).resolve().parent
HOME_DIR = Path.home()

MAPPINGS = [
    # .config files & directories
    ("dotfiles/.config/darklyrc", ".config/darklyrc"),
    ("dotfiles/.config/kdeglobals", ".config/kdeglobals"),
    ("dotfiles/.config/kwinrc", ".config/kwinrc"),
    ("dotfiles/.config/kwinrulesrc", ".config/kwinrulesrc"),
    ("dotfiles/.config/klassy", ".config/klassy"),
    ("dotfiles/.config/plasmashellrc", ".config/plasmashellrc"),
    ("dotfiles/.config/plasma-org.kde.plasma.desktop-appletsrc", ".config/plasma-org.kde.plasma.desktop-appletsrc"),
    ("dotfiles/.config/starship.toml", ".config/starship.toml"),
    ("dotfiles/.config/albert", ".config/albert"),
    ("dotfiles/.config/autostart/albert.desktop", ".config/autostart/albert.desktop"),
    ("dotfiles/.config/alacritty", ".config/alacritty"),
    ("dotfiles/.config/cava", ".config/cava"),
    ("dotfiles/.config/konsolerc", ".config/konsolerc"),
    ("dotfiles/.config/dolphinrc", ".config/dolphinrc"),
    ("dotfiles/.config/dolphin/dolphin.qss", ".config/dolphin/dolphin.qss"),
    ("dotfiles/.config/gtk-3.0", ".config/gtk-3.0"),
    ("dotfiles/.config/gtk-4.0", ".config/gtk-4.0"),
    ("dotfiles/.config/xsettingsd", ".config/xsettingsd"),

    # .local/share files & directories
    ("dotfiles/.local/share/color-schemes", ".local/share/color-schemes"),
    ("dotfiles/.local/share/konsole", ".local/share/konsole"),
    ("dotfiles/.local/share/plasma/plasmoids", ".local/share/plasma/plasmoids"),
    ("dotfiles/.local/share/kwin/scripts", ".local/share/kwin/scripts"),
    ("dotfiles/.local/share/kxmlgui5/dolphin", ".local/share/kxmlgui5/dolphin"),
    ("dotfiles/.local/share/kxmlgui6/dolphin", ".local/share/kxmlgui6/dolphin"),
    ("dotfiles/.local/share/albert", ".local/share/albert"),
    ("dotfiles/.local/share/applications/albert-toggle.desktop", ".local/share/applications/albert-toggle.desktop"),
    ("dotfiles/.local/share/applications/org.kde.dolphin.desktop", ".local/share/applications/org.kde.dolphin.desktop"),
    ("dotfiles/.local/bin/dolphin", ".local/bin/dolphin"),

    # Shell & Home
    ("dotfiles/shell/.zshrc", ".zshrc"),
    ("dotfiles/shell/.p10k.zsh", ".p10k.zsh"),
    ("dotfiles/shell/.gtkrc-2.0", ".gtkrc-2.0"),
]

def log_info(msg):
    print(f"{BLUE}[*]{RESET} {msg}")

def log_success(msg):
    print(f"{GREEN}[✓]{RESET} {msg}")

def log_warn(msg):
    print(f"{YELLOW}[!]{RESET} {msg}")

def log_error(msg):
    print(f"{RED}[✗]{RESET} {msg}")

def get_missing_packages():
    pkg_file = REPO_DIR / "packages.txt"
    if not pkg_file.exists():
        return []

    pkgs = []
    with open(pkg_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkgs.append(line)

    missing = []
    for pkg in pkgs:
        # Check if installed using pacman -Q
        res = subprocess.run(["pacman", "-Q", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            # Also check if it's an executable in PATH (e.g. starship in /usr/local/bin)
            if not shutil.which(pkg):
                missing.append(pkg)

    return missing

def install_packages(dry_run: bool, auto_yes: bool = False):
    missing = get_missing_packages()
    if not missing:
        log_success("All prerequisite packages are already installed.")
        return

    log_warn(f"Missing packages detected ({len(missing)}): {', '.join(missing)}")

    pkg_mgr = None
    for mgr in ["yay", "paru", "pacman"]:
        if shutil.which(mgr):
            pkg_mgr = mgr
            break

    if not pkg_mgr:
        log_error("No package manager (yay/paru/pacman) found to install missing packages.")
        return

    if dry_run:
        log_info(f"[Dry-Run] Would run: {pkg_mgr} -S --needed {' '.join(missing)}")
        return

    if not auto_yes:
        try:
            choice = input(f"{YELLOW}[?]{RESET} Install missing packages now using {pkg_mgr}? [Y/n]: ").strip().lower()
            if choice not in ["", "y", "yes"]:
                log_info("Skipping package installation.")
                return
        except (KeyboardInterrupt, EOFError):
            print()
            return

    log_info(f"Installing missing packages using {pkg_mgr}...")
    cmd = [pkg_mgr, "-S", "--needed"] + missing
    subprocess.run(cmd)

def install_item(src: Path, dest: Path, backup_dir: Path, use_symlink: bool, dry_run: bool):
    if not src.exists():
        return

    # Backup existing destination if it exists
    if dest.exists() or dest.is_symlink():
        if backup_dir:
            backup_target = backup_dir / dest.relative_to(HOME_DIR)
            if not dry_run:
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                if dest.is_symlink() or dest.is_file():
                    shutil.copy2(dest, backup_target, follow_symlinks=False)
                elif dest.is_dir():
                    shutil.copytree(dest, backup_target, symlinks=True, dirs_exist_ok=True)
            log_info(f"Backed up: {dest} -> {backup_target}")

        if not dry_run:
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            elif dest.is_dir():
                shutil.rmtree(dest)

    # Ensure parent directory exists
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)

    # Link or copy
    if use_symlink:
        if not dry_run:
            dest.symlink_to(src.resolve(), target_is_directory=src.is_dir())
        log_success(f"Symlinked: {dest} -> {src}")
    else:
        if not dry_run:
            if src.is_dir():
                shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
        log_success(f"Copied: {src.name} -> {dest}")

def apply_wifi_patch(dry_run: bool):
    icon_theme_dir = HOME_DIR / ".local/share/icons/MacTahoe"
    patch_24 = REPO_DIR / "patches/MacTahoe-wifi-icons/24"
    patch_32 = REPO_DIR / "patches/MacTahoe-wifi-icons/32"

    if not icon_theme_dir.exists():
        log_warn("MacTahoe icon theme not found at ~/.local/share/icons/MacTahoe.")
        log_warn("Please install MacTahoe first, then re-run to apply Wi-Fi icons patch.")
        return

    dest_24 = icon_theme_dir / "status/24"
    dest_32 = icon_theme_dir / "status/32"

    if patch_24.exists():
        log_info("Applying Wi-Fi patch to status/24...")
        if not dry_run:
            dest_24.mkdir(parents=True, exist_ok=True)
            for item in patch_24.iterdir():
                d = dest_24 / item.name
                if d.exists() or d.is_symlink():
                    d.unlink() if (d.is_file() or d.is_symlink()) else shutil.rmtree(d)
                if item.is_symlink():
                    link_target = os.readlink(item)
                    os.symlink(link_target, d)
                else:
                    shutil.copy2(item, d)

    if patch_32.exists():
        log_info("Applying Wi-Fi patch to status/32...")
        if not dry_run:
            dest_32.mkdir(parents=True, exist_ok=True)
            for item in patch_32.iterdir():
                d = dest_32 / item.name
                if d.exists() or d.is_symlink():
                    d.unlink() if (d.is_file() or d.is_symlink()) else shutil.rmtree(d)
                if item.is_symlink():
                    link_target = os.readlink(item)
                    os.symlink(link_target, d)
                else:
                    shutil.copy2(item, d)

    log_success("Wi-Fi icon patch applied successfully to MacTahoe theme!")

def apply_finder_patch(dry_run: bool):
    icon_source = REPO_DIR / "icons/file-manager-clear.svg"
    if not icon_source.exists():
        log_warn(f"Clear Finder icon not found at {icon_source}")
        return

    icons_dir = HOME_DIR / ".local/share/icons"
    if not icons_dir.exists():
        return

    targets = [p for p in icons_dir.glob("MacTahoe*/apps/scalable/file-manager.svg") if p.is_file() and not p.is_symlink()]
    if not targets:
        return

    log_info("Applying Clear Finder icon patch to MacTahoe themes...")
    for target in targets:
        if not dry_run:
            shutil.copy2(icon_source, target)
        log_info(f"Patched: {target.relative_to(HOME_DIR)}")

    log_success("Clear Finder icon patch applied successfully!")

def install_frosted_themes(dry_run: bool, modes):
    if not modes:
        return

    src = HOME_DIR / ".local/share/icons/MacTahoe"
    icons_dir = HOME_DIR / ".local/share/icons"
    script = REPO_DIR / "frostify.py"

    if not src.exists():
        log_warn("MacTahoe icon theme not found at ~/.local/share/icons/MacTahoe.")
        log_warn("Please install MacTahoe first, then re-run to generate frosted variants.")
        return

    if not script.exists():
        log_warn(f"Frosted icon generator not found at {script}")
        return

    names = {"clear": "MacTahoe-Frosted"}
    for mode in modes:
        name = names[mode]
        dest = icons_dir / name
        log_info(f"Generating frosted icon theme: {name} ({mode})...")

        if dry_run:
            log_info(f"[Dry-Run] Would generate {dest} from {src}")
            continue

        result = subprocess.run(
            [sys.executable, str(script), "--src", str(src), "--dest", str(dest), "--mode", mode]
        )
        if result.returncode == 0:
            log_success(f"Generated: {dest.relative_to(HOME_DIR)}")
        else:
            log_error(f"Failed to generate {name}")

def ensure_fonts(dry_run: bool):
    fonts_dir = HOME_DIR / ".local/share/fonts/apple-san-francisco-pro-fonts"
    
    has_font = False
    if fonts_dir.exists() and any(fonts_dir.iterdir()):
        has_font = True
    elif shutil.which("fc-list"):
        try:
            res = subprocess.run(["fc-list", ":", "family"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if "SF Pro Display" in res.stdout:
                has_font = True
        except Exception:
            pass

    if has_font:
        log_success("Apple SF Pro Display fonts are already installed.")
        return

    log_info("Apple SF Pro fonts not found. Downloading from GitHub...")
    if dry_run:
        log_info(f"[Dry-Run] Would clone https://github.com/sahibjotsw/apple-san-francisco-pro-fonts.git to {fonts_dir}")
        return

    fonts_dir.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("git"):
        ret = subprocess.run([
            "git", "clone", "--depth", "1",
            "https://github.com/sahibjotsw/apple-san-francisco-pro-fonts.git",
            str(fonts_dir)
        ])
        if ret.returncode == 0:
            log_success("Apple SF Pro fonts downloaded successfully.")
            if shutil.which("fc-cache"):
                log_info("Refreshing font cache (fc-cache)...")
                subprocess.run(["fc-cache", "-f", str(fonts_dir.parent)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log_success("Font cache updated.")
        else:
            log_error(f"Failed to clone fonts. You can manually download to: {fonts_dir}")
    else:
        log_warn(f"'git' not found. Please manually install fonts to: {fonts_dir}")

def ensure_gtk_theme(dry_run: bool):
    theme_dir = HOME_DIR / ".themes/MacTahoe-Dark"
    if theme_dir.exists():
        log_success("MacTahoe GTK theme is already installed in ~/.themes.")
        return

    log_info("MacTahoe GTK theme not detected. Downloading from GitHub...")
    if dry_run:
        log_info("[Dry-Run] Would clone https://github.com/vinceliuice/MacTahoe-gtk-theme.git and run ./install.sh -d ~/.themes")
        return

    if not shutil.which("git"):
        log_warn("git not found. Please install MacTahoe-gtk-theme manually from: https://github.com/vinceliuice/MacTahoe-gtk-theme")
        return

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_repo = Path(tmp_dir) / "MacTahoe-gtk-theme"
        ret = subprocess.run([
            "git", "clone", "--depth", "1",
            "https://github.com/vinceliuice/MacTahoe-gtk-theme.git",
            str(tmp_repo)
        ])
        if ret.returncode == 0:
            install_script = tmp_repo / "install.sh"
            if install_script.exists():
                subprocess.run(["bash", str(install_script), "-d", str(HOME_DIR / ".themes")], cwd=tmp_repo)
                log_success("MacTahoe GTK theme installed successfully to ~/.themes.")
        else:
            log_error("Failed to clone MacTahoe-gtk-theme. Please install manually.")

def rebuild_caches(dry_run: bool):
    if dry_run:
        log_info("[Dry-Run] Would rebuild sycoca and icon caches.")
        return

    log_info("Rebuilding desktop sycoca cache...")
    for cmd in ["kbuildsycoca6", "kbuildsycoca5"]:
        if shutil.which(cmd):
            subprocess.run([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break

    icons_base = HOME_DIR / ".local/share/icons"
    if icons_base.exists() and shutil.which("gtk-update-icon-cache"):
        log_info("Rebuilding GTK icon cache for MacTahoe themes...")
        for d in icons_base.glob("MacTahoe*"):
            if d.is_dir() and (d / "index.theme").exists():
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(d)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    log_success("Caches refreshed.")

def main():
    parser = argparse.ArgumentParser(description="Install and setup KDE Plasma 6 dotfiles.")
    parser.add_argument("--symlink", action="store_true", help="Create symlinks instead of copying files.")
    parser.add_argument("--no-backup", action="store_true", help="Skip backing up existing configuration files.")
    parser.add_argument("--install-pkgs", action="store_true", help="Automatically install missing packages without prompting.")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically answer yes to all confirmation prompts.")
    parser.add_argument("--dry-run", action="store_true", help="Show what actions would be performed without doing them.")
    parser.add_argument("--frosted", choices=("none", "clear"), default="clear",
                        help="Generate the frosted icon theme (Default: clear)")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}=== KDE Plasma 6 Dotfiles Installer ==={RESET}\n")

    # Step 1: Check and install missing packages
    install_packages(args.dry_run, auto_yes=(args.install_pkgs or args.yes))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = None
    if not args.no_backup and not args.dry_run:
        backup_dir = HOME_DIR / f".dotfiles_backup_{timestamp}"
        log_info(f"Existing files will be backed up to: {backup_dir}")

    # Process all mappings
    for repo_rel, home_rel in MAPPINGS:
        # Strip leading dotfiles/ if present
        clean_rel = repo_rel.removeprefix("dotfiles/")
        src = REPO_DIR / clean_rel
        dest = HOME_DIR / home_rel
        install_item(src, dest, backup_dir, args.symlink, args.dry_run)

    # Install Apple SF Pro fonts if missing
    ensure_fonts(args.dry_run)

    # Install MacTahoe GTK theme if missing
    ensure_gtk_theme(args.dry_run)

    # Patch MacTahoe Wi-Fi icons
    apply_wifi_patch(args.dry_run)

    # Patch MacTahoe Clear Finder icon
    apply_finder_patch(args.dry_run)

    # Generate frosted icon theme variants
    frosted_modes = {"none": [], "clear": ["clear"]}[args.frosted]
    install_frosted_themes(args.dry_run, frosted_modes)

    # Refresh KDE caches
    rebuild_caches(args.dry_run)

    print(f"\n{BOLD}{GREEN}All configurations installed successfully!{RESET}")
    print(f"{YELLOW}Tip:{RESET} If you want to restart Plasma to see changes immediately:")
    print("     systemctl --user restart plasma-plasmashell.service\n")

if __name__ == "__main__":
    main()
