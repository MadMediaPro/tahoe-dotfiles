"""Detection, overlay generation, and manipulation of squircle icon base tiles."""

import re
from typing import Callable, Optional
from .color import hex_to_rgb
from .constants import PATH_TILE, TILE_PATTERNS
from .geometry import compute_iou, element_bbox, path_bbox


def sub_outside_defs(
    pattern: str,
    repl: Callable[[re.Match], str],
    text: str,
    flags: int = 0,
) -> str:
    """Perform regex replacement strictly outside SVG <defs>...</defs> blocks."""
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(pos: int) -> bool:
        return any(start <= pos < end for start, end in defs)

    parts = []
    last = 0
    for match in re.finditer(pattern, text, flags):
        if in_defs(match.start()):
            continue
        parts.append(text[last:match.start()])
        parts.append(repl(match))
        last = match.end()
    parts.append(text[last:])
    return "".join(parts)


def find_tile(text: str) -> Optional[str]:
    """Find the main squircle/tile background element in the SVG."""
    # Mask defs so we only search renderable elements
    masked = re.sub(r"<defs>.*?</defs>", lambda m: " " * len(m.group(0)), text, flags=re.S)

    for pattern in TILE_PATTERNS:
        match = pattern.search(masked)
        if match:
            return text[match.start():match.end()]

    match = PATH_TILE.search(masked)
    if match:
        return text[match.start():match.end()]

    # Heuristic fallback: a rect or path covering ~78%-102% of the SVG dimensions with rounded corners
    vw = vh = None
    viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', text)
    if viewbox:
        vw, vh = float(viewbox.group(1)), float(viewbox.group(2))
    else:
        wm = re.search(r'<svg\b[^>]*\bwidth="([\d.]+)"', text)
        hm = re.search(r'<svg\b[^>]*\bheight="([\d.]+)"', text)
        if wm and hm:
            vw, vh = float(wm.group(1)), float(hm.group(1))

    if vw and vh:
        for match in re.finditer(r"<rect\b[^>]*?/?>", masked):
            tag = text[match.start():match.end()]
            if "transform=" in tag or "filter=" in tag or 'fill="none"' in tag:
                continue
            values = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tag))
            w = float(values.get("width", 0))
            h = float(values.get("height", 0))
            rx = float(values.get("rx", values.get("ry", 0)))
            if 0.78 <= w / vw <= 1.02 and 0.78 <= h / vh <= 1.02 and w and (rx == 0 or 0.12 <= rx / w <= 0.35):
                return tag

        for match in re.finditer(r"<path\b[^>]*?/?>", masked):
            tag = text[match.start():match.end()]
            if "transform=" in tag or "filter=" in tag or 'fill="none"' in tag:
                continue
            d_m = re.search(r'\bd="([^"]+)"', tag)
            if not d_m:
                continue
            d = d_m.group(1)
            if ("A" in d or "a" in d or "C" in d or "c" in d) and ("H" in d or "h" in d or "V" in d or "v" in d):
                bbox = path_bbox(d)
                if bbox:
                    pw = bbox[2] - bbox[0]
                    ph = bbox[3] - bbox[1]
                    if 0.78 <= pw / vw <= 1.02 and 0.78 <= ph / vh <= 1.02:
                        return tag

    return None


def tile_scale_for(tile: str, viewbox_width: float) -> float:
    """Calculate the scale factor of the tile relative to the viewBox width."""
    bbox = element_bbox(tile)
    if not bbox:
        return 1.0
    return viewbox_width / 64.0 if bbox[2] - bbox[0] > 32 else 1.0


def generate_tile_overlay(tile: str, prefix: str, scale: float) -> str:
    """Generate the frosted glass rim, specular sheen, and inner bottom shade overlays."""

    def q(val: float) -> str:
        return f"{val * scale:.3f}".rstrip("0").rstrip(".")

    def c(val: float) -> str:
        return f"{val:.3f}".rstrip("0").rstrip(".")

    if tile.startswith("<rect"):
        attrs = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tile))
        x = float(attrs.get("x", 0))
        y = float(attrs.get("y", 0))
        w = float(attrs.get("width", 56))
        h = float(attrs.get("height", 56))
        rx = float(attrs.get("rx", attrs.get("ry", 13)))

        inset = 0.35 * (scale if scale < 1.0 else 1.0)
        stroke_w = c(max(0.35, 0.7 * scale if scale < 1.0 else 0.7))
        rim = (
            f'<rect x="{c(x + inset)}" y="{c(y + inset)}" width="{c(w - 2 * inset)}" '
            f'height="{c(h - 2 * inset)}" rx="{c(max(rx - inset, 0))}" fill="none" '
            f'stroke="url(#{prefix}-rim)" stroke-width="{stroke_w}"/>'
        )
        shade = (
            f'<rect x="{c(x)}" y="{c(y)}" width="{c(w)}" height="{c(h)}" '
            f'rx="{c(rx)}" fill="url(#{prefix}-shade)"/>'
        )
    else:
        rim = (
            f'<rect x="{q(4.35)}" y="{q(4.35)}" width="{q(55.3)}" height="{q(55.3)}" '
            f'rx="{q(12.7)}" fill="none" stroke="url(#{prefix}-rim)" '
            f'stroke-width="{q(0.7 * scale)}"/>'
        )
        shade = (
            f'<rect x="{q(4.6)}" y="{q(4.6)}" width="{q(54.8)}" height="{q(54.8)}" '
            f'rx="{q(12.4)}" fill="url(#{prefix}-shade)"/>'
        )

    sheen = (
        f'<path d="M{q(17)} {q(4.6)}h{q(30)}c{q(6.9)} 0 {q(12.4)} {q(5.5)} {q(12.4)} {q(12.4)}'
        f'v{q(9.5)}C{q(48)} {q(15.9)} {q(40.4)} {q(8.3)} {q(29.9)} {q(6.9)} '
        f'{q(23.3)} {q(6)} {q(18.5)} {q(5.1)} {q(17)} {q(4.6)}z" '
        f'fill="url(#{prefix}-sheen)" filter="url(#{prefix}-blur)"/>'
    )

    return rim + sheen + shade


def remove_extra_path_tiles(text: str, tile: str) -> str:
    """Remove redundant duplicate path tiles outside defs."""
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(pos: int) -> bool:
        return any(start <= pos < end for start, end in defs)

    parts = []
    last = 0
    seen_tile = False
    for match in PATH_TILE.finditer(text):
        if in_defs(match.start()):
            continue
        if match.group(0) == tile and not seen_tile:
            seen_tile = True
            continue
        parts.append(text[last:match.start()])
        last = match.end()
    parts.append(text[last:])
    return "".join(parts)


def replace_tile(text: str, tile: str, new_tile: str) -> str:
    """Replace the first instance of a tile outside defs."""
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(pos: int) -> bool:
        return any(start <= pos < end for start, end in defs)

    idx = text.find(tile)
    while idx != -1 and in_defs(idx):
        idx = text.find(tile, idx + 1)
    if idx == -1:
        return text
    return text[:idx] + new_tile + text[idx + len(tile):]


def strip_tile_duplicates(text: str, tile: str, gradient_only: bool = False) -> str:
    """Remove duplicate background paths that overlap with the tile by >= 80% IoU."""
    tile_bbox = element_bbox(tile)
    if not tile_bbox:
        return text

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        if tag == tile or "mtf-" in tag or 'fill="none"' in tag:
            return tag
        if "clip-path" in tag or "mask=" in tag:
            return tag
        fill = re.search(r'\bfill="([^"]+)"', tag)
        if not fill:
            return tag
        if gradient_only and not fill.group(1).startswith("url(#"):
            return tag
        bbox = element_bbox(tag)
        if not bbox:
            return tag

        iou = compute_iou(tile_bbox, bbox)
        if iou >= 0.80:
            return ""
        return tag

    return sub_outside_defs(r"<path\b[^>]*?/>", repl, text)


def strip_dark_backgrounds(text: str, tile: str, tile_scale: float = 1.0) -> str:
    """Remove dark solid or gradient background cards behind the glyphs."""
    if not tile.startswith("<rect"):
        return text

    attrs = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tile))
    tx = float(attrs.get("x", 0)) * tile_scale
    ty = float(attrs.get("y", 0)) * tile_scale
    tw = float(attrs.get("width", 56)) * tile_scale
    th = float(attrs.get("height", 56)) * tile_scale
    tcx, tcy = tx + tw / 2.0, ty + th / 2.0

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        if "mtf-bg" in tag or 'fill="none"' in tag:
            return tag
        values = dict(re.findall(r'\b(x|y|width|height)="([\d.]+)"', tag))
        if not all(k in values for k in ("x", "y", "width", "height")):
            return tag
        x, y, w, h = (float(values[k]) for k in ("x", "y", "width", "height"))
        if w < 0.6 * tw or h < 0.6 * th:
            return tag
        if abs((x + w / 2.0) - tcx) > 0.05 * tw or abs((y + h / 2.0) - tcy) > 0.05 * th:
            return tag

        fill = re.search(r'(?:fill=|fill:)\s*["\']?(#[0-9a-fA-F]{3,6})', tag)
        if not fill:
            return ""

        rgb = hex_to_rgb(fill.group(1))
        if rgb is None:
            return tag
        r, g, b = (v / 255.0 for v in rgb)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if lum < 0.42:
            return ""
        return tag

    return sub_outside_defs(r"<rect\b[^>]*?/?>", repl, text)
