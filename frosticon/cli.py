"""Command line interface for frosticon."""

import argparse
import sys
from pathlib import Path
from .engine import FrostEngine
from .theme import ThemeGenerator


def main(args=None):
    """Entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        prog="frostify",
        description="Generate frosted-glass macOS Tahoe icon themes for Linux desktop.",
    )
    parser.add_argument(
        "--src",
        default=str(Path.home() / ".local/share/icons/MacTahoe"),
        help="Path to source upstream icon theme (default: ~/.local/share/icons/MacTahoe)",
    )
    parser.add_argument(
        "--dest",
        default=str(Path.home() / ".local/share/icons/MacTahoe-Frosted"),
        help="Path to output destination theme (default: ~/.local/share/icons/MacTahoe-Frosted)",
    )
    parser.add_argument(
        "--mode",
        choices=("clear", "tint"),
        default="clear",
        help="Visual style: 'clear' (pearl/monochrome glass) or 'tint' (tinted glass) (default: clear)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip rebuilding the GTK icon cache after generation",
    )
    parser.add_argument(
        "--no-overrides",
        action="store_true",
        help="Disable handcrafted custom overrides (e.g. dual-split Finder icon)",
    )
    parser.add_argument(
        "--file",
        dest="single_file",
        help="Convert a single SVG file to stdout or --output instead of processing a whole theme",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Destination path when converting a single file (--file)",
    )

    parsed = parser.parse_args(args)

    # Single-file conversion mode
    if parsed.single_file:
        file_path = Path(parsed.single_file)
        if not file_path.is_file():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)

        engine = FrostEngine(mode=parsed.mode)
        try:
            content = file_path.read_text(encoding="utf-8")
            result = engine.transform(content, fallback=True)
            if result is None:
                print(f"Error: failed to transform {file_path}", file=sys.stderr)
                sys.exit(1)

            if parsed.output:
                out_path = Path(parsed.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(result, encoding="utf-8")
                print(f"Transformed SVG written to: {out_path}")
            else:
                sys.stdout.write(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Full theme generation mode
    src_path = Path(parsed.src)
    dest_path = Path(parsed.dest)

    if not src_path.is_dir():
        print(f"Error: Source theme directory '{src_path}' does not exist.", file=sys.stderr)
        print("Please install the base MacTahoe theme first.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating frosted icon theme from {src_path} -> {dest_path} (mode={parsed.mode})...")

    generator = ThemeGenerator(
        src=src_path,
        dest=dest_path,
        mode=parsed.mode,
        cache=not parsed.no_cache,
        use_overrides=not parsed.no_overrides,
    )

    try:
        stats = generator.generate()
        print(f"\nSuccess! Generated {dest_path.name}:")
        print(f"  • {stats.converted} icons converted to frosted glass")
        if stats.overridden:
            print(f"  • {stats.overridden} custom icons integrated (Finder clear face, etc.)")
        print(f"  • {stats.copied} non-convertible files/symlinks copied")
        if stats.failed:
            print(f"  • {stats.failed} icons failed conversion and were copied as-is")
    except Exception as exc:
        print(f"Fatal error during theme generation: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
