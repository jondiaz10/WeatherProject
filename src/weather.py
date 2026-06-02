"""Core weather-fetching logic.

Wraps the OpenWeatherMap "current weather" REST endpoint in a small, typed
client. Network and API failures are translated into a focused hierarchy of
exceptions so that callers (such as the CLI) can present clear, actionable
error messages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from config.settings import ConfigurationError, Settings

logger = logging.getLogger(__name__)

# HTTP status codes that are worth a single retry: rate limiting and transient
# server-side errors. A 404 (city not found) or 401 (bad key) will never
# succeed on retry, so they are handled separately.
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class WeatherError(Exception):
    """Base class for all errors raised by this package."""


class CityNotFoundError(WeatherError):
    """Raised when the requested city cannot be found by the API."""


class WeatherAPIError(WeatherError):
    """Raised for network failures or unexpected API responses."""


@dataclass(frozen=True)
class WeatherData:
    """Structured snapshot of current weather for a single location.

    Temperatures are in the unit system used for the request (Celsius for
    metric, Fahrenheit for imperial). Wind speed is in metres per second for
    metric and miles per hour for imperial. Visibility is in metres. Sunrise
    and sunset are timezone-aware UTC offsets resolved to the location's local
    time.

    Attributes:
        city: City name as reported by the API.
        country: ISO 3166 country code.
        units: Unit system used for the request ("metric" or "imperial").
        temperature: Current temperature.
        feels_like: Apparent ("feels like") temperature.
        condition: Short weather condition (for example, "Clouds").
        description: Expanded human-readable description.
        humidity: Relative humidity as a percentage.
        wind_speed: Wind speed in the request's unit system.
        visibility: Visibility in metres.
        sunrise: Local sunrise time.
        sunset: Local sunset time.
    """

    city: str
    country: str
    units: str
    temperature: float
    feels_like: float
    condition: str
    description: str
    humidity: int
    wind_speed: float
    visibility: int
    sunrise: datetime
    sunset: datetime


class WeatherClient:
    """Client for the OpenWeatherMap current-weather endpoint.

    The client is configured once with a :class:`~config.settings.Settings`
    instance and can then be reused for multiple lookups.
    """

    def __init__(self, settings: Settings, session: Optional[requests.Session] = None) -> None:
        """Initialize the client.

        Args:
            settings: Validated application settings, including the API key.
            session: Optional pre-built :class:`requests.Session`. A new
                session is created when not provided; injecting one is useful
                for testing and connection reuse.
        """
        self._settings = settings
        self._session = session or requests.Session()

    def get_current_weather(self, city: str, units: Optional[str] = None) -> WeatherData:
        """Fetch the current weather for a city.

        Args:
            city: Name of the city to look up (for example, "Atlanta").
            units: Unit system, either "metric" or "imperial". Falls back to
                the configured default when omitted.

        Returns:
            A :class:`WeatherData` snapshot for the requested city.

        Raises:
            ConfigurationError: If ``units`` is not a supported value.
            CityNotFoundError: If the API does not recognize the city.
            WeatherAPIError: On authentication, network, or unexpected errors.
        """
        resolved_units = (units or self._settings.default_units).lower()
        if resolved_units not in ("metric", "imperial"):
            raise ConfigurationError(
                f"Invalid units: {resolved_units!r}. Expected 'metric' or 'imperial'."
            )

        params = {
            "q": city,
            "units": resolved_units,
            "appid": self._settings.api_key,
        }
        logger.info("Fetching current weather for %r (units=%s)", city, resolved_units)
        payload = self._request(params, city)
        return self._parse(payload, resolved_units)

    def _request(self, params: dict[str, str], city: str) -> dict[str, Any]:
        """Perform the HTTP request, retrying once on transient failures.

        Args:
            params: Query parameters for the request.
            city: City name, used to build friendly error messages.

        Returns:
            The decoded JSON response body.

        Raises:
            CityNotFoundError: If the API responds with 404.
            WeatherAPIError: On authentication, network, or unexpected errors.
        """
        max_attempts = 2  # One initial attempt plus a single retry.
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._session.get(
                    self._settings.base_url,
                    params=params,
                    timeout=self._settings.request_timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Network error fetching weather (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                continue

            if response.status_code == 404:
                raise CityNotFoundError(
                    f"City not found: {city!r}. Check the spelling and try again."
                )
            if response.status_code == 401:
                raise WeatherAPIError(
                    "Authentication failed (HTTP 401). Verify your "
                    "OPENWEATHERMAP_API_KEY is correct and active."
                )
            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = WeatherAPIError(
                    f"API returned a transient error (HTTP {response.status_code})."
                )
                logger.warning(
                    "Retryable API error (attempt %d/%d): HTTP %d",
                    attempt,
                    max_attempts,
                    response.status_code,
                )
                continue

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                raise WeatherAPIError(
                    f"Unexpected API error (HTTP {response.status_code})."
                ) from exc

            try:
                return response.json()
            except ValueError as exc:
                raise WeatherAPIError("API returned a malformed (non-JSON) response.") from exc

        # All attempts were exhausted without a usable response.
        raise WeatherAPIError(
            "Failed to reach the weather service after retrying. "
            "Check your network connection and try again."
        ) from last_error

    @staticmethod
    def _parse(payload: dict[str, Any], units: str) -> WeatherData:
        """Convert a raw API payload into a :class:`WeatherData` instance.

        Args:
            payload: Decoded JSON body from the API.
            units: Unit system used for the request.

        Returns:
            A populated :class:`WeatherData` snapshot.

        Raises:
            WeatherAPIError: If the payload is missing expected fields.
        """
        try:
            weather = payload["weather"][0]
            main = payload["main"]
            sys_info = payload["sys"]
            # OpenWeatherMap returns the location's UTC offset in seconds; apply
            # it so sunrise/sunset render in the city's local time.
            tz = timezone.utc if "timezone" not in payload else _offset(payload["timezone"])
            return WeatherData(
                city=payload["name"],
                country=sys_info.get("country", "??"),
                units=units,
                temperature=float(main["temp"]),
                feels_like=float(main["feels_like"]),
                condition=weather["main"],
                description=weather["description"],
                humidity=int(main["humidity"]),
                wind_speed=float(payload.get("wind", {}).get("speed", 0.0)),
                visibility=int(payload.get("visibility", 0)),
                sunrise=datetime.fromtimestamp(sys_info["sunrise"], tz=tz),
                sunset=datetime.fromtimestamp(sys_info["sunset"], tz=tz),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise WeatherAPIError(
                "API response was missing expected fields; the service may have "
                "changed or returned an error."
            ) from exc


def _offset(seconds: int) -> timezone:
    """Build a fixed-offset timezone from a UTC offset in seconds.

    Args:
        seconds: Offset from UTC, in seconds.

    Returns:
        A :class:`datetime.timezone` representing the offset.
    """
    from datetime import timedelta

    return timezone(timedelta(seconds=seconds))
