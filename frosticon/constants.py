"""Constants and regex patterns for frosted glass icon generation."""

import re

# Tonal shades for rendering glyph gradients in clear mode
GLYPH_TONES = (255, 244, 232, 218, 205, 194)

# SVG Standard Named Colors mapped to sRGB tuples
NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "brown": (165, 42, 42),
    "pink": (255, 192, 203),
    "lime": (0, 255, 0),
    "navy": (0, 0, 128),
    "teal": (0, 128, 128),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "silver": (192, 192, 192),
    "gold": (255, 215, 0),
}

# Regex patterns to detect standard macOS/Tahoe squircle base tiles
TILE_PATTERNS = [
    # Standard rect tile with width/height ~54-56 and corner radius rx/ry ~12-14
    re.compile(
        r'<rect\b(?![^>]*\btransform=)(?![^>]*\bfilter[:=])'
        r'(?=[^>]*\bwidth="5[4-6](?:\.\d+)?")(?=[^>]*\bheight="5[1-6](?:\.\d+)?")'
        r'(?=[^>]*\b(?:rx|ry)="1[2-4](?:\.\d+)?")[^>]*?/?>'
    ),
    # Scaled rect tile (e.g., 16x16 / 16.933 mm viewBox)
    re.compile(
        r'<rect\b(?![^>]*\btransform=)(?=[^>]*\bwidth="14\.8\d*")'
        r'(?=[^>]*\bheight="14\.8\d*")(?=[^>]*\bfill="url\(#)[^>]*?/?>'
    ),
    # Known path tile starting coordinates in MacTahoe icons
    re.compile(
        r'<path\b(?=[^>]*\bfill="url\(#[\w-]+\)")'
        r'(?=[^>]*\bd="(?:M20\.26 4|M5\.36 1\.058|M4\.498 1\.05|M17\.0\d+ [34]|M62\.44 64H1\.56))'
        r'[^>]*?/>'
    ),
    # Scaled path tile
    re.compile(
        r'<path\b(?=[^>]*\bd="[mM]5\.36(?:04|03) 1\.058)'
        r'[^>]*?/>'
    ),
]

# Secondary path tile pattern
PATH_TILE = re.compile(
    r'<path\b'
    r'(?=[^>]*\bd="[Mm](?:17|47|16\.9|5\.36|4\.498|20\.26|62\.44))'
    r'(?=[^>]*\bd="[^"]*(?:13\.002|12\.973|12\.974|9\.822|h29\.996|3\.999|h30|12\.9))'
    r'[^>]*?/?>'
)

# SVG Path data tokenizer
PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")

# Frosted glass SVG filter and gradient definition template
FROST_DEFS = """<linearGradient id="{p}-bg" x1="0" y1="0" x2="0" y2="1">
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
{gradients}"""
