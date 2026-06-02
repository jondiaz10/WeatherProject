"""Unit tests for the weather package.

The real OpenWeatherMap API is never contacted: every HTTP interaction is
mocked. Tests cover the happy path (a parsed, formatted report), invalid-city
handling, transient-error retry behavior, and missing-configuration errors.
"""

from __future__ import annotations

from unittest import mock

import pytest
import requests

from config.settings import (
    API_KEY_ENV_VAR,
    ConfigurationError,
    Settings,
    load_settings,
)
from src.formatter import format_weather
from src.weather import (
    CityNotFoundError,
    WeatherAPIError,
    WeatherClient,
)

# A representative OpenWeatherMap "current weather" response for Atlanta.
SAMPLE_RESPONSE = {
    "weather": [{"main": "Clouds", "description": "broken clouds"}],
    "main": {
        "temp": 21.5,
        "feels_like": 21.0,
        "humidity": 60,
    },
    "wind": {"speed": 3.6},
    "visibility": 10000,
    "sys": {
        "country": "US",
        "sunrise": 1717238400,
        "sunset": 1717290000,
    },
    "timezone": -14400,
    "name": "Atlanta",
}


def make_settings(**overrides: object) -> Settings:
    """Build a Settings instance with test-friendly defaults.

    Args:
        **overrides: Field values to override on the returned Settings.

    Returns:
        A populated Settings instance.
    """
    values = {
        "api_key": "test-key",
        "base_url": "https://example.test/weather",
        "default_units": "metric",
        "request_timeout": 5,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def make_response(status_code: int = 200, json_body: object | None = None) -> mock.Mock:
    """Create a mock ``requests.Response``.

    Args:
        status_code: HTTP status code the mock should report.
        json_body: Object returned by the mock's ``json()`` method.

    Returns:
        A configured mock response.
    """
    response = mock.Mock(spec=requests.Response)
    response.status_code = status_code
    response.json.return_value = json_body if json_body is not None else {}
    response.raise_for_status.return_value = None
    return response


def test_successful_response_returns_formatted_output() -> None:
    """A valid API response is parsed and rendered into a clean report."""
    session = mock.Mock(spec=requests.Session)
    session.get.return_value = make_response(200, SAMPLE_RESPONSE)
    client = WeatherClient(make_settings(), session=session)

    data = client.get_current_weather("Atlanta", units="metric")
    output = format_weather(data)

    # The HTTP layer was exercised exactly once (no retry on success).
    session.get.assert_called_once()
    assert data.city == "Atlanta"
    assert data.country == "US"
    assert "Atlanta, US" in output
    assert "Clouds (broken clouds)" in output
    assert "21.5°C" in output
    assert "feels like 21.0°C" in output
    assert "60%" in output
    assert "3.6 m/s" in output
    assert "10.0 km" in output
    # Sunrise/sunset are rendered as HH:MM, never as raw epoch seconds.
    assert "1717238400" not in output
    assert "Sunrise:" in output
    assert "Sunset:" in output


def test_imperial_units_use_fahrenheit_symbol() -> None:
    """Requesting imperial units renders Fahrenheit and mph."""
    session = mock.Mock(spec=requests.Session)
    session.get.return_value = make_response(200, SAMPLE_RESPONSE)
    client = WeatherClient(make_settings(), session=session)

    output = format_weather(client.get_current_weather("Atlanta", units="imperial"))

    assert "°F" in output
    assert "mph" in output


def test_invalid_city_raises_city_not_found() -> None:
    """A 404 from the API surfaces as a CityNotFoundError."""
    session = mock.Mock(spec=requests.Session)
    session.get.return_value = make_response(404, {"message": "city not found"})
    client = WeatherClient(make_settings(), session=session)

    with pytest.raises(CityNotFoundError) as exc_info:
        client.get_current_weather("NotARealCity")

    assert "NotARealCity" in str(exc_info.value)
    # A 404 will never succeed, so there must be no retry.
    session.get.assert_called_once()


def test_network_error_retries_once_then_fails() -> None:
    """A network error triggers exactly one retry before failing cleanly."""
    session = mock.Mock(spec=requests.Session)
    session.get.side_effect = requests.exceptions.ConnectionError("boom")
    client = WeatherClient(make_settings(), session=session)

    with pytest.raises(WeatherAPIError):
        client.get_current_weather("Atlanta")

    # One initial attempt plus a single retry == two calls.
    assert session.get.call_count == 2


def test_rate_limit_retries_then_succeeds() -> None:
    """A 429 is retried once; a subsequent success is returned normally."""
    session = mock.Mock(spec=requests.Session)
    session.get.side_effect = [
        make_response(429, {"message": "rate limit"}),
        make_response(200, SAMPLE_RESPONSE),
    ]
    client = WeatherClient(make_settings(), session=session)

    data = client.get_current_weather("Atlanta")

    assert data.city == "Atlanta"
    assert session.get.call_count == 2


def test_invalid_units_raises_configuration_error() -> None:
    """Unsupported units are rejected before any HTTP call is made."""
    session = mock.Mock(spec=requests.Session)
    client = WeatherClient(make_settings(), session=session)

    with pytest.raises(ConfigurationError):
        client.get_current_weather("Atlanta", units="kelvin")

    session.get.assert_not_called()


def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loading settings without an API key raises a ConfigurationError."""
    # Prevent a developer's local .env file from supplying a key during tests.
    monkeypatch.setattr("config.settings.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert API_KEY_ENV_VAR in str(exc_info.value)


def test_malformed_payload_raises_weather_api_error() -> None:
    """A response missing expected fields surfaces as a WeatherAPIError."""
    session = mock.Mock(spec=requests.Session)
    session.get.return_value = make_response(200, {"unexpected": "shape"})
    client = WeatherClient(make_settings(), session=session)

    with pytest.raises(WeatherAPIError):
        client.get_current_weather("Atlanta")
