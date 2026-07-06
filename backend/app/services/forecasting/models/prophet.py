import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

from .base import BaseForecaster

class ProphetForecaster(BaseForecaster):
    def __init__(self, 
                 seasonality_mode: str = 'additive', 
                 yearly_seasonality: bool = True,
                 weekly_seasonality: bool = True,
                 daily_seasonality: bool = False,
                 country: Optional[str] = None,
                 changepoint_prior_scale: float = 0.05,
                 seasonality_prior_scale: float = 10.0,
                 holidays_prior_scale: float = 10.0):
        super().__init__("Prophet")
        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.country = country
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self._fitted_model = None
        self._last_values = None
        self._has_external = False
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str,
            exog_data: Optional[Dict] = None, **kwargs) -> 'ProphetForecaster':
        prophet_df = df[[date_col, value_col]].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
        prophet_df = prophet_df.dropna()
        
        self._last_values = df.set_index(date_col)[value_col]
        
        self._fitted_model = Prophet(
            seasonality_mode=self.seasonality_mode,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            country_holidays=self.country,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale
        )
        
        self._has_external = False
        if exog_data:
            if 'promotions' in exog_data and exog_data['promotions'] is not None:
                promo_df = exog_data['promotions'].copy()
                promo_df['ds'] = pd.to_datetime(promo_df['ds'])
                self._fitted_model.add_regressor('promo_discount')
                prophet_df = prophet_df.merge(promo_df, on='ds', how='left')
                prophet_df['promo_discount'] = prophet_df['promo_discount'].fillna(0)
                self._has_external = True
            
            if 'media_plan' in exog_data and exog_data['media_plan'] is not None:
                media_df = exog_data['media_plan'].copy()
                media_df['ds'] = pd.to_datetime(media_df['ds'])
                self._fitted_model.add_regressor('media_spend')
                prophet_df = prophet_df.merge(media_df, on='ds', how='left')
                prophet_df['media_spend'] = prophet_df['media_spend'].fillna(0)
                self._has_external = True
        
        self._fitted_model.fit(prophet_df)
        return self
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        future = self._fitted_model.make_future_dataframe(periods=horizon)
        
        if exog_data:
            if 'promotions' in exog_data and exog_data['promotions'] is not None:
                promo_df = exog_data['promotions'].copy()
                promo_df['ds'] = pd.to_datetime(promo_df['ds'])
                future = future.merge(promo_df, on='ds', how='left')
                future['promo_discount'] = future['promo_discount'].fillna(0)
            
            if 'media_plan' in exog_data and exog_data['media_plan'] is not None:
                media_df = exog_data['media_plan'].copy()
                media_df['ds'] = pd.to_datetime(media_df['ds'])
                future = future.merge(media_df, on='ds', how='left')
                future['media_spend'] = future['media_spend'].fillna(0)
        
        pred = self._fitted_model.predict(future)
        pred = pred.tail(horizon)
        
        results = []
        for _, row in pred.iterrows():
            results.append({
                'date': str(row['ds'].date()),
                'forecast': float(row['yhat']),
                'lower_ci': float(row['yhat_lower']),
                'upper_ci': float(row['yhat_upper'])
            })
        
        return results
    
    def get_baseline(self, horizon: int) -> List[Dict[str, Any]]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        future = self._fitted_model.make_future_dataframe(periods=horizon)
        future_no_exog = future.copy()
        
        if 'promo_discount' in future_no_exog.columns:
            future_no_exog['promo_discount'] = 0
        if 'media_spend' in future_no_exog.columns:
            future_no_exog['media_spend'] = 0
        
        pred = self._fitted_model.predict(future_no_exog)
        pred = pred.tail(horizon)
        
        baseline = []
        for _, row in pred.iterrows():
            baseline.append({
                'date': str(row['ds'].date()),
                'forecast': float(row['yhat']),
                'lower_ci': float(row['yhat_lower']),
                'upper_ci': float(row['yhat_upper'])
            })
        
        return baseline
    
    def get_components(self, horizon: int) -> Dict[str, Any]:
        if self._fitted_model is None:
            raise ValueError("Model not fitted")
        
        future = self._fitted_model.make_future_dataframe(periods=horizon)
        pred = self._fitted_model.predict(future)
        pred = pred.tail(horizon)
        
        return {
            'trend': pred['trend'].tail(horizon).tolist(),
            'yearly': pred['yearly'].tail(horizon).tolist() if 'yearly' in pred else [],
            'weekly': pred['weekly'].tail(horizon).tolist() if 'weekly' in pred else [],
        }
    
    def get_metrics(self) -> Dict[str, float]:
        return {}
