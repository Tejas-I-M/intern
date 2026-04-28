import sys
import os

# Fix path properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from visualization.config import DATA_PATH
from visualization.charts import monthly_revenue_chart

print("Running script...")

# Load dataset
resolved_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', DATA_PATH))
df = pd.read_csv(resolved_data_path)

print("Dataset Loaded Successfully ✅")
print("Columns:", df.columns)

# Generate chart
chart_path = monthly_revenue_chart(df)

print("Chart saved at:", chart_path)

from visualization.charts import country_revenue_chart

country_chart = country_revenue_chart(df)
print("Country chart saved at:", country_chart)

from visualization.charts import product_revenue_chart

product_chart = product_revenue_chart(df)
print("Product chart saved at:", product_chart)

from visualization.charts import top_customers_chart

customer_chart = top_customers_chart(df)
print("Top customers chart saved at:", customer_chart)

from visualization.insights import (
    top_country_insight,
    top_product_insight,
    top_customer_insight,
    revenue_trend_insight
)

print("\n--- INSIGHTS ---")

print(top_country_insight(df))
print(top_product_insight(df))
print(top_customer_insight(df))
print(revenue_trend_insight(df))