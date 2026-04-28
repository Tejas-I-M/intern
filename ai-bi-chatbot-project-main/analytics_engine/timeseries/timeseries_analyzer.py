"""
Time-Series Decomposition Engine - Separates seasonal patterns, trends, and residuals
Analyzes temporal patterns to identify trends, seasonality, and anomalies over time
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TimeSeriesAnalyzer:
    """Perform time-series analysis and decomposition"""
    
    def __init__(self):
        self.ts_data = None
    
    def decompose_timeseries(self, df, date_col=None, amount_col=None, period=12):
        """
        Decompose time series into trend, seasonal, and residual components
        
        Args:
            df: DataFrame with time-series data
            date_col: Column name for dates
            amount_col: Column name for values (revenue/sales)
            period: Seasonality period (12 for monthly data = yearly pattern)
            
        Returns:
            dict with decomposition components and analysis
        """
        try:
            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'Empty dataset',
                    'components': {}
                }
            
            df_copy = df.copy()
            
            # Auto-detect columns if not provided
            if date_col is None:
                date_candidates = [col for col in df.columns 
                                  if col.lower() in ['date', 'transaction_date', 'purchase_date', 'order_date']]
                date_col = date_candidates[0] if date_candidates else None
            
            if amount_col is None:
                amount_candidates = [col for col in df.columns 
                                    if col.lower() in ['amount', 'revenue', 'total', 'sales', 'total amount']]
                amount_col = amount_candidates[0] if amount_candidates else None
            
            if date_col is None or amount_col is None:
                return {
                    'success': False,
                    'message': 'Required columns not found (date, amount)',
                    'components': {}
                }
            
            # Convert to proper types
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            # Aggregate by date (sum amounts by date)
            ts_data = df_copy.groupby(date_col)[amount_col].sum().reset_index()
            ts_data = ts_data.sort_values(date_col)
            
            # Set date as index
            ts_data.set_index(date_col, inplace=True)
            ts_series = ts_data[amount_col]
            
            # If data is too sparse, resample to ensure regularity
            ts_series = ts_series.resample('D').sum()
            
            # Apply simple moving average for trend
            window_size = max(7, period // 2)  # At least 7-day window
            trend = ts_series.rolling(window=window_size, center=True).mean()
            
            # Calculate detrended series (Original - Trend)
            detrended = ts_series - trend
            
            # Calculate seasonal component (average pattern for each period position)
            seasonal = pd.Series(index=ts_series.index, dtype=float)
            
            for i in range(len(ts_series)):
                # Find all data points at same position in cycle
                period_position = i % period if period > 0 else i
                period_indices = [j for j in range(len(ts_series)) if ((j % period) == period_position)]
                
                if period_indices:
                    # Average of detrended values at this position
                    seasonal_values = [detrended.iloc[j] for j in period_indices if pd.notna(detrended.iloc[j])]
                    if seasonal_values:
                        seasonal.iloc[i] = np.nanmean(seasonal_values)
                    else:
                        seasonal.iloc[i] = 0
                else:
                    seasonal.iloc[i] = 0
            
            # Calculate residual (Original - Trend - Seasonal)
            residual = ts_series - trend - seasonal
            
            # Convert to dict format for JSON response
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
                    'direction': 'Upward' if trend_clean[-1] > trend_clean[0] else 'Downward',
                    'change_pct': float((trend_clean[-1] - trend_clean[0]) / trend_clean[0] * 100) if trend_clean[0] != 0 else 0,
                    'volatility': float(trend_clean.std()) if len(trend_clean) > 1 else 0
                },
                'seasonal_stats': {
                    'strength': float(np.var(seasonal_clean) / np.var(seasonal_clean + residual_clean)) if len(residual_clean) > 0 else 0,
                    'period': period,
                    'amplitude': float(seasonal_clean.max() - seasonal_clean.min()) if len(seasonal_clean) > 0 else 0
                },
                'residual_stats': {
                    'mean': float(residual_clean.mean()),
                    'std_dev': float(residual_clean.std()),
                    'autocorrelation': float(self._calculate_autocorr(residual_clean, 1))
                }
            }
            
            return {
                'success': True,
                'message': 'Time-series decomposition completed',
                'components': result_data,
                'statistics': stats,
                'interpretation': self._generate_interpretation(stats)
            }
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Time-series decomposition failed: {str(e)}',
                'components': {}
            }
    
    def detect_trends(self, df, date_col=None, amount_col=None, window=30):
        """Detect uptrends and downtrends in time series"""
        try:
            if df is None or df.empty:
                return {'success': False, 'message': 'Empty dataset', 'trends': []}
            
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
                return {'success': False, 'message': 'Required columns not found', 'trends': []}
            
            # Convert and aggregate
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy[amount_col] = pd.to_numeric(df_copy[amount_col], errors='coerce')
            
            ts_data = df_copy.groupby(date_col)[amount_col].sum().reset_index()
            ts_data = ts_data.sort_values(date_col)
            
            ts_series = ts_data[amount_col].values
            
            # Calculate moving average
            ma = pd.Series(ts_series).rolling(window=window).mean().values
            
            # Detect trend changes
            trends_detected = []
            current_trend = None
            trend_start = 0
            
            for i in range(window, len(ma)):
                if pd.notna(ma[i]) and pd.notna(ma[i-1]):
                    if ma[i] > ma[i-1]:
                        new_trend = 'Uptrend'
                    else:
                        new_trend = 'Downtrend'
                    
                    if new_trend != current_trend:
                        if current_trend:
                            trends_detected.append({
                                'trend': current_trend,
                                'start_idx': trend_start,
                                'end_idx': i,
                                'duration_days': i - trend_start,
                                'start_value': float(ts_series[trend_start]),
                                'end_value': float(ts_series[i]),
                                'change_pct': float((ts_series[i] - ts_series[trend_start]) / ts_series[trend_start] * 100)
                            })
                        current_trend = new_trend
                        trend_start = i
            
            return {
                'success': True,
                'message': 'Trend detection completed',
                'trends': trends_detected,
                'current_trend': current_trend
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Trend detection failed: {str(e)}', 'trends': []}
    
    def _calculate_autocorr(self, series, lag=1):
        """Calculate autocorrelation at given lag"""
        try:
            clean_series = series.dropna()
            if len(clean_series) <= lag:
                return 0
            
            # Calculate Pearson correlation between series and lagged series
            return clean_series.corr(clean_series.shift(lag))
        except:
            return 0
    
    def _generate_interpretation(self, stats):
        """Generate human-readable interpretation of decomposition"""
        interpretation = []
        
        # Trend interpretation
        trend_dir = stats['trend_stats']['direction']
        trend_change = stats['trend_stats']['change_pct']
        interpretation.append(f"📈 {trend_dir} trend with {abs(trend_change):.1f}% overall change")
        
        # Seasonality interpretation
        seasonal_strength = stats['seasonal_stats']['strength']
        if seasonal_strength > 0.3:
            interpretation.append(f"🔄 Strong seasonality detected (strength: {seasonal_strength:.2f})")
        elif seasonal_strength > 0.1:
            interpretation.append(f"🔄 Moderate seasonality detected (strength: {seasonal_strength:.2f})")
        else:
            interpretation.append(f"🔄 Weak seasonality (strength: {seasonal_strength:.2f})")
        
        # Residual interpretation
        residual_std = stats['residual_stats']['std_dev']
        original_std = stats['original_stats']['std_dev']
        noise_ratio = (residual_std / original_std * 100) if original_std > 0 else 0
        interpretation.append(f"🔊 Unexplained variance: {noise_ratio:.1f}% of original variation")
        
        return interpretation


def timeseries_decomposition(df, date_col=None, amount_col=None, period=12):
    """Quick time-series decomposition function"""
    analyzer = TimeSeriesAnalyzer()
    return analyzer.decompose_timeseries(df, date_col, amount_col, period)
