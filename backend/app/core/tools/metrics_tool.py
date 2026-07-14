import math
from typing import List, Dict, Any, Optional

def analyze_metrics(metrics_series: List[Dict[str, Any]], threshold_z: float = 2.0) -> List[Dict[str, Any]]:
    """
    Scans a series of metric data points, running simple Z-score analysis to identify anomalous periods.
    """
    anomalies = []
    if len(metrics_series) < 3:
        return anomalies  # Not enough data points to compute variance
        
    keys_to_check = ["cpu_percent", "memory_percent", "latency_ms", "error_rate"]
    
    for key in keys_to_check:
        # Extract series values
        values = [item[key] for item in metrics_series if item.get(key) is not None]
        if len(values) < 3:
            continue
            
        # Calculate mean & standard deviation
        n = len(values)
        mean_val = sum(values) / n
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            continue
            
        for item in metrics_series:
            val = item.get(key)
            if val is not None:
                z = (val - mean_val) / std_dev
                if abs(z) > threshold_z:
                    anomalies.append({
                        "timestamp": item.get("timestamp"),
                        "metric": key,
                        "value": val,
                        "mean": round(mean_val, 2),
                        "z_score": round(z, 2),
                        "deviation_desc": f"Spike of {val} detected (average is {round(mean_val, 2)})" if z > 0 else f"Drop of {val} detected (average is {round(mean_val, 2)})"
                    })
                    
    return anomalies
