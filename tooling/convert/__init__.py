"""convert: High-performance frosted glass SVG icon transformation library."""

from .battery import is_battery_charging_icon, transform_battery_svg
from .color import hex_to_rgb, lighten_color, recolor_svg
from .engine import FrostEngine, frost_svg
from .geometry import BBox, compute_iou, element_bbox, path_bbox
from .overrides import IconOverrides
from .theme import ThemeGenerator, ThemeStats, generate_theme
from .tile import find_tile, generate_tile_overlay

__version__ = "1.0.0"

__all__ = [
    "BBox",
    "FrostEngine",
    "IconOverrides",
    "ThemeGenerator",
    "ThemeStats",
    "compute_iou",
    "element_bbox",
    "find_tile",
    "frost_svg",
    "generate_theme",
    "generate_tile_overlay",
    "hex_to_rgb",
    "is_battery_charging_icon",
    "lighten_color",
    "path_bbox",
    "recolor_svg",
    "transform_battery_svg",
]
