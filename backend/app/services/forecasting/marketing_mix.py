import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings('ignore')

class MarketingMixModeler:
    def __init__(self):
        self.adstock_params = {}
        self.saturation_params = {}
        self.channel_effects = {}
    
    @staticmethod
    def geometric_adstock(media_spend: np.ndarray, decay_rate: float = 0.5) -> np.ndarray:
        adstocked = np.zeros_like(media_spend, dtype=float)
        cumulative = 0.0
        
        for i in range(len(media_spend)):
            cumulative = media_spend[i] + cumulative * decay_rate
            adstocked[i] = cumulative
        
        return adstocked
    
    @staticmethod
    def saturation_hill(spend: np.ndarray, alpha: float = 0.5, gamma: float = 1.0) -> np.ndarray:
        return spend ** alpha / (spend ** alpha + gamma ** alpha)
    
    @staticmethod
    def exponential_saturation(spend: np.ndarray, lam: float = 0.01) -> np.ndarray:
        return 1 - np.exp(-lam * spend)
    
    def fit_channel(self, channel_name: str, media_spend: np.ndarray, 
                   sales: np.ndarray, decay_range: tuple = (0.1, 0.9),
                   alpha_range: tuple = (0.1, 2.0)) -> Dict[str, float]:
        def objective(params):
            decay, alpha, gamma = params
            adstocked = self.geometric_adstock(media_spend, decay)
            transformed = self.saturation_hill(adstocked, alpha, gamma)
            
            try:
                from sklearn.linear_model import LinearRegression
                X = transformed.reshape(-1, 1)
                model = LinearRegression()
                model.fit(X, sales)
                predicted = model.predict(X)
                mse = np.mean((sales - predicted) ** 2)
                return mse
            except:
                return 1e10
        
        best_params = None
        best_mse = 1e10
        
        for decay in np.linspace(decay_range[0], decay_range[1], 5):
            for alpha in np.linspace(alpha_range[0], alpha_range[1], 5):
                for gamma in np.linspace(0.1, 2.0, 5):
                    try:
                        params = [decay, alpha, gamma]
                        mse = objective(params)
                        if mse < best_mse:
                            best_mse = mse
                            best_params = {'decay': decay, 'alpha': alpha, 'gamma': gamma}
                    except:
                        continue
        
        if best_params is None:
            best_params = {'decay': 0.5, 'alpha': 0.5, 'gamma': 1.0}
        
        adstocked = self.geometric_adstock(media_spend, best_params['decay'])
        transformed = self.saturation_hill(adstocked, best_params['alpha'], best_params['gamma'])
        
        from sklearn.linear_model import LinearRegression
        X = transformed.reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, sales)
        coefficient = float(model.coef_[0])
        intercept = float(model.intercept_)
        
        self.adstock_params[channel_name] = best_params
        self.channel_effects[channel_name] = {
            'coefficient': coefficient,
            'intercept': intercept,
            'contribution_pct': float(coefficient * transformed.sum() / sales.sum() * 100) if sales.sum() != 0 else 0
        }
        
        return best_params
    
    def transform_media_spend(self, channel_name: str, media_spend: np.ndarray) -> np.ndarray:
        if channel_name not in self.adstock_params:
            return media_spend
        
        params = self.adstock_params[channel_name]
        adstocked = self.geometric_adstock(media_spend, params['decay'])
        transformed = self.saturation_hill(adstocked, params['alpha'], params['gamma'])
        
        return transformed * self.channel_effects[channel_name]['coefficient']
    
    def get_channel_roi(self, channel_name: str) -> Optional[Dict[str, float]]:
        if channel_name not in self.channel_effects:
            return None
        
        effect = self.channel_effects[channel_name]
        return {
            'coefficient': effect['coefficient'],
            'contribution_pct': effect['contribution_pct']
        }
    
    def get_all_effects(self) -> Dict[str, Any]:
        return {
            'channel_effects': self.channel_effects,
            'adstock_params': self.adstock_params
        }


class PriceElasticityModeler:
    def __init__(self):
        self.elasticity = None
        self.base_demand = None
        self.promo_depth_coef = None
    
    def fit(self, prices: np.ndarray, sales: np.ndarray, 
            promo_depths: Optional[np.ndarray] = None) -> Dict[str, float]:
        log_prices = np.log(prices + 1e-10)
        log_sales = np.log(sales + 1e-10)
        
        try:
            from sklearn.linear_model import LinearRegression
            X_price = log_prices.reshape(-1, 1)
            model = LinearRegression()
            model.fit(X_price, log_sales)
            price_elasticity = float(model.coef_[0])
            self.elasticity = price_elasticity
            self.base_demand = float(np.exp(model.intercept_))
        except:
            self.elasticity = -1.0
            self.base_demand = float(sales.mean())
        
        if promo_depths is not None:
            X_promo = promo_depths.reshape(-1, 1)
            model_promo = LinearRegression()
            model_promo.fit(X_promo, log_sales)
            self.promo_depth_coef = float(model_promo.coef_[0])
        
        return {
            'price_elasticity': self.elasticity,
            'base_demand': self.base_demand,
            'promo_depth_coef': self.promo_depth_coef
        }
    
    def predict_promo_impact(self, base_price: float, promo_price: float,
                            promo_depth_pct: float) -> float:
        if self.elasticity is None:
            return 1.0
        
        price_ratio = promo_price / base_price if base_price > 0 else 1.0
        price_effect = (price_ratio ** self.elasticity)
        
        promo_effect = 1.0
        if self.promo_depth_coef is not None:
            promo_effect = 1 + (self.promo_depth_coef * promo_depth_pct / 100)
        
        return price_effect * promo_effect
    
    def get_elasticity(self) -> Optional[float]:
        return self.elasticity


class HolidayEngineer:
    def __init__(self):
        self.holiday_dates = set()
        self.pre_holiday_days = 3
        self.post_holiday_days = 3
    
    def fit(self, holidays: pd.DataFrame, date_col: str = 'date'):
        dates = pd.to_datetime(holidays[date_col])
        self.holiday_dates = set(dates.dt.date)
        
        return self
    
    def add_holiday_features(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        df['is_holiday'] = df[date_col].dt.date.isin(self.holiday_dates).astype(int)
        
        holiday_dates_set = pd.to_datetime(list(self.holiday_dates))
        
        df['days_to_holiday'] = np.inf
        df['days_from_holiday'] = np.inf
        
        for h_date in holiday_dates_set:
            days_to = (df[date_col] - h_date).dt.days
            days_from = (h_date - df[date_col]).dt.days
            
            df.loc[days_to.between(0, self.pre_holiday_days), 'days_to_holiday'] = \
                np.minimum(df.loc[days_to.between(0, self.pre_holiday_days), 'days_to_holiday'], days_to)
            
            df.loc[days_from.between(0, self.post_holiday_days), 'days_from_holiday'] = \
                np.minimum(df.loc[days_from.between(0, self.post_holiday_days), 'days_from_holiday'], days_from)
        
        df['days_to_holiday'] = df['days_to_holiday'].replace({np.inf: -1})
        df['days_from_holiday'] = df['days_from_holiday'].replace({np.inf: -1})
        
        df['is_pre_holiday'] = ((df['days_to_holiday'] >= 0) & (df['days_to_holiday'] <= self.pre_holiday_days)).astype(int)
        df['is_post_holiday'] = ((df['days_from_holiday'] >= 0) & (df['days_from_holiday'] <= self.post_holiday_days)).astype(int)
        
        df.loc[df['is_pre_holiday'] == 1, 'holiday_effect'] = 1 + 0.2 * (1 - df.loc[df['is_pre_holiday'] == 1, 'days_to_holiday'] / self.pre_holiday_days)
        df.loc[df['is_post_holiday'] == 1, 'holiday_effect'] = 1 + 0.1 * (1 - df.loc[df['is_post_holiday'] == 1, 'days_from_holiday'] / self.post_holiday_days)
        df['holiday_effect'] = df['holiday_effect'].fillna(1.0)
        
        return df
    
    def get_holiday_impact(self, holidays: pd.DataFrame, impact_col: str = 'impact_factor') -> Dict[str, float]:
        if impact_col in holidays.columns:
            return holidays.set_index('date')[impact_col].to_dict()
        return {}


class WeatherModeler:
    def __init__(self):
        self.weather_effects = {}
    
    def fit(self, weather_data: pd.DataFrame, sales_data: pd.DataFrame,
            weather_cols: List[str] = None, date_col: str = 'date') -> Dict[str, Any]:
        if weather_cols is None:
            weather_cols = ['temperature', 'rain_mm', 'snow_mm']
        
        merged = weather_data.merge(sales_data, on=date_col, how='inner')
        
        effects = {}
        
        if 'temperature' in merged.columns and 'value' in merged.columns:
            temp_corr = merged['temperature'].corr(merged['value'])
            effects['temperature_corr'] = float(temp_corr)
            
            hot_threshold = merged['temperature'].quantile(0.9)
            cold_threshold = merged['temperature'].quantile(0.1)
            
            hot_sales = merged[merged['temperature'] >= hot_threshold]['value'].mean()
            cold_sales = merged[merged['temperature'] <= cold_threshold]['value'].mean()
            normal_sales = merged[(merged['temperature'] > cold_threshold) & 
                                  (merged['temperature'] < hot_threshold)]['value'].mean()
            
            effects['hot_weather_effect'] = float((hot_sales / normal_sales - 1) * 100) if normal_sales != 0 else 0
            effects['cold_weather_effect'] = float((cold_sales / normal_sales - 1) * 100) if normal_sales != 0 else 0
        
        if 'rain_mm' in merged.columns and 'value' in merged.columns:
            rain_corr = merged['rain_mm'].corr(merged['value'])
            effects['rain_corr'] = float(rain_corr)
            
            rainy_sales = merged[merged['rain_mm'] > 5]['value'].mean()
            normal_sales = merged[merged['rain_mm'] <= 5]['value'].mean()
            
            effects['rainy_day_effect'] = float((rainy_sales / normal_sales - 1) * 100) if normal_sales != 0 else 0
        
        self.weather_effects = effects
        return effects
    
    def get_weather_impact(self, temperature: float, rain_mm: float = 0) -> float:
        impact = 1.0
        
        if 'hot_weather_effect' in self.weather_effects and temperature > 30:
            impact *= (1 + self.weather_effects['hot_weather_effect'] / 100)
        
        if 'cold_weather_effect' in self.weather_effects and temperature < 5:
            impact *= (1 + self.weather_effects['cold_weather_effect'] / 100)
        
        if 'rainy_day_effect' in self.weather_effects and rain_mm > 5:
            impact *= (1 + self.weather_effects['rainy_day_effect'] / 100)
        
        return impact
    
    def get_all_effects(self) -> Dict[str, Any]:
        return self.weather_effects


class AnomalyDetector:
    def __init__(self, threshold: float = 1.5):
        self.threshold = threshold
        self.lower_bound = None
        self.upper_bound = None
    
    def fit(self, data: np.ndarray) -> Dict[str, Any]:
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        self.lower_bound = q1 - self.threshold * iqr
        self.upper_bound = q3 + self.threshold * iqr
        
        is_anomaly = (data < self.lower_bound) | (data > self.upper_bound)
        
        return {
            'lower_bound': float(self.lower_bound),
            'upper_bound': float(self.upper_bound),
            'anomaly_count': int(is_anomaly.sum()),
            'anomaly_pct': float(is_anomaly.mean() * 100)
        }
    
    def detect(self, data: np.ndarray) -> np.ndarray:
        if self.lower_bound is None:
            self.fit(data)
        
        return (data < self.lower_bound) | (data > self.upper_bound)
    
    def impute(self, data: np.ndarray) -> np.ndarray:
        anomalies = self.detect(data)
        
        imputed = data.copy()
        
        for i in range(len(imputed)):
            if anomalies[i]:
                left_idx = max(0, i - 1)
                right_idx = min(len(imputed) - 1, i + 1)
                
                while left_idx >= 0 and anomalies[left_idx]:
                    left_idx -= 1
                while right_idx < len(imputed) and anomalies[right_idx]:
                    right_idx += 1
                
                if left_idx >= 0 and right_idx < len(imputed):
                    imputed[i] = (imputed[left_idx] + imputed[right_idx]) / 2
                elif left_idx >= 0:
                    imputed[i] = imputed[left_idx]
                elif right_idx < len(imputed):
                    imputed[i] = imputed[right_idx]
        
        return imputed
