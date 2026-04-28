import re
from typing import Dict, Any


# Configurable schema (can later move to JSON/YAML)
METRIC_SYNONYMS = {
    "sales": ["sales", "revenue", "earnings"],
    "profit": ["profit", "margin"]
}

GROUP_BY_FIELDS = [
    "productline",
    "country",
    "customername",
    "territory",
    "dealsize",
    "month",
    "quarter",
    "year"
]

FILTER_PATTERNS = {
    "year_id": r"(?:year|year_id)\s*(\d{4})",
    "month_id": r"(?:month|month_id)\s*(\d{1,2})",
    "qtr_id": r"(?:qtr|quarter|qtr_id)\s*(\d)"
}


def extract_metric(text: str) -> str:
    for metric, synonyms in METRIC_SYNONYMS.items():
        for word in synonyms:
            if word in text:
                return metric
    return "sales"  # safe default


def extract_group_by(text: str) -> str:
    for field in GROUP_BY_FIELDS:
        if field in text:
            return field
    return None


def extract_top_n(text: str) -> int:
    match = re.search(r"(top|bottom)\s+(\d+)", text)
    if match:
        return int(match.group(2))
    return None


def extract_filters(text: str) -> Dict[str, Any]:
    filters = {}

    for key, pattern in FILTER_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            filters[key] = int(match.group(1))

    return filters


def extract_entities(text: str) -> Dict[str, Any]:
    text = text.lower()

    return {
        "metric": extract_metric(text),
        "group_by": extract_group_by(text),
        "top_n": extract_top_n(text),
        "filters": extract_filters(text)
    }