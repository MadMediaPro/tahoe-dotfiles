"""SVG defs management: frosted filter generation, glyph shading, and dangling ref cleanup."""

import re
from typing import Optional
from .color import ensure_luminance, hex_to_rgb
from .constants import (
    FROST_DEFS_DARK_SOLID,
    FROST_DEFS_FROSTED_DARK,
    FROST_DEFS_LIGHT,
    GLYPH_GRADIENT_STRENGTH,
    GLYPH_TONES,
)


def strip_dangling_uses(text: str) -> str:
    """Remove <use xlink:href="#..."> referencing non-existent element IDs."""
    ids = set(re.findall(r'\bid="([^"]+)"', text))

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        href = re.search(r'(?:xlink:)?href="#([^"]+)"', tag)
        if href and href.group(1) not in ids:
            return ""
        return tag

    return re.sub(r"<use\b[^>]*?/?>", repl, text)


def build_glyph_gradients(prefix: str) -> str:
    """Build multi-tone linear gradients with a soft shaded bottom for 3D glyphs."""
    parts = []
    for idx, tone in enumerate(GLYPH_TONES):
        top = min(255, tone + round(7 * GLYPH_GRADIENT_STRENGTH))
        lower = round(tone * (1 - 0.07 * GLYPH_GRADIENT_STRENGTH))
        bottom = round(tone * (1 - 0.16 * GLYPH_GRADIENT_STRENGTH))
        parts.append(
            f'<linearGradient id="{prefix}-g{idx}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#{top:02x}{top:02x}{top:02x}"/>'
            f'<stop offset=".35" stop-color="#{tone:02x}{tone:02x}{tone:02x}"/>'
            f'<stop offset=".70" stop-color="#{lower:02x}{lower:02x}{lower:02x}"/>'
            f'<stop offset="1" stop-color="#{bottom:02x}{bottom:02x}{bottom:02x}"/>'
            f'</linearGradient>'
        )
    return "".join(parts)


def apply_glyph_gradients(text: str, prefix: str) -> str:
    """Map bright fill and stroke colors to the corresponding glyph gradients."""

    def repl(match: re.Match) -> str:
        color = match.group(2)
        rgb = hex_to_rgb(color)
        if rgb is None:
            return match.group(0)
        tone = rgb[0]
        if tone < 92:
            return match.group(0)
        idx = min(range(len(GLYPH_TONES)), key=lambda i: abs(GLYPH_TONES[i] - tone))
        return f'{match.group(1)}="url(#{prefix}-g{idx})"'

    return re.sub(r'\b(fill|stroke)="(#[0-9a-fA-F]{3,6})"', repl, text)


def ensure_fill(text: str, prefix: str) -> str:
    """Ensure graphic elements without an explicit fill use the primary glyph gradient."""

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        if "fill=" in tag or "fill:" in tag:
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + f' fill="url(#{prefix}-g0)"/>'
        return tag[:-1] + f' fill="url(#{prefix}-g0)">'

    return re.sub(r"<(?:path|rect|circle|ellipse|polygon|polyline)\b[^>]*?/?>", repl, text)


def build_dark_glyph_gradient(prefix: str, top_color: str, bottom_color: str) -> str:
    """Generate linear gradient for coloring glyphs in dark frosted glass mode."""
    top = ensure_luminance(top_color)
    bottom = ensure_luminance(bottom_color)
    return (
        f'<linearGradient id="{prefix}-glyph" x1="0" y1="0" x2="0" y2="1">\n'
        f'<stop offset="0" stop-color="{top}"/>\n'
        f'<stop offset="1" stop-color="{bottom}"/>\n'
        f'</linearGradient>\n'
    )


def build_frost_defs(
    prefix: str,
    scale: float,
    blur: Optional[float] = None,
    mode: str = "light",
    dark_glyph_gradient: Optional[str] = None,
) -> str:
    """Render the full <defs> block with frosted blur filters and glyph gradients."""
    if blur is None:
        blur = max(0.22, 0.9 * scale)
    if mode in ("frosted-dark", "dark-frosted"):
        template = FROST_DEFS_FROSTED_DARK
    elif mode == "dark":
        template = FROST_DEFS_DARK_SOLID
    else:
        template = FROST_DEFS_LIGHT

    if mode == "dark":
        glyph_grads = dark_glyph_gradient or ""
    else:
        glyph_grads = build_glyph_gradients(prefix)
    return (
        template.replace("{p}", prefix)
        .replace("{gradients}", glyph_grads)
        .replace("{blur}", f"{blur:.2f}")
    )
