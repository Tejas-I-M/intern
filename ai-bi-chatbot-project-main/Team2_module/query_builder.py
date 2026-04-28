from typing import Dict, Any


DEFAULT_AGGREGATIONS = {
    "sales_query": "sum",
    "ranking_query": "sum",
    "comparison_query": "sum",
    "forecast_query": "sum"
}


def build_query(intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:

    query = {
        "intent": intent,
        "metric": entities.get("metric"),
        "aggregation": DEFAULT_AGGREGATIONS.get(intent, "sum"),
        "group_by": entities.get("group_by"),
        "filters": entities.get("filters", {})
    }

    # Ranking logic
    if intent == "ranking_query":
        query["top_n"] = entities.get("top_n", 5)  # default if not specified

    # Forecast logic
    if intent == "forecast_query":
        query["forecast"] = True

    return query