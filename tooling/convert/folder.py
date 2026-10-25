"""Folder icon transformation for the places context."""

import re
from typing import Optional, Set, Tuple

from .color import hex_to_rgb, is_hex_vivid, recolor_svg
from .geometry import element_bbox

FOLDER_NAME_HINTS = ("folder", "user-home", "user-desktop")

FOLDER_BG_STOPS = {
    "light": (
        ("0", "#b8b8be", ".20"),
        (".52", "#96969c", ".25"),
        ("1", "#7e7e84", ".30"),
    ),
    "frosted-dark": (
        ("0", "#0ea5e9", "1"),
        ("1", "#0284c7", "1"),
    ),
    "dark": (
        ("0", "#0ea5e9", "1"),
        ("1", "#0284c7", "1"),
    ),
}

_ELEMENT_RE = r"<(?:path|rect|circle|ellipse|polygon|polyline)\b[^>]*?/?>"


def is_folder_icon(name: str) -> bool:
    """Return True for folder-like icon filenames in places/scalable."""
    lowered = name.lower()
    return any(hint in lowered for hint in FOLDER_NAME_HINTS)


def _parse_viewbox(text: str) -> Tuple[float, float, float, float]:
    match = re.search(r'viewBox="([^"]+)"', text)
    if match:
        parts = re.split(r"[\s,]+", match.group(1).strip())
        if len(parts) == 4:
            try:
                return tuple(float(part) for part in parts)  # type: ignore[return-value]
            except ValueError:
                pass

    width_match = re.search(r'\bwidth="([\d.]+)"', text)
    height_match = re.search(r'\bheight="([\d.]+)"', text)
    width = float(width_match.group(1)) if width_match else 64.0
    height = float(height_match.group(1)) if height_match else width
    return 0.0, 0.0, width, height


def _stop_info(tag: str) -> Tuple[Optional[str], float]:
    color_match = re.search(r'stop-color\s*[:=]\s*["\']?(#[0-9a-fA-F]{3,6})', tag)
    if not color_match:
        return None, 1.0
    opacity_match = re.search(r'stop-opacity\s*[:=]\s*["\']?([\d.]+)', tag)
    opacity = float(opacity_match.group(1)) if opacity_match else 1.0
    return color_match.group(1), opacity


def _gradient_is_accent(defs_text: str, gradient_id: str, seen: Optional[Set[str]] = None) -> bool:
    if seen is None:
        seen = set()
    if gradient_id in seen:
        return False
    seen.add(gradient_id)

    pattern = (
        rf'<(?:linear|radial)Gradient\b[^>]*\bid="{re.escape(gradient_id)}"'
        rf'[^>]*>(.*?)</(?:linear|radial)Gradient>'
    )
    match = re.search(pattern, defs_text, re.S)
    if not match:
        self_closing = re.search(
            rf'<(?:linear|radial)Gradient\b[^>]*\bid="{re.escape(gradient_id)}"[^>]*/>',
            defs_text,
        )
        if self_closing:
            href = re.search(r'(?:xlink:)?href="#([^"]+)"', self_closing.group(0))
            if href:
                return _gradient_is_accent(defs_text, href.group(1), seen)
        return False

    body = match.group(1)
    href = re.search(r'(?:xlink:)?href="#([^"]+)"', match.group(0))
    if href and not re.search(r"<stop\b", body):
        return _gradient_is_accent(defs_text, href.group(1), seen)

    for stop in re.findall(r"<stop\b[^>]*?/?>", body):
        color, opacity = _stop_info(stop)
        if color and opacity >= 0.8 and is_hex_vivid(color):
            return True
    return False


def _accent_gradient_ids(defs_text: str) -> Set[str]:
    ids = set(re.findall(r'<(?:linear|radial)Gradient\b[^>]*\bid="([^"]+)"', defs_text))
    return {gradient_id for gradient_id in ids if _gradient_is_accent(defs_text, gradient_id)}


def _sub_outside_defs(pattern: str, repl, text: str) -> str:
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs\b[^>]*>.*?</defs>", text, re.S)]

    def in_defs(pos: int) -> bool:
        return any(start <= pos < end for start, end in defs)

    parts = []
    last = 0
    for match in re.finditer(pattern, text, re.S):
        if in_defs(match.start()):
            continue
        parts.append(text[last:match.start()])
        parts.append(repl(match))
        last = match.end()
    parts.append(text[last:])
    return "".join(parts)


def _is_symbol_element(
    tag: str,
    bbox: Tuple[float, float, float, float],
    view_width: float,
    view_height: float,
    folder_gradient_ref: str,
) -> bool:
    fill = _fill_value(tag).lower()
    if fill in ("none", folder_gradient_ref.lower()):
        return False

    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if width >= 0.55 * view_width and height >= 0.35 * view_height:
        return False

    if width >= 0.55 * view_width and height <= 0.2 * view_height:
        return False

    if (
        height <= 0.18 * view_height
        and width >= 0.5 * view_width
        and _is_low_contrast_fill(tag)
    ):
        opacity_match = re.search(r'\bopacity="([\d.]+)"', tag)
        opacity = float(opacity_match.group(1)) if opacity_match else 1.0
        if opacity <= 0.3:
            return False
    return True


def _recolor_symbol(tag: str, mode: str) -> str:
    fill = _fill_value(tag)
    if mode == "dark":
        if fill.lower().startswith("url(") or (
            fill.startswith("#") and is_hex_vivid(fill)
        ):
            return _ensure_opacity(tag, 0.75)
        return _ensure_opacity(_replace_fill(tag, "#ffffff"), 0.75)

    if mode in ("frosted-dark", "dark-frosted"):
        return _ensure_opacity(_replace_fill(tag, "#ffffff"), 0.75)

    return _ensure_opacity(_replace_fill(tag, "#2f2f31"), 0.65)


def _is_folder_base_fill(tag: str, accent_gradients: Set[str]) -> bool:
    fill_match = re.search(r'\bfill="([^"]+)"', tag)
    fill = fill_match.group(1) if fill_match else ""

    if fill.startswith("url(#"):
        return fill[5:-1] in accent_gradients
    if fill == "currentColor":
        return True
    if fill.startswith("#") and is_hex_vivid(fill):
        return True
    if "ColorScheme-Highlight" in tag and not fill:
        return True
    if re.search(r"\bfill:currentColor\b", tag):
        return True
    return False


def _fill_value(tag: str) -> str:
    style_match = re.search(r"\bfill\s*:\s*([^;\"]+)", tag)
    if style_match:
        return style_match.group(1).strip()
    fill_match = re.search(r'\bfill="([^"]+)"', tag)
    return fill_match.group(1) if fill_match else ""


def _is_white_fill(tag: str) -> bool:
    fill = _fill_value(tag).lower()
    return fill in ("#fff", "#ffffff", "white")


def _is_low_contrast_fill(tag: str) -> bool:
    fill = _fill_value(tag).lower()
    if fill in ("", "currentcolor", "none"):
        return True
    if fill in ("#000", "#000000", "black", "#fff", "#ffffff", "white"):
        return True
    rgb = hex_to_rgb(fill) if fill.startswith("#") else None
    if rgb is None:
        return False
    r, g, b = (value / 255.0 for value in rgb)
    return max(r, g, b) - min(r, g, b) <= 0.06


def _ensure_opacity(tag: str, target: float) -> str:
    match = re.search(r'\bopacity="([\d.]+)"', tag)
    if match:
        if float(match.group(1)) >= target:
            return tag
        return tag[: match.start(1)] + f"{target:g}" + tag[match.end(1):]
    if tag.endswith("/>"):
        return tag[:-2] + f' opacity="{target:g}"/>'
    return tag[:-1] + f' opacity="{target:g}">'


def _replace_fill(tag: str, gradient_ref: str) -> str:
    replaced = False
    if re.search(r'\bfill="[^"]*"', tag):
        tag = re.sub(r'\bfill="[^"]*"', f'fill="{gradient_ref}"', tag)
        replaced = True
    if re.search(r"\bfill\s*:\s*[^;\"]+", tag):
        tag = re.sub(r"\bfill\s*:\s*[^;\"]+", f"fill:{gradient_ref}", tag)
        replaced = True
    if replaced:
        return tag
    if tag.endswith("/>"):
        return tag[:-2] + f' fill="{gradient_ref}"/>'
    return tag[:-1] + f' fill="{gradient_ref}">'


def _build_folder_gradient(
    prefix: str,
    mode: str,
    viewbox: Tuple[float, float, float, float],
) -> str:
    min_x, min_y, width, height = viewbox
    stops = FOLDER_BG_STOPS.get(mode, FOLDER_BG_STOPS["light"])
    stop_tags = "".join(
        f'<stop offset="{offset}" stop-color="{color}" stop-opacity="{opacity}"/>'
        for offset, color, opacity in stops
    )
    x = min_x + width / 2
    return (
        f'<linearGradient id="{prefix}-folder-bg" x1="{x:.3f}" y1="{min_y:.3f}" '
        f'x2="{x:.3f}" y2="{min_y + height:.3f}" gradientUnits="userSpaceOnUse">'
        f"{stop_tags}</linearGradient>"
    )


def _add_gradient(text: str, gradient: str) -> str:
    defs_match = re.search(r"<defs\b[^>]*>", text)
    if defs_match:
        return text[:defs_match.end()] + gradient + text[defs_match.end():]

    svg_match = re.search(r"<svg\b[^>]*>", text)
    if svg_match:
        return text[:svg_match.end()] + f"<defs>{gradient}</defs>" + text[svg_match.end():]
    return text


def transform_folder_svg(
    text: str,
    mode: str = "light",
    base_prefix: str = "mtf",
) -> Optional[str]:
    """Recolor the folder body while keeping the themed overlay glyphs intact."""
    if "<svg" not in text:
        return None

    viewbox = _parse_viewbox(text)
    _, _, view_width, view_height = viewbox
    if view_width <= 0 or view_height <= 0:
        return None

    defs_match = re.search(r"<defs\b[^>]*>(.*?)</defs>", text, re.S)
    defs_text = defs_match.group(1) if defs_match else ""
    accent_gradients = _accent_gradient_ids(defs_text)

    prefix = base_prefix
    while f'id="{prefix}-folder-bg"' in text:
        prefix += "x"
    gradient_ref = f"url(#{prefix}-folder-bg)"

    changed = False

    def replace_base(match: re.Match) -> str:
        nonlocal changed
        tag = match.group(0)
        bbox = element_bbox(tag)
        if bbox is None:
            return tag
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width < 0.55 * view_width or height < 0.35 * view_height:
            return tag
        if not _is_folder_base_fill(tag, accent_gradients):
            return tag
        changed = True
        return _replace_fill(tag, gradient_ref)

    text = _sub_outside_defs(_ELEMENT_RE, replace_base, text)
    if not changed:
        return None

    if mode in ("light", "clear", "frosted-dark", "dark-frosted"):
        def remove_white_base(match: re.Match) -> str:
            tag = match.group(0)
            if not tag.startswith("<rect") or not _is_white_fill(tag):
                return tag
            bbox = element_bbox(tag)
            if bbox is None:
                return tag
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width >= 0.55 * view_width and height >= 0.35 * view_height:
                return ""
            return tag

        text = _sub_outside_defs(_ELEMENT_RE, remove_white_base, text)
        text = recolor_svg(text)

    def recolor_symbol(match: re.Match) -> str:
        tag = match.group(0)
        bbox = element_bbox(tag)
        if bbox is None:
            return tag
        if not _is_symbol_element(tag, bbox, view_width, view_height, gradient_ref):
            return tag
        return _recolor_symbol(tag, mode)

    text = _sub_outside_defs(_ELEMENT_RE, recolor_symbol, text)

    gradient = _build_folder_gradient(prefix, mode, viewbox)
    return _add_gradient(text, gradient)
