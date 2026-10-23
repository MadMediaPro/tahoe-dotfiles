#!/usr/bin/env python3
"""Frosted glass icon generator CLI for MacTahoe icon theme.

This script delegates to the modular 'frosticon' package.
"""

import sys
from pathlib import Path

# Ensure dotfiles directory is in python search path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from frosticon.cli import main
from frosticon.engine import FrostEngine, frost_svg
from frosticon.theme import ThemeGenerator, generate_theme


def generate(src, dest, mode="tint", cache=True):
    """Backwards-compatible wrapper for legacy callers."""
    stats = generate_theme(src, dest, mode=mode, cache=cache)
    return {"converted": stats.converted, "copied": stats.copied}


if __name__ == "__main__":
    main()
