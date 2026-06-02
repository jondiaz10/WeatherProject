"""Environment-based configuration for the weather CLI.

All runtime configuration is sourced from environment variables (optionally
loaded from a local ``.env`` file via :mod:`python-dotenv`). Nothing secret is
ever hardcoded in the source tree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Environment variable names are defined once here so they can be referenced
# consistently in error messages and documentation.
API_KEY_ENV_VAR = "OPENWEATHERMAP_API_KEY"
BASE_URL_ENV_VAR = "OPENWEATHERMAP_BASE_URL"
DEFAULT_UNITS_ENV_VAR = "WEATHER_DEFAULT_UNITS"
REQUEST_TIMEOUT_ENV_VAR = "WEATHER_REQUEST_TIMEOUT"

DEFAULT_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_UNITS = "metric"
DEFAULT_REQUEST_TIMEOUT = 10
VALID_UNITS = ("metric", "imperial")


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid.

    The message is intended to be shown directly to the user, so it should
    explain how to fix the problem (for example, which environment variable to
    set).
    """


@dataclass(frozen=True)
class Settings:
    """Immutable container for application configuration.

    Attributes:
        api_key: OpenWeatherMap API key used to authenticate requests.
        base_url: Base URL of the OpenWeatherMap "current weather" endpoint.
        default_units: Unit system to use when the caller does not specify one.
        request_timeout: Per-request timeout in seconds for HTTP calls.
    """

    api_key: str
    base_url: str
    default_units: str
    request_timeout: int


def load_settings() -> Settings:
    """Load and validate application settings from the environment.

    Reads configuration from the process environment, falling back to a local
    ``.env`` file when present. The OpenWeatherMap API key is required; all
    other values fall back to sensible defaults.

    Returns:
        A populated, validated :class:`Settings` instance.

    Raises:
        ConfigurationError: If the API key is missing or any value is invalid.
    """
    # Load variables from a local .env file if one exists. Real environment
    # variables always take precedence over values defined in the file.
    load_dotenv()

    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if not api_key:
        raise ConfigurationError(
            f"Missing API key. Set the {API_KEY_ENV_VAR} environment variable.\n"
            "Get a free key at https://home.openweathermap.org/api_keys and then run:\n"
            f"  export {API_KEY_ENV_VAR}='your-key-here'\n"
            "or copy .env.example to .env and fill in your key."
        )

    base_url = os.getenv(BASE_URL_ENV_VAR, DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    default_units = os.getenv(DEFAULT_UNITS_ENV_VAR, DEFAULT_UNITS).strip().lower()
    if default_units not in VALID_UNITS:
        raise ConfigurationError(
            f"Invalid {DEFAULT_UNITS_ENV_VAR}: {default_units!r}. "
            f"Expected one of {', '.join(VALID_UNITS)}."
        )

    raw_timeout = os.getenv(REQUEST_TIMEOUT_ENV_VAR, str(DEFAULT_REQUEST_TIMEOUT)).strip()
    try:
        request_timeout = int(raw_timeout)
    except ValueError as exc:
        raise ConfigurationError(
            f"Invalid {REQUEST_TIMEOUT_ENV_VAR}: {raw_timeout!r}. "
            "Expected an integer number of seconds."
        ) from exc
    if request_timeout <= 0:
        raise ConfigurationError(
            f"Invalid {REQUEST_TIMEOUT_ENV_VAR}: {request_timeout}. "
            "Expected a positive number of seconds."
        )

    return Settings(
        api_key=api_key,
        base_url=base_url,
        default_units=default_units,
        request_timeout=request_timeout,
    )
