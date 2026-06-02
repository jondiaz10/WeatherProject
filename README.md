# Weather CLI

Command-line weather tool using OpenWeatherMap API. Demonstrates REST API
integration, environment-based configuration, error handling, and unit testing
in Python.

Given a city name, it fetches the current conditions from
[OpenWeatherMap](https://openweathermap.org/) and prints a clean, formatted
report:

```
Weather for Atlanta, US
-----------------------------------
  Condition:    Clouds (broken clouds)
  Temperature:  21.5°C (feels like 21.0°C)
  Humidity:     60%
  Wind:         3.6 m/s
  Visibility:   10.0 km
  Sunrise:      06:40
  Sunset:       20:53
```

## Features

- Look up current weather for any city by name.
- Metric (°C, m/s) or imperial (°F, mph) units.
- Sunrise/sunset shown in the location's local time, not raw epoch values.
- Graceful error handling for invalid cities, missing API keys, rate limits,
  and network failures (with a single automatic retry on transient errors).
- API key loaded from the environment — never hardcoded.
- Fully unit-tested with the network layer mocked.

## Prerequisites

- Python 3.10 or newer
- An OpenWeatherMap API key (free tier is sufficient)

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd WeatherProject

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Setup: get an OpenWeatherMap API key

1. Create a free account at
   [openweathermap.org/api](https://openweathermap.org/api).
2. Open the [API keys](https://home.openweathermap.org/api_keys) page and copy
   your key. (New keys can take a little while to activate.)
3. Make the key available to the app. Either export it directly:

   ```bash
   export OPENWEATHERMAP_API_KEY="your-api-key-here"
   ```

   or copy the provided template and edit it:

   ```bash
   cp .env.example .env
   # then open .env and set OPENWEATHERMAP_API_KEY
   ```

The `.env` file is git-ignored and should never be committed.

## Usage

```bash
# Basic lookup (metric units by default)
python scripts/run.py --city "Atlanta"

# Imperial units
python scripts/run.py --city "London" --units imperial

# Verbose logging
python scripts/run.py --city "Tokyo" --verbose
```

### Options

| Option      | Required | Default  | Description                                   |
| ----------- | -------- | -------- | --------------------------------------------- |
| `--city`    | yes      | —        | City name to look up.                         |
| `--units`   | no       | `metric` | Unit system: `metric` or `imperial`.          |
| `--verbose` | no       | off      | Enable DEBUG-level logging.                   |

### Sample output

```
$ python scripts/run.py --city "Atlanta"
2026-06-01 10:15:02 INFO weather: Fetching current weather for 'Atlanta' (units=metric)
Weather for Atlanta, US
-----------------------------------
  Condition:    Clouds (broken clouds)
  Temperature:  21.5°C (feels like 21.0°C)
  Humidity:     60%
  Wind:         3.6 m/s
  Visibility:   10.0 km
  Sunrise:      06:40
  Sunset:       20:53
```

### Error handling

The CLI exits with a non-zero status and a clear message on failure:

- **Invalid city** — `Error: City not found: 'Atlantaa'. Check the spelling and try again.`
- **Missing API key** — instructions on which environment variable to set and
  where to get a key.
- **Rate limit / network error** — the request is retried once; if it still
  fails, the tool reports the failure and exits cleanly.

## Project structure

```
WeatherProject/
├── src/
│   ├── __init__.py
│   ├── weather.py        # Core weather-fetching client and data model
│   └── formatter.py      # Formats weather data for display
├── config/
│   ├── __init__.py
│   └── settings.py       # Loads & validates config from environment variables
├── tests/
│   ├── __init__.py
│   └── test_weather.py   # Unit tests with the API fully mocked
├── scripts/
│   └── run.py            # CLI entry point (argparse)
├── .env.example          # Template for required environment variables
├── requirements.txt      # Pinned dependencies
├── pytest.ini            # Test configuration
└── README.md
```

## Testing

Tests mock all HTTP calls, so they run offline and never contact the real API
or require a key.

```bash
pytest
```

Run with extra detail:

```bash
pytest -v
```

## License

Released under the MIT License.
