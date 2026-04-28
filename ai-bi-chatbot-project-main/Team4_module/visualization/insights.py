def top_country_insight(df):
    country = df.groupby('country')['sales'].sum().sort_values(ascending=False)
    top = country.index[0]
    second = country.index[1]

    return f"🌍 {top} is the top revenue-generating country, followed by {second}."


def country_contribution_insight(df):
    country = df.groupby('country')['sales'].sum()
    top = country.max()
    total = country.sum()
    percent = (top / total) * 100

    return f"📊 The top country contributes approximately {percent:.2f}% of total revenue."


def top_product_insight(df):
    product = df.groupby('productline')['sales'].sum().sort_values(ascending=False)

    return f"📦 {product.index[0]} is the best-performing product line."


def lowest_product_insight(df):
    product = df.groupby('productline')['sales'].sum().sort_values()

    return f"⚠️ {product.index[0]} shows the lowest performance and may need attention."


def top_customer_insight(df):
    customer = df.groupby('customername')['sales'].sum().sort_values(ascending=False)

    return f"👤 Top customer is {customer.index[0]} contributing highest revenue."


def customer_concentration_insight(df):
    customer = df.groupby('customername')['sales'].sum().sort_values(ascending=False)

    top5 = customer.head(5).sum()
    total = customer.sum()

    return f"📌 Top 5 customers contribute {(top5/total)*100:.2f}% of total revenue."


def revenue_trend_insight(df):
    monthly = df.groupby(df['orderdate'])['sales'].sum()

    trend = monthly.pct_change().mean()

    if trend > 0:
        return "📈 Overall revenue trend is increasing."
    else:
        return "📉 Revenue trend shows decline."


def peak_month_insight(df):
    df['month'] = df['orderdate'].dt.month
    month_sales = df.groupby('month')['sales'].sum()

    peak = month_sales.idxmax()

    return f"🔥 Month {peak} records the highest sales."


def dealsize_insight(df):
    deals = df.groupby('dealsize')['sales'].sum().sort_values(ascending=False)

    return f"💼 {deals.index[0]} deals contribute the highest revenue."