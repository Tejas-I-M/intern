import re
from analytics_engine.config import METRIC_COLUMNS, SUPPORTED_AGGREGATIONS

def validate_query(query):

    # 🔥 CASE 1: Already parsed (DICT) → SAFE
    if isinstance(query, dict):
        if "metric" not in query:
            raise ValueError("Metric Missing")
        return True

    # 🔥 CASE 2: Raw string → process
    elif isinstance(query, str):
        query = query.lower()

        metric = None
        aggregation = None
        limit = None
        intent = "aggregation"

        # Detect metric
        for col in METRIC_COLUMNS:
            if col in query:
                metric = col
                break

        # Detect aggregation
        for agg in SUPPORTED_AGGREGATIONS:
            if agg in query:
                aggregation = agg
                break

        if not aggregation:
            aggregation = "sum"

        # Detect TOP N
        if "top" in query:
            intent = "ranking"
            match = re.search(r'\d+', query)
            if match:
                limit = int(match.group())

        if not metric:
            raise ValueError("Metric Missing")

        return {
            "intent": intent,
            "metric": metric,
            "aggregation": aggregation,
            "limit": limit
        }

    else:
        raise ValueError("Invalid query format")