"""SVG path geometry parsing, bounding box calculation, and transform evaluation."""

import re
from typing import Optional, Tuple
from .constants import PATH_TOKEN

BBox = Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)


def path_bbox(d: str) -> Optional[BBox]:
    """Calculate the 2D bounding box (min_x, min_y, max_x, max_y) of an SVG path 'd'."""
    tokens = PATH_TOKEN.findall(d)
    index = 0
    command = None
    x = y = start_x = start_y = 0.0
    points = []

    def number() -> float:
        nonlocal index
        val = float(tokens[index])
        index += 1
        return val

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

    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    return min(xs), min(ys), max(xs), max(ys)


def transform_bbox(bbox: BBox, transform: Optional[str]) -> Optional[BBox]:
    """Apply an SVG transform attribute (matrix, scale, translate) to a bounding box."""
    if not transform:
        return bbox

    x0, y0, x1, y1 = bbox
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]

    matrix = re.search(
        r"matrix\(\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)\s*\)",
        transform,
    )
    if matrix:
        a, b, c, d, e, f = (float(v) for v in matrix.groups())
        transformed = [(a * x + c * y + e, b * x + d * y + f) for x, y in corners]
        xs = [pt[0] for pt in transformed]
        ys = [pt[1] for pt in transformed]
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


def element_bbox(tag: str) -> Optional[BBox]:
    """Extract and calculate the world-space bounding box of an SVG element tag."""
    transform = re.search(r'\btransform="([^"]+)"', tag)
    trans_val = transform.group(1) if transform else None

    if tag.startswith("<rect"):
        values = dict(re.findall(r'(?<!-)\b(x|y|width|height)="([\d.]+)"', tag))
        x = float(values.get("x", 0))
        y = float(values.get("y", 0))
        w = float(values.get("width", 0))
        h = float(values.get("height", 0))
        bbox: Optional[BBox] = (x, y, x + w, y + h)
    else:
        d = re.search(r'\bd="([^"]+)"', tag)
        if not d:
            return None
        bbox = path_bbox(d.group(1))

    if bbox is None:
        return None

    return transform_bbox(bbox, trans_val)


def compute_iou(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2

    ix_min, iy_min = max(x1_min, x2_min), max(y1_min, y2_min)
    ix_max, iy_max = min(x1_max, x2_max), min(y1_max, y2_max)

    if ix_max <= ix_min or iy_max <= iy_min:
        return 0.0

    intersection = (ix_max - ix_min) * (iy_max - iy_min)
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0
