import numpy as np


def generate_demo_data(variable, year, month):
    """
    Alternate synthetic generator, aligned with the main engine.
    """
    lat = np.linspace(-90, 90, 36)
    lon = np.linspace(-180, 180, 72)

    base = np.random.normal(0, 1, (36, 72))

    if variable == "Temperature":
        data = 15 + 10 * base
    elif variable == "Precipitation":
        data = 100 * np.abs(base)
    elif variable == "Wind Speed":
        data = 10 * np.abs(base)
    elif variable == "Humidity":
        data = 60 + 20 * base
    elif variable in ("Sea Level Pressure", "Sea Level"):
        data = 1013 + 5 * base
    else:
        data = base

    return lat, lon, data