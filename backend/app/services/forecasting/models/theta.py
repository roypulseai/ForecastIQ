import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from statsmodels.tsa.forecasting.theta import ThetaModel
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class ThetaForecaster(BaseForecaster):
    def __init__(self, period: int = 7, deseasonalize: bool = True, use_test: bool = False):
        super().__init__("Theta")
        self.period = period
        self.deseasonalize = deseasonalize
        self.use_test = use_test
        self._fitted_model = None
        self._last_values = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'ThetaForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        self._last_values = ts
        
        try:
            model = ThetaModel(
                ts,
                period=self.period,
                deseasonalize=self.deseasonalize,
                use_test=self.use_test
            )
            self._fitted_model = model.fit()
        except Exception:
            model = ThetaModel(ts, period=self.period)
            self._fitted_model = model.fit()
        
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
        return {'period': self.period, 'deseasonalize': self.deseasonalize}
    
    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        return {'aic': float(self._fitted_model.aic)}
