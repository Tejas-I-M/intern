from typing import Dict, Any


def generate_response(result: Dict[str, Any]) -> str:

    # ❌ Error handling
    if result.get("status") == "error":
        return f"❌ Error: {result.get('message')}"

    data = result.get("data")
    insight = result.get("insight", "")

    if not data:
        return "⚠️ No data found for your query."

    # 📈 Forecast handling
    if isinstance(data, dict) and "forecast" in data:
        return f"📈 Forecasted Value: {data['forecast']}"

    # 📊 Tabular data (MAIN IMPROVEMENT)
    if isinstance(data, list):
        preview = data[:5]

        response = "✅ Top Results:\n"

        for i, row in enumerate(preview, 1):

            # Smart field selection (clean output)
            product = row.get("productline") or row.get("productcode") or "N/A"
            sales = f"{row.get('sales', 0):,.2f}"
            country = row.get("country", "")

            response += f"{i}. {product} | Sales: {sales}"

            if country:
                response += f" | Country: {country}"

            response += "\n"

        # Add insight if available
        if insight:
            response += f"\n💡 Insight: {insight}"

        return response

    # 📌 Dictionary result (non-forecast)
    if isinstance(data, dict):
        formatted = "\n".join([f"{k}: {v}" for k, v in data.items()])
        return f"✅ Result:\n{formatted}"

    return "⚠️ Unable to interpret response."