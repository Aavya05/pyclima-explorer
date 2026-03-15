import xarray as xr


def load_dataset(path_or_file):
    """
    Load a NetCDF dataset from a file path or uploaded file.
    """
    return xr.open_dataset(path_or_file)


def extract_variable(ds, var):
    """
    Extract a variable from an xarray Dataset using flexible name mapping.
    """
    name_map = {
        "Temperature": ["t2m", "temperature", "temp"],
        "Precipitation": ["tp", "precipitation", "pr"],
        "Wind Speed": ["wind_speed", "windspeed", "u10", "v10"],
        "Humidity": ["humidity", "rh", "h2m"],
        "Sea Level Pressure": ["msl", "sea_level_pressure", "slp"],
        "Sea Level": ["msl", "sea_level_pressure", "slp"],
    }

    # Try mapped names first
    for candidate in name_map.get(var, []):
        if candidate in ds:
            return ds[candidate]

    # Fallback to first data variable if nothing matches
    if ds.data_vars:
        first_var = list(ds.data_vars)[0]
        return ds[first_var]

    raise ValueError("No data variables found in dataset.")