"""Command-line entry point for the weather tool.

Parses arguments, loads configuration, fetches current weather for the
requested city, and prints a formatted report. All known error conditions are
translated into clear messages and a non-zero exit code.

Usage:
    python scripts/run.py --city "Atlanta"
    python scripts/run.py --city "London" --units imperial
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running this file directly (``python scripts/run.py``) by ensuring the
# project root is importable as a package root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import ConfigurationError, load_settings  # noqa: E402
from src.formatter import format_weather  # noqa: E402
from src.weather import (  # noqa: E402
    CityNotFoundError,
    WeatherAPIError,
    WeatherClient,
)

logger = logging.getLogger("weather")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list. Defaults to ``sys.argv`` when omitted.

    Returns:
        The parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="weather",
        description="Fetch and display current weather from OpenWeatherMap.",
    )
    parser.add_argument(
        "--city",
        required=True,
        help="City name to look up, for example: --city \"Atlanta\".",
    )
    parser.add_argument(
        "--units",
        choices=("metric", "imperial"),
        default="metric",
        help="Unit system for temperature and wind speed (default: metric).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging.

    Args:
        verbose: When True, set the log level to DEBUG instead of INFO.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the weather CLI.

    Args:
        argv: Optional argument list, primarily for testing.

    Returns:
        Process exit code: 0 on success, non-zero on any handled error.
    """
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        settings = load_settings()
        client = WeatherClient(settings)
        data = client.get_current_weather(args.city, units=args.units)
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        return 2
    except CityNotFoundError as exc:
        logger.error("City not found: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except WeatherAPIError as exc:
        logger.error("Weather API error: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 4

    print(format_weather(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
