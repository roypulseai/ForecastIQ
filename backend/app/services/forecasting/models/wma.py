import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from .base import BaseForecaster

class WMAForecaster(BaseForecaster):
    def __init__(self, window: int = 8):
        super().__init__("WMA")
        self.window = window
        self._historical_mean = None
        self._seasonal_factors = {}
        self._promo_effects = {}
        self._last_values = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'WMAForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        self._last_values = ts
        self._historical_mean = ts.mean()
        
        if len(ts) >= 14:
            ts_dayofweek = ts.copy()
            ts_dayofweek.index = pd.to_datetime(ts_dayofweek.index)
            seasonal = ts_dayofweek.groupby(ts_dayofweek.index.dayofweek).mean()
            overall_mean = ts_dayofweek.mean()
            self._seasonal_factors = {
                i: (seasonal.get(i, overall_mean) / overall_mean) if overall_mean != 0 else 1.0
                for i in range(7)
            }
        
        self._promo_effects = {}
        if exog_data and 'promotions' in exog_data and exog_data['promotions'] is not None:
            promo_df = exog_data['promotions']
            for _, row in promo_df.iterrows():
                discount = row.get('discount', 0)
                self._promo_effects[row['date']] = 1 + (discount / 100)
        
        return self
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if self._historical_mean is None:
            raise ValueError("Model not fitted")
        
        last_date = pd.to_datetime(self._last_values.index[-1]) if hasattr(self, '_last_values') else pd.Timestamp.now()
        
        results = []
        base_value = self._historical_mean
        
        for i in range(horizon):
            future_date = last_date + pd.Timedelta(days=i+1)
            date_str = str(future_date.date())
            
            forecast_value = base_value
            
            if future_date.dayofweek in self._seasonal_factors:
                forecast_value *= self._seasonal_factors[future_date.dayofweek]
            
            promo_multiplier = 1.0
            if date_str in self._promo_effects:
                promo_multiplier = self._promo_effects[date_str]
            elif exog_data and 'promotions' in exog_data and exog_data['promotions'] is not None:
                promo_df = exog_data['promotions']
                for _, row in promo_df.iterrows():
                    if str(row.get('date', '')) == date_str:
                        promo_multiplier = 1 + (row.get('discount', 0) / 100)
                        break
            
            forecast_value *= promo_multiplier
            
            results.append({
                'date': date_str,
                'forecast': float(max(0, forecast_value)),
                'lower_ci': float(max(0, forecast_value * 0.85)),
                'upper_ci': float(forecast_value * 1.15)
            })
        
        return results
    
    def get_baseline(self, horizon: int, **kwargs) -> List[Dict[str, Any]]:
        if self._historical_mean is None:
            raise ValueError("Model not fitted")
        
        last_date = pd.to_datetime(self._last_values.index[-1]) if hasattr(self, '_last_values') else pd.Timestamp.now()
        
        baseline = []
        base_value = self._historical_mean
        
        for i in range(horizon):
            future_date = last_date + pd.Timedelta(days=i+1)
            date_str = str(future_date.date())
            
            forecast_value = base_value
            
            if future_date.dayofweek in self._seasonal_factors:
                forecast_value *= self._seasonal_factors[future_date.dayofweek]
            
            baseline.append({
                'date': date_str,
                'forecast': float(max(0, forecast_value)),
                'lower_ci': float(max(0, forecast_value * 0.85)),
                'upper_ci': float(forecast_value * 1.15)
            })
        
        return baseline
    
    def get_components(self, horizon: int) -> Dict[str, Any]:
        return {
            'seasonal_factors': self._seasonal_factors,
            'historical_mean': float(self._historical_mean)
        }
    
    def get_metrics(self) -> Dict[str, float]:
        return {}
