"""SVG defs management: frosted filter generation, glyph shading, and dangling ref cleanup."""

import re
from typing import Optional
from .color import hex_to_rgb
from .constants import FROST_DEFS, GLYPH_TONES


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
    """Build multi-tone linear gradients for 3D metallic/etched glyph rendering."""
    parts = []
    for idx, tone in enumerate(GLYPH_TONES):
        top = min(255, tone + 7)
        bottom = max(0, tone - 9)
        parts.append(
            f'<linearGradient id="{prefix}-g{idx}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#{top:02x}{top:02x}{top:02x}"/>'
            f'<stop offset=".5" stop-color="#{tone:02x}{tone:02x}{tone:02x}"/>'
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


def build_frost_defs(prefix: str, scale: float, blur: Optional[float] = None) -> str:
    """Render the full <defs> block with frosted blur filters and glyph gradients."""
    if blur is None:
        blur = max(0.22, 0.9 * scale)
    return (
        FROST_DEFS.replace("{p}", prefix)
        .replace("{gradients}", build_glyph_gradients(prefix))
        .replace("{blur}", f"{blur:.2f}")
    )
