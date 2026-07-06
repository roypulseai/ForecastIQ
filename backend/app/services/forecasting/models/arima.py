import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class ARIMAForecaster(BaseForecaster):
    def __init__(self, order: tuple = (1, 1, 1)):
        super().__init__("ARIMA")
        self.order = order
        self._fitted_model = None
        self._last_values = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str, 
            exog_data: Optional[Dict] = None, **kwargs) -> 'ARIMAForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        self._last_values = ts
        
        try:
            model = ARIMA(ts, order=self.order, enforce_stationarity=False)
            self._fitted_model = model.fit()
        except Exception:
            model = ARIMA(ts, order=(1, 1, 1), enforce_stationarity=False)
            self._fitted_model = model.fit()
        
        return self
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None, 
                 **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        pred = self._fitted_model.get_forecast(steps=horizon)
        pred_mean = pred.predicted_mean
        pred_conf = pred.conf_int()
        
        results = []
        for i, (date, value) in enumerate(pred_mean.items()):
            results.append({
                'date': str(date),
                'forecast': float(value),
                'lower_ci': float(pred_conf.iloc[i, 0]),
                'upper_ci': float(pred_conf.iloc[i, 1])
            })
        
        return results
    
    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        return {
            'aic': float(self._fitted_model.aic),
            'bic': float(self._fitted_model.bic)
        }


class SARIMAXForecaster(BaseForecaster):
    def __init__(self, order: tuple = (1, 1, 1), seasonal_order: tuple = (1, 1, 1, 7)):
        super().__init__("SARIMAX")
        self.order = order
        self.seasonal_order = seasonal_order
        self._fitted_model = None
        self._last_values = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'SARIMAXForecaster':
        ts = df.set_index(date_col)[value_col].sort_index()
        self._last_values = ts
        
        exog = None
        if exog_data and 'promotions' in exog_data:
            exog = exog_data['promotions']
            if len(exog) != len(ts):
                exog = None
        
        try:
            if exog is not None:
                model = SARIMAX(ts, exog=exog, order=self.order, 
                               seasonal_order=self.seasonal_order,
                               enforce_stationarity=False)
            else:
                model = SARIMAX(ts, order=self.order, 
                               seasonal_order=self.seasonal_order,
                               enforce_stationarity=False)
            self._fitted_model = model.fit(disp=False)
        except Exception:
            model = SARIMAX(ts, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7),
                           enforce_stationarity=False)
            self._fitted_model = model.fit(disp=False)
        
        return self
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        exog_future = None
        if exog_data and 'promotions' in exog_data:
            exog_future = exog_data['promotions'][:horizon]
        
        pred = self._fitted_model.get_forecast(steps=horizon, exog=exog_future)
        pred_mean = pred.predicted_mean
        pred_conf = pred.conf_int()
        
        results = []
        for i, (date, value) in enumerate(pred_mean.items()):
            results.append({
                'date': str(date),
                'forecast': float(value),
                'lower_ci': float(pred_conf.iloc[i, 0]),
                'upper_ci': float(pred_conf.iloc[i, 1])
            })
        
        return results
    
    def get_metrics(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        return {
            'aic': float(self._fitted_model.aic),
            'bic': float(self._fitted_model.bic)
        }
