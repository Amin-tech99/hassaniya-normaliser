"""Command-line interface for Hassaniya normalizer.

Provides the hassy-normalize command with diff and color output options.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

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
        # Use rich handler for colored output
        handler = RichHandler(show_time=False, show_path=False)
        logging.basicConfig(
            level=level,
            format="%(message)s",
            handlers=[handler]
        )
    else:
        # Fallback to standard logging
        logging.basicConfig(
            level=level,
            format="%(levelname)s: %(message)s",
            stream=sys.stdout
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
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Cannot decode file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
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
        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def print_diff(original_text: str, use_color: bool = True) -> None:
    """Print colored diff of text normalization.
    
    Args:
        original_text: Original text to normalize and show diff
        use_color: Whether to use color output
    """
    try:
        # Generate diff
        diff_entries = word_diff_simple(original_text)
        
        # Format with color
        formatted_diff = format_diff_ansi(diff_entries, use_color=use_color)
        
        # Print the diff
        print(formatted_diff)
        
        # Print statistics
        stats = get_change_stats(diff_entries)
        if stats["total_words"] > 0:
            print(f"\nStats: {stats['changed_words']}/{stats['total_words']} words changed ({stats['change_percentage']}%)")
        
    except Exception as e:
        print(f"Error generating diff: {e}", file=sys.stderr)
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
  echo "النص العربي" | hassy-normalize --diff
"""
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="Input file path (use '-' or omit for stdin)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show inline colored diff instead of normalized text"
    )
    
    parser.add_argument(
        "--color",
        action="store_true",
        help="Force colored output (auto-detected for terminals)"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Determine color usage
    use_color = False
    if args.color:
        use_color = True
    elif args.no_color:
        use_color = False
    else:
        # Auto-detect: use color if outputting to terminal
        use_color = sys.stdout.isatty()
    
    try:
        # Read input
        if args.input and args.input != "-":
            input_path = Path(args.input)
            text = read_input_file(input_path)
        else:
            # Read from stdin
            text = sys.stdin.read()
        
        if not text.strip():
            logging.warning("No input text provided")
            return
        
        # Process text
        if args.diff:
            # Show diff
            print_diff(text, use_color=use_color)
        else:
            # Normalize and output
            normalized_text = normalize_text(text)
            
            if args.output:
                write_output_file(args.output, normalized_text)
                logging.info(f"Normalized text written to {args.output}")
            else:
                print(normalized_text, end="")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()