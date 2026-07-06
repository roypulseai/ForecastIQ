import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from .models import (
    BaseForecaster, ARIMAForecaster, SARIMAXForecaster, 
    ProphetForecaster, LightGBMForecaster, WMAForecaster
)

class ModelSelector:
    def __init__(self):
        self.model_classes = {
            'arima': ARIMAForecaster,
            'sarimax': SARIMAXForecaster,
            'prophet': ProphetForecaster,
            'lightgbm': LightGBMForecaster,
            'wma': WMAForecaster
        }
        self._data_characteristics = {}
    
    def analyze_data(self, df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        
        characteristics = {
            'length': len(ts),
            'mean': float(ts.mean()),
            'std': float(ts.std()),
            'cv': float(ts.std() / ts.mean()) if ts.mean() != 0 else 0,
            'trend': self._detect_trend(ts),
            'seasonality': self._detect_seasonality(ts),
            'stationarity': self._test_stationarity(ts),
            'outliers_pct': self._detect_outliers(ts),
            'missing_pct': float(df[value_col].isna().sum() / len(df) * 100)
        }
        
        self._data_characteristics = characteristics
        return characteristics
    
    def _detect_trend(self, ts: pd.Series) -> str:
        if len(ts) < 10:
            return 'unknown'
        
        x = np.arange(len(ts))
        slope, _ = np.polyfit(x, ts.values, 1)
        slope_pct = slope / ts.mean() * 100 if ts.mean() != 0 else 0
        
        if slope_pct > 1:
            return 'increasing'
        elif slope_pct < -1:
            return 'decreasing'
        return 'stable'
    
    def _detect_seasonality(self, ts: pd.Series) -> str:
        if len(ts) < 14:
            return 'none'
        
        ts.index = pd.to_datetime(ts.index)
        
        autocorr = ts.autocorr(lag=7)
        if abs(autocorr) > 0.5:
            return 'weekly'
        
        autocorr_monthly = ts.autocorr(lag=30) if len(ts) > 30 else 0
        if abs(autocorr_monthly) > 0.5:
            return 'monthly'
        
        return 'none'
    
    def _test_stationarity(self, ts: pd.Series) -> bool:
        if len(ts) < 30:
            return True
        
        from statsmodels.tsa.stattools import adfuller
        try:
            result = adfuller(ts.dropna())
            return result[1] < 0.05
        except:
            return True
    
    def _detect_outliers(self, ts: pd.Series) -> float:
        q1 = ts.quantile(0.25)
        q3 = ts.quantile(0.75)
        iqr = q3 - q1
        outliers = ((ts < (q1 - 1.5 * iqr)) | (ts > (q3 + 1.5 * iqr))).sum()
        return float(outliers / len(ts) * 100)
    
    def recommend_models(self, data_chars: Dict[str, Any], 
                          has_external_features: bool = False) -> List[Dict[str, Any]]:
        recommendations = []
        
        if data_chars['length'] < 14:
            recommendations.append({'model': 'wma', 'score': 0.9, 'reason': 'Limited data, simple methods preferred'})
            return recommendations
        
        if data_chars['cv'] > 0.5:
            recommendations.append({'model': 'lightgbm', 'score': 0.85, 'reason': 'High variance, ML can capture patterns'})
        elif data_chars['cv'] < 0.2:
            recommendations.append({'model': 'wma', 'score': 0.8, 'reason': 'Low variance, stable demand'})
        
        if data_chars['seasonality'] != 'none':
            recommendations.append({'model': 'prophet', 'score': 0.9, 'reason': f'Detected {data_chars["seasonality"]} seasonality'})
            recommendations.append({'model': 'sarimax', 'score': 0.8, 'reason': 'Can capture seasonal patterns'})
        
        if data_chars['stationarity']:
            recommendations.append({'model': 'arima', 'score': 0.75, 'reason': 'Data is stationary'})
        
        if has_external_features:
            recommendations.append({'model': 'prophet', 'score': 0.85, 'reason': 'Can incorporate external regressors'})
            recommendations.append({'model': 'lightgbm', 'score': 0.85, 'reason': 'Handles multiple features well'})
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec['model'] not in seen:
                seen.add(rec['model'])
                unique_recs.append(rec)
        
        return unique_recs[:5]
    
    def get_model(self, model_type: str, **kwargs) -> BaseForecaster:
        if model_type.lower() not in self.model_classes:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return self.model_classes[model_type.lower()](**kwargs)
    
    def cross_validate_score(self, df: pd.DataFrame, date_col: str, value_col: str,
                             model_type: str, horizon: int = 7) -> Dict[str, float]:
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        
        if len(ts) < horizon * 2:
            return {'mae': np.nan, 'rmse': np.nan, 'mape': np.nan}
        
        train_size = len(ts) - horizon
        train = ts.iloc[:train_size]
        test = ts.iloc[train_size:]
        
        model = self.get_model(model_type)
        
        try:
            train_df = train.reset_index()
            train_df.columns = [date_col, value_col]
            
            model.fit(train_df, date_col, value_col)
            predictions = model.forecast(horizon)
            
            pred_values = [p['forecast'] for p in predictions]
            
            mae = np.mean(np.abs(np.array(pred_values) - test.values))
            rmse = np.sqrt(np.mean((np.array(pred_values) - test.values) ** 2))
            mape = np.mean(np.abs((np.array(pred_values) - test.values) / (test.values + 1e-10))) * 100
            
            return {'mae': float(mae), 'rmse': float(rmse), 'mape': float(mape)}
        except Exception as e:
            return {'mae': np.nan, 'rmse': np.nan, 'mape': np.nan, 'error': str(e)}
