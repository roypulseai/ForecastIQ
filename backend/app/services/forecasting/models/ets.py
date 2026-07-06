import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class ETSForecaster(BaseForecaster):
    def __init__(self, trend: str = 'add', seasonal: str = 'add', seasonal_periods: int = 7):
        super().__init__("ETS")
        self.trend = trend
        self.seasonal = seasonal
        self.seasonal_periods = seasonal_periods
        self._fitted_model = None
        self._last_values = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'ETSForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        self._last_values = ts
        
        try:
            model = ExponentialSmoothing(
                ts,
                trend=self.trend,
                seasonal=self.seasonal,
                seasonal_periods=self.seasonal_periods,
                damped_trend=True,
                use_boxcox=False
            )
            self._fitted_model = model.fit(optimized=True)
        except Exception:
            model = ExponentialSmoothing(
                ts,
                trend='add',
                seasonal=None,
                damped_trend=True
            )
            self._fitted_model = model.fit(optimized=True)
        
        return self
    
    def forecast(self, horizon: int, **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        pred = self._fitted_model.forecast(horizon)
        
        results = []
        for i, (date, value) in enumerate(pred.items()):
            results.append({
                'date': str(date.date()),
                'forecast': float(value),
                'lower_ci': float(value * 0.85),
                'upper_ci': float(value * 1.15)
            })
        
        return results
    
    def get_baseline(self, horizon: int) -> List[Dict[str, Any]]:
        return self.forecast(horizon)
    
    def get_components(self, horizon: int) -> Dict[str, Any]:
        if self._fitted_model is None:
            return {}
        
        return {
            'level': float(self._fitted_model.level.iloc[-1]) if hasattr(self._fitted_model, 'level') else None,
            'trend': float(self._fitted_model.trend.iloc[-1]) if hasattr(self._fitted_model, 'trend') else None,
        }
    
    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        return {
            'aic': float(self._fitted_model.aic),
            'bic': float(self._fitted_model.bic)
        }
