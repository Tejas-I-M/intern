"""
Churn Prediction Engine - Predicts which customers are at risk of leaving
Uses RFM analysis and temporal patterns to calculate churn risk scores
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class ChurnPredictor:
    """Predict customer churn risk"""
    
    def __init__(self):
        self.churn_scores = None
    
    def predict_churn(self, df, customer_col=None, date_col=None, amount_col=None, days_threshold=90):
        """
        Predict which customers are at risk of churning
        
        Args:
            df: DataFrame with transaction data
            customer_col: Column name for customer ID
            date_col: Column name for transaction date
            amount_col: Column name for transaction amount
            days_threshold: Days of inactivity to consider as churn risk (default 90)
            
        Returns:
            dict with churn predictions and risk scores
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'at_risk_customers': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if customer_col is None:
                customer_candidates = [col for col in df.columns 
                                      if col.lower() in ['customer', 'customer id', 'customer_id', 'id']]
                customer_col = customer_candidates[0] if customer_candidates else None
            
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
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
            
            # Calculate Recency (days since last purchase)
            rfm_data['Recency_Days'] = (current_date - rfm_data['Last_Purchase']).dt.days
            
            # Calculate days as customer
            rfm_data['Customer_Age_Days'] = (rfm_data['Last_Purchase'] - rfm_data['First_Purchase']).dt.days
            
            # Calculate purchase frequency (purchases per month)
            rfm_data['Purchase_Frequency_Monthly'] = (rfm_data['Frequency'] / max(rfm_data['Customer_Age_Days'].max() / 30, 1)).round(2)
            
            # Calculate churn risk score (0-100)
            churn_scores = self._calculate_churn_score(rfm_data, days_threshold)
            rfm_data['Churn_Risk_Score'] = churn_scores
            
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
            
            # Sort by churn risk score
            rfm_data = rfm_data.sort_values('Churn_Risk_Score', ascending=False).reset_index(drop=True)
            
            # Get at-risk customers (score >= 40)
            at_risk = rfm_data[rfm_data['Churn_Risk_Score'] >= 40]
            
            # Build response
            at_risk_list = []
            for idx, row in at_risk.head(20).iterrows():
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
                    'reason': self._get_churn_reason(row)
                })
            
            # Summary statistics
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
            
            # Generate insights
            insights = []
            if len(at_risk) > 0:
                top_at_risk = at_risk.iloc[0]
                insights.append(f"🚨 CRITICAL: {int(at_risk.iloc[0]['Customer_ID'])} at highest risk (Score: {int(at_risk.iloc[0]['Churn_Risk_Score'])})")
            
            critical_count = summary['critical_risk']
            if critical_count > 0:
                insights.append(f"⚠️ {critical_count} customers in CRITICAL risk - immediate retention action needed")
            
            insights.append(f"📊 {summary['at_risk_percentage']}% of customer base at risk of churning")
            
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
    
    def _calculate_churn_score(self, rfm_data, days_threshold):
        """Calculate churn risk score (0-100)"""
        scores = []
        
        for idx, row in rfm_data.iterrows():
            # High recency (days since last purchase) = high churn risk
            max_recency = rfm_data['Recency_Days'].max()
            recency_score = min((row['Recency_Days'] / days_threshold) * 50, 50)
            
            # Low frequency = high churn risk
            max_frequency = rfm_data['Frequency'].max()
            frequency_score = max(0, 30 - (row['Frequency'] / max_frequency * 30)) if max_frequency > 0 else 30
            
            # Low monetary value = high churn risk
            max_monetary = rfm_data['Monetary'].max()
            monetary_score = max(0, 20 - (row['Monetary'] / max_monetary * 20)) if max_monetary > 0 else 20
            
            # Combined score
            total_score = min(recency_score + frequency_score + monetary_score, 100)
            scores.append(total_score)
        
        return np.array(scores)
    
    def _get_churn_reason(self, customer_row):
        """Identify primary reason for churn risk"""
        recency = customer_row['Recency_Days']
        frequency = customer_row['Frequency']
        monetary = customer_row['Monetary']
        
        if recency > 180:
            return 'Long inactivity period'
        elif frequency < 2:
            return 'Low purchase frequency'
        elif monetary < 500:
            return 'Low lifetime value'
        elif recency > 90:
            return 'Recent inactivity'
        else:
            return 'Declining engagement'


def churn_prediction(df, customer_col=None, date_col=None, amount_col=None, days_threshold=90):
    """Quick churn prediction function"""
    predictor = ChurnPredictor()
    return predictor.predict_churn(df, customer_col, date_col, amount_col, days_threshold)
