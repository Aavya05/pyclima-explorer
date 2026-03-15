
import io
import json
import os
import time as _time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

try:
    import xarray as xr
    _XR = True
except ImportError:
    _XR = False

from clima_voice import generate_story, speak_story
from climate_engine import generate_data, generate_timeseries, get_events
from climate_stats import compute_stats
from data_loader import extract_variable, load_dataset

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="PyClimaExplorer", page_icon="🌍")

# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS — NASA dark theme (unchanged)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"]{
    background:radial-gradient(circle at top,#020617 0%,#020617 55%,#000 100%);
    color:#e5e7eb;
}
[data-testid="stSidebar"]{background:#020617;}
.section-title{
    font-size:.78rem;text-transform:uppercase;letter-spacing:.22em;
    color:#00c6ff;font-weight:700;margin:14px 0 10px;
    border-left:3px solid #00c6ff;padding-left:8px;
}
.metric-card{
    padding:.85rem 1rem;border-radius:.7rem;
    background:rgba(15,23,42,.9);border:1px solid rgba(0,198,255,.25);
    margin-bottom:8px;transition:border-color .2s;
}
.metric-card:hover{border-color:rgba(0,198,255,.6);}
.location-panel{
    background:rgba(0,30,60,.7);border:1px solid rgba(0,198,255,.3);
    border-radius:10px;padding:1rem 1.2rem;margin:10px 0;
}
.location-panel h4{
    color:#00c6ff;font-size:.85rem;letter-spacing:.1em;
    text-transform:uppercase;margin-bottom:8px;
}
.coord-badge{
    display:inline-block;background:rgba(0,198,255,.12);
    border:1px solid rgba(0,198,255,.35);border-radius:20px;
    padding:2px 12px;font-size:.82rem;color:#00c6ff;
    margin-right:6px;margin-bottom:8px;
}
.insight-panel{
    background:linear-gradient(135deg,rgba(0,20,60,.9),rgba(0,10,30,.95));
    border:1px solid rgba(0,198,255,.3);border-left:4px solid #00c6ff;
    border-radius:10px;padding:1rem 1.2rem;margin-top:10px;
    font-size:.88rem;line-height:1.65;color:#c8d8e8;
}
.insight-panel .insight-label{
    font-size:.72rem;text-transform:uppercase;letter-spacing:.2em;
    color:#00c6ff;font-weight:700;margin-bottom:8px;display:block;
}
.country-panel{
    background:linear-gradient(135deg,rgba(0,30,60,.9),rgba(0,10,40,.95));
    border:1px solid rgba(0,198,255,.3);border-radius:10px;
    padding:1rem 1.2rem;margin-top:10px;
    font-size:.88rem;line-height:1.65;color:#c8d8e8;
}
.country-panel h4{
    color:#00c6ff;font-size:.9rem;letter-spacing:.1em;
    text-transform:uppercase;margin-bottom:8px;
}
.anomaly-badge{
    display:inline-flex;align-items:center;gap:6px;
    background:rgba(0,198,255,.1);border:1px solid rgba(0,198,255,.3);
    border-radius:6px;padding:4px 10px;font-size:.75rem;
    color:#94b8c8;margin-bottom:6px;
}
.nc-badge{
    display:inline-flex;align-items:center;gap:6px;
    background:rgba(0,255,180,.08);border:1px solid rgba(0,255,180,.35);
    border-radius:6px;padding:4px 12px;font-size:.75rem;
    color:#00ffb4;margin-bottom:6px;
}
.anim-bar{
    height:3px;background:linear-gradient(90deg,#00c6ff,#0072ff);
    border-radius:2px;margin-top:6px;
}
[data-testid="stMetric"]{
    background:rgba(15,23,42,.9);border:1px solid rgba(0,198,255,.2);
    border-radius:8px;padding:.6rem .8rem;
}
[data-testid="stMetricLabel"]{color:#94b8c8!important;font-size:.78rem!important;}
[data-testid="stMetricValue"]{color:#e5e7eb!important;font-size:1.1rem!important;}
div[data-testid="stButton"] button{
    background:rgba(0,198,255,.1);border:1px solid rgba(0,198,255,.4);
    color:#00c6ff;border-radius:8px;font-size:.82rem;
    letter-spacing:.05em;transition:all .2s;
}
div[data-testid="stButton"] button:hover{
    background:rgba(0,198,255,.25);border-color:#00c6ff;
}
[data-testid="stCheckbox"] label{color:#94b8c8;font-size:.85rem;}
[data-testid="stSelectbox"] label,
[data-testid="stSlider"] label{color:#94b8c8;font-size:.82rem;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE  — P7: all mutable state lives here, never re-initialised
# ══════════════════════════════════════════════════════════════════════════════
_SS_DEFAULTS: dict = {
    "clicked_lat":      20.0,
    "clicked_lon":      78.0,
    "clicked_country":  "",
    "last_insight":     "",
    "insight_var":      "Temperature",
    "insight_year":     2007,
    "story_text":       "",
    "show_story":       False,
    "country_result":   None,
    "map_toggle":       False,
    "anim_active":      False,   # P3: animation guard
    "anim_year":        1980,    # P3: current frame during animation
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
COUNTRY_COORDS: dict = {
    "India":        (20.5937,  78.9629),
    "USA":          (37.0902, -95.7129),
    "Brazil":       (-14.235, -51.9253),
    "China":        (35.8617, 104.1954),
    "Russia":       (61.524,  105.319),
    "Australia":    (-25.274, 133.775),
    "Germany":      (51.1657,  10.4515),
    "France":       (46.2276,   2.2137),
    "Japan":        (36.2048, 138.2529),
    "Canada":       (56.130, -106.347),
    "UK":           (55.378,   -3.436),
    "South Africa": (-30.559,  22.938),
    "Nigeria":      ( 9.082,    8.675),
    "Argentina":    (-38.416, -63.617),
    "Mexico":       (23.634, -102.553),
    "Indonesia":    (-0.789,  113.921),
    "Egypt":        (26.820,   30.803),
    "Saudi Arabia": (23.886,   45.079),
    "Pakistan":     (30.375,   69.345),
    "Bangladesh":   (23.685,   90.356),
    "Turkey":       (38.964,   35.243),
    "Iran":         (32.427,   53.688),
    "Thailand":     (15.870,  100.993),
    "Vietnam":      (14.059,  108.278),
    "South Korea":  (35.908,  127.767),
    "Spain":        (40.463,   -3.750),
    "Italy":        (41.872,   12.567),
    "Ukraine":      (48.380,   31.165),
    "Poland":       (51.920,   19.145),
    "Peru":         (-9.190,  -75.015),
}

# Bounding boxes for fast reverse-geocoding: (lat_min, lat_max, lon_min, lon_max)
_COUNTRY_BBOX: dict = {
    "India":        (6.5,  37.1,  68.0, 97.5),
    "USA":          (24.0, 49.5, -125.0,-66.0),
    "Brazil":       (-33.8, 5.3, -73.9,-34.8),
    "China":        (18.0, 53.6,  73.5,135.1),
    "Russia":       (41.2, 81.9,  27.3,190.0),
    "Australia":    (-43.7,-10.7, 113.2,153.6),
    "Germany":      (47.3, 55.1,   5.9, 15.0),
    "France":       (41.3, 51.1,  -5.2,  9.6),
    "Japan":        (24.0, 45.5, 122.9,153.0),
    "Canada":       (41.7, 83.1,-141.0,-52.6),
    "UK":           (49.9, 60.9,  -8.6,  1.8),
    "South Africa": (-34.8,-22.1,  16.5, 32.9),
    "Nigeria":      ( 4.3, 13.9,   3.0, 14.7),
    "Argentina":    (-55.1,-21.8, -73.6,-53.6),
    "Mexico":       (14.5, 32.7,-117.1,-86.7),
    "Indonesia":    (-11.0,  6.1,  95.0,141.1),
    "Egypt":        (22.0, 31.7,  24.7, 37.1),
    "Saudi Arabia": (16.4, 32.2,  34.6, 55.7),
    "Pakistan":     (23.7, 37.1,  60.9, 77.8),
    "Bangladesh":   (20.7, 26.7,  88.0, 92.7),
    "Turkey":       (35.8, 42.1,  26.0, 44.8),
    "Iran":         (25.1, 39.8,  44.0, 63.3),
    "Thailand":     ( 5.6, 20.5,  97.3,105.6),
    "Vietnam":      ( 8.6, 23.4, 102.1,109.5),
    "South Korea":  (33.1, 38.6, 125.9,129.6),
    "Spain":        (35.9, 43.8,  -9.3,  4.3),
    "Italy":        (36.6, 47.1,   6.6, 18.5),
    "Ukraine":      (44.4, 52.4,  22.1, 40.2),
    "Poland":       (49.0, 54.9,  14.1, 24.2),
    "Peru":         (-18.4, -0.0, -81.4,-68.7),
}

VAR_ALIASES: dict = {
    "Temperature":        ["t2m","tas","temperature","temp","air","T","t","tmp"],
    "Precipitation":      ["pr","precip","precipitation","tp","rain","PREC","prcp"],
    "Wind Speed":         ["ws","wind","wspd","si10","windspeed","sfcWind","u10"],
    "Humidity":           ["hurs","rh","humidity","hum","q","specific_humidity","relhum"],
    "Sea Level Pressure": ["psl","slp","msl","sp","pressure","pres"],
}

_BASELINES: dict = {
    "Temperature": 14.0, "Precipitation": 2.5, "Wind Speed": 6.0,
    "Humidity": 60.0, "Sea Level Pressure": 1013.0,
}
_MONTHS = ["January","February","March","April","May","June",
           "July","August","September","October","November","December"]


# ══════════════════════════════════════════════════════════════════════════════
#  REVERSE GEOCODER  — P5: no external API, uses bounding boxes
# ══════════════════════════════════════════════════════════════════════════════
def reverse_geocode(lat: float, lon: float) -> str:
    """Return country name for (lat, lon) using bounding boxes, or empty str."""
    matches = []
    for country, (la0, la1, lo0, lo1) in _COUNTRY_BBOX.items():
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            # score = fraction of bbox that's closer to centre
            lat_centre = (la0 + la1) / 2
            lon_centre = (lo0 + lo1) / 2
            score = abs(lat - lat_centre) + abs(lon - lon_centre)
            matches.append((score, country))
    if matches:
        return min(matches, key=lambda x: x[0])[1]
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  CACHED DATA HELPERS  — P1: @st.cache_data on everything expensive
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def _load_nc_bytes(file_bytes: bytes):
    """Load NetCDF bytes → xarray Dataset. Cached by file content hash."""
    if not _XR:
        raise ImportError("xarray not installed")
    return xr.open_dataset(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def _cached_generate_data(variable: str, year: int, month: int):
    """Cached wrapper around the synthetic generate_data()."""
    return generate_data(variable, year, month)


@st.cache_data(show_spinner=False)
def _cached_generate_timeseries(variable: str, lat: float, lon: float):
    """Cached wrapper around generate_timeseries()."""
    return generate_timeseries(variable, lat, lon)


@st.cache_data(show_spinner=False)
def _cached_compute_stats(data_bytes: bytes) -> dict:
    """
    Cached compute_stats.  We serialise the numpy array to bytes so
    st.cache_data can hash it without complaints.
    """
    arr = np.frombuffer(data_bytes, dtype=np.float64)
    return compute_stats(arr)


def _stats_cached(data_2d: np.ndarray) -> dict:
    """Helper: flatten → bytes → cached stats."""
    flat = np.ascontiguousarray(data_2d.ravel().astype(np.float64))
    return _cached_compute_stats(flat.tobytes())


# ══════════════════════════════════════════════════════════════════════════════
#  XARRAY UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _detect_latlon(obj) -> tuple:
    """Return (lat_name, lon_name) by safely iterating xarray coords / dims."""
    lat_name = lon_name = None
    candidates: list = []
    try:
        candidates += [str(c) for c in obj.coords]
    except Exception:
        pass
    try:
        candidates += [str(d) for d in obj.dims]
    except Exception:
        pass
    seen: set = set()
    unique: list = []
    for c in candidates:
        if c not in seen:
            seen.add(c); unique.append(c)
    for c in unique:
        cl = c.lower()
        if cl in ("lat","latitude","y","nav_lat","rlat","ylat"):
            lat_name = c
        if cl in ("lon","longitude","x","nav_lon","rlon","xlon"):
            lon_name = c
    return lat_name, lon_name


def _find_var(ds, ui_var: str):
    """Return DataArray best matching ui_var, else first variable."""
    for name in VAR_ALIASES.get(ui_var, []):
        if name in ds:
            return ds[name]
    ds_lower = {k.lower(): k for k in ds.data_vars}
    for name in VAR_ALIASES.get(ui_var, []):
        if name.lower() in ds_lower:
            return ds[ds_lower[name.lower()]]
    return ds[list(ds.data_vars)[0]]


# ══════════════════════════════════════════════════════════════════════════════
#  CENTRAL DATA FUNCTION  — P1 + P2: cached + year properly drives slice
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def _nc_slice(file_bytes: bytes, ui_var: str, year: int, month: int):
    """
    Extract (lat_1d, lon_1d, data_2d) from NetCDF bytes for given year/month.
    Cached by (file_bytes, ui_var, year, month) — year change always triggers
    a new slice.  P2: time index selected by nearest year + exact month match.
    """
    ds  = _load_nc_bytes(file_bytes)
    da  = _find_var(ds, ui_var)

    # ── time selection (P2) ──────────────────────────────────────────────────
    time_dim = next(
        (str(d) for d in list(da.dims) + [str(c) for c in da.coords]
         if str(d).lower() == "time"),
        None,
    )
    if time_dim is not None:
        times = pd.to_datetime(da[time_dim].values)
        # prefer exact year+month match, else nearest year
        mask  = (times.year == year) & (times.month == month)
        if mask.any():
            idx = int(np.where(mask)[0][0])
        else:
            idx = int(np.abs(times.year - year).argmin())
        da = da.isel({time_dim: idx})

    da = da.squeeze()  # drop any size-1 leftover dims

    lat_name, lon_name = _detect_latlon(da)
    if lat_name is None or lon_name is None:
        raise ValueError(f"Lat/lon not found. Coords: {list(da.coords)}, Dims: {list(da.dims)}")

    lat_v  = da[lat_name].values.astype(float)
    lon_v  = da[lon_name].values.astype(float)
    data_v = da.values.astype(float)

    while data_v.ndim > 2:
        data_v = data_v[0]

    if len(lat_v) > 1 and lat_v[0] > lat_v[-1]:
        lat_v  = lat_v[::-1]
        data_v = data_v[::-1, :]

    return lat_v, lon_v, data_v


def get_data(ui_var: str, year: int, month: int,
             uploaded_file=None, warn: bool = False):
    """
    Returns (lat_1d, lon_1d, data_2d).
    Priority: uploaded NetCDF → cached synthetic generator.
    """
    if uploaded_file is not None and _XR:
        try:
            return _nc_slice(uploaded_file.getvalue(), ui_var, year, month)
        except Exception as exc:
            if warn:
                st.warning(f"⚠ NetCDF error — synthetic fallback. ({exc})")
    return _cached_generate_data(ui_var, year, month)


# ══════════════════════════════════════════════════════════════════════════════
#  NUMPY UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def to_2d(data) -> np.ndarray:
    arr = np.array(data, dtype=float)
    while arr.ndim > 2:
        arr = arr[0]
    return arr


def compute_anomaly(data: np.ndarray) -> np.ndarray:
    arr = to_2d(data)
    return arr - np.nanmean(arr)


def build_points(lat: np.ndarray, lon: np.ndarray, data) -> str:
    """
    P8: Vectorised build — no Python nested loops.
    Uses meshgrid + boolean mask for NaN filtering.
    """
    arr = to_2d(data)
    LON, LAT = np.meshgrid(lon, lat)          # shape (nlat, nlon)
    mask = ~np.isnan(arr)
    la_flat   = LAT[mask].ravel()
    lo_flat   = LON[mask].ravel()
    val_flat  = arr[mask].ravel()
    pts = [
        {"lat": float(la), "lng": float(lo), "value": float(v)}
        for la, lo, v in zip(la_flat, lo_flat, val_flat)
    ]
    return json.dumps(pts)


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBE + MAP RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def render_globe(heatmap_json: str, height: int = 500):
    html_path = os.path.join(os.path.dirname(__file__), "globe.html")
    with open(html_path, "r", encoding="utf-8") as fh:
        html = fh.read()
    components.html(html.replace("DATA_PLACEHOLDER", heatmap_json), height=height)


def render_flat_map(lat_arr, lon_arr, data_2d, variable: str,
                    use_anomaly: bool, height: int = 480):
    """
    Plotly Scattergeo world map (zoomable, clickable).
    P5: on click → reverse_geocode updates session_state.
    P6: selection captured via on_select="rerun".
    """
    arr   = to_2d(data_2d)
    # subsample ≤ 50×50 points for snappy render
    sl    = max(1, len(lat_arr) // 50)
    sm    = max(1, len(lon_arr) // 50)
    lat_s = lat_arr[::sl];  lon_s = lon_arr[::sm]
    arr_s = arr[::sl, ::sm][:len(lat_s), :len(lon_s)]

    LON_S, LAT_S = np.meshgrid(lon_s, lat_s)
    mask  = ~np.isnan(arr_s)
    lats  = LAT_S[mask].ravel().tolist()
    lons  = LON_S[mask].ravel().tolist()
    vals  = arr_s[mask].ravel().tolist()

    cscale = "RdBu_r" if use_anomaly else "RdYlBu"
    fig    = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, mode="markers",
        marker=dict(
            color=vals, colorscale=cscale, size=7, opacity=0.82,
            showscale=True,
            colorbar=dict(
                title=dict(text=variable, font=dict(color="#94b8c8", size=11)),
                tickfont=dict(color="#94b8c8", size=10),
                bgcolor="rgba(2,6,23,.8)", bordercolor="rgba(0,198,255,.3)",
                thickness=12, len=0.75,
            ),
        ),
        text=[f"{variable}: {v:.2f}<br>Lat {la:.1f}°  Lon {lo:.1f}°"
              for v, la, lo in zip(vals, lats, lons)],
        hoverinfo="text", name=variable,
    ))
    # selection pin
    sl_ = st.session_state["clicked_lat"]
    sl_lon = st.session_state["clicked_lon"]
    fig.add_trace(go.Scattergeo(
        lat=[sl_], lon=[sl_lon], mode="markers+text",
        marker=dict(size=14, color="#ff4444", line=dict(color="#fff", width=2)),
        text=[f"📍 {sl_:.2f}°, {sl_lon:.2f}°"],
        textposition="top center", textfont=dict(color="#fff", size=10),
        name="Selected", hoverinfo="text",
    ))
    fig.update_layout(
        height=height, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            showframe=False,
            showcoastlines=True,  coastlinecolor="rgba(0,198,255,.55)",
            showland=True,        landcolor="rgba(15,23,42,.9)",
            showocean=True,       oceancolor="rgba(2,6,23,.95)",
            showcountries=True,   countrycolor="rgba(0,198,255,.3)",
            showlakes=False,      bgcolor="rgba(0,0,0,0)",
            projection_type="natural earth",
            lataxis=dict(showgrid=True, gridcolor="rgba(0,198,255,.1)"),
            lonaxis=dict(showgrid=True, gridcolor="rgba(0,198,255,.1)"),
        ),
        legend=dict(font=dict(color="#94b8c8", size=10), bgcolor="rgba(0,0,0,0)"),
        dragmode="zoom",
    )
    result = st.plotly_chart(
        fig, use_container_width=True,
        on_select="rerun", selection_mode="points",
        key="flat_map_chart",
    )
    # capture click (P5 + P6)
    if result and hasattr(result, "selection"):
        pts = (result.selection or {}).get("points", [])
        if pts:
            p = pts[0]
            new_lat = p.get("lat") or p.get("y")
            new_lon = p.get("lon") or p.get("x")
            if new_lat is not None and new_lon is not None:
                st.session_state["clicked_lat"]     = float(new_lat)
                st.session_state["clicked_lon"]     = float(new_lon)
                # P5: reverse geocode
                st.session_state["clicked_country"] = reverse_geocode(
                    float(new_lat), float(new_lon)
                )
    return st.session_state["clicked_lat"], st.session_state["clicked_lon"]


# ══════════════════════════════════════════════════════════════════════════════
#  DOMAIN HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_location_metrics(lat_arr, lon_arr, data_2d,
                         lat_sel: float, lon_sel: float, variable: str) -> dict:
    arr = to_2d(data_2d)
    li  = int(np.abs(lat_arr - lat_sel).argmin())
    lj  = int(np.abs(lon_arr - lon_sel).argmin())
    return {
        "lat":   float(lat_arr[li]),
        "lon":   float(lon_arr[lj]),
        "value": round(float(arr[li, lj]), 3),
        "var":   variable,
    }


def classify_risk(stats: dict, variable: str) -> tuple:
    mean  = stats.get("mean", 0)
    std   = stats.get("std",  0)
    sprd  = std / (abs(mean) + 1e-9)
    hw = ("High ","inverse")  if variable=="Temperature" and (mean>30 or std>10) else \
         ("Medium ","off")    if variable=="Temperature" and mean>20 else \
         ("Low ","normal")    if variable=="Temperature" else \
         ("Moderate ","off")
    fl = ("High ","inverse")  if variable=="Precipitation" and (mean>5 or std>4) else \
         ("Medium ","off")    if variable=="Precipitation" and mean>2 else \
         ("Low ","normal")    if variable=="Precipitation" else \
         ("Medium ","off")   if sprd>0.5 else ("Low ","normal")
    sr = ("High ","inverse")  if variable=="Wind Speed" and mean>10 else \
         ("Medium ","off")    if variable=="Wind Speed" and mean>5 else \
         ("Low ","normal")    if variable=="Wind Speed" else \
         ("Elevated ","off") if std>8 else ("Low ","normal")
    return hw, fl, sr


def generate_ai_insight(stats: dict, variable: str, year: int, month: int) -> str:
    """
    P4: Always generates a fresh, data-driven insight from current stats.
    Example: "The global mean temperature anomaly in 2007 is 1.14 units above
              the long-term average, indicating moderate warming conditions."
    """
    mean    = stats.get("mean", 0)
    std     = stats.get("std",  0)
    maxv    = stats.get("max",  mean * 1.3)
    minv    = stats.get("min",  mean * 0.7)
    mo      = _MONTHS[max(0, min(11, month - 1))]
    base    = _BASELINES.get(variable, mean)
    anomaly = mean - base
    trend   = "above" if anomaly >= 0 else "below"
    sev     = ("significant" if abs(anomaly) > 2 else
               "moderate"    if abs(anomaly) > 0.5 else "minimal")
    vdesc   = ("relatively uniform"   if std < 3 else
               "moderately variable"  if std < 8 else
               "highly variable with strong regional contrasts")
    rng     = maxv - minv
    rdesc   = (f"extreme range of {rng:.1f}"  if rng > 40 else
               f"notable spread of {rng:.1f}" if rng > 15 else
               f"contained spread of {rng:.1f}")

    # Lead sentence (P4 example format)
    lead = (
        f"The global mean {variable.lower()} anomaly in **{year}** is "
        f"**{abs(anomaly):.2f} units {trend}** the long-term average "
        f"({base:.1f}), indicating **{sev} conditions**."
    )
    detail = (
        f"In {mo} {year}, the global {variable.lower()} averaged **{mean:.2f}**. "
        f"Distribution is {vdesc}, with {rdesc} units "
        f"(peak {maxv:.1f}, trough {minv:.1f})."
    )
    context = (
        "🔴 Elevated temperatures align with observed warming — tropics & mid-latitudes most affected."
        if variable == "Temperature" and anomaly > 1.5 else
        "🔵 Below-baseline temperatures suggest a cooling episode — possibly La Niña influence."
        if variable == "Temperature" and anomaly < -1.5 else
        "🌧 Heavy precipitation indicates active monsoon / storm systems. Flood risk elevated."
        if variable == "Precipitation" and mean > 4 else
        "💨 Strong winds indicate active synoptic circulation — elevated wildfire & sea-surface risk."
        if variable == "Wind Speed" and mean > 8 else
        f"📊 Pattern is consistent with typical {mo} climatology. Monitor for regional outliers."
    )
    return "\n\n".join([lead, detail, context])


def generate_country_summary(country: str, year: int, sbv: dict) -> str:
    t  = sbv.get("Temperature",   {}).get("mean", 14)
    p  = sbv.get("Precipitation", {}).get("mean", 2.5)
    h  = sbv.get("Humidity",      {}).get("mean", 60)
    w  = sbv.get("Wind Speed",    {}).get("mean", 6)
    td = "above-average" if t > 20 else "below-average" if t < 10 else "near-average"
    pd_ = "heavy rainfall" if p > 5 else "moderate rainfall" if p > 2 else "low rainfall"
    wd  = "high storm activity" if w > 10 else "moderate storm activity" if w > 5 else "low storm activity"
    hd  = "high humidity" if h > 70 else "moderate humidity" if h > 45 else "low humidity"
    return (
        f"**{country}** in **{year}** experienced {td} temperatures "
        f"(avg {t:.1f}°C), {pd_} ({p:.1f} mm/day), {hd} ({h:.0f}%), "
        f"and {wd} ({w:.1f} m/s)."
    )


def _build_timeseries_nc(uploaded_file, variable: str,
                         lat_sel: float, lon_sel: float) -> pd.DataFrame:
    if uploaded_file is None or not _XR:
        return pd.DataFrame()
    try:
        ds = _load_nc_bytes(uploaded_file.getvalue())
        da = _find_var(ds, variable)
        time_dim = next(
            (str(d) for d in list(da.dims) + [str(c) for c in da.coords]
             if str(d).lower() == "time"),
            None,
        )
        if time_dim is None:
            return pd.DataFrame()
        lat_name, lon_name = _detect_latlon(da)
        if lat_name is None or lon_name is None:
            return pd.DataFrame()
        da_pt  = da.sel({lat_name: lat_sel, lon_name: lon_sel}, method="nearest")
        times  = pd.to_datetime(da_pt[time_dim].values)
        values = da_pt.values.astype(float).ravel()
        return pd.DataFrame({"time": times, "value": values}).dropna()
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hdr_l, hdr_r = st.columns([2, 3])
with hdr_l:
    st.markdown("### 🌍 PyClimaExplorer Dashboard")
with hdr_r:
    view_mode = st.radio(
        "View",
        ["Map", "Time Series", "Compare", "Story Mode"],
        horizontal=True, label_visibility="collapsed",
    )

# ══════════════════════════════════════════════════════════════════════════════
#  THREE-COLUMN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
controls_col, globe_col, stats_col = st.columns([1, 2, 1])


# ══════════════════════════════════════════════════════════════════════════════
#  LEFT — CONTROLS
# ══════════════════════════════════════════════════════════════════════════════
with controls_col:

    st.markdown("<div class='section-title'>Controls</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload NetCDF (.nc)", type=["nc"],
        help="Any CF-compliant NetCDF. Selected variable drives all panels.",
    )
    if uploaded_file is not None:
        st.markdown(f"<div class='nc-badge'>✅ {uploaded_file.name}</div>",
                    unsafe_allow_html=True)
        if _XR:
            try:
                _dp = _load_nc_bytes(uploaded_file.getvalue())
                st.caption(f"Vars: {', '.join(list(_dp.data_vars)[:8])}")
            except Exception:
                pass
        else:
            st.warning("`xarray` not installed — run `pip install xarray netCDF4`")

    variable = st.selectbox(
        "Variable",
        ["Temperature","Precipitation","Wind Speed","Humidity","Sea Level Pressure"],
    )

    st.markdown("<div class='section-title'>Year / Month</div>", unsafe_allow_html=True)

    # P7: year stored in session_state so animation can update it without rerun
    year = st.slider("Year", 1980, 2024,
                     value=st.session_state.get("selected_year", 2007),
                     key="year_slider")
    st.session_state["selected_year"] = year

    month = st.slider("Month", 1, 12, 6)

    use_anomaly = st.checkbox("🔴 Show Anomaly Map", value=False,
                              help="Deviation from spatial mean")
    map_flat = st.checkbox("🗺 Interactive Flat Map (Map mode)",
                           value=st.session_state["map_toggle"],
                           help="Switch between 3-D globe and flat zoomable map")
    st.session_state["map_toggle"] = map_flat

    # ── Animation (P3) ────────────────────────────────────────────
    st.markdown("<div class='section-title'>Animation</div>", unsafe_allow_html=True)
    cp1, cp2 = st.columns(2)
    with cp1:
        play_btn  = st.button("▶ Play", use_container_width=True)
        stop_btn  = st.button("■ Stop", use_container_width=True)
    with cp2:
        anim_speed = st.select_slider(
            "Speed", options=["Slow","Normal","Fast"],
            value="Normal", label_visibility="collapsed",
        )
    anim_delay = {"Slow": 1.0, "Normal": 0.5, "Fast": 0.15}[anim_speed]

    if play_btn:
        st.session_state["anim_active"] = True
        st.session_state["anim_year"]   = 1980
    if stop_btn:
        st.session_state["anim_active"] = False

    # ── Country Analysis ──────────────────────────────────────────
    st.markdown("<div class='section-title'>🌐 Country Analysis</div>",
                unsafe_allow_html=True)
    selected_country = st.selectbox("Select Country", list(COUNTRY_COORDS.keys()))
    run_country = st.button("Analyze Country ▶", use_container_width=True)

    compare_year = None
    if view_mode == "Compare":
        compare_year = st.slider("Comparison Year", 1980, 2024, 2020)

    # ── Manual Coordinates ────────────────────────────────────────
    st.markdown("<div class='section-title'>📍 Manual Coordinates</div>",
                unsafe_allow_html=True)
    manual_lat = st.number_input(
        "Latitude", -90.0, 90.0,
        value=float(st.session_state["clicked_lat"]), step=0.5, format="%.2f",
    )
    manual_lon = st.number_input(
        "Longitude", -180.0, 180.0,
        value=float(st.session_state["clicked_lon"]), step=0.5, format="%.2f",
    )
    if st.button("Set Location", use_container_width=True):
        st.session_state["clicked_lat"]     = float(manual_lat)
        st.session_state["clicked_lon"]     = float(manual_lon)
        st.session_state["clicked_country"] = reverse_geocode(
            float(manual_lat), float(manual_lon)
        )
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHORITATIVE DATA FETCH  — P1: cached, P2: year/month drive slice
# ══════════════════════════════════════════════════════════════════════════════
lat, lon, data = get_data(variable, year, month, uploaded_file, warn=True)
data_2d        = to_2d(data)
display_data   = compute_anomaly(data_2d) if use_anomaly else data_2d.copy()
heatmap_json   = build_points(lat, lon, display_data)
gstats         = _stats_cached(data_2d)   # P1: cached stats


# ══════════════════════════════════════════════════════════════════════════════
#  ANIMATION LOOP  — P3: session_state guard, loops 1980 → selected_year
# ══════════════════════════════════════════════════════════════════════════════
anim_ph  = globe_col.empty()
anim_lbl = globe_col.empty()

if st.session_state["anim_active"]:
    ay  = st.session_state["anim_year"]
    end = year   # animate up to the selected year (P3)

    if ay > end:
        st.session_state["anim_active"] = False
        st.session_state["anim_year"]   = 1980
    else:
        al, aln, ad = get_data(variable, ay, month, uploaded_file)
        ad2   = to_2d(ad)
        adis  = compute_anomaly(ad2) if use_anomaly else ad2
        ah    = build_points(al, aln, adis)
        pct   = int((ay - 1980) / max(1, end - 1980) * 100)

        with anim_ph.container():
            st.markdown(
                f"<div style='font-size:.8rem;color:#00c6ff;text-align:center;margin-bottom:4px'>Year: <b>{ay}</b> / {end}</div><div class='anim-bar' style='width:{pct}%'></div>",
                unsafe_allow_html=True,
            )
            render_globe(ah, 460)

        _time.sleep(anim_delay)
        st.session_state["anim_year"] = ay + 1
        st.rerun()   # lightweight rerun to advance one frame


# ══════════════════════════════════════════════════════════════════════════════
#  CENTER — VISUALIZATION + PANELS
# ══════════════════════════════════════════════════════════════════════════════
with globe_col:

    st.markdown("<div class='section-title'>Visualization</div>",
                unsafe_allow_html=True)

    if use_anomaly:
        st.markdown(
            "<div class='anomaly-badge'>🔴 Anomaly mode — deviation from spatial mean</div>",
            unsafe_allow_html=True,
        )
    if uploaded_file is not None:
        st.markdown(f"<div class='nc-badge'>📂 {uploaded_file.name}</div>",
                    unsafe_allow_html=True)

    # ── MAP (P6) ──────────────────────────────────────────────────
    if view_mode == "Map":
        if map_flat:
            st.caption("🖱️ Click any point to select — panel below updates instantly.")
            lat_sel, lon_sel = render_flat_map(
                lat, lon, display_data, variable, use_anomaly, height=480,
            )
        else:
            st.caption("🌐 3-D globe — tick 'Interactive Flat Map' to switch.")
            render_globe(heatmap_json, 480)
            lat_sel = st.session_state["clicked_lat"]
            lon_sel = st.session_state["clicked_lon"]

    # ── TIME SERIES (P6) ─────────────────────────────────────────
    elif view_mode == "Time Series":
        render_globe(heatmap_json, 320)
        lat_sel = st.session_state["clicked_lat"]
        lon_sel = st.session_state["clicked_lon"]

        st.markdown("<div class='section-title'>Time Series</div>",
                    unsafe_allow_html=True)
        st.caption(f"Location: Lat {lat_sel:.2f}°  Lon {lon_sel:.2f}°")

        series = _build_timeseries_nc(uploaded_file, variable, lat_sel, lon_sel)
        if series.empty:
            series = _cached_generate_timeseries(variable, lat_sel, lon_sel)

        if not series.empty:
            fig_ts = px.line(series, x="time", y="value", template="plotly_dark",
                             title=f"{variable} — ({lat_sel:.1f}°, {lon_sel:.1f}°)")
            fig_ts.update_traces(line_color="#00c6ff", line_width=2.5)
            fig_ts.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e5e7eb", title_font_color="#00c6ff",
                height=260, margin=dict(l=10,r=10,t=40,b=10),
            )
            st.plotly_chart(fig_ts, use_container_width=True, key="ts_chart")
        else:
            st.info("No time-series data. Use Manual Coordinates or upload a multi-time NetCDF.")

    # ── COMPARE (P6) ─────────────────────────────────────────────
    elif view_mode == "Compare":
        lat2, lon2, data2 = get_data(variable, compare_year, month, uploaded_file)
        data2_2d = to_2d(data2)
        dd2      = compute_anomaly(data2_2d) if use_anomaly else data2_2d.copy()
        hm2      = build_points(lat2, lon2, dd2)

        g1, g2 = st.columns(2)
        with g1:
            st.caption(f"▶ Year {year}")
            render_globe(heatmap_json, 340)
        with g2:
            st.caption(f"▶ Year {compare_year}")
            render_globe(hm2, 340)

        st.markdown("---")
        s2   = _stats_cached(data2_2d)
        diff = s2["mean"] - gstats["mean"]
        ca, cb, cc = st.columns(3)
        ca.metric(f"{year} Mean",          f"{gstats['mean']:.2f}")
        cb.metric(f"{compare_year} Mean",  f"{s2['mean']:.2f}")
        cc.metric("Δ Mean",                f"{diff:+.2f}")

        lat_sel = st.session_state["clicked_lat"]
        lon_sel = st.session_state["clicked_lon"]

    # ── STORY MODE (P6) ──────────────────────────────────────────
    elif view_mode == "Story Mode":
        render_globe(heatmap_json, 340)
        st.markdown("---")
        st.markdown("<div class='section-title'>📖 Climate Narrative</div>",
                    unsafe_allow_html=True)

        for ev in (get_events(year) or []):
            st.write("•", ev)

        if st.checkbox("Generate narrated story", key="gen_story_cb"):
            if not st.session_state["story_text"]:
                with st.spinner("Generating story…"):
                    st.session_state["story_text"] = generate_story(
                        year, month, gstats
                    )
                st.session_state["show_story"] = True

        # reset story when year/variable changes
        if (st.session_state.get("_story_year") != year or
                st.session_state.get("_story_var") != variable):
            st.session_state["story_text"] = ""
            st.session_state["show_story"] = False
            st.session_state["_story_year"] = year
            st.session_state["_story_var"]  = variable

        if st.session_state["show_story"] and st.session_state["story_text"]:
            _story_body = st.session_state['story_text']
            st.markdown(
                f"<div class='insight-panel'>{_story_body}</div>",
                unsafe_allow_html=True,
            )
            if st.button("🔊 Play narration", key="play_narration_btn"):  # P6
                speak_story(st.session_state["story_text"])

        lat_sel = st.session_state["clicked_lat"]
        lon_sel = st.session_state["clicked_lon"]

    # ──────────────────────────────────────────────────────────────
    #  SELECTED LOCATION CLIMATE PANEL
    # ──────────────────────────────────────────────────────────────
    loc     = get_location_metrics(lat, lon, data_2d, lat_sel, lon_sel, variable)
    country = st.session_state.get("clicked_country", "")

    _country_badge = f"<span class='coord-badge'>🌍 {country}</span>" if country else ""
    _lat_v = f"{loc['lat']:.2f}"
    _lon_v = f"{loc['lon']:.2f}"
    st.markdown(
        f"<div class='location-panel'><h4>📍 Selected Location Climate</h4><span class='coord-badge'>Lat: {_lat_v}°</span><span class='coord-badge'>Lon: {_lon_v}°</span>{_country_badge}</div>",
        unsafe_allow_html=True,
    )

    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.metric(variable, f"{loc['value']:.2f}")

    extra_vars = [v for v in ["Temperature","Precipitation","Wind Speed","Humidity"]
                  if v != variable]
    for i, ev in enumerate(extra_vars[:3]):
        col = [lc2, lc3, lc4][i]
        try:
            el, eln, ed = get_data(ev, year, month, uploaded_file)
            eloc = get_location_metrics(el, eln, to_2d(ed), lat_sel, lon_sel, ev)
            col.metric(ev, f"{eloc['value']:.2f}")
        except Exception:
            col.metric(ev, "—")

    # ── CLIMATE RISK INDICATORS ───────────────────────────────────
    hw_r, fl_r, sr = classify_risk(gstats, variable)
    st.markdown("<div class='section-title'>⚠ Climate Risk Indicators</div>",
                unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    r1.metric("Heatwave Risk",  hw_r[0], delta_color=hw_r[1])
    r2.metric("Flood Risk",     fl_r[0], delta_color=fl_r[1])
    r3.metric("Storm Activity", sr[0],   delta_color=sr[1])

    # ── COUNTRY ANALYSIS ─────────────────────────────────────────
    if run_country:
        c_lat, c_lon = COUNTRY_COORDS[selected_country]
        sbv = {}
        for cv in ["Temperature","Precipitation","Wind Speed","Humidity"]:
            try:
                cl, cln, cd = get_data(cv, year, month, uploaded_file)
                cd2 = to_2d(cd)
                li  = int(np.abs(cl  - c_lat).argmin())
                lj  = int(np.abs(cln - c_lon).argmin())
                reg = cd2[max(0,li-3):li+4, max(0,lj-3):lj+4]
                sbv[cv] = {"mean": float(np.nanmean(reg)),
                           "max":  float(np.nanmax(reg)),
                           "min":  float(np.nanmin(reg))}
            except Exception:
                sbv[cv] = {"mean": 0}
        st.session_state["country_result"] = {
            "country": selected_country, "year": year, "stats": sbv,
            "summary": generate_country_summary(selected_country, year, sbv),
        }

    cr = st.session_state.get("country_result")
    if cr:
        st.markdown("<div class='section-title'>🌐 Country Climate Analysis</div>",
                    unsafe_allow_html=True)
        cst = cr["stats"]
        ca, cb, cc, cd_ = st.columns(4)
        ca.metric("Temp °C",   f"{cst.get('Temperature',  {}).get('mean',0):.1f}")
        cb.metric("Precip mm", f"{cst.get('Precipitation',{}).get('mean',0):.1f}")
        cc.metric("Humidity%", f"{cst.get('Humidity',     {}).get('mean',0):.0f}")
        cd_.metric("Wind m/s", f"{cst.get('Wind Speed',   {}).get('mean',0):.1f}")
        _cr_c = cr['country']; _cr_y = cr['year']; _cr_s = cr['summary']
        st.markdown(
            f"<div class='country-panel'><h4>🌍 {_cr_c} · {_cr_y}</h4>{_cr_s}</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  RIGHT — GLOBAL STATS  +  COLOR LEGEND  +  AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
with stats_col:

    # ── Global stats ──────────────────────────────────────────────
    st.markdown("<div class='section-title'>Global Stats</div>", unsafe_allow_html=True)

    st.markdown(
        f"<div class='metric-card'><b style='color:#94b8c8;font-size:.75rem'>GLOBAL MEAN</b><br><span style='font-size:1.4rem;color:#e5e7eb'>{gstats['mean']:.2f}</span></div>",
        unsafe_allow_html=True,
    )
    if "std" in gstats:
        st.markdown(
            f"<div class='metric-card'><b style='color:#94b8c8;font-size:.75rem'>STD DEV</b><br><span style='font-size:1.2rem;color:#e5e7eb'>{gstats['std']:.2f}</span></div>",
            unsafe_allow_html=True,
        )
    if "max" in gstats:
        sm1, sm2 = st.columns(2)
        sm1.metric("Max", f"{gstats['max']:.2f}")
        sm2.metric("Min", f"{gstats['min']:.2f}")

    # ── Color legend ──────────────────────────────────────────────
    st.markdown("<div class='section-title'>Color Legend</div>", unsafe_allow_html=True)
    cleg   = "RdBu_r" if use_anomaly else "RdYlBu"
    leg_a  = np.linspace(np.nanmin(display_data), np.nanmax(display_data), 100).reshape(1,-1)
    fig_l  = px.imshow(leg_a, aspect="auto", color_continuous_scale=cleg,
                       template="plotly_dark")
    fig_l.update_layout(
        height=70, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False, xaxis_visible=False, yaxis_visible=False,
    )
    st.plotly_chart(fig_l, use_container_width=True, key="legend_chart")
    lmn, lmx = st.columns(2)
    lmn.markdown(
        f"<div style='font-size:.72rem;color:#94b8c8'>{np.nanmin(display_data):.1f}</div>",
        unsafe_allow_html=True)
    _lmx_val = f"{np.nanmax(display_data):.1f}"
    lmx.markdown(
        f"<div style='font-size:.72rem;color:#94b8c8;text-align:right'>{_lmx_val}</div>",
        unsafe_allow_html=True)

    # ── AI Climate Insights (P4) ──────────────────────────────────
    st.markdown("<div class='section-title'> AI Climate Insights</div>",
                unsafe_allow_html=True)

    full_stats = {
        "mean": gstats.get("mean", 0),
        "std":  gstats.get("std",  abs(gstats.get("mean", 0)) * 0.1),
        "max":  gstats.get("max",  gstats.get("mean", 0) * 1.3),
        "min":  gstats.get("min",  gstats.get("mean", 0) * 0.7),
    }

    # P4: button always regenerates from current stats (never stale)
    if st.button("Generate Insight ✨", use_container_width=True, key="gen_insight_btn"):
        st.session_state["last_insight"]  = generate_ai_insight(full_stats, variable, year, month)
        st.session_state["insight_var"]   = variable
        st.session_state["insight_year"]  = year

    # Auto-generate on first load or when variable/year changes
    insight_stale = (
        not st.session_state["last_insight"]
        or st.session_state.get("insight_var")  != variable
        or st.session_state.get("insight_year") != year
    )
    if insight_stale:
        st.session_state["last_insight"]  = generate_ai_insight(full_stats, variable, year, month)
        st.session_state["insight_var"]   = variable
        st.session_state["insight_year"]  = year

    ins = st.session_state["last_insight"]
    if ins:
        _ins_var  = st.session_state['insight_var']
        _ins_year = st.session_state['insight_year']
        _ins_body = ins.replace(chr(10), '<br>')
        st.markdown(
            f"<div class='insight-panel'><span class='insight-label'>{_ins_var} · {_ins_year}</span>{_ins_body}</div>",
            unsafe_allow_html=True,
        )



    

    