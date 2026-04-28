def total_revenue(df):
    return df["revenue"].sum()

def profit_margin(df):
    revenue = df["revenue"].sum()
    profit = df["profit"].sum()

    if revenue == 0:
        return 0
    return(profit/revenue) * 100

def average_order_value(df):
    if "order_id" not in df.columns:
        return 0
    return df["revenue"].sum() / df["order_id"].nunique()
