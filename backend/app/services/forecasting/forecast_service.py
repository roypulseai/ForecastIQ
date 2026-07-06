from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import json
import os
import uuid

from .model_selector import ModelSelector
from .ensemble import EnsembleForecaster, RollingEnsemble
from ...schemas.models import (
    ForecastRequest, ForecastResponse, ForecastResult, ModelResult,
    EnsembleResult, ModelType, DataStatus
)

class ForecastingService:
    def __init__(self, upload_dir: str = "uploads", output_dir: str = "outputs"):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.model_selector = ModelSelector()
        self._forecasts: Dict[str, ForecastResult] = {}
        
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
    
    def analyze_data(self, df: pd.DataFrame, date_col: str, value_col: str,
                     has_external_features: bool = False) -> Dict[str, Any]:
        data_chars = self.model_selector.analyze_data(df, date_col, value_col)
        recommendations = self.model_selector.recommend_models(
            data_chars, has_external_features
        )
        
        return {
            'data_characteristics': data_chars,
            'model_recommendations': recommendations
        }
    
    def run_forecast(self, request: ForecastRequest, data: Dict[str, pd.DataFrame]) -> ForecastResult:
        forecast_id = str(uuid.uuid4())
        
        sales_df = data.get('sales')
        if sales_df is None or sales_df.empty:
            raise ValueError("Sales data is required")
        
        date_col = request.date_column
        value_col = request.target_column
        
        exog_data = {}
        if request.include_media_plan and 'media_plan' in data:
            exog_data['media_plan'] = data['media_plan']
        if request.include_promotions and 'promotions' in data:
            exog_data['promotions'] = data['promotions']
        if request.include_holidays and 'holidays' in data:
            exog_data['holidays'] = data['holidays']
        if request.include_events and 'events' in data:
            exog_data['events'] = data['events']
        
        results: Dict[str, ModelResult] = {}
        model_rankings = []
        
        for model_type in request.models:
            try:
                model = self.model_selector.get_model(
                    model_type.value,
                    seasonality_mode=request.seasonality_mode,
                    country=request.country
                )
                
                if model_type == ModelType.PROPHET:
                    model.fit(sales_df, date_col, value_col, exog_data=exog_data)
                else:
                    model.fit(sales_df, date_col, value_col, exog_data=exog_data)
                
                forecast_values = model.forecast(request.horizon, exog_data=exog_data)
                
                metrics = self.model_selector.cross_validate_score(
                    sales_df, date_col, value_col, model_type.value, 
                    horizon=min(7, request.horizon)
                )
                
                feature_importance = None
                if hasattr(model, 'get_feature_importance'):
                    feature_importance = model.get_feature_importance()
                
                results[model_type.value] = ModelResult(
                    model_name=model.name,
                    forecast_values=forecast_values,
                    metrics=metrics,
                    feature_importance=feature_importance
                )
                
                model_rankings.append({
                    'model': model_type.value,
                    'name': model.name,
                    'mae': metrics.get('mae', float('inf')),
                    'rmse': metrics.get('rmse', float('inf')),
                    'mape': metrics.get('mape', float('inf')),
                    'score': 1 / (metrics.get('mae', 1) + 1)
                })
                
            except Exception as e:
                print(f"Error running {model_type}: {e}")
                continue
        
        model_rankings.sort(key=lambda x: x['score'], reverse=True)
        
        ensemble_result = None
        best_model = None
        
        if request.ensemble_models and len(request.ensemble_models) >= 2:
            try:
                ensemble_models = []
                ensemble_weights = request.ensemble_weights or [1.0/len(request.ensemble_models)] * len(request.ensemble_models)
                
                for model_type in request.ensemble_models:
                    if model_type.value in results:
                        model = self.model_selector.get_model(
                            model_type.value,
                            seasonality_mode=request.seasonality_mode,
                            country=request.country
                        )
                        model.fit(sales_df, date_col, value_col, exog_data=exog_data)
                        ensemble_models.append(model)
                
                if len(ensemble_models) >= 2:
                    weights = ensemble_weights[:len(ensemble_models)]
                    ensemble = EnsembleForecaster(ensemble_models, weights)
                    ensemble_forecast = ensemble.forecast(request.horizon, exog_data=exog_data)
                    
                    ensemble_result = EnsembleResult(
                        models_used=[m.name for m in ensemble_models],
                        weights=weights,
                        forecast_values=ensemble_forecast,
                        individual_results=[results[m.value] for m in request.ensemble_models if m.value in results]
                    )
                    
            except Exception as e:
                print(f"Error creating ensemble: {e}")
        
        if model_rankings:
            best_model = ModelType(model_rankings[0]['model'])
        
        forecast_result = ForecastResult(
            forecast_id=forecast_id,
            request=request,
            results=results,
            ensemble=ensemble_result,
            created_at=datetime.now()
        )
        
        self._forecasts[forecast_id] = forecast_result
        self._save_to_csv(forecast_result)
        
        return forecast_result
    
    def _save_to_csv(self, result: ForecastResult):
        output_path = os.path.join(self.output_dir, f"{result.forecast_id}.csv")
        
        all_dates = set()
        for model_result in result.results.values():
            for val in model_result.forecast_values:
                all_dates.add(val['date'])
        
        if result.ensemble:
            for val in result.ensemble.forecast_values:
                all_dates.add(val['date'])
        
        sorted_dates = sorted(all_dates)
        
        data_rows = []
        for date in sorted_dates:
            row = {'date': date}
            
            for model_name, model_result in result.results.items():
                for val in model_result.forecast_values:
                    if val['date'] == date:
                        row[model_name] = val['forecast']
                        break
            
            if result.ensemble:
                for val in result.ensemble.forecast_values:
                    if val['date'] == date:
                        row['ensemble'] = val['forecast']
                        break
            
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        df.to_csv(output_path, index=False)
    
    def get_forecast(self, forecast_id: str) -> Optional[ForecastResult]:
        return self._forecasts.get(forecast_id)
    
    def list_forecasts(self) -> List[Dict[str, Any]]:
        return [
            {
                'forecast_id': k,
                'created_at': v.created_at.isoformat(),
                'name': v.request.name,
                'horizon': v.request.horizon,
                'models': list(v.results.keys())
            }
            for k, v in self._forecasts.items()
        ]
