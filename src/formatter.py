"""Presentation helpers for weather data.

Turns a :class:`~src.weather.WeatherData` snapshot into a clean, human-readable
block of text suitable for printing to a terminal.
"""

from __future__ import annotations

from src.weather import WeatherData

# Unit-system-specific display symbols.
_TEMPERATURE_SYMBOLS = {"metric": "°C", "imperial": "°F"}
_WIND_UNITS = {"metric": "m/s", "imperial": "mph"}


def format_weather(data: WeatherData) -> str:
    """Render a :class:`WeatherData` snapshot as a formatted report.

    Args:
        data: The weather snapshot to display.

    Returns:
        A multi-line string ready to print to the console.
    """
    temp_symbol = _TEMPERATURE_SYMBOLS.get(data.units, "°")
    wind_unit = _WIND_UNITS.get(data.units, "m/s")

    location = f"{data.city}, {data.country}"
    condition = f"{data.condition} ({data.description})"
    visibility_km = data.visibility / 1000

    lines = [
        f"Weather for {location}",
        "-" * (len(location) + 12),
        f"  Condition:    {condition}",
        f"  Temperature:  {data.temperature:.1f}{temp_symbol} "
        f"(feels like {data.feels_like:.1f}{temp_symbol})",
        f"  Humidity:     {data.humidity}%",
        f"  Wind:         {data.wind_speed:.1f} {wind_unit}",
        f"  Visibility:   {visibility_km:.1f} km",
        f"  Sunrise:      {data.sunrise.strftime('%H:%M')}",
        f"  Sunset:       {data.sunset.strftime('%H:%M')}",
    ]
    return "\n".join(lines)
