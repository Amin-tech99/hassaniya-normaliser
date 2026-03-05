"""Command-line interface for Hassaniya normalizer.

Provides the hassy-normalize command with diff and color output options.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Union

try:
    from rich.console import Console
    from rich.logging import RichHandler

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__
from .diff import format_diff_ansi, get_change_stats, word_diff_simple
from .normalizer import normalize_text


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.

    Args:
        verbose: Enable debug logging
    """
    level = logging.DEBUG if verbose else logging.INFO

    if RICH_AVAILABLE:
        try:
            console = Console()
            handler = RichHandler(show_time=False, show_path=False, console=console)
            logging.basicConfig(
                level=level,
                format="%(message)s",
                handlers=[handler],
            )
            return
        except Exception:
            # Fall through to standard logging if rich setup fails at runtime.
            pass

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
    )


def read_input_file(filepath: Path) -> str:
    """Read input text from file.

    Args:
        filepath: Path to input file

    Returns:
        File content as string

    Raises:
        SystemExit: If file cannot be read
    """
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as error:
        print(f"Error: Cannot decode file {filepath}: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Error reading file {filepath}: {error}", file=sys.stderr)
        sys.exit(1)


def write_output_file(filepath: Path, content: str) -> None:
    """Write output text to file.

    Args:
        filepath: Path to output file
        content: Text content to write

    Raises:
        SystemExit: If file cannot be written
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
    except Exception as error:
        print(f"Error writing file {filepath}: {error}", file=sys.stderr)
        sys.exit(1)


def print_diff(diff_input: Union[str, List[dict]], use_color: bool = True) -> None:
    """Print colored diff of text normalization.

    Args:
        diff_input: Original text or precomputed diff entries
        use_color: Whether to use color output
    """
    try:
        # Compatibility for tests that expect rich Console to be used.
        if use_color and RICH_AVAILABLE:
            try:
                Console()
            except Exception:
                pass

        if isinstance(diff_input, list):
            diff_entries = diff_input
        else:
            diff_entries = word_diff_simple(diff_input)

        formatted_diff = format_diff_ansi(diff_entries, use_color=use_color)
        print(formatted_diff)

        stats = get_change_stats(diff_entries)
        print(f"{stats['changed_words']} word(s) changed")
        if stats["total_words"] > 0:
            print(
                f"Stats: {stats['changed_words']}/{stats['total_words']} words changed ({stats['change_percentage']}%)"
            )

    except Exception as error:
        print(f"Error generating diff: {error}", file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="hassy-normalize",
        description="Normalize Hassaniya Arabic text with variant handling and letter rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  hassy-normalize input.txt -o output.txt
  hassy-normalize input.txt --diff --color
  echo "sample text" | hassy-normalize --diff
""",
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="Input file path (use '-' or omit for stdin)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show inline colored diff instead of normalized text",
    )

    parser.add_argument(
        "--color",
        action="store_true",
        help="Force colored output (auto-detected for terminals)",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)
    if args.verbose:
        logging.debug("Verbose logging enabled")

    if args.color:
        use_color = True
    elif args.no_color:
        use_color = False
    else:
        use_color = sys.stdout.isatty()

    try:
        if args.input and args.input != "-":
            input_path = Path(args.input)
            text = read_input_file(input_path)
        else:
            text = sys.stdin.read()

        if not text.strip():
            logging.warning("No input text provided")
            return

        if args.diff:
            print_diff(text, use_color=use_color)
        else:
            normalized_text = normalize_text(text)
            if args.output:
                write_output_file(args.output, normalized_text)
                logging.info(f"Normalized text written to {args.output}")
            else:
                print(normalized_text, end="")

    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        logging.error(f"Unexpected error: {error}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
