import json
import os
import numpy as np
import pandas as pd


def generate_data(variable, year, month):
    """
    Synthetic fallback data generator used when no NetCDF dataset
    is available or cannot be read.
    """
    lat = np.linspace(-90, 90, 36)
    lon = np.linspace(-180, 180, 72)

    noise = np.random.normal(0, 1, (36, 72))

    if variable == "Temperature":
        data = 15 + 10 * noise
    elif variable == "Precipitation":
        data = 100 * np.abs(noise)
    elif variable == "Wind Speed":
        data = 8 * np.abs(noise)
    elif variable == "Humidity":
        data = 60 + 20 * noise
    elif variable in ("Sea Level Pressure", "Sea Level"):
        data = 1013 + 5 * noise
    else:
        data = 0 + noise

    return lat, lon, data


def generate_timeseries(variable, lat, lon):
    """
    Simple synthetic time series for a given location.
    """
    time = np.arange(240)
    values = 15 + 5 * np.random.randn(240)

    return pd.DataFrame(
        {
            "time": time,
            "value": values,
        }
    )


def get_events(year):
    """
    Load climate events dynamically from events.json.
    Falls back to a small built-in catalog if the file
    is missing or unreadable.
    """
    # Try external JSON first
    try:
        events_path = os.path.join(os.path.dirname(__file__), "events.json")
        with open(events_path, "r", encoding="utf-8") as f:
            events_map = json.load(f)

        year_str = str(year)
        if year_str in events_map:
            return events_map[year_str]
    except Exception:
        pass

    # Fallback in case events.json is not available
    fallback_events = {
        2007: [
            "Arctic sea ice minimum",
            "European heatwave",
            "Indian monsoon variability",
        ],
        2020: [
            "Siberian heatwave",
            "Australian bushfire climate anomaly",
            "Atlantic hurricane season record",
        ],
    }

    return fallback_events.get(year, ["No major global events recorded"])