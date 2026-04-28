import pandas as pd


class InsightBuilder:
    """Build a few simple deterministic insight strings from dataset signals."""

    def build(self, df, data_quality, analysis_results=None):
        analysis_results = analysis_results or {}
        insights = []

        row_count = int(data_quality.get('dataset_shape', {}).get('row_count', len(df)))
        column_count = int(data_quality.get('dataset_shape', {}).get('column_count', len(df.columns)))
        insights.append(f"Dataset contains {row_count} rows across {column_count} columns.")

        quality_score = data_quality.get('data_quality_score')
        missing_pct = data_quality.get('missing_percentage', 0)
        duplicate_pct = data_quality.get('duplicate_percentage', 0)
        if quality_score is not None:
            insights.append(
                f"Data quality score is {quality_score:.2f}/100 with {missing_pct:.2f}% missing values and {duplicate_pct:.2f}% duplicate rows."
            )

        if 'Total Amount' in df.columns:
            revenue_series = pd.to_numeric(df['Total Amount'], errors='coerce').dropna()
            if not revenue_series.empty:
                total_revenue = float(revenue_series.sum())
                insights.append(f"Total mapped revenue is {total_revenue:.2f} across the available records.")

        if 'Date' in df.columns and 'Total Amount' in df.columns:
            date_series = pd.to_datetime(df['Date'], errors='coerce')
            revenue_series = pd.to_numeric(df['Total Amount'], errors='coerce')
            trend_df = pd.DataFrame({'Date': date_series, 'Total Amount': revenue_series}).dropna()

            if len(trend_df) >= 2:
                trend_df['Period'] = trend_df['Date'].dt.to_period('M').astype(str)
                trend_summary = trend_df.groupby('Period', as_index=False)['Total Amount'].sum()
                if len(trend_summary) >= 2:
                    first_value = float(trend_summary.iloc[0]['Total Amount'])
                    last_value = float(trend_summary.iloc[-1]['Total Amount'])
                    if last_value > first_value:
                        insights.append("Revenue trend is moving upward between the earliest and latest available periods.")
                    elif last_value < first_value:
                        insights.append("Revenue trend is moving downward between the earliest and latest available periods.")
                    else:
                        insights.append("Revenue trend is stable between the earliest and latest available periods.")

        if not insights:
            insights.append("Dataset uploaded successfully and is ready for analysis.")

        return insights[:4]
