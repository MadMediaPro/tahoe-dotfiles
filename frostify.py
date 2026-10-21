#!/usr/bin/env python3
"""Generate frosted-glass variants of the MacTahoe icon theme."""

import argparse
import colorsys
import os
import re
import shutil
import subprocess
from pathlib import Path

TILE_PATTERNS = [
    re.compile(
        r'<rect\b(?![^>]*\btransform=)(?![^>]*\bfilter[:=])'
        r'(?=[^>]*\bwidth="5[4-6](?:\.\d+)?")(?=[^>]*\bheight="5[1-6](?:\.\d+)?")'
        r'(?=[^>]*\b(?:rx|ry)="1[2-4](?:\.\d+)?")[^>]*?/?>'
    ),
    re.compile(
        r'<rect\b(?![^>]*\btransform=)(?=[^>]*\bwidth="14\.8\d*")'
        r'(?=[^>]*\bheight="14\.8\d*")(?=[^>]*\bfill="url\(#)[^>]*?/?>'
    ),
    re.compile(
        r'<path\b(?=[^>]*\bfill="url\(#[\w-]+\)")'
        r'(?=[^>]*\bd="(?:M20\.26 4|M5\.36 1\.058|M4\.498 1\.05|M17\.0\d+ [34]|M62\.44 64H1\.56))'
        r'[^>]*?/>'
    ),
    re.compile(
        r'<path\b(?=[^>]*\bd="[mM]5\.36(?:04|03) 1\.058)'
        r'[^>]*?/>'
    ),
]

NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "orange": (255, 165, 0), "purple": (128, 0, 128), "gray": (128, 128, 128),
    "grey": (128, 128, 128), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "brown": (165, 42, 42), "pink": (255, 192, 203), "lime": (0, 255, 0),
    "navy": (0, 0, 128), "teal": (0, 128, 128), "maroon": (128, 0, 0),
    "olive": (128, 128, 0), "silver": (192, 192, 192), "gold": (255, 215, 0),
}

PATH_TILE = re.compile(
    r'<path\b'
    r'(?=[^>]*\bd="[Mm](?:17|47|16\.9|5\.36|4\.498|20\.26|62\.44))'
    r'(?=[^>]*\bd="[^"]*(?:13\.002|12\.973|12\.974|9\.822|h29\.996|3\.999|h30|12\.9))'
    r'[^>]*?/?>'
)

FROST_DEFS = '''<linearGradient id="{p}-bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#b8b8be" stop-opacity=".20"/>
<stop offset=".52" stop-color="#96969c" stop-opacity=".25"/>
<stop offset="1" stop-color="#7e7e84" stop-opacity=".30"/>
</linearGradient>
<linearGradient id="{p}-rim" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#ffffff" stop-opacity=".75"/>
<stop offset=".45" stop-color="#ffffff" stop-opacity=".18"/>
<stop offset="1" stop-color="#ffffff" stop-opacity=".04"/>
</linearGradient>
<linearGradient id="{p}-sheen" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#ffffff" stop-opacity=".20"/>
<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
</linearGradient>
<linearGradient id="{p}-shade" x1="0" y1="0" x2="0" y2="1">
<stop offset=".55" stop-color="#000000" stop-opacity="0"/>
<stop offset="1" stop-color="#000000" stop-opacity=".10"/>
</linearGradient>
<filter id="{p}-blur" x="-25%" y="-25%" width="150%" height="150%">
<feGaussianBlur stdDeviation="{blur}"/>
</filter>
{gradients}'''

GLYPH_TONES = (255, 244, 232, 218, 205, 194)


def hex_to_rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def recolor(body):
    visible = re.sub(r"<defs>.*?</defs>", "", body, flags=re.S)
    dark = light = 0
    for value in re.findall(r"#[0-9a-fA-F]{3,6}\b", visible):
        rgb = hex_to_rgb(value)
        if rgb is None:
            continue
        r, g, b = (v / 255 for v in rgb)
        _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
        if saturation <= 0.12:
            if lightness < 0.35:
                dark += 1
            elif lightness > 0.75:
                light += 1
    invert_dark = dark > 0 and dark > light

    def lighten(r, g, b):
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        tone = 176 + round(min(1.0, max(0.0, (lum - 0.20) / 0.80)) * 79)
        return f"#{tone:02x}{tone:02x}{tone:02x}"

    def named_repl(match):
        attr, name = match.group(1), match.group(2)
        r, g, b = (value / 255 for value in NAMED_COLORS[name])
        return f'{attr}="{lighten(r, g, b)}"'

    body = re.sub(
        r'(stop-color|fill|stroke)="(' + "|".join(NAMED_COLORS) + r')"',
        named_repl,
        body,
    )

    def repl(match):
        value = match.group(0)
        rgb = hex_to_rgb(value)
        if rgb is None:
            return value
        r, g, b = (v / 255 for v in rgb)
        _, _, saturation = colorsys.rgb_to_hls(r, g, b)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        context = body[max(0, match.start() - 24):match.start()]
        if "stop-color=\"" in context or "stop-color:" in context:
            return lighten(r, g, b)
        if saturation <= 0.20 and lum < 0.35 and not invert_dark:
            return value
        return lighten(r, g, b)

    return re.sub(r"#[0-9a-fA-F]{3,6}\b", repl, body)


def tile_overlay(tile, prefix, scale):
    def q(value):
        return f"{value * scale:.3f}".rstrip("0").rstrip(".")

    if tile.startswith("<rect"):
        attrs = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tile))
        x = float(attrs.get("x", 0))
        y = float(attrs.get("y", 0))
        w = float(attrs.get("width", 56))
        h = float(attrs.get("height", 56))
        rx = float(attrs.get("rx", attrs.get("ry", 13)))

        def c(value):
            return f"{value:.3f}".rstrip("0").rstrip(".")

        inset = 0.35
        rim = (
            f'<rect x="{c(x + inset)}" y="{c(y + inset)}" width="{c(w - 2 * inset)}" '
            f'height="{c(h - 2 * inset)}" rx="{c(max(rx - inset, 0))}" fill="none" '
            f'stroke="url(#{prefix}-rim)" stroke-width="{c(0.7 * scale if scale < 1 else 0.7)}"/>'
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


def strip_dangling_uses(text):
    ids = set(re.findall(r'\bid="([^"]+)"', text))

    def repl(match):
        tag = match.group(0)
        href = re.search(r'(?:xlink:)?href="#([^"]+)"', tag)
        if href and href.group(1) not in ids:
            return ""
        return tag

    return re.sub(r"<use\b[^>]*?/?>", repl, text)


def remove_extra_path_tiles(text, tile):
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(position):
        return any(start <= position < end for start, end in defs)

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


def replace_tile(text, tile, new_tile):
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(position):
        return any(start <= position < end for start, end in defs)

    index = text.find(tile)
    while index != -1 and in_defs(index):
        index = text.find(tile, index + 1)
    if index == -1:
        return text
    return text[:index] + new_tile + text[index + len(tile):]


def sub_outside_defs(pattern, repl, text, flags=0):
    defs = [(m.start(), m.end()) for m in re.finditer(r"<defs>.*?</defs>", text, re.S)]

    def in_defs(position):
        return any(start <= position < end for start, end in defs)

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


PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def path_bbox(d):
    tokens = PATH_TOKEN.findall(d)
    index = 0
    command = None
    x = y = start_x = start_y = 0.0
    points = []

    def number():
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        token = tokens[index]
        if token in "MmLlHhVvCcSsQqTtAaZz":
            command = token
            index += 1
            if command in "Zz":
                x, y = start_x, start_y
                points.append((x, y))
                command = None
            continue
        if command is None:
            index += 1
            continue
        upper = command.upper()
        relative = command.islower()
        try:
            if upper == "M":
                nx, ny = number(), number()
                x, y = (x + nx, y + ny) if relative else (nx, ny)
                start_x, start_y = x, y
                points.append((x, y))
                command = "l" if relative else "L"
            elif upper == "L":
                nx, ny = number(), number()
                x, y = (x + nx, y + ny) if relative else (nx, ny)
                points.append((x, y))
            elif upper == "H":
                nx = number()
                x = x + nx if relative else nx
                points.append((x, y))
            elif upper == "V":
                ny = number()
                y = y + ny if relative else ny
                points.append((x, y))
            elif upper == "C":
                x1, y1, x2, y2, nx, ny = [number() for _ in range(6)]
                if relative:
                    x1, y1, x2, y2, nx, ny = x1 + x, y1 + y, x2 + x, y2 + y, nx + x, ny + y
                points.extend(((x1, y1), (x2, y2), (nx, ny)))
                x, y = nx, ny
            elif upper == "S":
                x2, y2, nx, ny = [number() for _ in range(4)]
                if relative:
                    x2, y2, nx, ny = x2 + x, y2 + y, nx + x, ny + y
                points.extend(((x2, y2), (nx, ny)))
                x, y = nx, ny
            elif upper == "Q":
                x1, y1, nx, ny = [number() for _ in range(4)]
                if relative:
                    x1, y1, nx, ny = x1 + x, y1 + y, nx + x, ny + y
                points.extend(((x1, y1), (nx, ny)))
                x, y = nx, ny
            elif upper == "T":
                nx, ny = number(), number()
                x, y = (x + nx, y + ny) if relative else (nx, ny)
                points.append((x, y))
            elif upper == "A":
                values = [number() for _ in range(7)]
                nx, ny = values[-2], values[-1]
                x, y = (x + nx, y + ny) if relative else (nx, ny)
                points.append((x, y))
            else:
                index += 1
        except IndexError:
            break
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def transform_bbox(bbox, transform):
    if not transform:
        return bbox
    x0, y0, x1, y1 = bbox
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    matrix = re.search(r"matrix\(\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)\s*\)", transform)
    if matrix:
        a, b, c, d, e, f = (float(value) for value in matrix.groups())
        transformed = [(a * x + c * y + e, b * x + d * y + f) for x, y in corners]
        xs = [point[0] for point in transformed]
        ys = [point[1] for point in transformed]
        return min(xs), min(ys), max(xs), max(ys)
    scale = re.search(r"scale\(\s*([-\d.]+)(?:[ ,]+([-\d.]+))?\s*\)", transform)
    if scale:
        sx = float(scale.group(1))
        sy = float(scale.group(2) or sx)
        return x0 * sx, y0 * sy, x1 * sx, y1 * sy
    translate = re.search(r"translate\(\s*([-\d.]+)(?:[ ,]+([-\d.]+))?\s*\)", transform)
    if translate:
        tx = float(translate.group(1))
        ty = float(translate.group(2) or 0)
        return x0 + tx, y0 + ty, x1 + tx, y1 + ty
    return None


def element_bbox(tag):
    transform = re.search(r'\btransform="([^"]+)"', tag)
    transform = transform.group(1) if transform else None
    if tag.startswith("<rect"):
        values = dict(re.findall(r'\b(x|y|width|height)="([\d.]+)"', tag))
        x = float(values.get("x", 0))
        y = float(values.get("y", 0))
        w = float(values.get("width", 0))
        h = float(values.get("height", 0))
        bbox = (x, y, x + w, y + h)
    else:
        d = re.search(r'\bd="([^"]+)"', tag)
        if not d:
            return None
        bbox = path_bbox(d.group(1))
    if bbox is None:
        return None
    return transform_bbox(bbox, transform)


def strip_tile_duplicates(text, tile, gradient_only=False):
    tile_bbox = element_bbox(tile)
    if not tile_bbox:
        return text
    tx0, ty0, tx1, ty1 = tile_bbox

    def repl(match):
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
        x0, y0, x1, y1 = bbox
        ix0, iy0 = max(tx0, x0), max(ty0, y0)
        ix1, iy1 = min(tx1, x1), min(ty1, y1)
        if ix1 <= ix0 or iy1 <= iy0:
            return tag
        intersection = (ix1 - ix0) * (iy1 - iy0)
        union = (tx1 - tx0) * (ty1 - ty0) + (x1 - x0) * (y1 - y0) - intersection
        if union and intersection / union >= 0.80:
            return ""
        return tag

    return sub_outside_defs(r"<path\b[^>]*?/>", repl, text)


def tile_scale_for(tile, viewbox_width):
    bbox = element_bbox(tile)
    if not bbox:
        return 1.0
    return viewbox_width / 64.0 if bbox[2] - bbox[0] > 32 else 1.0


def strip_dark_backgrounds(text, tile, tile_scale=1.0):
    if not tile.startswith("<rect"):
        return text
    attrs = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tile))
    tx = float(attrs.get("x", 0)) * tile_scale
    ty = float(attrs.get("y", 0)) * tile_scale
    tw = float(attrs.get("width", 56)) * tile_scale
    th = float(attrs.get("height", 56)) * tile_scale
    tcx, tcy = tx + tw / 2, ty + th / 2

    def repl(match):
        tag = match.group(0)
        if "mtf-bg" in tag or 'fill="none"' in tag:
            return tag
        values = dict(re.findall(r'\b(x|y|width|height)="([\d.]+)"', tag))
        if not all(key in values for key in ("x", "y", "width", "height")):
            return tag
        x, y, w, h = (float(values[key]) for key in ("x", "y", "width", "height"))
        if w < 0.6 * tw or h < 0.6 * th:
            return tag
        if abs((x + w / 2) - tcx) > 0.05 * tw or abs((y + h / 2) - tcy) > 0.05 * th:
            return tag
        fill = re.search(r'(?:fill=|fill:)\s*["\']?(#[0-9a-fA-F]{3,6})', tag)
        if not fill:
            return ""
        rgb = hex_to_rgb(fill.group(1))
        if rgb is None:
            return tag
        r, g, b = (v / 255 for v in rgb)
        if 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.42:
            return ""
        return tag

    return sub_outside_defs(r"<rect\b[^>]*?/?>", repl, text)


def find_tile(text):
    masked = re.sub(r"<defs>.*?</defs>", lambda m: " " * len(m.group(0)), text, flags=re.S)
    for pattern in TILE_PATTERNS:
        match = pattern.search(masked)
        if match:
            return text[match.start():match.end()]
    match = PATH_TILE.search(masked)
    if match:
        return text[match.start():match.end()]

    viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', text)
    if viewbox:
        width, height = float(viewbox.group(1)), float(viewbox.group(2))
        for match in re.finditer(r"<rect\b[^>]*?/?>", masked):
            tag = text[match.start():match.end()]
            if "transform=" in tag or "filter=" in tag or 'fill="none"' in tag:
                continue
            values = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tag))
            w = float(values.get("width", 0))
            h = float(values.get("height", 0))
            rx = float(values.get("rx", values.get("ry", 0)))
            if 0.84 <= w / width <= 0.90 and 0.84 <= h / height <= 0.90 and w and 0.18 <= rx / w <= 0.28:
                return tag
    return None


def glyph_gradients(prefix):
    parts = []
    for index, tone in enumerate(GLYPH_TONES):
        top = min(255, tone + 7)
        bottom = max(0, tone - 9)
        parts.append(
            f'<linearGradient id="{prefix}-g{index}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#{top:02x}{top:02x}{top:02x}"/>'
            f'<stop offset=".5" stop-color="#{tone:02x}{tone:02x}{tone:02x}"/>'
            f'<stop offset="1" stop-color="#{bottom:02x}{bottom:02x}{bottom:02x}"/>'
            f'</linearGradient>'
        )
    return "".join(parts)


def apply_glyph_gradients(text, prefix):
    def repl(match):
        color = match.group(2)
        rgb = hex_to_rgb(color)
        if rgb is None:
            return match.group(0)
        tone = rgb[0]
        if tone < 92:
            return match.group(0)
        index = min(range(len(GLYPH_TONES)), key=lambda i: abs(GLYPH_TONES[i] - tone))
        return f'{match.group(1)}="url(#{prefix}-g{index})"'

    return re.sub(r'\b(fill|stroke)="(#[0-9a-fA-F]{3,6})"', repl, text)


def ensure_fill(text, prefix):
    def repl(match):
        tag = match.group(0)
        if "fill=" in tag or "fill:" in tag:
            return tag
        if tag.endswith("/>"):
            return tag[:-2] + f' fill="url(#{prefix}-g0)"/>'
        return tag[:-1] + f' fill="url(#{prefix}-g0)">'

    return re.sub(r"<(?:path|rect|circle|ellipse|polygon|polyline)\b[^>]*?/?>", repl, text)


def frost_fallback(text, mode):
    prefix = "mtf"
    while f'id="{prefix}-bg"' in text:
        prefix += "x"

    viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', text)
    if viewbox:
        width, height = float(viewbox.group(1)), float(viewbox.group(2))
    else:
        wm = re.search(r'\bwidth="([\d.]+)"', text)
        hm = re.search(r'\bheight="([\d.]+)"', text)
        width = float(wm.group(1)) if wm else 64.0
        height = float(hm.group(1)) if hm else 64.0

    text = re.sub(r"<image\b[^>]*/>", "", text)
    text = strip_dangling_uses(text)

    def rect_repl(match):
        tag = match.group(0)
        if 'fill="none"' in tag:
            return tag
        values = dict(re.findall(r'\b(x|y|width|height)="([\d.]+)"', tag))
        if "width" not in values or "height" not in values:
            return tag
        w, h = float(values["width"]), float(values["height"])
        if w >= 0.85 * width and h >= 0.85 * height:
            return ""
        return tag

    text = sub_outside_defs(r"<rect\b[^>]*?/?>", rect_repl, text)

    def transformed_repl(match):
        tag = match.group(0)
        values = dict(re.findall(r'\b(width|height)="([\d.]+)"', tag))
        w = float(values.get("width", 0))
        h = float(values.get("height", 0))
        if 0.8 * width <= w <= 0.9 * width and 0.8 * height <= h <= 0.9 * height:
            return ""
        return tag

    text = sub_outside_defs(r'<rect\b[^>]*\btransform="[^"]*"[^>]*?/?>', transformed_repl, text)
    text = re.sub(r'<path\b[^>]*\bd="M1\.559 [\d.]+h60\.882[vV][\d.]+H1\.559z"[^>]*?/>', "", text)

    def path_repl(match):
        tag = match.group(0)
        d = re.search(r'\bd="([^"]+)"', tag)
        if not d:
            return tag
        value = d.group(1)
        starts = value.startswith("M17") or value.startswith("M47") or value.startswith("m5.3604") or value.startswith("m5.3603")
        markers = ("13.002", "12.973", "h29.996", "9.822", "3.999", "C54.174", "13 13", "12.974", "12.9")
        if starts and any(marker in value for marker in markers):
            return ""
        return tag

    text = sub_outside_defs(r"<path\b[^>]*?/>", path_repl, text)

    scale = width / 64.0
    tile = (
        f'<rect x="{4 * scale:.3f}" y="{4 * scale:.3f}" width="{56 * scale:.3f}" '
        f'height="{56 * scale:.3f}" rx="{13 * scale:.3f}" fill="url(#{prefix}-bg)"/>'
    )
    text = strip_dark_backgrounds(text, tile)
    text = strip_tile_duplicates(text, tile, gradient_only=True)

    if mode == "clear":
        text = apply_glyph_gradients(recolor(text), prefix)
        text = ensure_fill(text, prefix)

    overlay = tile_overlay(tile, prefix, scale)
    blur = max(0.22, 0.9 * scale)
    defs = (
        FROST_DEFS.replace("{p}", prefix)
        .replace("{gradients}", glyph_gradients(prefix))
        .replace("{blur}", f"{blur:.2f}")
    )

    svg_match = re.search(r"<svg\b[^>]*>", text)
    start = svg_match.end() if svg_match else 0
    draw = re.compile(r"<(?:defs\b.*?</defs>|path\b|rect\b|circle\b|ellipse\b|polygon\b|polyline\b|g\b|image\b|text\b)", re.S)
    insert_at = start
    for match in draw.finditer(text, start):
        if match.group(0).startswith("<defs"):
            continue
        insert_at = match.start()
        break
    block = "<defs>" + defs + "</defs>" + tile + overlay
    return text[:insert_at] + block + text[insert_at:]


def frost_svg(text, mode, fallback=False):
    tile = find_tile(text)
    if tile is None:
        return frost_fallback(text, mode) if fallback else None

    prefix = "mtf"
    while f'id="{prefix}-bg"' in text:
        prefix += "x"

    new_tile = re.sub(r'fill="[^"]*"', f'fill="url(#{prefix}-bg)"', tile, count=1)
    new_tile = re.sub(r'fill:[^;"]+', f"fill:url(#{prefix}-bg)", new_tile)
    if "fill=" not in new_tile and "fill:" not in new_tile:
        new_tile = new_tile.replace("/>", f' fill="url(#{prefix}-bg)"/>')

    viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ', text)
    viewbox_width = float(viewbox.group(1)) if viewbox else 64.0
    scale = viewbox_width / 64.0

    if tile.startswith("<rect"):
        def rect_geom(tag):
            attrs = dict(re.findall(r'\b(x|y|width|height|rx|ry)="([\d.]+)"', tag))
            return tuple(round(float(attrs.get(k, 0)), 3) for k in ("x", "y", "width", "height", "rx", "ry"))

        geom = rect_geom(tile)
        split = text.find(tile) + len(tile)
        head, tail = text[:split], text[split:]

        def drop_duplicate(match):
            tag = match.group(0)
            if "filter=" in tag or "filter:" in tag or 'fill="none"' in tag:
                return tag
            return "" if rect_geom(tag) == geom else tag

        text = head + re.sub(r"<rect\b[^>]*?/?>", drop_duplicate, tail)

    text = re.sub(r"<image\b[^>]*/>", "", text)
    text = strip_dangling_uses(text)
    text = re.sub(r'<path\b[^>]*\bd="M1\.559 [\d.]+h60\.882[vV][\d.]+H1\.559z"[^>]*?/>', "", text)
    if tile.startswith("<path"):
        text = remove_extra_path_tiles(text, tile)
    text = re.sub(r'<path\b[^>]*\bd="M18 4C10\.244[^"]*"[^>]*?/>', "", text)
    text = re.sub(r'<path\b[^>]*\bd="M17 4\.6h30[^"]*"[^>]*?/>', "", text)
    if re.search(r'width="14\.8', tile):
        text = re.sub(
            r"<(?:rect|path|circle|ellipse)\b[^>]*transform=\"scale\(\.0?2645[0-9]*\)\"[^>]*?/>",
            "",
            text,
        )
    text = replace_tile(text, tile, new_tile)
    text = strip_tile_duplicates(text, tile)
    if mode == "clear":
        text = strip_dark_backgrounds(text, tile, tile_scale_for(tile, viewbox_width))
        text = apply_glyph_gradients(recolor(text), prefix)
        text = ensure_fill(text, prefix)

    blur = max(0.22, 0.9 * scale)
    defs = (
        FROST_DEFS.replace("{p}", prefix)
        .replace("{gradients}", glyph_gradients(prefix))
        .replace("{blur}", f"{blur:.2f}")
    )
    defs_match = re.search(r"<defs>", text)
    if defs_match:
        text = text[:defs_match.end()] + defs + text[defs_match.end():]
    else:
        svg_match = re.search(r"<svg\b[^>]*>", text)
        text = text[:svg_match.end()] + "<defs>" + defs + "</defs>" + text[svg_match.end():]

    return text.replace(new_tile, new_tile + tile_overlay(tile, prefix, scale), 1)


def generate(src, dest, mode="tint", cache=True):
    src = Path(src)
    dest = Path(dest)
    if not src.is_dir():
        raise FileNotFoundError(src)
    if src.resolve() == dest.resolve():
        raise ValueError("source and destination must differ")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    stats = {"converted": 0, "copied": 0}

    def walk(current_src, current_dest):
        for entry in os.scandir(current_src):
            source = Path(entry.path)
            target = current_dest / entry.name
            if entry.is_symlink():
                os.symlink(os.readlink(source), target)
            elif entry.is_dir(follow_symlinks=False):
                target.mkdir()
                walk(source, target)
            else:
                if entry.name == "icon-theme.cache":
                    continue
                if (
                    source.name == "file-manager.svg"
                    and source.parent.name == "scalable"
                    and source.parent.parent.name == "apps"
                ):
                    shutil.copy2(source, target)
                    stats["copied"] += 1
                    continue
                if source.suffix.lower() == ".svg":
                    try:
                        text = source.read_text(encoding="utf-8", errors="replace")
                        converted = frost_svg(
                            text,
                            mode,
                            fallback=(
                                source.parent.name == "scalable"
                                and source.parent.parent.name == "apps"
                                and "symbolic" not in source.name.lower()
                            ),
                        )
                    except Exception:
                        converted = None
                    if converted is not None:
                        target.write_text(converted, encoding="utf-8")
                        stats["converted"] += 1
                        continue
                shutil.copy2(source, target)
                stats["copied"] += 1

    walk(src, dest)

    index = dest / "index.theme"
    if index.exists():
        content = index.read_text(encoding="utf-8")
        content = re.sub(r"(?m)^Name=.*$", f"Name={dest.name}", content)
        content = re.sub(
            r"(?m)^Comment=.*$",
            "Comment=macOS Tahoe frosted glass icon theme for Linux.",
            content,
        )
        index.write_text(content, encoding="utf-8")

    if cache and shutil.which("gtk-update-icon-cache"):
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(dest)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate frosted-glass MacTahoe icon themes.")
    parser.add_argument("--src", default=str(Path.home() / ".local/share/icons/MacTahoe"))
    parser.add_argument("--dest", default=str(Path.home() / ".local/share/icons/MacTahoe-Frosted"))
    parser.add_argument("--mode", choices=("tint", "clear"), default="clear")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    stats = generate(args.src, args.dest, args.mode, cache=not args.no_cache)
    print(f"{args.dest}: {stats['converted']} converted, {stats['copied']} copied")


if __name__ == "__main__":
    main()
