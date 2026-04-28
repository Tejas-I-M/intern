"""
Real Analytics Service - Integrates Team2_module, analytics_engine with actual dataset data
Provides real data for dashboard visualizations from uploaded CSV files
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add paths for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

class RealAnalyticsService:
    """Process real data from uploaded CSVs and generate actual metrics"""
    
    def __init__(self):
        self.datasets = {}  # Cache: {file_id: dataframe}
        self.analysis_cache = {}  # Cache: {file_id: analysis_results}

    def _detect_date_column(self, df, preferred=None):
        """Pick the best date-like column using parse-rate and name signals."""
        if preferred and preferred in df.columns:
            parsed = pd.to_datetime(df[preferred], errors='coerce')
            if float(parsed.notna().mean()) >= 0.5:
                return preferred

        exact_priority = ['Date', 'date', 'transaction_date', 'purchase_date', 'order_date', 'sale_date', 'Sale_Date']
        for candidate in exact_priority:
            if candidate in df.columns:
                parsed = pd.to_datetime(df[candidate], errors='coerce')
                if float(parsed.notna().mean()) >= 0.5:
                    return candidate

        keywords = ['date', 'time', 'order', 'purchase', 'transaction', 'sale']
        best_col = None
        best_score = -1.0

        for col in df.columns:
            col_lower = str(col).lower()
            if not any(token in col_lower for token in keywords):
                continue

            parsed = pd.to_datetime(df[col], errors='coerce')
            parse_rate = float(parsed.notna().mean())
            if parse_rate < 0.5:
                continue

            name_score = 1.0 if 'date' in col_lower else 0.65
            score = parse_rate * 0.8 + name_score * 0.2
            if score > best_score:
                best_col = col
                best_score = score

        return best_col

    def _detect_amount_column(self, df, preferred=None):
        """Pick numeric amount/revenue column while avoiding text columns (e.g. Sales_Rep)."""
        if preferred and preferred in df.columns:
            parsed = pd.to_numeric(df[preferred], errors='coerce')
            parse_rate = float(parsed.notna().mean())
            if parse_rate >= 0.5 and float(parsed.abs().sum()) > 0:
                return preferred

        exact_priority = ['Total Amount', 'Amount', 'Revenue', 'Sales Amount', 'Sales_Amount']
        for candidate in exact_priority:
            if candidate in df.columns:
                parsed = pd.to_numeric(df[candidate], errors='coerce')
                parse_rate = float(parsed.notna().mean())
                if parse_rate >= 0.5 and float(parsed.abs().sum()) > 0:
                    return candidate

        positive_keywords = ['amount', 'revenue', 'price', 'value', 'sales', 'total']
        negative_tokens = [
            'rep', 'name', 'region', 'country', 'city', 'state', 'category',
            'channel', 'method', 'gender', 'type', 'id', 'code'
        ]

        best_col = None
        best_score = -1.0

        for col in df.columns:
            col_lower = str(col).lower()
            if not any(token in col_lower for token in positive_keywords):
                continue

            parsed = pd.to_numeric(df[col], errors='coerce')
            parse_rate = float(parsed.notna().mean())
            if parse_rate < 0.5:
                continue

            magnitude = float(parsed.abs().sum())
            if magnitude <= 0:
                continue

            non_zero_ratio = float((parsed.fillna(0) != 0).mean())
            variability = float(parsed.std()) if parsed.notna().sum() > 1 else 0.0

            name_score = 0.0
            if 'amount' in col_lower:
                name_score += 1.0
            if 'revenue' in col_lower:
                name_score += 0.9
            if 'total' in col_lower:
                name_score += 0.6
            if 'sales' in col_lower:
                name_score += 0.45
            if any(token in col_lower for token in negative_tokens):
                name_score -= 0.8

            variability_score = 1.0 if variability > 0 else 0.0
            score = parse_rate * 0.45 + non_zero_ratio * 0.2 + variability_score * 0.15 + max(name_score, 0) * 0.2

            if score > best_score:
                best_col = col
                best_score = score

        return best_col

    def _detect_region_column(self, df, preferred=None):
        """Pick a geographic column with meaningful non-empty values."""
        if preferred and preferred in df.columns:
            values = df[preferred].astype(str).str.strip().replace({'nan': '', 'None': ''})
            if float((values != '').mean()) >= 0.3 and int(values[values != ''].nunique()) >= 2:
                return preferred

        exact_priority = ['Region', 'region', 'Country', 'country', 'State', 'City']
        for candidate in exact_priority:
            if candidate in df.columns:
                values = df[candidate].astype(str).str.strip().replace({'nan': '', 'None': ''})
                if float((values != '').mean()) >= 0.3 and int(values[values != ''].nunique()) >= 2:
                    return candidate

        geo_keywords = ['region', 'location', 'country', 'city', 'state', 'province', 'area', 'zone']
        best_col = None
        best_score = -1.0

        for col in df.columns:
            col_lower = str(col).lower()
            if not any(token in col_lower for token in geo_keywords):
                continue

            values = df[col].astype(str).str.strip().replace({'nan': '', 'None': ''})
            non_empty_ratio = float((values != '').mean())
            unique_non_empty = int(values[values != ''].nunique())
            if non_empty_ratio < 0.3 or unique_non_empty < 2:
                continue

            name_score = 1.0 if ('region' in col_lower or 'country' in col_lower) else 0.7
            diversity_score = min(unique_non_empty / 10.0, 1.0)
            score = non_empty_ratio * 0.55 + name_score * 0.3 + diversity_score * 0.15
            if score > best_score:
                best_col = col
                best_score = score

        return best_col

    def _detect_customer_column(self, df, preferred=None):
        """Pick a customer identifier column while avoiding transaction/product ids."""
        if preferred and preferred in df.columns:
            return preferred

        exact_priority = ['Customer ID', 'customer_id', 'customer id', 'Customer', 'customer']
        for candidate in exact_priority:
            if candidate in df.columns:
                return candidate

        best_col = None
        best_score = -1.0
        for col in df.columns:
            col_lower = str(col).lower()
            if not any(token in col_lower for token in ['customer', 'client', 'buyer', 'member', 'account']):
                continue
            if any(token in col_lower for token in ['transaction', 'invoice', 'order', 'product', 'sku']):
                continue

            series = df[col].astype(str).str.strip()
            non_empty = series[series != '']
            if non_empty.empty:
                continue

            unique_ratio = float(non_empty.nunique() / max(len(non_empty), 1))
            if unique_ratio < 0.01 or unique_ratio > 0.98:
                continue

            score = 0.7 + (1.0 - abs(unique_ratio - 0.35)) * 0.3
            if score > best_score:
                best_col = col
                best_score = score

        return best_col
    
    def load_dataset(self, filepath):
        """Load and cache dataset from CSV"""
        try:
            df = pd.read_csv(filepath)
            
            # Ensure Date column is datetime
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            
            # Ensure Amount/Revenue column exists
            amount_cols = [col for col in df.columns if col.lower() in ['amount', 'total', 'revenue', 'sales', 'total amount']]
            if amount_cols:
                amount_col = amount_cols[0]
                df['Amount'] = df[amount_col].apply(pd.to_numeric, errors='coerce')
            
            return df
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return None
    
    def get_revenue_trends(self, df, period='month'):
        """Extract real revenue trend data from dataset"""
        try:
            if df is None or 'Date' not in df.columns:
                return []
            
            df_copy = df.copy()
            
            # Find amount column
            amount_candidates = [col for col in df_copy.columns 
                                if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
            amount_col = amount_candidates[0] if amount_candidates else None
            
            if amount_col is None:
                return []
            
            # Group by period
            if period == 'month':
                df_copy['Period'] = df_copy['Date'].dt.to_period('M')
            elif period == 'week':
                df_copy['Period'] = df_copy['Date'].dt.to_period('W')
            elif period == 'day':
                df_copy['Period'] = df_copy['Date'].dt.date
            else:
                df_copy['Period'] = df_copy['Date'].dt.to_period('M')
            
            # Sum revenue by period
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            revenue_by_period = df_copy.groupby('Period')[amount_col].sum().reset_index()
            revenue_by_period.columns = ['Period', 'Revenue']
            revenue_by_period['Period'] = revenue_by_period['Period'].astype(str)
            
            # Return as list of dicts
            trends = []
            for _, row in revenue_by_period.iterrows():
                label = str(row['Period']).split('-')[-1][:3]  # Extract month/day label
                trends.append({
                    'period': label,
                    'revenue': float(row['Revenue']),
                    'date': str(row['Period'])
                })
            
            return trends[-12:] if len(trends) > 12 else trends  # Last 12 periods
        
        except Exception as e:
            print(f"Error extracting trends: {e}")
            return []
    
    def get_top_categories(self, df, categories_col=None, amount_col=None, top_n=4):
        """Extract top performing categories from dataset"""
        try:
            if df is None:
                return []
            
            df_copy = df.copy()
            
            # Find category column
            if categories_col is None:
                category_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['category', 'product', 'product category', 'type', 'segment']]
                categories_col = category_candidates[0] if category_candidates else None
            
            # Find amount column
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if categories_col is None or amount_col is None:
                return []
            
            # Group by category
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            category_stats = df_copy.groupby(categories_col)[amount_col].sum().reset_index()
            category_stats.columns = ['Category', 'Revenue']
            category_stats = category_stats.sort_values('Revenue', ascending=False).head(top_n)
            
            return [
                {'name': row['Category'], 'revenue': float(row['Revenue'])}
                for _, row in category_stats.iterrows()
            ]
        
        except Exception as e:
            print(f"Error extracting categories: {e}")
            return []
    
    def get_customer_segments(self, df, customer_col=None, amount_col=None):
        """Analyze customer segments using RFM"""
        try:
            if df is None:
                return {}
            
            df_copy = df.copy()
            
            # Find columns
            if customer_col is None:
                customer_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None or amount_col is None:
                return {}
            
            # Simple segmentation by spending
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            customer_spending = df_copy.groupby(customer_col)[amount_col].sum().reset_index()
            customer_spending.columns = ['Customer', 'Total_Spend']
            
            # Calculate quantiles for segmentation
            q66 = customer_spending['Total_Spend'].quantile(0.66)
            q33 = customer_spending['Total_Spend'].quantile(0.33)
            
            premium = len(customer_spending[customer_spending['Total_Spend'] >= q66])
            standard = len(customer_spending[(customer_spending['Total_Spend'] < q66) & 
                                           (customer_spending['Total_Spend'] >= q33)])
            basic = len(customer_spending[customer_spending['Total_Spend'] < q33])
            
            total_customers = len(customer_spending)
            total_revenue = float(df_copy[amount_col].sum())
            
            # Calculate segment revenues
            premium_revenue = float(customer_spending[customer_spending['Total_Spend'] >= q66]['Total_Spend'].sum())
            standard_revenue = float(customer_spending[(customer_spending['Total_Spend'] < q66) & 
                                                       (customer_spending['Total_Spend'] >= q33)]['Total_Spend'].sum())
            basic_revenue = float(customer_spending[customer_spending['Total_Spend'] < q33]['Total_Spend'].sum())
            
            segments = {
                'Premium': {
                    'count': premium,
                    'percent': round(100 * premium / total_customers, 1) if total_customers > 0 else 0,
                    'revenue': premium_revenue
                },
                'Standard': {
                    'count': standard,
                    'percent': round(100 * standard / total_customers, 1) if total_customers > 0 else 0,
                    'revenue': standard_revenue
                },
                'Basic': {
                    'count': basic,
                    'percent': round(100 * basic / total_customers, 1) if total_customers > 0 else 0,
                    'revenue': basic_revenue
                },
                'Total': {
                    'customers': total_customers,
                    'revenue': total_revenue
                }
            }
            
            return segments
        
        except Exception as e:
            print(f"Error segmenting customers: {e}")
            return {}
    
    def get_real_kpis(self, df):
        """Calculate real KPIs from dataset"""
        try:
            if df is None:
                return {}
            
            df_copy = df.copy()
            
            # Find amount column
            amount_candidates = [col for col in df_copy.columns 
                                if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
            amount_col = amount_candidates[0] if amount_candidates else None
            
            if amount_col is None:
                return {}
            
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Count customers
            customer_candidates = [col for col in df_copy.columns 
                                 if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
            customer_col = customer_candidates[0] if customer_candidates else None
            
            unique_customers = df_copy[customer_col].nunique() if customer_col else 0
            
            return {
                'total_revenue': float(df_copy[amount_col].sum()),
                'average_order_value': float(df_copy[amount_col].mean()),
                'unique_customers': int(unique_customers),
                'total_orders': len(df_copy),
                'date_range': {
                    'start': str(df_copy['Date'].min().date()) if 'Date' in df_copy.columns else 'N/A',
                    'end': str(df_copy['Date'].max().date()) if 'Date' in df_copy.columns else 'N/A'
                }
            }
        
        except Exception as e:
            print(f"Error calculating KPIs: {e}")
            return {}
    
    def calculate_customer_lifetime_value(self, df, customer_col=None, amount_col=None):
        """Calculate Customer Lifetime Value (CLV) for each customer
        
        CLV = Total revenue generated by a customer over their lifetime
        
        Returns:
            - Dictionary with CLV metrics and per-customer breakdown
        """
        try:
            if df is None:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find customer column
            if customer_col is None:
                customer_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            # Find amount column
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None or amount_col is None:
                return {'success': False, 'message': 'Customer ID or Amount column not found'}
            
            # Convert amount to numeric
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Calculate CLV per customer (total revenue)
            customer_clv = df_copy.groupby(customer_col).agg({
                amount_col: ['sum', 'count', 'mean', 'min', 'max'],
                'Date': ['min', 'max']
            }).reset_index()
            
            customer_clv.columns = ['Customer_ID', 'CLV', 'Purchase_Count', 'Avg_Order_Value', 
                                    'Min_Order_Value', 'Max_Order_Value', 'First_Purchase_Date', 'Last_Purchase_Date']
            
            # Calculate customer lifetime (days)
            customer_clv['Customer_Lifetime_Days'] = (
                customer_clv['Last_Purchase_Date'] - customer_clv['First_Purchase_Date']
            ).dt.days
            
            # Calculate avg purchase frequency (purchases per day)
            customer_clv['Purchase_Frequency_Days'] = (
                customer_clv['Customer_Lifetime_Days'] / (customer_clv['Purchase_Count'] - 1)
            ).replace([np.inf, -np.inf], 0)
            
            # Sort by CLV descending
            customer_clv_sorted = customer_clv.sort_values('CLV', ascending=False).reset_index(drop=True)
            
            # Calculate CLV segments/tiers
            total_clv = customer_clv['CLV'].sum()
            top_20_pct_count = max(1, int(len(customer_clv) * 0.2))
            top_20_pct_clv = customer_clv_sorted.head(top_20_pct_count)['CLV'].sum()
            
            # Prepare response
            clv_metrics = {
                'success': True,
                'summary': {
                    'total_customers': len(customer_clv),
                    'total_clv': float(total_clv),
                    'average_clv': float(customer_clv['CLV'].mean()),
                    'median_clv': float(customer_clv['CLV'].median()),
                    'max_clv': float(customer_clv['CLV'].max()),
                    'min_clv': float(customer_clv['CLV'].min()),
                    'std_dev_clv': float(customer_clv['CLV'].std()),
                    'top_20_pct_count': top_20_pct_count,
                    'top_20_pct_revenue': float(top_20_pct_clv),
                    'top_20_pct_contribution': round(100 * top_20_pct_clv / total_clv, 2) if total_clv > 0 else 0
                },
                'customers': []
            }
            
            # Add top 10 customers
            for idx, row in customer_clv_sorted.head(10).iterrows():
                clv_metrics['customers'].append({
                    'rank': idx + 1,
                    'customer_id': str(row['Customer_ID']),
                    'clv': float(row['CLV']),
                    'purchase_count': int(row['Purchase_Count']),
                    'avg_order_value': float(row['Avg_Order_Value']),
                    'min_order_value': float(row['Min_Order_Value']),
                    'max_order_value': float(row['Max_Order_Value']),
                    'first_purchase': str(row['First_Purchase_Date'].date()),
                    'last_purchase': str(row['Last_Purchase_Date'].date()),
                    'lifetime_days': int(row['Customer_Lifetime_Days']),
                    'purchase_frequency_days': round(row['Purchase_Frequency_Days'], 2) if row['Purchase_Frequency_Days'] > 0 else 0,
                    'clv_percentage': round(100 * row['CLV'] / total_clv, 2) if total_clv > 0 else 0
                })
            
            # CLV Distribution
            clv_distribution = {
                'high_value': len(customer_clv[customer_clv['CLV'] >= customer_clv['CLV'].quantile(0.75)]),
                'medium_value': len(customer_clv[(customer_clv['CLV'] < customer_clv['CLV'].quantile(0.75)) & 
                                                 (customer_clv['CLV'] >= customer_clv['CLV'].quantile(0.25))]),
                'low_value': len(customer_clv[customer_clv['CLV'] < customer_clv['CLV'].quantile(0.25)])
            }
            
            clv_metrics['distribution'] = clv_distribution
            
            return clv_metrics
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'CLV calculation error: {str(e)}'}
    
    def calculate_repeat_purchase_analysis(self, df, customer_col=None, date_col=None):
        """Analyze repeat purchase frequency and customer retention patterns
        
        Returns:
            - Dictionary with repeat purchase metrics and customer cohorts
        """
        try:
            if df is None or len(df) == 0:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find customer column
            if customer_col is None:
                customer_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            # Find date column
            if date_col is None:
                date_candidates = [col for col in df_copy.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if customer_col is None or date_col is None:
                return {'success': False, 'message': 'Customer ID or Date column not found'}
            
            # Convert date to datetime
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            
            # Calculate purchase frequency per customer
            purchase_counts = df_copy.groupby(customer_col).size().reset_index(name='purchase_count')
            
            # Categorize repeat purchases
            repeat_customers = purchase_counts[purchase_counts['purchase_count'] > 1]
            one_time_customers = purchase_counts[purchase_counts['purchase_count'] == 1]
            
            # Calculate retention metrics
            total_customers = len(purchase_counts)
            repeat_rate = (len(repeat_customers) / total_customers * 100) if total_customers > 0 else 0
            
            # Cohort analysis - group by purchase frequency
            frequency_cohorts = {
                'one_time': len(one_time_customers),
                '2_purchases': len(purchase_counts[purchase_counts['purchase_count'] == 2]),
                '3_5_purchases': len(purchase_counts[(purchase_counts['purchase_count'] >= 3) & (purchase_counts['purchase_count'] <= 5)]),
                '6_10_purchases': len(purchase_counts[(purchase_counts['purchase_count'] >= 6) & (purchase_counts['purchase_count'] <= 10)]),
                '10_plus_purchases': len(purchase_counts[purchase_counts['purchase_count'] > 10])
            }
            
            # Get time between purchases for repeat customers
            time_between_purchases = {}
            for customer in repeat_customers[customer_col]:
                customer_dates = sorted(df_copy[df_copy[customer_col] == customer][date_col].dropna())
                if len(customer_dates) > 1:
                    days_between = [(customer_dates[i+1] - customer_dates[i]).days for i in range(len(customer_dates)-1)]
                    if days_between:
                        time_between_purchases[customer] = {
                            'avg_days': float(np.mean(days_between)),
                            'min_days': float(np.min(days_between)),
                            'max_days': float(np.max(days_between))
                        }
            
            # Get top repeat customers
            top_repeat = purchase_counts.nlargest(10, 'purchase_count')
            
            repeat_metrics = {
                'success': True,
                'summary': {
                    'total_customers': int(total_customers),
                    'repeat_customers': int(len(repeat_customers)),
                    'one_time_customers': int(len(one_time_customers)),
                    'repeat_rate_percent': round(repeat_rate, 2),
                    'avg_purchases_per_customer': round(purchase_counts['purchase_count'].mean(), 2),
                    'median_purchases': int(purchase_counts['purchase_count'].median()),
                    'max_purchases': int(purchase_counts['purchase_count'].max()),
                    'avg_days_between_purchase': round(np.mean([v['avg_days'] for v in time_between_purchases.values()]) if time_between_purchases else 0, 1)
                },
                'frequency_cohorts': frequency_cohorts,
                'top_repeat_customers': []
            }
            
            # Add top repeat customers
            for idx, row in top_repeat.iterrows():
                customer_id = str(row[customer_col])
                repeat_metrics['top_repeat_customers'].append({
                    'rank': len(repeat_metrics['top_repeat_customers']) + 1,
                    'customer_id': customer_id,
                    'purchase_count': int(row['purchase_count']),
                    'time_between_purchases_days': time_between_purchases.get(customer_id, {}).get('avg_days', 0)
                })
            
            return repeat_metrics
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Repeat purchase analysis error: {str(e)}'}
    
    def calculate_customer_health_score(self, df, customer_col=None, date_col=None, amount_col=None):
        """Calculate RFM-based Customer Health Score (0-100 scale)
        
        RFM = Recency (days since last purchase) + Frequency (purchase count) + Monetary (total spending)
        Health Score combines all three into a single 0-100 metric
        
        Returns:
            - Dictionary with health scores and customer rankings
        """
        try:
            if df is None or len(df) == 0:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find columns
            if customer_col is None:
                customer_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df_copy.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None or date_col is None or amount_col is None:
                return {'success': False, 'message': 'Required columns (Customer, Date, Amount) not found'}
            
            # Convert columns
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Calculate RFM metrics
            current_date = df_copy[date_col].max()
            
            rfm_data = df_copy.groupby(customer_col).agg({
                date_col: ['max', 'count'],
                amount_col: 'sum'
            }).reset_index()
            
            rfm_data.columns = ['Customer_ID', 'Last_Purchase_Date', 'Frequency', 'Monetary']
            
            # Calculate Recency (days since last purchase)
            rfm_data['Recency_Days'] = (current_date - rfm_data['Last_Purchase_Date']).dt.days
            
            # Normalize RFM to 0-100 scale
            # Recency: Lower is better (fewer days = higher score)
            recency_max = rfm_data['Recency_Days'].max()
            rfm_data['Recency_Score'] = 100 - (rfm_data['Recency_Days'] / recency_max * 100) if recency_max > 0 else 100
            
            # Frequency: Higher is better
            frequency_max = rfm_data['Frequency'].max()
            rfm_data['Frequency_Score'] = (rfm_data['Frequency'] / frequency_max * 100) if frequency_max > 0 else 100
            
            # Monetary: Higher is better
            monetary_max = rfm_data['Monetary'].max()
            rfm_data['Monetary_Score'] = (rfm_data['Monetary'] / monetary_max * 100) if monetary_max > 0 else 100
            
            # Calculate overall Health Score (weighted average)
            rfm_data['Health_Score'] = (
                (rfm_data['Recency_Score'] * 0.3) +  # 30% weight on recency
                (rfm_data['Frequency_Score'] * 0.3) +  # 30% weight on frequency
                (rfm_data['Monetary_Score'] * 0.4)     # 40% weight on monetary
            ).round(1)
            
            # Sort by health score
            rfm_sorted = rfm_data.sort_values('Health_Score', ascending=False).reset_index(drop=True)
            
            # Categorize health
            def get_health_status(score):
                if score >= 80:
                    return 'Excellent'
                elif score >= 60:
                    return 'Good'
                elif score >= 40:
                    return 'Fair'
                else:
                    return 'Poor'
            
            rfm_sorted['Health_Status'] = rfm_sorted['Health_Score'].apply(get_health_status)
            
            # Summary statistics
            health_summary = {
                'success': True,
                'summary': {
                    'total_customers': len(rfm_sorted),
                    'avg_health_score': round(rfm_sorted['Health_Score'].mean(), 1),
                    'median_health_score': round(rfm_sorted['Health_Score'].median(), 1),
                    'excellent_customers': len(rfm_sorted[rfm_sorted['Health_Score'] >= 80]),
                    'good_customers': len(rfm_sorted[(rfm_sorted['Health_Score'] >= 60) & (rfm_sorted['Health_Score'] < 80)]),
                    'fair_customers': len(rfm_sorted[(rfm_sorted['Health_Score'] >= 40) & (rfm_sorted['Health_Score'] < 60)]),
                    'poor_customers': len(rfm_sorted[rfm_sorted['Health_Score'] < 40])
                },
                'top_customers': [],
                'at_risk_customers': []
            }
            
            # Top 10 healthy customers
            for idx, row in rfm_sorted.head(10).iterrows():
                health_summary['top_customers'].append({
                    'rank': idx + 1,
                    'customer_id': str(row['Customer_ID']),
                    'health_score': float(row['Health_Score']),
                    'health_status': row['Health_Status'],
                    'recency_days': int(row['Recency_Days']),
                    'frequency': int(row['Frequency']),
                    'monetary_value': float(row['Monetary'])
                })
            
            # Bottom 10 at-risk customers
            for idx, row in rfm_sorted.tail(10).iterrows():
                health_summary['at_risk_customers'].append({
                    'rank': len(rfm_sorted) - idx,
                    'customer_id': str(row['Customer_ID']),
                    'health_score': float(row['Health_Score']),
                    'health_status': row['Health_Status'],
                    'recency_days': int(row['Recency_Days']),
                    'frequency': int(row['Frequency']),
                    'monetary_value': float(row['Monetary'])
                })
            
            return health_summary
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Customer health score calculation error: {str(e)}'}
    
    def detect_anomalies(self, df, date_col=None, amount_col=None, sensitivity=2.0):
        """Detect unusual spikes or drops in sales using statistical methods (Z-score)
        
        Sensitivity parameter controls threshold:
        - 1.0 = 68% normal range (stricter detection)
        - 2.0 = 95% normal range (balanced, default)
        - 3.0 = 99.7% normal range (lenient detection)
        
        Returns:
            - Dictionary with anomalies detected and flagged transactions
        """
        try:
            if df is None or len(df) == 0:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find date column
            if date_col is None:
                date_candidates = [col for col in df_copy.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            # Find amount column
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if date_col is None or amount_col is None:
                return {'success': False, 'message': 'Required columns (Date, Amount) not found'}
            
            # Convert to proper types
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Sort by date
            df_copy = df_copy.sort_values(date_col).reset_index(drop=True)
            
            # Calculate mean and std deviation
            mean_amount = df_copy[amount_col].mean()
            std_amount = df_copy[amount_col].std()
            
            if std_amount == 0:
                return {'success': True, 'anomalies': [], 'summary': {'total_anomalies': 0, 'anomaly_rate': 0.0}}
            
            # Calculate Z-scores
            z_scores = np.abs((df_copy[amount_col] - mean_amount) / std_amount)
            threshold = sensitivity
            
            # Identify anomalies
            anomaly_mask = z_scores > threshold
            anomalies_df = df_copy[anomaly_mask].copy()
            anomalies_df['zscore'] = z_scores[anomaly_mask]
            anomalies_df['deviation'] = anomalies_df[amount_col] - mean_amount
            anomalies_df['deviation_pct'] = (anomalies_df['deviation'] / mean_amount * 100) if mean_amount != 0 else 0
            
            # Sort by Z-score (most anomalous first)
            anomalies_df = anomalies_df.sort_values('zscore', ascending=False)
            
            # Prepare response
            anomaly_results = {
                'success': True,
                'summary': {
                    'total_transactions': len(df_copy),
                    'total_anomalies': len(anomalies_df),
                    'anomaly_rate': round(len(anomalies_df) / len(df_copy) * 100, 2),
                    'mean_amount': float(mean_amount),
                    'std_deviation': float(std_amount),
                    'sensitivity_threshold': float(threshold)
                },
                'anomalies': []
            }
            
            # Add anomalies
            for idx, row in anomalies_df.head(20).iterrows():
                anomaly_results['anomalies'].append({
                    'date': str(row[date_col].date()),
                    'amount': float(row[amount_col]),
                    'zscore': float(row['zscore']),
                    'deviation_from_mean': float(row['deviation']),
                    'deviation_percent': round(float(row['deviation_pct']), 2),
                    'type': 'spike' if row[amount_col] > mean_amount else 'drop'
                })
            
            return anomaly_results
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Anomaly detection error: {str(e)}'}
    
    def analyze_product_performance(self, df, product_col=None, amount_col=None):
        """Analyze product performance by profitability and volume
        
        Compares products across three dimensions:
        - Total sales (volume)
        - Average order value (profitability)
        - Number of transactions (frequency)
        
        Returns:
            - Dictionary with product rankings and performance matrix
        """
        try:
            if df is None or len(df) == 0:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find product column
            if product_col is None:
                product_candidates = [col for col in df_copy.columns 
                                     if col.lower() in ['product', 'product_name', 'product name', 'item', 'item_name', 'category', 'product category', 'product line', 'productline']]
                product_col = product_candidates[0] if product_candidates else None
            
            # Find amount column
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if product_col is None or amount_col is None:
                return {'success': False, 'message': 'Required columns (Product, Amount) not found'}
            
            # Convert amount to numeric
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Aggregate by product
            product_perf = df_copy.groupby(product_col).agg({
                amount_col: ['sum', 'mean', 'count', 'min', 'max', 'std']
            }).reset_index()
            
            product_perf.columns = ['Product', 'Total_Sales', 'Avg_Order_Value', 'Transaction_Count', 
                                   'Min_Amount', 'Max_Amount', 'Std_Dev']
            
            # Calculate market share
            total_revenue = product_perf['Total_Sales'].sum()
            product_perf['Market_Share_Pct'] = (product_perf['Total_Sales'] / total_revenue * 100) if total_revenue > 0 else 0
            
            # Calculate growth potential (based on frequency and avg value)
            product_perf['Growth_Score'] = (product_perf['Transaction_Count'] * product_perf['Avg_Order_Value']) / 100
            
            # Categorize performance
            def get_performance_category(row):
                if row['Total_Sales'] > product_perf['Total_Sales'].quantile(0.75):
                    if row['Avg_Order_Value'] > product_perf['Avg_Order_Value'].quantile(0.75):
                        return 'Star'  # High volume, high value
                    else:
                        return 'Workhorse'  # High volume, lower value
                else:
                    if row['Avg_Order_Value'] > product_perf['Avg_Order_Value'].quantile(0.75):
                        return 'Premium'  # Lower volume, high value
                    else:
                        return 'Standard'  # Lower volume, lower value
            
            product_perf['Performance_Category'] = product_perf.apply(get_performance_category, axis=1)
            
            # Sort by total sales
            product_perf = product_perf.sort_values('Total_Sales', ascending=False).reset_index(drop=True)
            
            # Prepare response
            perf_results = {
                'success': True,
                'summary': {
                    'total_products': len(product_perf),
                    'total_revenue': float(total_revenue),
                    'avg_product_revenue': float(product_perf['Total_Sales'].mean()),
                    'top_product': str(product_perf.iloc[0]['Product']),
                    'top_product_revenue': float(product_perf.iloc[0]['Total_Sales'])
                },
                'products': [],
                'category_distribution': {}
            }
            
            # Add products
            for idx, row in product_perf.iterrows():
                perf_results['products'].append({
                    'rank': idx + 1,
                    'product': str(row['Product']),
                    'total_sales': float(row['Total_Sales']),
                    'market_share_pct': float(row['Market_Share_Pct']),
                    'avg_order_value': float(row['Avg_Order_Value']),
                    'transaction_count': int(row['Transaction_Count']),
                    'growth_score': float(row['Growth_Score']),
                    'performance_category': str(row['Performance_Category'])
                })
            
            # Category distribution
            for category in product_perf['Performance_Category'].unique():
                count = len(product_perf[product_perf['Performance_Category'] == category])
                perf_results['category_distribution'][category] = count
            
            return perf_results
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Product performance analysis error: {str(e)}'}
    
    def analyze_promotional_impact(self, df, promo_col=None, amount_col=None, date_col=None):
        """Measure effectiveness of promotions/discounts on sales
        
        Calculates impact by comparing promotional vs non-promotional transactions
        
        Returns:
            - Dictionary with promotion metrics and effectiveness analysis
        """
        try:
            if df is None or len(df) == 0:
                return {'success': False, 'message': 'No data available'}
            
            df_copy = df.copy()
            
            # Find promotion/discount column
            if promo_col is None:
                promo_candidates = [col for col in df_copy.columns 
                                   if col.lower() in ['promo', 'promotion', 'discount', 'coupon', 'promo_used', 'discount_amount']]
                promo_col = promo_candidates[0] if promo_candidates else None
            
            # Find amount column
            if amount_col is None:
                amount_candidates = [col for col in df_copy.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            # Find date column
            if date_col is None:
                date_candidates = [col for col in df_copy.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                return {'success': False, 'message': 'Amount column not found'}
            
            # Convert amount to numeric
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # If no promo column, create one based on data  patterns
            if promo_col is None:
                # Use lower 25% as "discounted" for analysis
                discount_threshold = df_copy[amount_col].quantile(0.25)
                df_copy['Is_Promotional'] = df_copy[amount_col] < discount_threshold
            else:
                # Convert promo column to boolean
                df_copy['Is_Promotional'] = df_copy[promo_col].astype(bool)
            
            # Split data
            promo_data = df_copy[df_copy['Is_Promotional'] == True]
            non_promo_data = df_copy[df_copy['Is_Promotional'] == False]
            
            # Calculate metrics
            promo_results = {
                'success': True,
                'summary': {
                    'total_transactions': len(df_copy),
                    'promotional_transactions': len(promo_data),
                    'non_promotional_transactions': len(non_promo_data),
                    'promotion_rate': round(len(promo_data) / len(df_copy) * 100, 2) if len(df_copy) > 0 else 0,
                    'promo_avg_value': float(promo_data[amount_col].mean()) if len(promo_data) > 0 else 0,
                    'non_promo_avg_value': float(non_promo_data[amount_col].mean()) if len(non_promo_data) > 0 else 0,
                    'promo_total_revenue': float(promo_data[amount_col].sum()) if len(promo_data) > 0 else 0,
                    'non_promo_total_revenue': float(non_promo_data[amount_col].sum()) if len(non_promo_data) > 0 else 0
                },
                'effectiveness': {}
            }
            
            # Calculate effectiveness metrics
            if len(promo_data) > 0 and len(non_promo_data) > 0:
                promo_avg = promo_data[amount_col].mean()
                non_promo_avg = non_promo_data[amount_col].mean()
                
                # Impact direction
                impact = ((promo_avg - non_promo_avg) / non_promo_avg * 100) if non_promo_avg != 0 else 0
                
                promo_results['effectiveness'] = {
                    'avg_order_lift': round(impact, 2),
                    'promo_volume_percentage': round(len(promo_data) / len(df_copy) * 100, 2),
                    'promo_revenue_percentage': round(promo_results['summary']['promo_total_revenue'] / 
                                                     (promo_results['summary']['promo_total_revenue'] + 
                                                      promo_results['summary']['non_promo_total_revenue']) * 100, 2),
                    'effectiveness_rating': 'Positive' if impact > 0 else 'Negative',
                    'recommendation': 'Expand promos' if impact > 5 else 'Maintain current level' if impact > -5 else 'Reduce promos'
                }
            
            return promo_results
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Promotional impact analysis error: {str(e)}'}
    
    def analyze_customer_cohorts(self, df, customer_col=None, date_col=None, amount_col=None):
        """Analyze customer cohorts based on first purchase date (signup cohort)
        
        Groups customers by acquisition month and tracks their behavior over time
        Measures retention, repeat purchase rates, and lifetime value by cohort
        
        Returns:
            - Dictionary with cohort metrics, retention rates, and insights
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'cohorts': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            if customer_col is None:
                customer_keywords = ['customer', 'customer id', 'customer_id', 'client', 'buyer', 'id']
                customer_candidates = [col for col in df.columns if any(k in col.lower() for k in customer_keywords)]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'purchase date', 'transaction date', 'order date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_keywords = ['amount', 'revenue', 'total', 'sales', 'total amount', 'price', 'value']
                amount_candidates = [col for col in df.columns if any(k in col.lower() for k in amount_keywords)]
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
            
            # Convert amount to numeric if present
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
            cohorts = sorted([c for c in df_copy['cohort_month'].unique() if pd.notna(c)])
            
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
            retention_table = []
            try:
                cohort_month_group = df_copy.groupby(['cohort_month', 'months_since_cohort'])[customer_col].nunique().reset_index()
                cohort_month_group.columns = ['cohort_month', 'month', 'customers']
                
                # Pivot to matrix
                cohort_pivot = cohort_month_group.pivot_table(
                    index='cohort_month',
                    columns='month',
                    values='customers',
                    fill_value=0
                )
                
                # Convert to percentages (retention rates)
                cohort_size_col = cohort_pivot.iloc[:, 0]
                retention_table_df = cohort_pivot.divide(cohort_size_col, axis=0) * 100
                
                # Convert to dict format for JSON
                for idx, row in retention_table_df.iterrows():
                    row_data = {
                        'cohort': str(idx),
                        'data': {str(col): round(float(val), 2) for col, val in row.items()}
                    }
                    retention_table.append(row_data)
            except Exception as e:
                print(f"Error building retention table: {e}")
            
            # Generate insights
            insights = []
            if cohort_metrics:
                # Find best performing cohort
                best_cohort = max(cohort_metrics, key=lambda x: x['lifetime_value'])
                insights.append(
                    f"🏆 Best cohort: {best_cohort['cohort_month']} (${best_cohort['lifetime_value']:,.0f} LTV)"
                )
                
                # Average cohort size
                avg_size = np.mean([c['cohort_size'] for c in cohort_metrics])
                insights.append(f"📊 Avg cohort size: {avg_size:,.0f} customers")
            
            return {
                'success': True,
                'message': 'Cohort analysis completed',
                'cohorts': cohort_metrics,
                'retention_table': retention_table,
                'total_cohorts': len(cohort_metrics),
                'insights': insights,
                'analysis_period': {
                    'start': str(cohorts[0]) if cohorts else 'N/A',
                    'end': str(cohorts[-1]) if cohorts else 'N/A'
                }
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Cohort analysis failed: {str(e)}',
                'cohorts': []
            }
    
    def analyze_geography(self, df, region_col=None, amount_col=None, customer_col=None):
        """Analyze sales performance by geographic region
        
        Groups sales by region and calculates key metrics:
        - Total revenue by region
        - Market share percentage
        - Customer concentration
        - Regional growth potential
        - Performance tiers
        
        Args:
            df: DataFrame with sales data (must have region/location column)
            region_col: Column name for region (auto-detected if None)
            amount_col: Column name for transaction amount (auto-detected if None)
            customer_col: Column name for customer ID (optional, auto-detected if None)
            
        Returns:
            Dictionary with geographic metrics, regional rankings, and insights
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'regions': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            region_col = self._detect_region_column(df, preferred=region_col)
            amount_col = self._detect_amount_column(df, preferred=amount_col)
            customer_col = self._detect_customer_column(df, preferred=customer_col)
            
            if region_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (region/location, amount)',
                    'regions': []
                }
            
            # Convert amount to numeric
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            df_copy[region_col] = df_copy[region_col].astype(str).str.strip()
            df_copy = df_copy[(df_copy[region_col] != '') & (df_copy[region_col].str.lower() != 'nan')]
            df_copy = df_copy.dropna(subset=[amount_col])

            if df_copy.empty:
                return {
                    'success': False,
                    'message': 'No valid geographic rows found after column mapping',
                    'regions': []
                }
            
            # Group by region
            agg_spec = {
                amount_col: ['sum', 'count', 'mean', 'min', 'max', 'std']
            }
            if customer_col and customer_col in df_copy.columns:
                agg_spec[customer_col] = 'nunique'

            region_stats = df_copy.groupby(region_col).agg(agg_spec).reset_index()

            if region_stats.empty:
                return {
                    'success': False,
                    'message': 'No geographic groups available after cleaning data',
                    'regions': []
                }
            
            if customer_col and customer_col in df_copy.columns:
                region_stats.columns = ['Region', 'Total_Revenue', 'Transaction_Count', 'Avg_Transaction_Value',
                                       'Min_Transaction', 'Max_Transaction', 'Std_Dev', 'Unique_Customers']
            else:
                region_stats.columns = ['Region', 'Total_Revenue', 'Transaction_Count', 'Avg_Transaction_Value',
                                       'Min_Transaction', 'Max_Transaction', 'Std_Dev']
                region_stats['Unique_Customers'] = 0
            
            # Calculate market metrics
            total_revenue = region_stats['Total_Revenue'].sum()
            region_stats['Market_Share_Pct'] = (region_stats['Total_Revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            region_stats['Revenue_Per_Customer'] = (
                region_stats['Total_Revenue'] / region_stats['Unique_Customers']
            ) if customer_col else 0
            
            # Calculate growth potential score
            region_stats['Growth_Score'] = (
                (region_stats['Transaction_Count'] / region_stats['Transaction_Count'].max() * 50) +
                (region_stats['Unique_Customers'] / region_stats['Unique_Customers'].max() * 50) if customer_col else region_stats['Transaction_Count']
            )
            
            # Categorize region performance
            def get_performance_tier(row, df_stats):
                revenue_75 = df_stats['Total_Revenue'].quantile(0.75)
                revenue_50 = df_stats['Total_Revenue'].quantile(0.50)
                
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
    
    def analyze_timeseries(self, df, date_col=None, amount_col=None, period=12):
        """Analyze time-series data and decompose into trend, seasonal, and residual components
        
        Separates time-series into:
        - Trend: Long-term direction of the data
        - Seasonal: Repeating patterns (e.g., yearly cycles)
        - Residual: Unexplained variation/noise
        
        Args:
            df: DataFrame with time-series data
            date_col: Column name for dates (auto-detected if None)
            amount_col: Column name for values (auto-detected if None)
            period: Seasonality period in observations (default 12 for monthly data = yearly pattern)
            
        Returns:
            Dictionary with decomposition components, statistics, and interpretation
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'components': {}
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            date_col = self._detect_date_column(df, preferred=date_col)
            amount_col = self._detect_amount_column(df, preferred=amount_col)
            
            if date_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (date, amount)',
                    'components': {}
                }
            
            # Convert to proper types
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[date_col, amount_col])

            if len(df_copy) < 3:
                return {
                    'success': False,
                    'message': 'Insufficient valid date/amount rows after mapping',
                    'components': {}
                }
            
            # Aggregate by date (sum amounts by date)
            ts_data = df_copy.groupby(date_col)[amount_col].sum().reset_index()
            ts_data = ts_data.sort_values(date_col)

            if ts_data.empty:
                return {
                    'success': False,
                    'message': 'No valid time-series points available after cleaning',
                    'components': {}
                }
            
            # Set date as index
            ts_data.set_index(date_col, inplace=True)
            ts_series = ts_data[amount_col]
            
            # If data is too sparse, resample to ensure regularity
            ts_series = ts_series.resample('D').sum()

            if ts_series.empty or int(ts_series.notna().sum()) < 3:
                return {
                    'success': False,
                    'message': 'Insufficient time-series observations for decomposition',
                    'components': {}
                }

            if float(ts_series.abs().sum()) <= 0:
                return {
                    'success': False,
                    'message': 'Time-series values are all zero after mapping. Check amount column mapping.',
                    'components': {}
                }
            
            # Apply simple moving average for trend
            window_size = max(7, period // 2)  # At least 7-day window
            trend = ts_series.rolling(window=window_size, center=True).mean()
            
            # Calculate detrended series (Original - Trend)
            detrended = ts_series - trend
            
            # Calculate seasonal component
            seasonal = pd.Series(index=ts_series.index, dtype=float)
            
            for i in range(len(ts_series)):
                period_position = i % period if period > 0 else i
                period_indices = [j for j in range(len(ts_series)) if ((j % period) == period_position)]
                
                if period_indices:
                    seasonal_values = [detrended.iloc[j] for j in period_indices if pd.notna(detrended.iloc[j])]
                    if seasonal_values:
                        seasonal.iloc[i] = np.nanmean(seasonal_values)
                    else:
                        seasonal.iloc[i] = 0
                else:
                    seasonal.iloc[i] = 0
            
            # Calculate residual (Original - Trend - Seasonal)
            residual = ts_series - trend - seasonal
            
            # Convert to dict format for JSON response (sample every 7 days to reduce data size)
            result_data = {
                'original': [],
                'trend': [],
                'seasonal': [],
                'residual': []
            }
            
            for idx, val in ts_series.items():
                result_data['original'].append({
                    'date': str(idx.date()),
                    'value': float(val) if pd.notna(val) else None
                })
                result_data['trend'].append({
                    'date': str(idx.date()),
                    'value': float(trend[idx]) if pd.notna(trend[idx]) else None
                })
                result_data['seasonal'].append({
                    'date': str(idx.date()),
                    'value': float(seasonal[idx]) if pd.notna(seasonal[idx]) else None
                })
                result_data['residual'].append({
                    'date': str(idx.date()),
                    'value': float(residual[idx]) if pd.notna(residual[idx]) else None
                })
            
            # Calculate statistics
            trend_clean = trend.dropna()
            seasonal_clean = seasonal[seasonal != 0]
            residual_clean = residual.dropna()
            
            stats = {
                'total_observations': len(ts_series),
                'date_range': {
                    'start': str(ts_series.index.min().date()),
                    'end': str(ts_series.index.max().date())
                },
                'original_stats': {
                    'mean': float(ts_series.mean()),
                    'std_dev': float(ts_series.std()),
                    'min': float(ts_series.min()),
                    'max': float(ts_series.max())
                },
                'trend_stats': {
                    'direction': 'Upward' if len(trend_clean) > 1 and trend_clean.iloc[-1] > trend_clean.iloc[0] else 'Downward',
                    'change_pct': float((trend_clean.iloc[-1] - trend_clean.iloc[0]) / trend_clean.iloc[0] * 100) if len(trend_clean) > 1 and trend_clean.iloc[0] != 0 else 0,
                    'volatility': float(trend_clean.std()) if len(trend_clean) > 1 else 0
                },
                'seasonal_stats': {
                    'strength': float(np.var(seasonal_clean) / np.var(seasonal_clean + residual_clean)) if len(residual_clean) > 0 and len(seasonal_clean) > 0 else 0,
                    'period': period,
                    'amplitude': float(seasonal_clean.max() - seasonal_clean.min()) if len(seasonal_clean) > 0 else 0
                },
                'residual_stats': {
                    'mean': float(residual_clean.mean()),
                    'std_dev': float(residual_clean.std()),
                    'autocorrelation': float(self._calculate_autocorr(residual_clean))
                }
            }
            
            # Generate interpretation
            interpretation = []
            trend_dir = stats['trend_stats']['direction']
            trend_change = stats['trend_stats']['change_pct']
            interpretation.append(f"📈 {trend_dir} trend with {abs(trend_change):.1f}% overall change")
            
            seasonal_strength = stats['seasonal_stats']['strength']
            if seasonal_strength > 0.3:
                interpretation.append(f"🔄 Strong seasonality detected (strength: {seasonal_strength:.2f})")
            elif seasonal_strength > 0.1:
                interpretation.append(f"🔄 Moderate seasonality detected (strength: {seasonal_strength:.2f})")
            else:
                interpretation.append(f"🔄 Weak seasonality (strength: {seasonal_strength:.2f})")
            
            residual_std = stats['residual_stats']['std_dev']
            original_std = stats['original_stats']['std_dev']
            noise_ratio = (residual_std / original_std * 100) if original_std > 0 else 0
            interpretation.append(f"🔊 Unexplained variance: {noise_ratio:.1f}% of original variation")
            
            return {
                'success': True,
                'message': 'Time-series decomposition completed',
                'components': result_data,
                'statistics': stats,
                'interpretation': interpretation
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Time-series decomposition failed: {str(e)}',
                'components': {}
            }
    
    def predict_churn(self, df, customer_col=None, date_col=None, amount_col=None, days_threshold=90):
        """Predict which customers are at risk of churning
        
        Uses RFM analysis to calculate churn risk scores (0-100):
        - Recency: Days since last purchase (higher = higher risk)
        - Frequency: Purchase frequency (lower = higher risk)
        - Monetary: Total spending (lower = higher risk)
        
        Categorizes customers into risk levels:
        - Critical (80-100): Immediate retention needed
        - High (60-80): High risk, requires attention
        - Medium (40-60): Monitor closely
        - Low (20-40): Low risk, stable
        - Minimal (0-20): Loyal customers
        
        Args:
            df: DataFrame with transaction data
            customer_col: Customer ID column (auto-detected if None)
            date_col: Date column (auto-detected if None)
            amount_col: Transaction amount column (auto-detected if None)
            days_threshold: Days of inactivity threshold (default 90)
            
        Returns:
            Dictionary with churn predictions, risk scores, and at-risk customer list
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'at_risk_customers': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if customer_col is None:
                customer_keywords = ['customer', 'customer id', 'customer_id', 'client', 'buyer', 'id']
                customer_candidates = [col for col in df.columns if any(k in col.lower() for k in customer_keywords)]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_keywords = ['amount', 'revenue', 'total', 'sales', 'total amount', 'price', 'value']
                amount_candidates = [col for col in df.columns if any(k in col.lower() for k in amount_keywords)]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if customer_col is None or date_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (customer_id, date)',
                    'at_risk_customers': []
                }
            
            # Convert to proper types
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Current date
            current_date = df_copy[date_col].max()
            
            # Calculate RFM metrics
            rfm_data = df_copy.groupby(customer_col).agg({
                date_col: ['max', 'count', 'min'],
                amount_col: ['sum', 'mean']
            }).reset_index()
            
            rfm_data.columns = ['Customer_ID', 'Last_Purchase', 'Frequency', 'First_Purchase', 'Monetary', 'Avg_Order_Value']
            
            # Calculate Recency
            rfm_data['Recency_Days'] = (current_date - rfm_data['Last_Purchase']).dt.days
            
            # Calculate customer age
            rfm_data['Customer_Age_Days'] = (rfm_data['Last_Purchase'] - rfm_data['First_Purchase']).dt.days
            
            # Calculate purchase frequency (purchases per month)
            rfm_data['Purchase_Frequency_Monthly'] = (rfm_data['Frequency'] / max(rfm_data['Customer_Age_Days'].max() / 30, 1)).round(2)
            
            # Calculate churn risk score
            scores = []
            for idx, row in rfm_data.iterrows():
                max_recency = rfm_data['Recency_Days'].max()
                recency_score = min((row['Recency_Days'] / days_threshold) * 50, 50)
                
                max_frequency = rfm_data['Frequency'].max()
                frequency_score = max(0, 30 - (row['Frequency'] / max_frequency * 30)) if max_frequency > 0 else 30
                
                max_monetary = rfm_data['Monetary'].max()
                monetary_score = max(0, 20 - (row['Monetary'] / max_monetary * 20)) if max_monetary > 0 else 20
                
                total_score = min(recency_score + frequency_score + monetary_score, 100)
                scores.append(total_score)
            
            rfm_data['Churn_Risk_Score'] = np.array(scores)
            
            # Categorize risk level
            def get_risk_level(score):
                if score >= 80:
                    return 'Critical'
                elif score >= 60:
                    return 'High'
                elif score >= 40:
                    return 'Medium'
                elif score >= 20:
                    return 'Low'
                else:
                    return 'Minimal'
            
            rfm_data['Risk_Level'] = rfm_data['Churn_Risk_Score'].apply(get_risk_level)
            
            # Sort by churn risk
            rfm_data = rfm_data.sort_values('Churn_Risk_Score', ascending=False).reset_index(drop=True)
            
            # Get at-risk customers
            at_risk = rfm_data[rfm_data['Churn_Risk_Score'] >= 40]
            
            # Build response
            at_risk_list = []
            for idx, row in at_risk.head(20).iterrows():
                # Determine reason
                if row['Recency_Days'] > 180:
                    reason = 'Long inactivity period'
                elif row['Frequency'] < 2:
                    reason = 'Low purchase frequency'
                elif row['Monetary'] < 500:
                    reason = 'Low lifetime value'
                elif row['Recency_Days'] > 90:
                    reason = 'Recent inactivity'
                else:
                    reason = 'Declining engagement'
                
                at_risk_list.append({
                    'rank': idx + 1,
                    'customer_id': str(row['Customer_ID']),
                    'churn_risk_score': float(row['Churn_Risk_Score']),
                    'risk_level': str(row['Risk_Level']),
                    'recency_days': int(row['Recency_Days']),
                    'frequency': int(row['Frequency']),
                    'monetary_value': float(row['Monetary']),
                    'avg_order_value': float(row['Avg_Order_Value']),
                    'purchase_frequency_monthly': float(row['Purchase_Frequency_Monthly']),
                    'last_purchase_date': str(row['Last_Purchase'].date()),
                    'customer_age_days': int(row['Customer_Age_Days']),
                    'reason': reason
                })
            
            # Summary
            summary = {
                'total_customers': len(rfm_data),
                'critical_risk': len(rfm_data[rfm_data['Risk_Level'] == 'Critical']),
                'high_risk': len(rfm_data[rfm_data['Risk_Level'] == 'High']),
                'medium_risk': len(rfm_data[rfm_data['Risk_Level'] == 'Medium']),
                'low_risk': len(rfm_data[rfm_data['Risk_Level'] == 'Low']),
                'minimal_risk': len(rfm_data[rfm_data['Risk_Level'] == 'Minimal']),
                'avg_churn_score': float(rfm_data['Churn_Risk_Score'].mean()),
                'at_risk_count': len(at_risk),
                'at_risk_percentage': round(len(at_risk) / len(rfm_data) * 100, 2)
            }
            
            # Insights
            insights = []
            if len(at_risk) > 0:
                top_risk = at_risk.iloc[0]
                insights.append(f"🚨 CRITICAL: Customer at highest risk (Score: {int(top_risk['Churn_Risk_Score'])})")
            
            if summary['critical_risk'] > 0:
                insights.append(f"⚠️ {summary['critical_risk']} customers in CRITICAL risk - immediate action needed")
            
            insights.append(f"📊 {summary['at_risk_percentage']}% of customer base at churn risk")
            
            return {
                'success': True,
                'message': 'Churn prediction completed',
                'at_risk_customers': at_risk_list,
                'summary': summary,
                'insights': insights
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Churn prediction failed: {str(e)}',
                'at_risk_customers': []
            }
    
    def analyze_forecast(self, df, date_col=None, amount_col=None, periods=30):
        """Forecast future sales using exponential smoothing
        
        Analyzes historical sales patterns and produces forecasts with confidence intervals
        
        Args:
            df: DataFrame with time-series sales data
            date_col: Date column (auto-detected if None)
            amount_col: Sales amount column (auto-detected if None)
            periods: Number of periods to forecast (default 30 days)
            
        Returns:
            Dictionary with forecasted sales, confidence intervals, and trend analysis
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'forecast': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            date_col = self._detect_date_column(df, preferred=date_col)
            amount_col = self._detect_amount_column(df, preferred=amount_col)
            
            if date_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (date, amount)',
                    'forecast': []
                }
            
            # Convert and aggregate
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[date_col, amount_col])

            if len(df_copy) < 7:
                return {
                    'success': False,
                    'message': 'Insufficient valid date/amount rows for forecasting',
                    'forecast': []
                }
            
            # Aggregate by date
            ts_data = df_copy.groupby(date_col)[amount_col].sum().reset_index()
            ts_data = ts_data.sort_values(date_col)
            ts_data.set_index(date_col, inplace=True)
            
            # Resample to ensure daily data
            ts_series = ts_data[amount_col].resample('D').sum()
            
            # Remove zeros for calculation
            ts_clean = ts_series[ts_series > 0]
            
            if len(ts_clean) < 7:
                return {
                    'success': False,
                    'message': 'Insufficient historical data for forecasting',
                    'forecast': []
                }
            
            # Apply exponential smoothing
            alpha = 0.3  # Smoothing factor
            s = ts_clean.mean()
            
            # Exponential smoothing
            for value in ts_clean:
                s = alpha * value + (1 - alpha) * s
            
            # Calculate standard deviation for confidence intervals
            residuals = ts_clean - ts_clean.rolling(window=7).mean()
            residuals = residuals.dropna()
            std_dev = residuals.std() if len(residuals) > 0 else ts_clean.std()
            
            # Calculate trend
            last_30 = ts_clean.tail(30)
            trend = (last_30.iloc[-1] - last_30.iloc[0]) / 30 if len(last_30) > 1 else 0
            
            # Generate forecasts
            last_date = ts_series.index.max()
            forecast_list = []
            
            for i in range(1, periods + 1):
                forecast_date = last_date + timedelta(days=i)
                
                # Exponential smoothing forecast with trend
                forecast_value = s + (trend * i)
                forecast_value = max(forecast_value, 0)  # Ensure non-negative
                
                # Confidence intervals (95% CI)
                margin_of_error = 1.96 * std_dev
                upper_bound = forecast_value + margin_of_error
                lower_bound = max(0, forecast_value - margin_of_error)
                
                forecast_list.append({
                    'date': str(forecast_date.date()),
                    'forecast': float(forecast_value),
                    'upper_bound_95': float(upper_bound),
                    'lower_bound_95': float(lower_bound),
                    'confidence': 95
                })
            
            # Calculate forecast metrics
            forecast_df = pd.DataFrame(forecast_list)
            avg_forecast = forecast_df['forecast'].mean()
            total_forecast = forecast_df['forecast'].sum()
            
            # Trend analysis
            recent_forecast = forecast_df.tail(7)['forecast'].mean()
            early_forecast = forecast_df.head(7)['forecast'].mean()
            trend_direction = 'Upward' if recent_forecast > early_forecast else 'Downward'
            trend_change_pct = ((recent_forecast - early_forecast) / early_forecast * 100) if early_forecast > 0 else 0
            
            # Historical stats
            historical_mean = ts_clean.mean()
            historical_std = ts_clean.std()
            
            summary = {
                'forecast_period_days': periods,
                'total_forecasted_sales': float(total_forecast),
                'average_daily_forecast': float(avg_forecast),
                'trend': trend_direction,
                'trend_change_pct': float(trend_change_pct),
                'historical_mean': float(historical_mean),
                'historical_std': float(historical_std),
                'forecast_std': float(forecast_df['forecast'].std()),
                'confidence_level': 95,
                'forecast_start_date': str(last_date.date()),
                'forecast_end_date': str(forecast_list[-1]['date']),
                'historical_data_points': len(ts_clean),
                'avg_daily_historical': float(ts_clean.mean()),
                'growth_vs_history': float((avg_forecast - historical_mean) / historical_mean * 100)
            }
            
            # Insights
            insights = []
            insights.append(f"Forecast: ${total_forecast:,.0f} total sales over {periods} days")
            insights.append(f"Average daily: ${avg_forecast:,.0f} (historical: ${historical_mean:,.0f})")
            insights.append(f"Trend: {trend_direction} ({abs(trend_change_pct):.1f}% change)")
            
            if avg_forecast > historical_mean * 1.2:
                insights.append("Sales expected to exceed historical average significantly")
            elif avg_forecast < historical_mean * 0.8:
                insights.append("Forecasted sales below historical average")
            
            if trend_direction == 'Upward':
                insights.append(f"Positive momentum: {trend_change_pct:.1f}% growth expected")
            
            return {
                'success': True,
                'message': 'Sales forecasting completed',
                'forecast': forecast_list,
                'summary': summary,
                'insights': insights
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Sales forecasting failed: {str(e)}',
                'forecast': []
            }
    
    def analyze_product_affinity(self, df, product_col=None, transaction_col=None, 
                                amount_col=None, min_support=0.02, min_confidence=0.3):
        """Analyze product affinity and cross-sell opportunities
        
        Identifies products frequently purchased together using market basket analysis
        
        Args:
            df: DataFrame with transaction data
            product_col: Product/Item column (auto-detected if None)
            transaction_col: Transaction ID column (auto-detected if None)
            amount_col: Transaction amount column (optional)
            min_support: Minimum support threshold (default 0.02)
            min_confidence: Minimum confidence threshold (default 0.3)
            
        Returns:
            Dictionary with association rules, affinity matrix, and recommendations
        """
        try:
            if df is None or len(df) == 0:
                return {
                    'success': False,
                    'message': 'No data available',
                    'rules': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if product_col is None:
                product_candidates = [col for col in df.columns 
                                     if col.lower() in ['product', 'product_name', 'item', 'category', 'productname', 'product category', 'product line', 'productline']]
                product_col = product_candidates[0] if product_candidates else None
            
            if transaction_col is None:
                transaction_candidates = [col for col in df.columns 
                                        if col.lower() in ['transaction', 'transaction_id', 'order', 'order_id', 'customer', 'customer_id', 'customer id', 'order id', 'transaction id']]
                transaction_col = transaction_candidates[0] if transaction_candidates else None
            
            if product_col is None or transaction_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (product, transaction_id)',
                    'rules': []
                }
            
            # Create market basket
            market_basket = df_copy.groupby(transaction_col)[product_col].apply(list).reset_index()
            
            if len(market_basket) == 0:
                return {
                    'success': False,
                    'message': 'No transactions found',
                    'rules': []
                }
            
            # Calculate support for individual items
            from collections import Counter
            from itertools import combinations
            
            all_items = []
            for items in market_basket[product_col]:
                all_items.extend(items)
            
            item_support = Counter(all_items)
            total_transactions = len(market_basket)
            item_support_pct = {item: count / total_transactions 
                               for item, count in item_support.items()}
            
            # Filter items by minimum support
            frequent_items = {item: support for item, support in item_support_pct.items() 
                            if support >= min_support}
            
            if len(frequent_items) < 2:
                return {
                    'success': False,
                    'message': f'Not enough frequent items for affinity analysis',
                    'rules': []
                }
            
            # Generate association rules
            rules = []
            affinity_scores = {}
            
            # Find product pairs
            for transaction_items in market_basket[product_col]:
                transaction_items = [item for item in transaction_items 
                                    if item in frequent_items]
                
                if len(transaction_items) >= 2:
                    pairs = list(combinations(sorted(set(transaction_items)), 2))
                    for pair in pairs:
                        pair_key = f"{pair[0]} -> {pair[1]}"
                        affinity_scores[pair_key] = affinity_scores.get(pair_key, 0) + 1
            
            # Calculate metrics
            for pair_key, pair_count in affinity_scores.items():
                product_a, product_b = pair_key.split(' -> ')
                
                pair_support = pair_count / total_transactions
                confidence = pair_count / item_support[product_a] \
                    if item_support[product_a] > 0 else 0
                
                lift = pair_support / (item_support_pct[product_a] * item_support_pct[product_b]) \
                    if (item_support_pct[product_a] * item_support_pct[product_b]) > 0 else 0
                
                if confidence >= min_confidence and lift > 1:
                    rules.append({
                        'product_a': product_a,
                        'product_b': product_b,
                        'support': float(pair_support),
                        'confidence': float(confidence),
                        'lift': float(lift),
                        'co_purchase_count': int(pair_count),
                        'strength': 'Very Strong' if lift > 3 else 'Strong' if lift > 2 else 'Moderate'
                    })
            
            # Sort by lift
            rules = sorted(rules, key=lambda x: x['lift'], reverse=True)
            
            # Build affinity matrix
            affinity_matrix = {}
            for product in frequent_items.keys():
                affinity_matrix[product] = {
                    'support': float(frequent_items[product]),
                    'frequency': int(item_support[product]),
                    'related_products': []
                }
            
            for rule in rules[:50]:
                product_a = rule['product_a']
                product_b = rule['product_b']
                
                if product_a in affinity_matrix:
                    affinity_matrix[product_a]['related_products'].append({
                        'product': product_b,
                        'confidence': rule['confidence'],
                        'lift': rule['lift']
                    })
            
            # Generate recommendations
            recommendations = []
            for rule in rules[:10]:
                recommendation = {
                    'when_bought': rule['product_a'],
                    'also_recommend': rule['product_b'],
                    'likelihood': f"{rule['confidence']*100:.1f}%",
                    'strength': rule['strength'],
                    'co_purchase_count': rule['co_purchase_count'],
                    'lift_multiplier': f"{rule['lift']:.2f}x"
                }
                recommendations.append(recommendation)
            
            # Summary
            summary = {
                'total_products': len(frequent_items),
                'total_rules': len(rules),
                'top_product_pair': f"{rules[0]['product_a']} & {rules[0]['product_b']}" \
                    if rules else 'N/A',
                'highest_confidence': float(max([r['confidence'] for r in rules], default=0)),
                'highest_lift': float(max([r['lift'] for r in rules], default=0)),
                'average_confidence': float(np.mean([r['confidence'] for r in rules])) \
                    if rules else 0,
                'average_lift': float(np.mean([r['lift'] for r in rules])) \
                    if rules else 0,
                'total_transactions': total_transactions,
                'opportunities_count': len([r for r in rules if r['strength'] in ['Strong', 'Very Strong']])
            }
            
            # Insights
            insights = []
            insights.append(f"Found {len(rules)} product associations")
            if rules:
                insights.append(f"Top combo: {summary['top_product_pair']} " +
                              f"({summary['highest_confidence']*100:.0f}% confidence)")
            
            strong_rules = [r for r in rules[:5] if r['strength'] == 'Very Strong']
            if strong_rules:
                insights.append(f"{len(strong_rules)} very strong cross-sell opportunities")
            
            if rules:
                insights.append(f"Cross-sell potential: {summary['average_lift']:.1f}x" +
                              f" average lift across rules")
            
            return {
                'success': True,
                'message': 'Product affinity analysis completed',
                'rules': rules[:50],
                'affinity_matrix': affinity_matrix,
                'recommendations': recommendations,
                'summary': summary,
                'insights': insights
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Affinity analysis failed: {str(e)}',
                'rules': []
            }
    
    def _calculate_autocorr(self, series):
        """Calculate autocorrelation at lag 1"""
        try:
            clean_series = series.dropna()
            if len(clean_series) <= 1:
                return 0
            return float(clean_series.corr(clean_series.shift(1)))
        except:
            return 0
    
    def analyze_dataset(self, filepath, file_id):
        """Complete analysis of dataset"""
        try:
            # Load dataset
            df = self.load_dataset(filepath)
            if df is None:
                return {'success': False, 'message': 'Failed to load dataset'}
            
            # Cache dataset
            self.datasets[file_id] = df
            
            # Extract all analytics
            analysis = {
                'success': True,
                'kpis': self.get_real_kpis(df),
                'trends': self.get_revenue_trends(df, 'month'),
                'top_categories': self.get_top_categories(df, top_n=4),
                'segments': self.get_customer_segments(df),
                'row_count': len(df),
                'columns': list(df.columns)
            }
            
            # Cache analysis
            self.analysis_cache[file_id] = analysis
            
            return analysis
        
        except Exception as e:
            print(f"Error in dataset analysis: {e}")
            return {'success': False, 'message': str(e)}


# Global instance
_real_analytics_service = None

def get_real_analytics_service():
    """Get or create singleton instance"""
    global _real_analytics_service
    if _real_analytics_service is None:
        _real_analytics_service = RealAnalyticsService()
    return _real_analytics_service
