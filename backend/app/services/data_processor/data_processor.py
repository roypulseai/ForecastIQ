import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
import os

class DataProcessor:
    @staticmethod
    def process_csv(file_path: str) -> pd.DataFrame:
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file_path)
        raise ValueError(f"Unsupported file format: {file_path}")
    
    @staticmethod
    def validate_sales_data(df: pd.DataFrame) -> Dict[str, any]:
        errors = []
        
        if df.empty:
            errors.append("DataFrame is empty")
            return {'valid': False, 'errors': errors}
        
        date_col = None
        value_col = None
        
        possible_date_cols = ['date', 'ds', 'timestamp', 'datetime', 'order_date', 'sales_date']
        for col in possible_date_cols:
            if col in df.columns:
                date_col = col
                break
        
        if date_col is None:
            for col in df.columns:
                if df[col].dtype == 'datetime64[ns]' or 'date' in col.lower():
                    date_col = col
                    break
        
        possible_value_cols = ['value', 'y', 'sales', 'demand', 'revenue', 'quantity', 'qty', 'units']
        for col in possible_value_cols:
            if col in df.columns:
                value_col = col
                break
        
        if value_col is None:
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64'] and col not in ['id', 'year', 'month']:
                    value_col = col
                    break
        
        if date_col is None:
            errors.append("Could not identify date column")
        if value_col is None:
            errors.append("Could not identify value column")
        
        if date_col and date_col not in df.columns:
            errors.append(f"Date column '{date_col}' not found")
        if value_col and value_col not in df.columns:
            errors.append(f"Value column '{value_col}' not found")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'date_column': date_col,
            'value_column': value_col,
            'row_count': len(df)
        }
    
    @staticmethod
    def process_media_plan(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Media plan must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        
        required_cols = ['channel', 'spend']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Media plan missing required column: {col}")
        
        df['media_spend'] = df['spend'].fillna(0)
        df['media_channel'] = df['channel']
        
        result_cols = ['date', 'media_channel', 'media_spend']
        if 'reach' in df.columns:
            df['reach'] = df['reach'].fillna(0)
            result_cols.append('reach')
        if 'impressions' in df.columns:
            df['impressions'] = df['impressions'].fillna(0)
            result_cols.append('impressions')
        
        return df[result_cols]
    
    @staticmethod
    def process_promotions(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Promotions data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        
        discount_col = None
        for col in df.columns:
            if 'discount' in col.lower() or 'pct' in col.lower() or 'off' in col.lower():
                discount_col = col
                break
        
        if discount_col is None:
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64'] and col not in ['id']:
                    discount_col = col
                    break
        
        if discount_col is None:
            df['discount'] = 0
        else:
            df['discount'] = df[discount_col].fillna(0)
        
        promo_cols = ['date', 'discount']
        if 'promo_id' in df.columns:
            df['promo_id'] = df['promo_id'].fillna('NA')
            promo_cols.append('promo_id')
        if 'promo_type' in df.columns:
            promo_cols.append('promo_type')
        if 'original_price' in df.columns:
            promo_cols.append('original_price')
        if 'promo_price' in df.columns:
            promo_cols.append('promo_price')
        
        return df[promo_cols]
    
    @staticmethod
    def process_holidays(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Holidays data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        df['is_holiday'] = 1.0
        
        if 'impact_factor' in df.columns:
            df['is_holiday'] = df['impact_factor'].fillna(1.0)
        elif 'impact' in df.columns:
            df['is_holiday'] = df['impact'].fillna(1.0)
        
        result_cols = ['date', 'is_holiday']
        if 'holiday_name' in df.columns:
            df['holiday_name'] = df['holiday_name'].fillna('Unknown')
            result_cols.append('holiday_name')
        if 'holiday_type' in df.columns:
            result_cols.append('holiday_type')
        
        return df[result_cols]
    
    @staticmethod
    def process_events(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Events data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        df['is_event'] = 1.0
        
        if 'impact_factor' in df.columns:
            df['is_event'] = df['impact_factor'].fillna(1.0)
        
        result_cols = ['date', 'is_event']
        if 'event_name' in df.columns:
            df['event_name'] = df['event_name'].fillna('Unknown')
            result_cols.append('event_name')
        if 'event_type' in df.columns:
            result_cols.append('event_type')
        
        return df[result_cols]
    
    @staticmethod
    def process_weather(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Weather data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        
        if 'temperature' not in df.columns:
            temp_col = None
            for col in df.columns:
                if 'temp' in col.lower():
                    temp_col = col
                    break
            if temp_col:
                df['temperature'] = df[temp_col]
        
        df['temperature'] = df.get('temperature', 20).fillna(20)
        
        rain_col = None
        for col in df.columns:
            if 'rain' in col.lower() or 'precip' in col.lower():
                rain_col = col
                break
        if rain_col:
            df['rain_mm'] = df[rain_col].fillna(0)
        else:
            df['rain_mm'] = 0
        
        snow_col = None
        for col in df.columns:
            if 'snow' in col.lower():
                snow_col = col
                break
        if snow_col:
            df['snow_mm'] = df[snow_col].fillna(0)
        else:
            df['snow_mm'] = 0
        
        return df[['date', 'temperature', 'rain_mm', 'snow_mm']]
    
    @staticmethod
    def process_competitor(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Competitor data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        
        competitor_col = None
        for col in df.columns:
            if 'competitor' in col.lower() or 'name' in col.lower():
                competitor_col = col
                break
        
        price_col = None
        for col in df.columns:
            if 'price' in col.lower():
                price_col = col
                break
        
        market_share_col = None
        for col in df.columns:
            if 'market_share' in col.lower() or 'share' in col.lower():
                market_share_col = col
                break
        
        result = df[['date']].copy()
        
        if competitor_col:
            result['competitor_name'] = df[competitor_col].fillna('Unknown')
        if price_col:
            result['competitor_price'] = df[price_col].fillna(0)
        if market_share_col:
            result['market_share'] = df[market_share_col].fillna(0)
        else:
            result['market_share'] = 0
        
        if 'promotion_flag' in df.columns:
            result['promotion_flag'] = df['promotion_flag'].fillna(0)
        else:
            result['promotion_flag'] = 0
        
        return result
    
    @staticmethod
    def process_economic(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            raise ValueError("Economic data must have a date column")
        
        df['date'] = pd.to_datetime(df[date_col])
        
        result = df[['date']].copy()
        
        if 'gdp' in df.columns:
            result['gdp'] = df['gdp'].fillna(0)
        if 'growth_rate' in df.columns:
            result['growth_rate'] = df['growth_rate'].fillna(0)
        if 'consumer_confidence' in df.columns:
            result['consumer_confidence'] = df['consumer_confidence'].fillna(100)
        if 'inflation' in df.columns:
            result['inflation'] = df['inflation'].fillna(0)
        if 'cpi' in df.columns:
            result['cpi'] = df['cpi'].fillna(100)
        
        return result
    
    @staticmethod
    def resample_time_series(df: pd.DataFrame, date_col: str, value_col: str,
                             target_freq: str) -> pd.DataFrame:
        ts = df.set_index(date_col)[value_col].sort_index()
        ts.index = pd.to_datetime(ts.index)
        
        resampled = ts.resample(target_freq).sum()
        
        result = pd.DataFrame({
            date_col: resampled.index,
            value_col: resampled.values
        })
        
        return result.dropna()
    
    @staticmethod
    def add_time_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
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
        
        return df
    
    @staticmethod
    def detect_anomalies(series: pd.Series, threshold: float = 1.5) -> pd.Series:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        return (series < lower_bound) | (series > upper_bound)
    
    @staticmethod
    def impute_anomalies(df: pd.DataFrame, date_col: str, value_col: str,
                        threshold: float = 1.5) -> pd.DataFrame:
        df = df.copy()
        
        series = df.set_index(date_col)[value_col]
        anomalies = DataProcessor.detect_anomalies(series, threshold)
        
        for idx in df[anomalies.values].index:
            left_idx = max(0, idx - 1)
            right_idx = min(len(df) - 1, idx + 1)
            
            while left_idx >= 0 and df.index[left_idx] in anomalies[anomalies].index:
                left_idx -= 1
            while right_idx < len(df) and df.index[right_idx] in anomalies[anomalies].index:
                right_idx += 1
            
            if left_idx >= 0 and right_idx < len(df):
                df.loc[idx, value_col] = (df.iloc[left_idx][value_col] + df.iloc[right_idx][value_col]) / 2
        
        return df
