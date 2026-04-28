class DataQualityService:
    """Compute simple dataset quality metrics for backend responses."""

    def calculate(self, df):
        row_count = int(len(df))
        column_count = int(len(df.columns))
        total_cells = max(row_count * max(column_count, 1), 1)

        missing_cells = int(df.isna().sum().sum())
        missing_percentage = round((missing_cells / total_cells) * 100, 2)

        duplicate_rows = int(df.duplicated(keep='first').sum())
        duplicate_percentage = round((duplicate_rows / max(row_count, 1)) * 100, 2)

        score = 100.0
        score -= missing_percentage
        score -= duplicate_percentage
        score = max(0.0, min(100.0, score))

        return {
            'data_quality_score': round(score, 2),
            'missing_percentage': missing_percentage,
            'duplicate_percentage': duplicate_percentage,
            'dataset_shape': {
                'row_count': row_count,
                'column_count': column_count
            }
        }
