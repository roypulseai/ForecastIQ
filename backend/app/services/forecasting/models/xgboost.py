import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class XGBoostForecaster(BaseForecaster):
    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1,
                 max_depth: int = 5, min_child_weight: int = 1,
                 subsample: float = 1.0, colsample_bytree: float = 1.0):
        super().__init__("XGBoost")
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_child_weight = min_child_weight
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self._fitted_model = None
        self._feature_names = []
        self._scaler = StandardScaler()
        self._last_values = None
    
    def _create_features(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        df['dayofweek'] = df[date_col].dt.dayofweek
        df['dayofmonth'] = df[date_col].dt.day
        df['month'] = df[date_col].dt.month
        df['quarter'] = df[date_col].dt.quarter
        df['year'] = df[date_col].dt.year
        df['weekofyear'] = df[date_col].dt.isocalendar().week.astype(int)
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        df['is_month_start'] = df[date_col].dt.is_month_start.astype(int)
        df['is_month_end'] = df[date_col].dt.is_month_end.astype(int)
        df['is_quarter_start'] = df[date_col].dt.is_quarter_start.astype(int)
        df['is_quarter_end'] = df[date_col].dt.is_quarter_end.astype(int)
        
        for lag in [1, 2, 3, 7, 14, 21, 28]:
            if lag == 1:
                df['lag_1'] = df[date_col].diff()
            else:
                df[f'lag_{lag}'] = df[date_col].diff(lag)
        
        for window in [7, 14, 28]:
            df[f'rolling_mean_{window}'] = df[date_col].rolling(window).mean()
            df[f'rolling_std_{window}'] = df[date_col].rolling(window).std()
            df[f'rolling_min_{window}'] = df[date_col].rolling(window).min()
            df[f'rolling_max_{window}'] = df[date_col].rolling(window).max()
        
        return df
    
    def _add_external_features(self, df: pd.DataFrame, exog_data: Optional[Dict],
                               include_external: bool = True) -> pd.DataFrame:
        if exog_data is None or not include_external:
            return df
        
        df = df.copy()
        
        if 'promotions' in exog_data and exog_data['promotions'] is not None:
            promo_df = exog_data['promotions'].copy()
            promo_df['date'] = pd.to_datetime(promo_df['date'])
            df = df.merge(promo_df, on='date', how='left')
            df['discount'] = df['discount'].fillna(0)
            df['is_promo'] = (df['discount'] > 0).astype(int)
        
        if 'media_plan' in exog_data and exog_data['media_plan'] is not None:
            media_df = exog_data['media_plan'].copy()
            media_df['date'] = pd.to_datetime(media_df['date'])
            df = df.merge(media_df, on='date', how='left')
            df['spend'] = df['spend'].fillna(0)
            df['log_spend'] = np.log1p(df['spend'])
        
        if 'holidays' in exog_data and exog_data['holidays'] is not None:
            holiday_df = exog_data['holidays'].copy()
            holiday_df['date'] = pd.to_datetime(holiday_df['date'])
            df = df.merge(holiday_df, on='date', how='left')
            df['is_holiday'] = df['is_holiday'].fillna(0).astype(int)
        
        if 'weather' in exog_data and exog_data['weather'] is not None:
            weather_df = exog_data['weather'].copy()
            weather_df['date'] = pd.to_datetime(weather_df['date'])
            df = df.merge(weather_df, on='date', how='left')
            if 'temperature' in df.columns:
                df['temp_normalized'] = (df['temperature'] - df['temperature'].mean()) / df['temperature'].std()
        
        if 'competitor' in exog_data and exog_data['competitor'] is not None:
            comp_df = exog_data['competitor'].copy()
            comp_df['date'] = pd.to_datetime(comp_df['date'])
            df = df.merge(comp_df, on='date', how='left')
        
        return df
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'XGBoostForecaster':
        df_feat = self._create_features(df, date_col)
        df_feat = self._add_external_features(df_feat, exog_data, include_external=True)
        
        self._last_values = df.set_index(date_col)[value_col]
        
        exclude_cols = [date_col, value_col]
        feature_cols = [c for c in df_feat.columns if c not in exclude_cols and c not in ['date']]
        self._feature_names = feature_cols
        
        X = df_feat[feature_cols].fillna(0)
        y = df_feat[value_col]
        
        self._scaler.fit(X)
        X_scaled = self._scaler.transform(X)
        
        self._fitted_model = XGBRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            min_child_weight=self.min_child_weight,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=42,
            verbosity=0
        )
        self._fitted_model.fit(X_scaled, y)
        
        return self
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        last_date = pd.to_datetime(self._last_values.index[-1])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        future_df = pd.DataFrame({date_col: future_dates})
        df_full = pd.concat([pd.DataFrame({date_col: self._last_values.index}), future_df], ignore_index=True)
        
        df_feat = self._create_features(df_full, date_col)
        df_feat = self._add_external_features(df_feat, exog_data, include_external=True)
        
        X_future = df_feat[feature_cols].fillna(0)
        X_future_scaled = self._scaler.transform(X_future)
        
        predictions = self._fitted_model.predict(X_future_scaled)
        
        results = []
        for i, date in enumerate(future_dates):
            results.append({
                'date': str(date.date()),
                'forecast': float(max(0, predictions[i])),
                'lower_ci': float(max(0, predictions[i] * 0.85)),
                'upper_ci': float(predictions[i] * 1.15)
            })
        
        return results
    
    def get_baseline(self, horizon: int, exog_data: Optional[Dict] = None,
                     **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        last_date = pd.to_datetime(self._last_values.index[-1])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        future_df = pd.DataFrame({date_col: future_dates})
        df_full = pd.concat([pd.DataFrame({date_col: self._last_values.index}), future_df], ignore_index=True)
        
        df_feat = self._create_features(df_full, date_col)
        df_feat = self._add_external_features(df_feat, exog_data, include_external=False)
        
        for col in self._feature_names:
            if col not in df_feat.columns:
                df_feat[col] = 0
        
        X_future = df_feat[self._feature_names].fillna(0)
        X_future_scaled = self._scaler.transform(X_future)
        
        predictions = self._fitted_model.predict(X_future_scaled)
        
        baseline = []
        for i, date in enumerate(future_dates):
            baseline.append({
                'date': str(date.date()),
                'forecast': float(max(0, predictions[i])),
                'lower_ci': float(max(0, predictions[i] * 0.85)),
                'upper_ci': float(predictions[i] * 1.15)
            })
        
        return baseline
    
    def get_feature_importance(self) -> Dict[str, float]:
        if self._fitted_model is None:
            return {}
        
        importance = self._fitted_model.feature_importances_
        return {name: float(imp) for name, imp in zip(self._feature_names, importance)}
    
    def get_components(self, horizon: int) -> Dict[str, Any]:
        return {'feature_importance': self.get_feature_importance()}
    
    def get_metrics(self) -> Dict[str, float]:
        return {}
