from fastapi import FastAPI
from typing import Dict, Any
import pandas as pd

# ✅ Initialize app
app = FastAPI()

# ✅ Import engine logic
from analytics_engine.core.engine import process_query
from analytics_engine.core.query_validator import validate_query
from analytics_engine.utils.data_loader import load_dataset
from analytics_engine.processors.filter_processor import apply_filters
from analytics_engine.forecasting.forecast_engine import forecast_metric


# ✅ Root endpoint
@app.get("/")
def home():
    return {"message": "AI BI Chatbot API is running 🚀"}


# ✅ MAIN ENDPOINT (FIXED FOR NLP INTEGRATION)
@app.post("/analyze")
def analyze(query: Dict[str, Any]):
    """
    Receives structured JSON from NLP module
    Example:
    {
        "action": "get_top_products",
        "limit": 5,
        "metric": "sales",
        "time": "last month"
    }
    """
    return process_query(query)


# ---------------- TESTING ENDPOINTS ----------------

# 1️⃣ NLP Validation Test (optional)
@app.post("/test/validate")
def test_validate(query: Dict[str, Any]):
    try:
        result = validate_query(query)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 2️⃣ Data Loader Test
@app.get("/test/data")
def test_data():
    df = load_dataset()
    return {
        "rows": len(df),
        "columns": list(df.columns)
    }


# 3️⃣ Filter Test
@app.post("/test/filter")
def test_filter(query: Dict[str, Any]):
    return process_query(query)


# 4️⃣ Engine Test
@app.post("/test/engine")
def test_engine(query: Dict[str, Any]):
    return process_query(query)


# 5️⃣ Forecast Test
@app.get("/test/forecast")
def test_forecast():
    try:
        df = load_dataset()

        if "orderdate" not in df.columns:
            return {"status": "error", "message": "orderdate column missing"}

        if "sales" not in df.columns:
            return {"status": "error", "message": "sales column missing"}

        df["orderdate"] = pd.to_datetime(df["orderdate"], errors="coerce")
        df = df.dropna(subset=["orderdate", "sales"])
        df = df.sort_values("orderdate")

        df_grouped = df.groupby("orderdate")["sales"].sum().reset_index()
        df_grouped.columns = ["date", "sales"]

        return forecast_metric(df_grouped, metric="sales")

    except Exception as e:
        return {"status": "error", "message": str(e)}