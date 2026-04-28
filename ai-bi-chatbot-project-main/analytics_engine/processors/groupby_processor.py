def apply_groupby(df, group_columns, metric, aggregation):
    grouped_df = (
        df.groupby(group_columns)[metric]
        .agg(aggregation)
        .reset_index()
    )

    return grouped_df