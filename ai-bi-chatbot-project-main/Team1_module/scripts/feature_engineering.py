def add_time_features(df):
    if 'date' in df.columns:
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['month_name'] = df['date'].dt.month_name()
    return df


def add_kpis_sales(df):
    if 'quantity' in df.columns and 'price' in df.columns:
        df['revenue'] = df['quantity'] * df['price']
    return df


def add_kpis_finance(df):
    if 'revenue' in df.columns and 'cost' in df.columns:
        df['profit'] = df['revenue'] - df['cost']
    return df