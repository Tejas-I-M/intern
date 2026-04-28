import os
import sys
import traceback
import pandas as pd
import matplotlib

# Async workers must use a non-GUI backend to avoid tkinter thread errors.
matplotlib.use('Agg')

# Resolve project root so Team4 imports are available from Team5 backend runtime.
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
backend_dir = os.path.dirname(current_dir)
team5_dir = os.path.dirname(backend_dir)
project_root = os.path.dirname(team5_dir)
team4_root = os.path.join(project_root, 'Team4_module')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if team4_root not in sys.path:
    sys.path.insert(0, team4_root)

try:
    from Team4_module.visualization.insights import (
        top_country_insight,
        country_contribution_insight,
        top_product_insight,
        lowest_product_insight,
        top_customer_insight,
        customer_concentration_insight,
        revenue_trend_insight,
        peak_month_insight,
        dealsize_insight,
    )
    TEAM4_INSIGHTS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Team4 insights import failed: {e}")
    TEAM4_INSIGHTS_AVAILABLE = False

try:
    from Team4_module.visualization.charts import (
        monthly_revenue_chart,
        country_revenue_chart,
        product_revenue_chart,
        top_customers_chart,
    )
    TEAM4_CHARTS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Team4 charts import failed: {e}")
    TEAM4_CHARTS_AVAILABLE = False


class Team4VisualizationAdapter:
    """Adapter to run Team4 visualization functions on Team5 uploaded datasets."""

    def __init__(self):
        self.insights_available = TEAM4_INSIGHTS_AVAILABLE
        self.charts_available = TEAM4_CHARTS_AVAILABLE
        self.available = self.insights_available or self.charts_available

    def _pick_column(self, df, candidates):
        for col in candidates:
            if col in df.columns:
                return col
        lowered = {str(c).lower(): c for c in df.columns}
        for col in candidates:
            lc = str(col).lower()
            if lc in lowered:
                return lowered[lc]
        return None

    def _clean_dimension_series(self, series):
        """Normalize categorical dimensions and drop placeholder-like unknown values."""
        if series is None:
            return None

        cleaned = series.astype(str).str.strip()
        lowered = cleaned.str.lower()
        invalid_tokens = {'', 'unknown', 'n/a', 'na', 'none', 'null', 'nan'}
        cleaned = cleaned.where(~lowered.isin(invalid_tokens), pd.NA)
        return cleaned

    def _derive_dealsize(self, series):
        numeric = pd.to_numeric(series, errors='coerce')
        if numeric.notna().sum() == 0:
            return pd.Series(['Medium'] * len(series))

        q1 = numeric.quantile(0.33)
        q2 = numeric.quantile(0.66)

        def bucket(x):
            if pd.isna(x):
                return 'Medium'
            if x <= q1:
                return 'Small'
            if x <= q2:
                return 'Medium'
            return 'Large'

        return numeric.apply(bucket)

    def _to_team4_frame(self, df):
        """Transform input dataframe to Team4 expected schema."""
        out = pd.DataFrame(index=df.index)

        date_col = self._pick_column(df, ['orderdate', 'Date', 'date', 'Order Date', 'transaction_date', 'purchase_dt', 'transaction date'])
        sales_col = self._pick_column(df, ['sales', 'Total Amount', 'amount', 'order_value', 'revenue', 'net_sales', 'total spent'])
        country_col = self._pick_column(df, ['country', 'Country', 'nation', 'Region', 'region', 'Location', 'location', 'state', 'city'])
        product_col = self._pick_column(df, ['productline', 'Product Category', 'category', 'item_category', 'product', 'item', 'sku'])
        customer_col = self._pick_column(df, ['customername', 'Customer Name', 'Customer ID', 'customer_id', 'customer', 'client', 'buyer'])
        deal_col = self._pick_column(df, ['dealsize', 'deal_size'])

        if date_col is None or sales_col is None:
            return None

        out['orderdate'] = pd.to_datetime(df[date_col], errors='coerce')
        out['sales'] = pd.to_numeric(df[sales_col], errors='coerce')

        out['country'] = self._clean_dimension_series(df[country_col]) if country_col else pd.Series(pd.NA, index=df.index)
        out['productline'] = self._clean_dimension_series(df[product_col]) if product_col else pd.Series(pd.NA, index=df.index)
        out['customername'] = self._clean_dimension_series(df[customer_col]) if customer_col else pd.Series(pd.NA, index=df.index)

        if deal_col:
            out['dealsize'] = df[deal_col].astype(str)
        else:
            out['dealsize'] = self._derive_dealsize(out['sales'])

        out = out.dropna(subset=['orderdate', 'sales'])
        return out if not out.empty else None

    def _has_groupable_dimension(self, df, column_name, min_groups=2):
        """Return True when a categorical dimension has enough valid groups for a bar chart."""
        if column_name not in df.columns:
            return False

        series = df[column_name].dropna()
        if series.empty:
            return False

        return int(series.astype(str).nunique()) >= int(min_groups)

    def _clear_known_chart_files(self):
        """Delete old Team4 chart files so stale charts do not leak into new reports."""
        try:
            from Team4_module.visualization.config import REPORT_PATH
        except Exception:
            return

        known_files = [
            '1_monthly_revenue.png',
            '2_country_revenue.png',
            '3_product_revenue.png',
            '4_top_customers.png',
        ]

        for name in known_files:
            path = os.path.join(REPORT_PATH, name)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                continue

    def _generate_insights(self, team4_df):
        if not self.insights_available:
            return []

        insights = []
        insight_funcs = [
            top_country_insight,
            country_contribution_insight,
            top_product_insight,
            lowest_product_insight,
            top_customer_insight,
            customer_concentration_insight,
            revenue_trend_insight,
            peak_month_insight,
            dealsize_insight,
        ]

        for func in insight_funcs:
            try:
                insights.append(func(team4_df.copy()))
            except Exception:
                continue

        return insights

    def _generate_charts(self, team4_df):
        if not self.charts_available:
            return []

        charts = []
        self._clear_known_chart_files()

        chart_specs = [('monthly_revenue', monthly_revenue_chart, None)]

        if self._has_groupable_dimension(team4_df, 'country'):
            chart_specs.append(('country_revenue', country_revenue_chart, 'country'))

        if self._has_groupable_dimension(team4_df, 'productline'):
            chart_specs.append(('product_revenue', product_revenue_chart, 'productline'))

        if self._has_groupable_dimension(team4_df, 'customername'):
            chart_specs.append(('top_customers', top_customers_chart, 'customername'))

        for name, func, dim in chart_specs:
            try:
                chart_df = team4_df.copy()
                if dim:
                    chart_df = chart_df.dropna(subset=[dim])
                if chart_df.empty:
                    continue

                path = func(chart_df)
                if path and os.path.exists(path):
                    charts.append({'name': name, 'path': path})
            except Exception:
                continue

        return charts

    def build_payload(self, df):
        """Return Team4 visualization payload for API responses."""
        try:
            if not self.available:
                return {
                    'enabled': False,
                    'message': 'Team4 visualization module not available',
                    'insights': [],
                    'charts': []
                }

            team4_df = self._to_team4_frame(df)
            if team4_df is None:
                return {
                    'enabled': False,
                    'message': 'Required fields for Team4 visualization are missing (need date + numeric sales-like column)',
                    'insights': [],
                    'charts': []
                }

            return {
                'enabled': True,
                'message': 'Team4 visualization integrated successfully',
                'rows_used': int(len(team4_df)),
                'insights': self._generate_insights(team4_df),
                'charts': self._generate_charts(team4_df)
            }
        except Exception as e:
            traceback.print_exc()
            return {
                'enabled': False,
                'message': f'Team4 visualization failed: {str(e)}',
                'insights': [],
                'charts': []
            }


team4_adapter = None


def initialize_team4_adapter():
    global team4_adapter
    team4_adapter = Team4VisualizationAdapter()
    return team4_adapter


def get_team4_adapter():
    global team4_adapter
    if team4_adapter is None:
        team4_adapter = initialize_team4_adapter()
    return team4_adapter
