#!/usr/bin/env python3
"""Set KDE and MacTahoe corner radii consistently.

Outer surfaces are set to the requested radius. Nested/dependent values are
scaled from the previous outer radius so their visual proportion is preserved.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
DOTFILES = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "desktop").is_dir() else HOME / "dotfiles"
WORKSPACE = HOME / "custom-workspace"

INI_HEADER = re.compile(r"^\s*\[(.+?)\]\s*$")
INI_LINE = re.compile(r"^([^=\n]+?)=(.*?)(\r?\n)?$")
CORNER_PATH = re.compile(
    r'd="m (?P<x>-?\d+(?:\.\d+)?),(?P<y>-?\d+(?:\.\d+)?) '
    r"h -(?P<top>\d+(?:\.\d+)?) "
    r"c -(?P<c1>\d+(?:\.\d+)?),0 "
    r"-(?P<r>\d+(?:\.\d+)?),(?P<c2y>\d+(?:\.\d+)?) "
    r"-(?P<r2>\d+(?:\.\d+)?),(?P<r3>\d+(?:\.\d+)?) "
    r"v (?P<bottom>\d+(?:\.\d+)?) "
    r'h (?P<w>\d+(?:\.\d+)?) z"'
)

KCFG_ARC = 0.5522847498


def number(value: float, like: str) -> str:
    if "." not in like and "e" not in like.lower():
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def parse_ini(path: Path) -> dict[tuple[str, str], str]:
    values: dict[tuple[str, str], str] = {}
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        header = INI_HEADER.match(line)
        if header:
            section = header.group(1)
            continue
        match = INI_LINE.match(line)
        if match:
            values[(section, match.group(1).strip())] = match.group(2).strip()
    return values


def replace_ini(text: str, replacements: dict[tuple[str, str], str]) -> str:
    lines = text.splitlines(keepends=True)
    section = ""
    result: list[str] = []
    for line in lines:
        header = INI_HEADER.match(line)
        if header:
            section = header.group(1)
            result.append(line)
            continue
        match = INI_LINE.match(line)
        if not match:
            result.append(line)
            continue
        key = match.group(1).strip()
        newline = match.group(3) or ""
        replacement = replacements.get((section, key))
        if replacement is None:
            result.append(line)
        else:
            result.append(f"{key}={replacement}{newline}")
    return "".join(result)


def write_text(path: Path, text: str, dry_run: bool, backups: Path | None) -> None:
    old = path.read_text(encoding="utf-8")
    if old == text:
        return
    if dry_run:
        return
    if backups is not None:
        destination = backups / path.relative_to(path.anchor)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_bytes(path: Path, data: bytes, dry_run: bool, backups: Path | None) -> None:
    old = path.read_bytes()
    if old == data:
        return
    if dry_run:
        return
    if backups is not None:
        destination = backups / path.relative_to(path.anchor)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def patch_ini(
    path: Path,
    primary: list[tuple[str, str]],
    scaled: list[tuple[str, str]],
    target: int,
    dry_run: bool,
    backups: Path | None,
    verbose: bool,
) -> list[str]:
    if not path.exists():
        return []
    values = parse_ini(path)
    old_primary = None
    for key in primary:
        try:
            old_primary = float(values[key])
            break
        except (KeyError, ValueError):
            continue
    if old_primary is None or old_primary <= 0:
        old_primary = float(target)

    replacements: dict[tuple[str, str], str] = {}
    for key in primary:
        if key in values:
            replacements[key] = number(float(target), values[key])

    for key in scaled:
        if key not in values:
            continue
        try:
            current = float(values[key])
        except ValueError:
            continue
        desired = current * float(target) / old_primary
        replacements[key] = number(desired, values[key])

    changed = []
    for key, value in replacements.items():
        old = values.get(key)
        if old != value:
            changed.append(f"{key[0]}.{key[1]}: {old} -> {value}")
    if changed:
        text = replace_ini(path.read_text(encoding="utf-8"), replacements)
        write_text(path, text, dry_run, backups)
    if verbose and changed:
        print(f"{path}:")
        for item in changed:
            print(f"  {item}")
    return changed


def patch_svgz(
    path: Path,
    target: int,
    scale: float,
    dry_run: bool,
    backups: Path | None,
    verbose: bool,
) -> list[str]:
    if not path.exists():
        return []
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    changes: list[str] = []

    def replace(match: re.Match[str]) -> str:
        groups = match.groupdict()
        tile = float(groups["w"])
        radius = float(groups["r"])
        if abs(float(groups["r2"]) - radius) > 0.01 or abs(float(groups["r3"]) - radius) > 0.01:
            return match.group(0)
        if abs(float(groups["bottom"]) + radius - tile) > 0.01:
            return match.group(0)
        if abs(float(groups["top"]) + radius - tile) > 0.01:
            return match.group(0)
        desired = target / scale
        if desired <= 0:
            return match.group(0)
        desired = min(desired, tile)
        if abs(desired - radius) < 0.001:
            return match.group(0)
        top = tile - desired
        control = desired * KCFG_ARC
        value = (
            f'd="m {groups["x"]},{groups["y"]} '
            f"h -{number(top, groups['top'])} "
            f"c -{number(control, groups['c1'])},0 "
            f"-{number(desired, groups['r'])},{number(desired - control, groups['c2y'])} "
            f"-{number(desired, groups['r'])},{number(desired, groups['r3'])} "
            f"v {number(top, groups['bottom'])} "
            f'h {groups["w"]} z"'
        )
        changes.append(f"corner radius {number(radius, groups['r'])} -> {number(desired, groups['r'])}")
        return value

    updated = CORNER_PATH.sub(replace, text)
    if changes:
        data = gzip.compress(updated.encode("utf-8"), mtime=0)
        write_bytes(path, data, dry_run, backups)
    if verbose and changes:
        print(f"{path}:")
        for item in changes:
            print(f"  {item}")
    return changes


def theme_files(root: Path) -> list[tuple[Path, float]]:
    names = [
        ("dialogs/background.svgz", 2.0),
        ("solid/dialogs/background.svgz", 2.0),
        ("widgets/tooltip.svgz", 2.0),
        ("solid/widgets/tooltip.svgz", 2.0),
        ("widgets/panel-background.svgz", 1.0),
        ("solid/widgets/panel-background.svgz", 1.0),
    ]
    return [(root / name, scale) for name, scale in names]


def collect_theme_roots(home: Path, dotfiles: Path, workspace: Path) -> list[Path]:
    roots = []
    for base in (
        home / ".local/share/plasma/desktoptheme",
        workspace / "MacTahoe-kde/plasma/desktoptheme",
        dotfiles / "desktop/plasma/desktoptheme",
    ):
        roots.extend([base / "MacTahoe-Light", base / "MacTahoe-Dark"])
    return roots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounded", type=int, required=True, help="outer corner radius in pixels")
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing")
    parser.add_argument("--no-backup", action="store_true", help="do not create backups")
    parser.add_argument("--no-theme", action="store_true", help="skip Plasma SVG theme files")
    parser.add_argument("--verbose", action="store_true", help="show every changed key")
    parser.add_argument("--home", type=Path, default=HOME, help=argparse.SUPPRESS)
    parser.add_argument("--dotfiles", type=Path, default=DOTFILES, help=argparse.SUPPRESS)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.rounded < 0:
        parser.error("--rounded must be zero or greater")

    target = args.rounded
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backups = None
    if not args.dry_run and not args.no_backup:
        backups = args.home / ".cache/radius-patch/backups" / timestamp

    kwin_paths = [
        args.home / ".config/kwinrc",
        args.dotfiles / "desktop/kwin/config/kwinrc",
    ]
    darkly_paths = [
        args.home / ".config/darklyrc",
        args.dotfiles / "desktop/decorations/darkly/darklyrc",
    ]
    klassy_paths = [
        args.home / ".config/klassy/klassyrc",
        args.dotfiles / "themes/light/klassy/klassyrc",
        args.dotfiles / "themes/dark/klassy/klassyrc",
    ]

    kwin_primary = [
        ("Round-Corners", "Size"),
        ("Round-Corners", "InactiveCornerRadius"),
        ("Effect-blurplus", "TopCornerRadius"),
        ("Effect-blurplus", "BottomCornerRadius"),
        ("Effect-blurplus", "MenuCornerRadius"),
        ("Effect-blurplus", "DockCornerRadius"),
        ("Effect-kwin4_effect_liquidglass", "Radius"),
    ]
    darkly_primary = [
        ("Common", "CornerRadius"),
        ("Windeco", "OtherCornerRadius"),
    ]
    klassy_primary = [
        ("Windeco", "WindowCornerRadius"),
    ]
    klassy_scaled = [
        ("ButtonSizing", "ButtonCustomCornerRadius"),
    ]

    changed: list[str] = []
    for path in kwin_paths:
        changed.extend(patch_ini(path, kwin_primary, [], target, args.dry_run, backups, args.verbose))
    for path in darkly_paths:
        values = parse_ini(path) if path.exists() else {}
        primary = list(darkly_primary)
        other = values.get(("Windeco", "OtherCornerRadius"))
        if other is not None:
            try:
                if float(other) < 0:
                    primary.remove(("Windeco", "OtherCornerRadius"))
            except ValueError:
                primary.remove(("Windeco", "OtherCornerRadius"))
        changed.extend(patch_ini(path, primary, [], target, args.dry_run, backups, args.verbose))
    for path in klassy_paths:
        values = parse_ini(path) if path.exists() else {}
        scaled = list(klassy_scaled) if values.get(("ButtonSizing", "ButtonCornerRadius")) == "Custom" else []
        changed.extend(patch_ini(path, klassy_primary, scaled, target, args.dry_run, backups, args.verbose))

    if not args.no_theme:
        for root in collect_theme_roots(args.home, args.dotfiles, args.workspace):
            for path, scale in theme_files(root):
                changed.extend(patch_svgz(path, target, scale, args.dry_run, backups, args.verbose))

    if not changed:
        print(f"Already at {target}px; nothing to change.")
        return 0

    prefix = "Would change" if args.dry_run else "Changed"
    print(f"{prefix} {len(changed)} value(s) to {target}px.")
    if backups is not None:
        print(f"Backups: {backups}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
