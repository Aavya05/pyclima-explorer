import numpy as np

def compute_stats(data):

    stats = {}

    stats["mean"] = float(np.nanmean(data))
    stats["max"] = float(np.nanmax(data))
    stats["min"] = float(np.nanmin(data))

    anomaly = data - stats["mean"]

    stats["anomaly_mean"] = float(np.nanmean(anomaly))
    stats["anomaly_max"] = float(np.nanmax(anomaly))
    stats["anomaly_min"] = float(np.nanmin(anomaly))

    return stats