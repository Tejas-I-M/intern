def month_over_month_growth(df):

    df = df.sort_values("date")
    monthly = df.resample("M",on="date")["revenue"].sum()
    growth = monthly.pct_change().mean()
    return growth * 100

def year_over_year_growth(df):
    yearly = df.groupby("year")["revenue"].sum()
    growth = yearly.pct_change().mean()
    return growth * 100
