from analytics_engine.utils.data_loader import load_dataset
from analytics_engine.utils.metric_mapper import map_metric
from analytics_engine.utils.response_formatter import success_response, error_response
from analytics_engine.utils.query_parser import parse_query

from analytics_engine.core.query_validator import validate_query

from analytics_engine.processors.filter_processor import apply_filters
from analytics_engine.processors.groupby_processor import apply_groupby
from analytics_engine.processors.ranking_processor import apply_ranking

from analytics_engine.forecasting.forecast_engine import forecast_metric
from analytics_engine.insights.insight_generator import generate_insight


def process_query(query):
    try:
        df = load_dataset()

        # ✅ Ensure structured input
        if not isinstance(query, dict):
            raise ValueError("Query must be structured JSON")

        print("🔥 Received Query from NLP:", query)

        # ---------------- 🔄 NORMALIZATION LAYER ----------------
        # Convert NLP format → Engine format

        # action → intent
        if "action" in query:
            action_map = {
                "get_top_products": "ranking_query",
                "sales_trend": "sales_query",
                "filtered_search": "sales_query",
                "forecast": "forecast_query",
                "insights": "insight_query"
            }
            query["intent"] = action_map.get(query["action"], query.get("intent"))

        # limit → top_n
        if "limit" in query:
            query["top_n"] = query["limit"]

        # time → filters (basic handling)
        if "time" in query:
            if "filters" not in query or query["filters"] is None:
                query["filters"] = {}

            query["filters"]["time"] = query["time"]

        # Ensure intent is string
        query["intent"] = str(query.get("intent"))

        # -------------------------------------------------------

        validate_query(query)

        intent = query.get("intent")

        # Forecast flag
        if intent == "forecast_query":
            query["forecast"] = True

        metric = map_metric(query.get("metric", "sales"))

        # Apply filters
        df = apply_filters(df, query.get("filters"))

        # Grouping
        if query.get("group_by"):
            df = apply_groupby(
                df,
                query["group_by"],
                metric,
                query.get("aggregation", "sum")
            )

        # Ranking
        if query.get("top_n"):
            df = apply_ranking(df, metric, query["top_n"])

        # Forecast
        if query.get("forecast"):
            forecast = forecast_metric(df, metric)
            return success_response(forecast)

        # Insights
        insight = generate_insight(df, metric)

        return success_response(
            df.to_dict(orient="records"),
            insight
        )

    except Exception as e:
        return error_response(str(e))