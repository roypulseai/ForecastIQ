import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from .models import (
    BaseForecaster, ARIMAForecaster, SARIMAXForecaster, 
    ProphetForecaster, LightGBMForecaster, WMAForecaster,
    XGBoostForecaster, ETSForecaster, ThetaForecaster, STLForecaster
)

class ModelSelector:
    def __init__(self):
        self.model_classes = {
            'arima': ARIMAForecaster,
            'sarimax': SARIMAXForecaster,
            'prophet': ProphetForecaster,
            'lightgbm': LightGBMForecaster,
            'xgboost': XGBoostForecaster,
            'wma': WMAForecaster,
            'ets': ETSForecaster,
            'theta': ThetaForecaster,
            'stl': STLForecaster
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
            recommendations.append({'model': 'theta', 'score': 0.85, 'reason': 'Simple but effective for short series'})
            return recommendations[:5]
        
        if data_chars['cv'] > 0.5:
            recommendations.append({'model': 'lightgbm', 'score': 0.85, 'reason': 'High variance, ML can capture patterns'})
            recommendations.append({'model': 'xgboost', 'score': 0.82, 'reason': 'Robust boosting for complex patterns'})
        elif data_chars['cv'] < 0.2:
            recommendations.append({'model': 'wma', 'score': 0.8, 'reason': 'Low variance, stable demand'})
            recommendations.append({'model': 'ets', 'score': 0.78, 'reason': 'Exponential smoothing for stable series'})
        
        if data_chars['seasonality'] != 'none':
            recommendations.append({'model': 'prophet', 'score': 0.9, 'reason': f'Detected {data_chars["seasonality"]} seasonality'})
            recommendations.append({'model': 'sarimax', 'score': 0.82, 'reason': 'Can capture seasonal patterns'})
            recommendations.append({'model': 'stl', 'score': 0.8, 'reason': 'STL decomposition for flexible seasonality'})
            recommendations.append({'model': 'theta', 'score': 0.78, 'reason': 'Simple seasonal decomposition'})
        
        if data_chars['stationarity']:
            recommendations.append({'model': 'arima', 'score': 0.75, 'reason': 'Data is stationary'})
        
        if has_external_features:
            recommendations.append({'model': 'prophet', 'score': 0.85, 'reason': 'Can incorporate external regressors'})
            recommendations.append({'model': 'lightgbm', 'score': 0.85, 'reason': 'Handles multiple features well'})
            recommendations.append({'model': 'xgboost', 'score': 0.82, 'reason': 'Robust to feature interactions'})
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec['model'] not in seen:
                seen.add(rec['model'])
                unique_recs.append(rec)
        
        return unique_recs[:5]
    
    def get_model(self, model_type: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> BaseForecaster:
        model_type = model_type.lower()
        
        if model_type == 'arima':
            p, d, q = 1, 1, 1
            if params and params.get('arima'):
                p = params['arima'].get('p', 1)
                d = params['arima'].get('d', 1)
                q = params['arima'].get('q', 1)
            return ARIMAForecaster(order=(p, d, q))
        
        elif model_type == 'sarimax':
            p, d, q = 1, 1, 1
            sp, sd, sq, s_period = 1, 1, 1, 7
            if params and params.get('sarimax'):
                p = params['sarimax'].get('p', 1)
                d = params['sarimax'].get('d', 1)
                q = params['sarimax'].get('q', 1)
                sp = params['sarimax'].get('seasonal_p', 1)
                sd = params['sarimax'].get('seasonal_d', 1)
                sq = params['sarimax'].get('seasonal_q', 1)
                s_period = params['sarimax'].get('seasonal_period', 7)
            return SARIMAXForecaster(order=(p, d, q), seasonal_order=(sp, sd, sq, s_period))
        
        elif model_type == 'prophet':
            prophet_params = params.get('prophet', {}) if params else {}
            return ProphetForecaster(
                seasonality_mode=prophet_params.get('seasonality_mode', 'additive'),
                yearly_seasonality=prophet_params.get('yearly_seasonality', True),
                weekly_seasonality=prophet_params.get('weekly_seasonality', True),
                daily_seasonality=prophet_params.get('daily_seasonality', False),
                changepoint_prior_scale=prophet_params.get('changepoint_prior_scale', 0.05),
                seasonality_prior_scale=prophet_params.get('seasonality_prior_scale', 10.0),
                holidays_prior_scale=prophet_params.get('holidays_prior_scale', 10.0)
            )
        
        elif model_type == 'lightgbm':
            lgbm_params = params.get('lightgbm', {}) if params else {}
            return LightGBMForecaster(
                n_estimators=lgbm_params.get('n_estimators', 100),
                learning_rate=lgbm_params.get('learning_rate', 0.1),
                max_depth=lgbm_params.get('max_depth', 5),
                num_leaves=lgbm_params.get('num_leaves', 31),
                min_child_samples=lgbm_params.get('min_child_samples', 20)
            )
        
        elif model_type == 'xgboost':
            xgb_params = params.get('xgboost', {}) if params else {}
            return XGBoostForecaster(
                n_estimators=xgb_params.get('n_estimators', 100),
                learning_rate=xgb_params.get('learning_rate', 0.1),
                max_depth=xgb_params.get('max_depth', 5),
                min_child_weight=xgb_params.get('min_child_weight', 1),
                subsample=xgb_params.get('subsample', 1.0),
                colsample_bytree=xgb_params.get('colsample_bytree', 1.0)
            )
        
        elif model_type == 'wma':
            wma_params = params.get('wma', {}) if params else {}
            return WMAForecaster(window=wma_params.get('window', 8))
        
        elif model_type == 'ets':
            ets_params = params.get('ets', {}) if params else {}
            return ETSForecaster(
                trend=ets_params.get('trend', 'add'),
                seasonal=ets_params.get('seasonal', 'add'),
                seasonal_periods=ets_params.get('seasonal_periods', 7)
            )
        
        elif model_type == 'theta':
            theta_params = params.get('theta', {}) if params else {}
            return ThetaForecaster(
                period=theta_params.get('period', 7),
                deseasonalize=theta_params.get('deseasonalize', True)
            )
        
        elif model_type == 'stl':
            stl_params = params.get('stl', {}) if params else {}
            return STLForecaster(
                period=stl_params.get('period', 7),
                robust=stl_params.get('robust', True)
            )
        
        if model_type not in self.model_classes:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return self.model_classes[model_type](**kwargs)
    
    def cross_validate_score(self, df: pd.DataFrame, date_col: str, value_col: str,
                             model_type: str, params: Optional[Dict] = None,
                             horizon: int = 7) -> Dict[str, float]:
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        
        if len(ts) < horizon * 2:
            return {'mae': np.nan, 'rmse': np.nan, 'mape': np.nan}
        
        train_size = len(ts) - horizon
        train = ts.iloc[:train_size]
        test = ts.iloc[train_size:]
        
        model = self.get_model(model_type, params)
        
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
