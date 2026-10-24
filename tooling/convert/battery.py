"""Battery charging icon transformation module.

Ensures that battery charging icons have an Apple-style green fill (#30d158)
and a solid white lightning bolt (#ffffff) across all theme variants (light, dark, frosted).
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union
from .geometry import path_bbox


BOLT_MARKERS = [
    "6.1581", "4.0542", "m17 9-7", "7.334", "10.834", "3.4206", "4.3047",
    "8.834 4-3.334", "3.334 5h3l-0.75 3", "3.334-5h-3l0.75-3",
]

SHELL_MARKERS = [
    "m3 3c-1.662", "m4 7c-1.108", "m3 5c-1.662", "m3.3125 3", "M 3.3125 3",
    "m15 6v4", "m15 9.5", "m20 10v4", "m18 6v4", "M 4,7", "m2 3c-1.108", "m4.5 8c-2.493",
]


def is_battery_charging_icon(path: Union[str, Path]) -> bool:
    """Return True if the icon represents a battery charging status indicator."""
    name = path.name.lower() if isinstance(path, Path) else Path(path).name.lower()
    return "charging" in name or "plugged" in name


def is_bolt(tag: str, elem: ET.Element) -> bool:
    """Check if the SVG element represents the lightning bolt glyph."""
    d = elem.get("d", "")
    return tag in ("path", "polygon") and any(m in d for m in BOLT_MARKERS)


def is_shell(tag: str, elem: ET.Element) -> bool:
    """Check if the SVG element represents the battery outer shell/border or cap."""
    d = elem.get("d", "")
    op = elem.get("opacity", "")
    if op in (".5", "0.5", ".45", "0.45", ".35", "0.35"):
        return True
    return tag in ("path", "rect") and any(m in d for m in SHELL_MARKERS)


def clean_style(style_str: str, keep_fill: str = "", stroke_spec: str = "") -> str:
    """Filter out existing fill/color/stroke from style string, optionally replacing with keep_fill and stroke_spec."""
    if not style_str:
        parts = []
    else:
        parts = [p.strip() for p in style_str.split(";") if p.strip()]
    filtered = []
    for p in parts:
        if (
            p.startswith("fill:")
            or p.startswith("fill-opacity:")
            or p.startswith("color:")
            or p.startswith("stroke:")
            or p.startswith("stroke-width:")
            or p.startswith("stroke-linejoin:")
            or p.startswith("stroke-linecap:")
            or p.startswith("paint-order:")
            or p.startswith("-inkscape-stroke:")
        ):
            continue
        filtered.append(p)
    if keep_fill:
        filtered.append(f"fill:{keep_fill}")
    if stroke_spec:
        filtered.append(stroke_spec)
    return ";".join(filtered)


def transform_battery_svg(
    content: str,
    bolt_scale: float = 1.0,
    dark_mode: bool = True,
) -> str:
    """Transform battery charging SVG into green fill with white lightning bolt.

    If dark_mode is True, borders on the bolt are eliminated (clean white on dark/green).
    If dark_mode is False (light theme), a dark outline is added to the bolt so it
    remains sharp and distinct against light panels/backgrounds.
    """
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(content)

    defs = root.find("{http://www.w3.org/2000/svg}defs")
    text_color = "#f2f2f2" if dark_mode else "#232629"
    if defs is not None:
        style = defs.find("{http://www.w3.org/2000/svg}style")
        if style is not None and style.get("id") == "current-color-scheme":
            style.text = f".ColorScheme-Text {{ color:{text_color}; }} .ColorScheme-PositiveText {{ color:#30d158; }}"

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag not in ("path", "rect"):
            continue

        # Ignore off-screen leftover artboard elements
        if "translate(-1 -25.427)" in elem.get("transform", ""):
            continue

        if is_bolt(tag, elem):
            elem.set("fill", "#ffffff")
            elem.set("opacity", "1")
            if bolt_scale != 1.0:
                d = elem.get("d", "")
                bbox = path_bbox(d)
                if bbox:
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    elem.set(
                        "transform",
                        f"translate({cx:.3f}, {cy:.3f}) scale({bolt_scale}) translate(-{cx:.3f}, -{cy:.3f})",
                    )
            else:
                tf = elem.get("transform", "")
                if "scale(" in tf:
                    del elem.attrib["transform"]
            if "class" in elem.attrib:
                del elem.attrib["class"]
            if "color" in elem.attrib:
                del elem.attrib["color"]

            if dark_mode:
                # Eliminate border / outline on bolt
                elem.set("stroke", "none")
                for k in ("stroke-width", "stroke-linejoin", "stroke-linecap", "paint-order"):
                    elem.attrib.pop(k, None)
                if "style" in elem.attrib:
                    elem.attrib["style"] = clean_style(elem.attrib["style"], keep_fill="#ffffff", stroke_spec="stroke:none")
            else:
                # In light mode, add a dark outline around the bolt
                elem.set("stroke", "#1c1c1e")
                elem.set("stroke-width", "0.8")
                elem.set("stroke-linejoin", "round")
                elem.set("paint-order", "stroke fill")
                if "style" in elem.attrib:
                    elem.attrib["style"] = clean_style(
                        elem.attrib["style"],
                        keep_fill="#ffffff",
                        stroke_spec="paint-order:stroke fill;stroke:#1c1c1e;stroke-width:0.8;stroke-linejoin:round",
                    )
        elif is_shell(tag, elem):
            elem.set("class", "ColorScheme-Text")
            elem.set("fill", "currentColor")
            elem.set("opacity", "0.5")
            if "style" in elem.attrib:
                elem.attrib["style"] = clean_style(elem.attrib["style"], keep_fill="currentColor")
        else:
            # Inside charge level fill
            elem.set("fill", "#30d158")
            elem.set("opacity", "1")
            if "class" in elem.attrib:
                del elem.attrib["class"]
            if "style" in elem.attrib:
                elem.attrib["style"] = clean_style(elem.attrib["style"], keep_fill="#30d158")
            if "color" in elem.attrib:
                del elem.attrib["color"]

    return ET.tostring(root, encoding="utf-8").decode("utf-8")
