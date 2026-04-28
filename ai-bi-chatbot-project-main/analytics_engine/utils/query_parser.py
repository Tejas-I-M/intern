def parse_query(query_text):

    # 🔥 FORCE STRING ALWAYS (NO MATTER WHAT)
    query_text = str(query_text).lower()

    result = {}

    if "sales" in query_text:
        result["metric"] = "sales"

    if "month" in query_text:
        result["group_by"] = "month_id"
    elif "year" in query_text:
        result["group_by"] = "year_id"
    elif "country" in query_text:
        result["group_by"] = "country"
    elif "product" in query_text:
        result["group_by"] = "productline"
    elif "customer" in query_text:
        result["group_by"] = "customername"

    result["aggregation"] = "sum"

    import re
    match = re.search(r"top (\d+)", query_text)
    if match:
        result["top_n"] = int(match.group(1))

    if "forecast" in query_text or "predict" in query_text:
        result["forecast"] = True

    return result