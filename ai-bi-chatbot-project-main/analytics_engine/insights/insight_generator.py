def generate_insight(df, metric):

    if df.empty:
        return "No Data Available."
   
    top_row = df.iloc[0]
    column = df.columns[0]

    return f"{top_row[column]} has the highest {metric}."
