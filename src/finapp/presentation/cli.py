"""Command-line entry point for FinApp.

Sprint 1.1 provides a placeholder command that verifies the package installs
and runs correctly. Real subcommands (e.g. ``finapp simulate``,
``finapp dca``) are introduced in later sprints alongside their use cases.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from finapp import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""

    parser = argparse.ArgumentParser(
        prog="finapp",
        description=(
            "FinApp: a dividend investing and retirement optimizer for the "
            "Bucharest Stock Exchange (BVB)."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"finapp {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the FinApp CLI.

    Returns the process exit code.
    """

    parser = build_parser()
    parser.parse_args(argv)
    print(f"FinApp v{__version__} — bootstrap sprint. No commands implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
