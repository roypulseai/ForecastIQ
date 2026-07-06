import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from statsmodels.tsa.seasonal import STL
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class STLForecaster(BaseForecaster):
    def __init__(self, period: int = 7, robust: bool = True, seasonal: int = 7):
        super().__init__("STL")
        self.period = period
        self.robust = robust
        self.seasonal = seasonal
        self._fitted_model = None
        self._last_values = None
        self._forecast_method = 'linear'
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'STLForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        self._last_values = ts
        
        try:
            stl = STL(ts, period=self.period, robust=self.robust)
            self._fitted_model = stl.fit()
            
            detrended = self._fitted_model.resid + self._fitted_model.seasonal
            
            x = np.arange(len(ts))
            slope, intercept = np.polyfit(x, detrended.values, 1)
            self._trend_slope = slope
            self._trend_intercept = intercept
            self._seasonal_pattern = self._fitted_model.seasonal
            self._last_residual_mean = self._fitted_model.resid.mean()
        except Exception:
            self._trend_slope = 0
            self._trend_intercept = ts.mean()
            self._seasonal_pattern = pd.Series(0, index=ts.index)
            self._last_residual_mean = 0
        
        return self
    
    def forecast(self, horizon: int, **kwargs) -> List[Dict[str, Any]]:
        if self._last_values is None:
            raise ValueError("Model not fitted")
        
        last_date = pd.to_datetime(self._last_values.index[-1])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        results = []
        seasonal_pattern_values = self._seasonal_pattern.values
        
        for i, date in enumerate(future_dates):
            days_ahead = i + 1
            
            trend_value = self._trend_intercept + self._trend_slope * (len(self._last_values) + days_ahead - 1)
            
            seasonal_idx = (date.dayofweek + days_ahead) % 7
            if seasonal_idx < len(seasonal_pattern_values):
                seasonal_value = seasonal_pattern_values[seasonal_idx]
            else:
                seasonal_value = 0
            
            forecast_value = trend_value + seasonal_value + self._last_residual_mean
            
            results.append({
                'date': str(date.date()),
                'forecast': float(max(0, forecast_value)),
                'lower_ci': float(max(0, forecast_value * 0.85)),
                'upper_ci': float(forecast_value * 1.15)
            })
        
        return results
    
    def get_baseline(self, horizon: int) -> List[Dict[str, Any]]:
        return self.forecast(horizon)
    
    def get_components(self, horizon: int) -> Dict[str, Any]:
        if self._fitted_model is None:
            return {}
        
        return {
            'trend_slope': float(self._trend_slope),
            'seasonal_strength': float(self._fitted_model. seasonalstrength) if hasattr(self._fitted_model, 'seasonalstrength') else 0,
            'residual_std': float(self._fitted_model.resid.std())
        }
    
    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        return {
            'residual_std': float(self._fitted_model.resid.std())
        }
