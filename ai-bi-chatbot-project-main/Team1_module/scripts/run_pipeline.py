import pandas as pd
import matplotlib.pyplot as plt
import os

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define correct paths
data_path = os.path.join(BASE_DIR, "data", "processed", "master_dataset.csv")
report_path = os.path.join(BASE_DIR, "reports")

# Create reports folder if not exists
os.makedirs(report_path, exist_ok=True)

# Load dataset
df = pd.read_csv(data_path)

# -----------------------------
# Monthly Revenue
# -----------------------------
if "month" in df.columns and "revenue" in df.columns:
    monthly = df.groupby("month")["revenue"].sum()

    plt.figure()
    monthly.plot()
    plt.title("Monthly Revenue Trend")
    plt.xlabel("Month")
    plt.ylabel("Revenue")
    plt.savefig(os.path.join(report_path, "monthly_revenue.png"))
    plt.close()

# -----------------------------
# Quarterly Revenue
# -----------------------------
if "quarter" in df.columns and "revenue" in df.columns:
    quarterly = df.groupby("quarter")["revenue"].sum()

    plt.figure()
    quarterly.plot(kind="bar")
    plt.title("Quarterly Revenue")
    plt.xlabel("Quarter")
    plt.ylabel("Revenue")
    plt.savefig(os.path.join(report_path, "quarterly_revenue.png"))
    plt.close()

# -----------------------------
# Profit Trend
# -----------------------------
if "profit" in df.columns:
    profit_trend = df.groupby("month")["profit"].sum()

    plt.figure()
    profit_trend.plot()
    plt.title("Monthly Profit Trend")
    plt.xlabel("Month")
    plt.ylabel("Profit")
    plt.savefig(os.path.join(report_path, "profit_trend.png"))
    plt.close()

print("✅ Professional EDA Charts Generated Successfully!")