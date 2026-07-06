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
        
        required_cols = ['channel', 'spend', 'start_date', 'end_date']
        for col in required_cols:
            if col not in df.columns:
                if col in ['start_date', 'end_date']:
                    continue
                raise ValueError(f"Media plan missing required column: {col}")
        
        spend_col = 'spend'
        if 'spend' not in df.columns:
            for col in df.columns:
                if 'spend' in col.lower() or 'cost' in col.lower():
                    spend_col = col
                    break
        
        df['media_spend'] = df[spend_col].fillna(0)
        
        return df[['date', 'channel', 'media_spend']].rename(columns={'channel': 'media_channel'})
    
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
        
        return df[['date', 'discount']]
    
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
        df['is_holiday'] = 1
        
        if 'impact' in df.columns:
            df['is_holiday'] = df['impact']
        
        return df[['date', 'is_holiday']]
    
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
        df['is_event'] = 1
        
        if 'impact_factor' in df.columns:
            df['is_event'] = df['impact_factor']
        
        return df[['date', 'is_event']]
    
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
        
        return df
