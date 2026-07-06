import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from .models import BaseForecaster
from .model_selector import ModelSelector

class EnsembleForecaster:
    def __init__(self, models: List[BaseForecaster], weights: Optional[List[float]] = None):
        self.models = models
        self.num_models = len(models)
        
        if weights is None:
            self.weights = [1.0 / self.num_models] * self.num_models
        else:
            if len(weights) != self.num_models:
                raise ValueError("Number of weights must match number of models")
            total = sum(weights)
            self.weights = [w / total for w in weights]
    
    def forecast(self, horizon: int, exog_data: Optional[Dict] = None,
                 **kwargs) -> List[Dict[str, Any]]:
        all_predictions = []
        
        for model in self.models:
            try:
                pred = model.forecast(horizon, exog_data=exog_data, **kwargs)
                all_predictions.append(pred)
            except Exception as e:
                print(f"Error forecasting with {model.name}: {e}")
                continue
        
        if not all_predictions:
            raise ValueError("No models produced valid forecasts")
        
        ensemble_results = []
        
        for i in range(horizon):
            date = all_predictions[0][i]['date']
            weighted_sum = 0
            total_weight = 0
            
            for j, pred in enumerate(all_predictions):
                if i < len(pred):
                    w = self.weights[j]
                    weighted_sum += pred[i]['forecast'] * w
                    total_weight += w
            
            if total_weight > 0:
                ensemble_forecast = weighted_sum / total_weight
            else:
                ensemble_forecast = np.mean([pred[i]['forecast'] for pred in all_predictions])
            
            lower_ci = min([pred[i]['lower_ci'] for pred in all_predictions])
            upper_ci = max([pred[i]['upper_ci'] for pred in all_predictions])
            
            ensemble_results.append({
                'date': date,
                'forecast': float(max(0, ensemble_forecast)),
                'lower_ci': float(max(0, lower_ci)),
                'upper_ci': float(upper_ci)
            })
        
        return ensemble_results
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            'num_models': self.num_models,
            'models_used': [m.name for m in self.models],
            'weights': self.weights
        }


class RollingEnsemble:
    def __init__(self, model_selector: ModelSelector, window_size: int = 3):
        self.model_selector = model_selector
        self.window_size = window_size
        self._performance_history: Dict[str, List[float]] = {}
    
    def add_performance(self, model_name: str, metric_value: float):
        if model_name not in self._performance_history:
            self._performance_history[model_name] = []
        
        self._performance_history[model_name].append(metric_value)
        
        if len(self._performance_history[model_name]) > self.window_size:
            self._performance_history[model_name].pop(0)
    
    def get_best_weights(self, model_names: List[str]) -> List[float]:
        if not model_names:
            return []
        
        weights = []
        for name in model_names:
            history = self._performance_history.get(name, [1.0])
            avg_perf = np.mean(history)
            weights.append(max(0.1, avg_perf))
        
        total = sum(weights)
        return [w / total for w in weights]
    
    def select_ensemble_models(self, recommendations: List[Dict[str, Any]], 
                                top_n: int = 3) -> List[str]:
        selected = []
        for rec in recommendations:
            if len(selected) >= top_n:
                break
            model = rec['model']
            if model not in selected:
                selected.append(model)
        
        return selected
