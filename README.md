## PyClimaExplorer

An interactive Streamlit dashboard for rapid climate data exploration, built for the **Hack It Out – PyClimaExplorer** challenge.

### Features

- **3D globe heatmap** powered by `globe.gl`, showing spatial patterns for:
  - Temperature
  - Precipitation
  - Wind Speed
  - Humidity
  - Sea Level Pressure
- **Time-series analysis** for any selected point on the globe.
- **Compare mode**: side‑by‑side globes for two different years.
- **Story mode**: guided climate anomaly stories loaded from `events.json`, with optional voice narration.
- **Automatic data handling**:
  - Uses an uploaded NetCDF (`.nc`) file if provided.
  - Otherwise falls back to `sample.nc` if present.
  - Otherwise falls back to synthetic demo data so the app always runs.

### Requirements

- Python 3.10+ (tested with 3.13)
- Packages listed in `requirements.txt`:
  - `streamlit`, `xarray`, `netcdf4`, `numpy`, `pandas`, `plotly`, `gtts`

Install them with:

```bash
python -m pip install -r requirements.txt
```

### Running the app

From the project root (`Pyclima_Explorer`):

```bash
python -m streamlit run app.py
```

Streamlit will print a local URL like `http://localhost:8501` – open it in your browser.

### Using the dashboard

- **Left panel – Controls**
  - Upload a NetCDF file (`Upload NetCDF file`) or rely on `sample.nc`/synthetic data.
  - Choose the **variable**, **year**, and **month**.
  - Toggle **Compare Mode** to add a comparison year.
  - Toggle **Story Mode** to see guided climate stories.

- **Center – Globe**
  - Shows a 3D globe heatmap for the selected variable and year.
  - In Compare Mode, shows **two globes** (reference vs comparison year).
  - Click anywhere on the globe to select a point.

- **Right panel – Analytics**
  - Global summary statistics for the current globe.
  - Color legend for the heatmap values.
  - **Selected Point • Time Series** for the last point you clicked on the globe.
  - Story Mode: list of climate anomalies and optional narrated story playback.

### Data format expectations

When using a NetCDF file:

- Dimensions should include `lat` and `lon`.
- For time‑varying data, a `time` dimension is supported; the app currently uses the first time slice.
- Variable names are mapped flexibly:
  - Temperature → `t2m`, `temperature`, `temp`, …
  - Precipitation → `tp`, `precipitation`, `pr`, …
  - Wind Speed → `wind_speed`, `windspeed`, `u10`, `v10`, …
  - Humidity → `humidity`, `rh`, `h2m`, …
  - Sea Level Pressure / Sea Level → `msl`, `sea_level_pressure`, `slp`, …

If no matching variable is found, the first data variable is used as a fallback.

