def apply_ranking(df, metric, top_n=None, order="desc"):
    ascending = True if order == "asc" else False
    df = df.sort_values(by=metric, ascending=ascending)
    if top_n:
        df=df.head(top_n)
    return df