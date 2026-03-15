import plotly.express as px
import pandas as pd

def plot_time_series(values):

    df = pd.DataFrame({
        "Month":range(len(values)),
        "Value":values
    })

    fig = px.line(df,x="Month",y="Value",title="Climate Time Series")

    return fig