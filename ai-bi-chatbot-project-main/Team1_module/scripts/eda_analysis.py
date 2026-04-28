import pandas as pd
import matplotlib.pyplot as plt
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(BASE_DIR, "data", "processed", "master_dataset.csv")
report_path = os.path.join(BASE_DIR, "reports")

os.makedirs(report_path, exist_ok=True)

df = pd.read_csv(data_path)

# -----------------------------
# 1️⃣ Monthly Revenue
# -----------------------------
monthly = df.groupby("month_id")["sales"].sum()
plt.figure()
monthly.plot()
plt.title("Monthly Revenue Trend")
plt.xlabel("Month")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "1_monthly_revenue.png"))
plt.close()

# -----------------------------
# 2️⃣ Quarterly Revenue
# -----------------------------
quarterly = df.groupby("qtr_id")["sales"].sum()
plt.figure()
quarterly.plot(kind="bar")
plt.title("Quarterly Revenue")
plt.xlabel("Quarter")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "2_quarterly_revenue.png"))
plt.close()

# -----------------------------
# 3️⃣ Yearly Revenue
# -----------------------------
yearly = df.groupby("year_id")["sales"].sum()
plt.figure()
yearly.plot(kind="bar")
plt.title("Yearly Revenue")
plt.xlabel("Year")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "3_yearly_revenue.png"))
plt.close()

# -----------------------------
# 4️⃣ Revenue by Product Line
# -----------------------------
product = df.groupby("productline")["sales"].sum().sort_values()
plt.figure()
product.plot(kind="bar")
plt.title("Revenue by Product Line")
plt.xlabel("Product Line")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "4_productline_revenue.png"))
plt.close()

# -----------------------------
# 5️⃣ Revenue by Country
# -----------------------------
country = df.groupby("country")["sales"].sum().sort_values()
plt.figure()
country.plot(kind="bar")
plt.title("Revenue by Country")
plt.xlabel("Country")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "5_country_revenue.png"))
plt.close()

# -----------------------------
# 6️⃣ Revenue by Deal Size
# -----------------------------
deal = df.groupby("dealsize")["sales"].sum()
plt.figure()
deal.plot(kind="bar")
plt.title("Revenue by Deal Size")
plt.xlabel("Deal Size")
plt.ylabel("Revenue")
plt.savefig(os.path.join(report_path, "6_dealsize_revenue.png"))
plt.close()

# -----------------------------
# 7️⃣ Top 10 Customers
# -----------------------------
top_customers = df.groupby("customername")["sales"].sum().sort_values(ascending=False).head(10)
plt.figure()
top_customers.plot(kind="bar")
plt.title("Top 10 Customers by Revenue")
plt.xlabel("Customer")
plt.ylabel("Revenue")
plt.xticks(rotation=45)
plt.savefig(os.path.join(report_path, "7_top_customers.png"))
plt.close()

print("✅  Professional EDA Charts Generated Successfully!")