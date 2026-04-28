"""
Cohort Analysis Engine - Tracks customer retention and behavior by signup/first purchase cohorts
Analyzes how different customer cohorts (based on signup/acquisition month) perform over time
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class CohortAnalyzer:
    """Perform cohort analysis on customer data"""
    
    def __init__(self):
        self.cohort_data = None
        self.retention_table = None
    
    def analyze_cohorts(self, df, customer_col=None, date_col=None, amount_col=None):
        """
        Perform cohort analysis on customer dataset
        
        Args:
            df: DataFrame with customer transactions
            customer_col: Column name for customer ID
            date_col: Column name for transaction date
            amount_col: Column name for transaction amount
            
        Returns:
            dict with cohort analysis results
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'cohorts': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            if customer_col is None:
                customer_candidates = [col for col in df.columns 
                                     if col.lower() in ['customer', 'customer id', 'customer_id', 'id', 'cust_id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'purchase date', 'transaction date', 'order date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None or date_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (customer_id, date)',
                    'cohorts': []
                }
            
            # Convert date column to datetime
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[date_col])
            
            # Convert amount to numeric
            if amount_col:
                df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Get first purchase date for each customer (cohort assignment)
            first_purchase = df_copy.groupby(customer_col)[date_col].min().reset_index()
            first_purchase.columns = [customer_col, 'cohort_date']
            first_purchase['cohort_month'] = first_purchase['cohort_date'].dt.to_period('M')
            
            # Merge cohort info back to original data
            df_copy = df_copy.merge(first_purchase, on=customer_col, how='left')
            
            # Create transaction month
            df_copy['transaction_month'] = df_copy[date_col].dt.to_period('M')
            
            # Calculate months since cohort (X-axis)
            df_copy['months_since_cohort'] = (
                df_copy['transaction_month'] - df_copy['cohort_month']
            ).apply(lambda x: x.n if pd.notna(x) else None)
            
            # Build cohort metrics
            cohort_metrics = []
            
            # Get unique cohorts
            cohorts = df_copy['cohort_month'].unique()
            cohorts = sorted([c for c in cohorts if pd.notna(c)])
            
            for cohort in cohorts:
                cohort_data = df_copy[df_copy['cohort_month'] == cohort]
                
                # Cohort size (unique customers in cohort)
                cohort_size = cohort_data[customer_col].nunique()
                
                # Revenue by months since cohort
                monthly_revenue = cohort_data.groupby('months_since_cohort').agg({
                    customer_col: 'nunique',  # Repeat customers
                    amount_col: 'sum' if amount_col else 'size'  # Revenue or transaction count
                }).reset_index()
                
                monthly_revenue.columns = ['month', 'customers', 'revenue']
                
                # Calculate retention rate (% of original cohort size)
                monthly_revenue['retention_rate'] = (
                    monthly_revenue['customers'] / cohort_size * 100
                ).round(2)
                
                # Average Revenue Per User in cohort
                monthly_revenue['revenue_per_customer'] = (
                    monthly_revenue['revenue'] / monthly_revenue['customers']
                ).round(2)
                
                cohort_metrics.append({
                    'cohort_month': str(cohort),
                    'cohort_size': int(cohort_size),
                    'monthly_data': monthly_revenue[monthly_revenue['month'].notna()].to_dict('records'),
                    'lifetime_value': float(cohort_data[amount_col].sum()) if amount_col else int(len(cohort_data)),
                    'avg_revenue_per_customer': float(
                        cohort_data[amount_col].sum() / cohort_size
                    ) if amount_col else 0
                })
            
            # Build retention table (cohort x months matrix)
            retention_table = self._build_retention_table(df_copy, customer_col, 'cohort_month', 'months_since_cohort')
            
            return {
                'success': True,
                'message': 'Cohort analysis completed',
                'cohorts': cohort_metrics,
                'retention_table': retention_table,
                'total_cohorts': len(cohort_metrics),
                'analysis_period': {
                    'start': str(min(cohorts)),
                    'end': str(max(cohorts))
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'Cohort analysis failed: {str(e)}',
                'cohorts': []
            }
    
    def _build_retention_table(self, df, customer_col, cohort_col, month_col):
        """Build cohort retention table (Matrix)"""
        try:
            # Create cohort-month matrix
            cohort_month_group = df.groupby([cohort_col, month_col])[customer_col].nunique().reset_index()
            cohort_month_group.columns = [cohort_col, month_col, 'customers']
            
            # Pivot to matrix
            cohort_pivot = cohort_month_group.pivot_table(
                index=cohort_col,
                columns=month_col,
                values='customers',
                fill_value=0
            )
            
            # Convert to percentages (retention rates)
            cohort_size = cohort_pivot.iloc[:, 0]
            retention_table = cohort_pivot.divide(cohort_size, axis=0) * 100
            
            # Convert to dict format for JSON
            table = []
            for idx, row in retention_table.iterrows():
                row_data = {
                    'cohort': str(idx),
                    'data': {str(col): float(val) for col, val in row.items()}
                }
                table.append(row_data)
            
            return table
        
        except Exception as e:
            print(f"Error building retention table: {e}")
            return []
    
    def get_cohort_insights(self, cohort_metrics):
        """Generate insights from cohort analysis"""
        try:
            insights = []
            
            if not cohort_metrics:
                return insights
            
            # Find best performing cohort
            best_cohort = max(cohort_metrics, key=lambda x: x['lifetime_value'])
            insights.append(
                f"Best performing cohort: {best_cohort['cohort_month']} "
                f"(${best_cohort['lifetime_value']:,.0f} lifetime value)"
            )
            
            # Find worst performing cohort
            worst_cohort = min(cohort_metrics, key=lambda x: x['lifetime_value'])
            insights.append(
                f"Needs improvement: {worst_cohort['cohort_month']} "
                f"(${worst_cohort['lifetime_value']:,.0f} lifetime value)"
            )
            
            # Average cohort size
            avg_size = np.mean([c['cohort_size'] for c in cohort_metrics])
            insights.append(
                f"Average customers per cohort: {avg_size:,.0f}"
            )
            
            # Retention trend
            avg_retention_month_1 = np.mean([
                c['monthly_data'][1]['retention_rate'] 
                for c in cohort_metrics 
                if len(c['monthly_data']) > 1
            ])
            insights.append(
                f"Average 1-month retention: {avg_retention_month_1:.1f}%"
            )
            
            return insights
        
        except Exception as e:
            return [f"Could not generate insights: {str(e)}"]


def cohort_analysis(df, customer_col=None, date_col=None, amount_col=None):
    """Quick cohort analysis function"""
    analyzer = CohortAnalyzer()
    return analyzer.analyze_cohorts(df, customer_col, date_col, amount_col)
