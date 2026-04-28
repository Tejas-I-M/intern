"""
Geographic Analytics Engine - Analyzes sales by region/location
Provides insights into geographical distribution of revenue, customers, and performance metrics
"""

import pandas as pd
import numpy as np


class GeographicAnalyzer:
    """Perform geographic analysis on customer/sales data"""
    
    def __init__(self):
        self.geo_data = None
    
    def analyze_geography(self, df, region_col=None, amount_col=None, customer_col=None):
        """
        Perform geographic analysis on sales dataset
        
        Args:
            df: DataFrame with sales data
            region_col: Column name for region/location/country
            amount_col: Column name for transaction amount
            customer_col: Column name for customer ID
            
        Returns:
            dict with geographic analysis results
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'regions': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            if region_col is None:
                region_candidates = [col for col in df.columns 
                                    if col.lower() in ['region', 'location', 'country', 'city', 'state', 'province', 'area', 'zone']]
                region_col = region_candidates[0] if region_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None:
                customer_candidates = [col for col in df.columns 
                                      if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if region_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (region/location, amount)',
                    'regions': []
                }
            
            # Convert amount to numeric
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[amount_col])
            
            # Group by region
            region_stats = df_copy.groupby(region_col).agg({
                amount_col: ['sum', 'count', 'mean', 'min', 'max', 'std'],
                customer_col: 'nunique' if customer_col else None
            }).reset_index()
            
            region_stats.columns = ['Region', 'Total_Revenue', 'Transaction_Count', 'Avg_Transaction_Value',
                                   'Min_Transaction', 'Max_Transaction', 'Std_Dev', 'Unique_Customers']
            
            # Calculate market metrics
            total_revenue = region_stats['Total_Revenue'].sum()
            region_stats['Market_Share_Pct'] = (region_stats['Total_Revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            region_stats['Revenue_Per_Customer'] = (
                region_stats['Total_Revenue'] / region_stats['Unique_Customers']
            ) if customer_col else 0
            
            # Calculate growth potential score (based on frequency and customer base)
            region_stats['Growth_Score'] = (
                (region_stats['Transaction_Count'] / region_stats['Transaction_Count'].max() * 50) +
                (region_stats['Unique_Customers'] / region_stats['Unique_Customers'].max() * 50) if customer_col else region_stats['Transaction_Count']
            )
            
            # Categorize region performance
            def get_performance_tier(row, df):
                revenue_75 = df['Total_Revenue'].quantile(0.75)
                revenue_50 = df['Total_Revenue'].quantile(0.50)
                
                if row['Total_Revenue'] >= revenue_75:
                    return 'Tier 1 (Top Performer)'
                elif row['Total_Revenue'] >= revenue_50:
                    return 'Tier 2 (Strong)'
                else:
                    return 'Tier 3 (Growth Opportunity)'
            
            region_stats['Performance_Tier'] = region_stats.apply(lambda row: get_performance_tier(row, region_stats), axis=1)
            
            # Sort by revenue descending
            region_stats = region_stats.sort_values('Total_Revenue', ascending=False).reset_index(drop=True)
            
            # Build geographic metrics
            geo_metrics = []
            for idx, row in region_stats.iterrows():
                geo_metrics.append({
                    'rank': idx + 1,
                    'region': str(row['Region']),
                    'total_revenue': float(row['Total_Revenue']),
                    'market_share_pct': float(row['Market_Share_Pct']),
                    'transaction_count': int(row['Transaction_Count']),
                    'avg_transaction_value': float(row['Avg_Transaction_Value']),
                    'unique_customers': int(row['Unique_Customers']) if customer_col else 0,
                    'revenue_per_customer': float(row['Revenue_Per_Customer']) if customer_col else 0,
                    'growth_score': float(row['Growth_Score']),
                    'performance_tier': str(row['Performance_Tier'])
                })
            
            # Generate insights
            insights = []
            if geo_metrics:
                top_region = geo_metrics[0]
                insights.append(
                    f"🏆 Top region: {top_region['region']} (${top_region['total_revenue']:,.0f}, {top_region['market_share_pct']:.1f}% market share)"
                )
                
                # Find emerging market (high growth score, lower revenue)
                emerging = min([m for m in geo_metrics if m['growth_score'] > 30], 
                              key=lambda x: x['total_revenue'], default=None)
                if emerging:
                    insights.append(
                        f"📈 Emerging market: {emerging['region']} (Growth score: {emerging['growth_score']:.1f})"
                    )
                
                # Regional diversity
                tier_1_count = len([m for m in geo_metrics if 'Tier 1' in m['performance_tier']])
                insights.append(f"🌍 Regional distribution: {tier_1_count} top-performing regions out of {len(geo_metrics)} total")
            
            return {
                'success': True,
                'message': 'Geographic analysis completed',
                'regions': geo_metrics,
                'total_regions': len(geo_metrics),
                'summary': {
                    'total_revenue': float(total_revenue),
                    'total_transactions': int(region_stats['Transaction_Count'].sum()),
                    'total_customers': int(region_stats['Unique_Customers'].sum()) if customer_col else 0,
                    'avg_region_revenue': float(region_stats['Total_Revenue'].mean()),
                    'highest_performing': geo_metrics[0]['region'] if geo_metrics else 'N/A'
                },
                'insights': insights
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Geographic analysis failed: {str(e)}',
                'regions': []
            }
    
    def get_region_performance_matrix(self, df, region_col=None, amount_col=None, date_col=None):
        """Generate performance matrix comparing regions across time periods"""
        try:
            if df is None or df.empty:
                return []
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if region_col is None:
                region_candidates = [col for col in df.columns 
                                    if col.lower() in ['region', 'location', 'country', 'city', 'state']]
                region_col = region_candidates[0] if region_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if region_col is None or amount_col is None:
                return []
            
            # Convert to proper types
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            if date_col:
                df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
                df_copy['Month'] = df_copy[date_col].dt.to_period('M')
            
            # Create region-month performance matrix
            if date_col:
                matrix_data = df_copy.groupby([region_col, 'Month'])[amount_col].sum().reset_index()
                matrix_data.columns = ['Region', 'Month', 'Revenue']
                
                # Pivot to matrix
                matrix_pivot = matrix_data.pivot_table(
                    index='Region',
                    columns='Month',
                    values='Revenue',
                    fill_value=0
                )
                
                # Convert to list format
                matrix = []
                for idx, row in matrix_pivot.iterrows():
                    region_data = {
                        'region': str(idx),
                        'monthly_revenue': {str(col): float(val) for col, val in row.items()}
                    }
                    matrix.append(region_data)
                
                return matrix
            
            return []
        
        except Exception as e:
            print(f"Error building performance matrix: {e}")
            return []


def geographic_analysis(df, region_col=None, amount_col=None, customer_col=None):
    """Quick geographic analysis function"""
    analyzer = GeographicAnalyzer()
    return analyzer.analyze_geography(df, region_col, amount_col, customer_col)
