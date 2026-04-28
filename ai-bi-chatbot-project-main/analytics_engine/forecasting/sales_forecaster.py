"""
Advanced Sales Forecasting Engine - Predicts future sales with confidence intervals
Uses exponential smoothing and trend analysis for accurate forecasting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class SalesForecaster:
    """Advanced sales forecasting"""
    
    def __init__(self):
        self.forecast_data = None
    
    def forecast_sales(self, df, date_col=None, amount_col=None, periods=30, method='exponential'):
        """
        Forecast future sales using exponential smoothing or ARIMA-like approach
        
        Args:
            df: DataFrame with time-series sales data
            date_col: Column name for dates
            amount_col: Column name for sales amount
            periods: Number of periods to forecast (default 30 days)
            method: 'exponential' for exponential smoothing (default)
            
        Returns:
            dict with forecasted sales and confidence intervals
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'forecast': []
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if date_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (date, amount)',
                    'forecast': []
                }
            
            # Convert and aggregate
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Aggregate by date
            ts_data = df_copy.groupby(date_col)[amount_col].sum().reset_index()
            ts_data = ts_data.sort_values(date_col)
            ts_data.set_index(date_col, inplace=True)
            
            # Resample to ensure daily data
            ts_series = ts_data[amount_col].resample('D').sum()
            
            # Remove zeros for calculation
            ts_clean = ts_series[ts_series > 0]
            
            # Apply exponential smoothing
            alpha = 0.3  # Smoothing factor
            forecast_values = []
            
            # Initialize with mean
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
            forecast_df  = pd.DataFrame(forecast_list)
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
                'forecast_end_date': str(forecast_list[-1]['date'])
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


def sales_forecast(df, date_col=None, amount_col=None, periods=30):
    """Quick sales forecast function"""
    forecaster = SalesForecaster()
    return forecaster.forecast_sales(df, date_col, amount_col, periods)
