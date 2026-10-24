"""Theme generator for building complete frosted icon themes from upstream directories."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union
from .battery import is_battery_charging_icon, transform_battery_svg
from .engine import FrostEngine
from .overrides import IconOverrides


# Context categories eligible for frosted glass transformation
FROST_ELIGIBLE_CONTEXTS = {"apps", "preferences", "categories"}

# Context categories strictly excluded (system tray status indicators, toolbar buttons)
FROST_EXCLUDED_CONTEXTS = {"status", "actions"}


@dataclass
class ThemeStats:
    """Statistics for theme generation."""

    converted: int = 0
    copied: int = 0
    overridden: int = 0
    failed: int = 0


class ThemeGenerator:
    """Manages the full build lifecycle of a frosted icon theme."""

    def __init__(
        self,
        src: Union[str, Path],
        dest: Union[str, Path],
        mode: str = "light",
        cache: bool = True,
        use_overrides: bool = True,
    ):
        self.src = Path(src)
        self.dest = Path(dest)
        self.mode = mode
        self.cache = cache
        self.use_overrides = use_overrides
        self.engine = FrostEngine(mode=mode)

    def generate(
        self,
        progress_cb: Optional[Callable[[str, str], None]] = None,
    ) -> ThemeStats:
        """Run the theme generation process and return statistics."""
        if not self.src.is_dir():
            raise FileNotFoundError(f"Source icon theme directory not found: {self.src}")
        if self.src.resolve() == self.dest.resolve():
            raise ValueError("Source and destination theme paths must differ")

        if self.dest.is_symlink():
            self.dest.unlink()
        elif self.dest.is_dir():
            shutil.rmtree(self.dest)
        elif self.dest.exists():
            self.dest.unlink()
        self.dest.mkdir(parents=True)

        stats = ThemeStats()

        def walk(current_src: Path, current_dest: Path) -> None:
            for entry in os.scandir(current_src):
                source = Path(entry.path)
                target = current_dest / entry.name

                if entry.is_symlink():
                    raw_target = os.readlink(source)
                    resolved = source.resolve()
                    if entry.is_dir():
                        try:
                            is_external = not resolved.is_relative_to(self.src.resolve())
                        except ValueError:
                            is_external = True
                        if is_external:
                            target.mkdir(exist_ok=True)
                            walk(resolved, target)
                            continue
                    os.symlink(raw_target, target)
                    continue

                if entry.is_dir(follow_symlinks=False):
                    target.mkdir()
                    walk(source, target)
                    continue

                if entry.name == "icon-theme.cache":
                    continue

                try:
                    rel_parts = source.relative_to(self.src).parts
                except ValueError:
                    rel_parts = target.relative_to(self.dest).parts
                context = rel_parts[0] if rel_parts else ""

                # Battery charging status icons: customize with Apple green inside and white bolt
                if is_battery_charging_icon(source) and source.suffix.lower() == ".svg":
                    try:
                        text = source.read_text(encoding="utf-8", errors="replace")
                        is_dark = self.mode in ("dark", "frosted-dark")
                        converted = transform_battery_svg(text, dark_mode=is_dark)
                        target.write_text(converted, encoding="utf-8")
                        stats.converted += 1
                        if progress_cb:
                            progress_cb(str(source), "battery-charging")
                        continue
                    except Exception:
                        pass

                # Explicitly skip excluded categories (system tray status indicators, action buttons) or any symbolic icon
                if context in FROST_EXCLUDED_CONTEXTS or "symbolic" in source.name.lower():
                    shutil.copy2(source, target)
                    stats.copied += 1
                    if progress_cb:
                        progress_cb(str(source), "copied")
                    continue

                # 1. Check for custom icon overrides (e.g. Finder / file-manager.svg)
                if self.use_overrides:
                    override_content = IconOverrides.get_override_content(source, self.mode)
                    if override_content is not None:
                        target.write_text(override_content, encoding="utf-8")
                        stats.overridden += 1
                        stats.converted += 1
                        if progress_cb:
                            progress_cb(str(source), "overridden")
                        continue

                # 2. Process SVG icons through the frost engine
                if source.suffix.lower() == ".svg":
                    try:
                        text = source.read_text(encoding="utf-8", errors="replace")
                        is_app_scalable = (
                            context == "apps"
                            and "scalable" in rel_parts
                            and "symbolic" not in source.name.lower()
                        )
                        converted = self.engine.transform(
                            text,
                            fallback=is_app_scalable,
                            icon_name=source.stem,
                        )
                    except Exception:
                        converted = None
                        stats.failed += 1

                    if converted is not None:
                        target.write_text(converted, encoding="utf-8")
                        stats.converted += 1
                        if progress_cb:
                            progress_cb(str(source), "converted")
                        continue

                # 3. Default copy for non-convertible files
                shutil.copy2(source, target)
                stats.copied += 1
                if progress_cb:
                    progress_cb(str(source), "copied")

        walk(self.src, self.dest)

        # Update index.theme metadata
        index = self.dest / "index.theme"
        if index.exists():
            content = index.read_text(encoding="utf-8")
            content = re.sub(r"(?m)^Name=.*$", f"Name={self.dest.name}", content)
            if self.mode == "dark":
                variant_desc = "dark"
            elif self.mode in ("frosted-dark", "dark-frosted"):
                variant_desc = "frosted dark"
            else:
                variant_desc = "frosted light"
            content = re.sub(
                r"(?m)^Comment=.*$",
                f"Comment=macOS Tahoe {variant_desc} icon theme for Linux.",
                content,
            )
            index.write_text(content, encoding="utf-8")

        # Refresh GTK icon cache if requested
        if self.cache and shutil.which("gtk-update-icon-cache"):
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(self.dest)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        return stats


def generate_theme(
    src: Union[str, Path],
    dest: Union[str, Path],
    mode: str = "light",
    cache: bool = True,
    use_overrides: bool = True,
) -> ThemeStats:
    """Convenience helper to generate a frosted icon theme."""
    generator = ThemeGenerator(
        src=src,
        dest=dest,
        mode=mode,
        cache=cache,
        use_overrides=use_overrides,
    )
    return generator.generate()
