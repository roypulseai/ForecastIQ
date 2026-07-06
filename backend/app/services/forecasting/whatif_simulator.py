import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class WhatIfSimulator:
    def __init__(self):
        self.baseline_forecast = None
        self.historical_data = None
        self.models = {}
    
    def set_baseline(self, forecast_values: List[Dict[str, Any]]):
        self.baseline_forecast = forecast_values
    
    def set_historical(self, df: pd.DataFrame, date_col: str, value_col: str):
        self.historical_data = df[[date_col, value_col]].copy()
    
    def simulate_promo(self, promo_discount: float, duration_days: int = 7,
                       elasticity: float = -1.5) -> List[Dict[str, Any]]:
        if self.baseline_forecast is None:
            return []
        
        results = []
        for i, val in enumerate(self.baseline_forecast):
            if i < duration_days:
                uplift = 1 + elasticity * (promo_discount / 100)
                uplift = max(0.5, min(2.0, uplift))
            else:
                uplift = 1.0
            
            results.append({
                'date': val['date'],
                'baseline': val.get('baseline', val['forecast']),
                'forecast': val['forecast'] * uplift,
                'lower_ci': val['lower_ci'] * uplift,
                'upper_ci': val['upper_ci'] * uplift,
                'uplift_pct': (uplift - 1) * 100
            })
        
        return results
    
    def simulate_media_spend(self, channel: str, spend_increase_pct: float,
                            duration_days: int = 30) -> List[Dict[str, Any]]:
        if self.baseline_forecast is None:
            return []
        
        channel_roi = {
            'tv': 1.5,
            'digital': 1.2,
            'social': 0.8,
            'print': 0.5,
            'radio': 0.6
        }
        
        roi = channel_roi.get(channel.lower(), 1.0)
        spend_multiplier = 1 + (spend_increase_pct / 100) * roi
        
        results = []
        for i, val in enumerate(self.baseline_forecast):
            if i < duration_days:
                decay = np.exp(-i / 10)
                effect = 1 + ((spend_multiplier - 1) * decay)
            else:
                effect = 1.0
            
            results.append({
                'date': val['date'],
                'baseline': val.get('baseline', val['forecast']),
                'forecast': val['forecast'] * effect,
                'lower_ci': val['lower_ci'] * effect,
                'upper_ci': val['upper_ci'] * effect,
                'spend_effect': (effect - 1) * 100
            })
        
        return results
    
    def simulate_holiday(self, holiday_dates: List[str],
                        uplift_pct: float = 20) -> List[Dict[str, Any]]:
        if self.baseline_forecast is None:
            return []
        
        holiday_set = set(holiday_dates)
        
        results = []
        for val in self.baseline_forecast:
            if val['date'] in holiday_set:
                effect = 1 + (uplift_pct / 100)
            else:
                effect = 1.0
            
            results.append({
                'date': val['date'],
                'baseline': val.get('baseline', val['forecast']),
                'forecast': val['forecast'] * effect,
                'lower_ci': val['lower_ci'] * effect,
                'upper_ci': val['upper_ci'] * effect,
                'holiday_effect': uplift_pct if val['date'] in holiday_set else 0
            })
        
        return results
    
    def simulate_price_change(self, price_change_pct: float,
                             promo_depth_pct: float = 0,
                             duration_days: int = 14) -> List[Dict[str, Any]]:
        if self.baseline_forecast is None:
            return []
        
        elasticity = -1.5
        price_effect = 1 + (price_change_pct / 100) * elasticity
        promo_effect = 1 + (promo_depth_pct / 100) * 0.5
        
        total_effect = price_effect * promo_effect
        
        results = []
        for i, val in enumerate(self.baseline_forecast):
            if i < duration_days:
                effect = total_effect
            else:
                effect = 1.0
            
            results.append({
                'date': val['date'],
                'baseline': val.get('baseline', val['forecast']),
                'forecast': val['forecast'] * effect,
                'lower_ci': val['lower_ci'] * effect,
                'upper_ci': val['upper_ci'] * effect,
                'price_effect': (effect - 1) * 100
            })
        
        return results
    
    def compare_scenarios(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        comparison = {
            'total_impact': {},
            'average_impact': {},
            'peak_impact': {}
        }
        
        for scenario in scenarios:
            name = scenario['name']
            values = scenario['values']
            
            impacts = [(v['forecast'] / v['baseline'] - 1) * 100 
                      for v in values if v['baseline'] != 0]
            
            if impacts:
                comparison['total_impact'][name] = float(sum(v['forecast'] - v['baseline'] 
                                                            for v in values))
                comparison['average_impact'][name] = float(np.mean(impacts))
                comparison['peak_impact'][name] = float(max(impacts))
        
        return comparison
