METRIC_MAP = {
    "sales": "sales",
    "revenue": "sales",
    "income": "sales",
    "amount": "sales",
    "profit": "sales",
    "earnings": "sales"
}

def map_metric(metric):
    metric = metric.lower()

    if metric in METRIC_MAP:
        return METRIC_MAP[metric]

    raise ValueError(f"Unsupported metric: {metric}")