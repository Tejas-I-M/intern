def apply_filters(df, filters):
    
    if not filters:
        return df
    
    for column, value in filters.items():
        if isinstance(value, list):
            df = df[df[column].isin(value)]
        else:
            df = df[df[column] == value]

    return df
