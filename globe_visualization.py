import plotly.graph_objects as go
import numpy as np

def create_globe(lat,lon,data):

    lon_grid,lat_grid = np.meshgrid(lon,lat)

    fig = go.Figure(data=[go.Surface(
        x=lon_grid,
        y=lat_grid,
        z=data,
        colorscale="RdYlBu",
        showscale=True
    )])

    fig.update_layout(
        title="Global Climate Globe",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Value",
        ),
        height=700
    )

    return fig