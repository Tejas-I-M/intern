import pandas as pd
import matplotlib.pyplot as plt
import os
from visualization.config import REPORT_PATH

print("charts.py loaded")


def _style_and_save(fig, ax, file_path, x_label, y_label, caption):
    """Apply consistent labels and caption, then save chart."""
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(axis='y', linestyle='--', alpha=0.35)
    fig.autofmt_xdate(rotation=30)
    fig.text(0.5, 0.01, caption, ha='center', va='bottom', fontsize=9, color='#444')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(file_path, dpi=140)
    plt.close(fig)


def monthly_revenue_chart(df):
    os.makedirs(REPORT_PATH, exist_ok=True)

    # Convert date
    df['orderdate'] = pd.to_datetime(df['orderdate'])

    # Group monthly
    monthly = df.groupby(df['orderdate'].dt.to_period('M'))['sales'].sum()

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5.5))
    monthly.index = monthly.index.astype(str)
    monthly.plot(kind='line', title="Monthly Revenue Trend", marker='o', linewidth=2, color='#1f77b4', ax=ax)

    # Point labels for readability
    for x, y in zip(range(len(monthly)), monthly.values):
        ax.annotate(f"{y:,.0f}", (x, y), textcoords='offset points', xytext=(0, 6), ha='center', fontsize=8)

    # Save
    file_path = os.path.join(REPORT_PATH, "1_monthly_revenue.png")
    _style_and_save(
        fig,
        ax,
        file_path,
        x_label="Month",
        y_label="Revenue",
        caption="Figure 1: Monthly revenue aggregated from transactional sales data."
    )

    return file_path

def country_revenue_chart(df):
    import os
    import matplotlib.pyplot as plt

    os.makedirs(REPORT_PATH, exist_ok=True)

    # Group by country
    country = df.groupby('country')['sales'].sum().sort_values(ascending=False)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = country.plot(kind='bar', title="Country-wise Revenue", color='#2ca02c', ax=ax)

    for bar in bars.patches:
        height = bar.get_height()
        if pd.notna(height):
            ax.annotate(f"{height:,.0f}",
                        (bar.get_x() + bar.get_width() / 2, height),
                        textcoords='offset points',
                        xytext=(0, 4),
                        ha='center',
                        fontsize=8)

    # Save
    file_path = os.path.join(REPORT_PATH, "2_country_revenue.png")
    _style_and_save(
        fig,
        ax,
        file_path,
        x_label="Country",
        y_label="Revenue",
        caption="Figure 2: Revenue contribution by country."
    )

    return file_path

def product_revenue_chart(df):
    import os
    import matplotlib.pyplot as plt

    os.makedirs(REPORT_PATH, exist_ok=True)

    # Group by product line
    product = df.groupby('productline')['sales'].sum().sort_values(ascending=False)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = product.plot(kind='bar', title="Product-wise Revenue", color='#ff7f0e', ax=ax)

    for bar in bars.patches:
        height = bar.get_height()
        if pd.notna(height):
            ax.annotate(f"{height:,.0f}",
                        (bar.get_x() + bar.get_width() / 2, height),
                        textcoords='offset points',
                        xytext=(0, 4),
                        ha='center',
                        fontsize=8)

    # Save
    file_path = os.path.join(REPORT_PATH, "3_product_revenue.png")
    _style_and_save(
        fig,
        ax,
        file_path,
        x_label="Product Line",
        y_label="Revenue",
        caption="Figure 3: Revenue by product line."
    )

    return file_path

def top_customers_chart(df):
    import os
    import matplotlib.pyplot as plt

    os.makedirs(REPORT_PATH, exist_ok=True)

    # Top 10 customers by revenue
    customers = (
        df.groupby('customername')['sales']
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # Plot
    fig, ax = plt.subplots(figsize=(11, 5.8))
    bars = customers.plot(kind='bar', title="Top 10 Customers by Revenue", color='#9467bd', ax=ax)

    for bar in bars.patches:
        height = bar.get_height()
        if pd.notna(height):
            ax.annotate(f"{height:,.0f}",
                        (bar.get_x() + bar.get_width() / 2, height),
                        textcoords='offset points',
                        xytext=(0, 4),
                        ha='center',
                        fontsize=8)

    # Save
    file_path = os.path.join(REPORT_PATH, "4_top_customers.png")
    _style_and_save(
        fig,
        ax,
        file_path,
        x_label="Customer Name",
        y_label="Revenue",
        caption="Figure 4: Top 10 customers ranked by revenue."
    )

    return file_path