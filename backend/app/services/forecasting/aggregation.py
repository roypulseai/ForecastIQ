import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

class TimeGranularity(str, Enum):
    DAILY = "D"
    WEEKLY = "W"
    FORTNIGHT = "F"
    MONTHLY = "M"
    QUARTERLY = "Q"
    YEARLY = "Y"

class ProductLevel(str, Enum):
    SKU = "sku"
    PRODUCT = "product"
    CATEGORY = "category"
    SUB_CATEGORY = "sub_category"
    PORTFOLIO = "portfolio"
    REGION = "region"
    STORE = "store"

class AggregationService:
    @staticmethod
    def roll_time(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        target_granularity: TimeGranularity,
        agg_func: str = 'sum'
    ) -> pd.DataFrame:
        if target_granularity == TimeGranularity.DAILY:
            return df
        
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        df = df.set_index(date_col)
        
        if target_granularity == TimeGranularity.WEEKLY:
            df.index = df.index.to_period('W').to_timestamp()
            freq_label = 'Week'
        elif target_granularity == TimeGranularity.FORTNIGHT:
            df['fortnight'] = (df.index.day - 1) // 14 + 1
            df['period'] = df.index.to_period('M').astype(str) + '-F' + df['fortnight'].astype(str)
            df = df.drop(columns=['fortnight'])
            df.index = df['period']
            freq_label = 'Fortnight'
        elif target_granularity == TimeGranularity.MONTHLY:
            df.index = df.index.to_period('M').to_timestamp()
            freq_label = 'Month'
        elif target_granularity == TimeGranularity.QUARTERLY:
            df.index = df.index.to_period('Q').to_timestamp()
            freq_label = 'Quarter'
        elif target_granularity == TimeGranularity.YEARLY:
            df.index = df.index.to_period('Y').to_timestamp()
            freq_label = 'Year'
        else:
            return df
        
        if agg_func == 'sum':
            result = df.groupby(df.index)[value_col].sum()
        elif agg_func == 'mean':
            result = df.groupby(df.index)[value_col].mean()
        elif agg_func == 'median':
            result = df.groupby(df.index)[value_col].median()
        elif agg_func == 'min':
            result = df.groupby(df.index)[value_col].min()
        elif agg_func == 'max':
            result = df.groupby(df.index)[value_col].max()
        else:
            result = df.groupby(df.index)[value_col].sum()
        
        result_df = pd.DataFrame({
            date_col: result.index,
            value_col: result.values
        })
        
        return result_df
    
    @staticmethod
    def roll_time_multiple(
        df: pd.DataFrame,
        date_col: str,
        value_cols: List[str],
        target_granularity: TimeGranularity,
        agg_func: str = 'sum'
    ) -> pd.DataFrame:
        if target_granularity == TimeGranularity.DAILY:
            return df
        
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        agg_dict = {col: agg_func for col in value_cols if col in df.columns}
        
        if target_granularity == TimeGranularity.WEEKLY:
            df['_period'] = df[date_col].dt.to_period('W').dt.to_timestamp()
        elif target_granularity == TimeGranularity.FORTNIGHT:
            df['_fortnight'] = ((df[date_col].dt.day - 1) // 14 + 1).astype(str)
            df['_period'] = df[date_col].dt.to_period('M').astype(str) + '-F' + df['_fortnight']
        elif target_granularity == TimeGranularity.MONTHLY:
            df['_period'] = df[date_col].dt.to_period('M').dt.to_timestamp()
        elif target_granularity == TimeGranularity.QUARTERLY:
            df['_period'] = df[date_col].dt.to_period('Q').dt.to_timestamp()
        elif target_granularity == TimeGranularity.YEARLY:
            df['_period'] = df[date_col].dt.to_period('Y').dt.to_timestamp()
        else:
            return df
        
        result = df.groupby('_period').agg(agg_dict).reset_index()
        result = result.rename(columns={'_period': date_col})
        
        return result
    
    @staticmethod
    def aggregate_product_hierarchy(
        df: pd.DataFrame,
        hierarchy_df: pd.DataFrame,
        groupby_cols: List[str],
        value_col: str = 'sales',
        product_level: ProductLevel = ProductLevel.SKU
    ) -> pd.DataFrame:
        df = df.copy()
        hierarchy_df = hierarchy_df.copy()
        
        if product_level == ProductLevel.SKU:
            return df.groupby(groupby_cols)[value_col].sum().reset_index()
        
        level_mapping = {
            ProductLevel.PRODUCT: 'product_name',
            ProductLevel.CATEGORY: 'category',
            ProductLevel.SUB_CATEGORY: 'sub_category',
            ProductLevel.PORTFOLIO: 'portfolio',
        }
        
        if product_level not in level_mapping:
            return df.groupby(groupby_cols)[value_col].sum().reset_index()
        
        product_col = level_mapping[product_level]
        
        sku_to_level = hierarchy_df[['sku_code', product_col]].drop_duplicates()
        df = df.merge(sku_to_level, left_on='sku_code', right_on='sku_code', how='left')
        
        result = df.groupby(groupby_cols + [product_col])[value_col].sum().reset_index()
        
        return result
    
    @staticmethod
    def hierarchical_rollup(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        hierarchy_df: pd.DataFrame,
        time_granularity: TimeGranularity = TimeGranularity.MONTHLY,
        product_level: ProductLevel = ProductLevel.SKU
    ) -> Dict[str, pd.DataFrame]:
        df_time_rolled = AggregationService.roll_time(
            df, date_col, value_col, time_granularity
        )
        
        levels_to_aggregate = []
        if product_level == ProductLevel.SKU:
            levels_to_aggregate = [ProductLevel.SKU]
        elif product_level == ProductLevel.PRODUCT:
            levels_to_aggregate = [ProductLevel.PRODUCT, ProductLevel.CATEGORY, ProductLevel.PORTFOLIO]
        elif product_level == ProductLevel.CATEGORY:
            levels_to_aggregate = [ProductLevel.CATEGORY, ProductLevel.PORTFOLIO]
        elif product_level == ProductLevel.SUB_CATEGORY:
            levels_to_aggregate = [ProductLevel.SUB_CATEGORY, ProductLevel.CATEGORY, ProductLevel.PORTFOLIO]
        elif product_level == ProductLevel.PORTFOLIO:
            levels_to_aggregate = [ProductLevel.PORTFOLIO]
        
        results = {}
        for level in levels_to_aggregate:
            level_df = AggregationService.aggregate_product_hierarchy(
                df_time_rolled,
                hierarchy_df,
                groupby_cols=[date_col],
                value_col=value_col,
                product_level=level
            )
            results[f'{level.value}_level'] = level_df
        
        return results
    
    @staticmethod
    def regional_aggregation(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        region_col: str = 'region',
        level: str = 'region'
    ) -> pd.DataFrame:
        df = df.copy()
        
        if level == 'store':
            return df.groupby([date_col, region_col])[value_col].sum().reset_index()
        elif level == 'region':
            return df.groupby([date_col, region_col])[value_col].sum().reset_index()
        elif level == 'national':
            return df.groupby(date_col)[value_col].sum().reset_index()
        else:
            return df.groupby([date_col, region_col])[value_col].sum().reset_index()
    
    @staticmethod
    def combined_aggregation(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        hierarchy_df: pd.DataFrame,
        time_granularity: TimeGranularity = TimeGranularity.MONTHLY,
        product_level: ProductLevel = ProductLevel.CATEGORY,
        region_level: str = 'national'
    ) -> pd.DataFrame:
        df_rolled = AggregationService.roll_time(
            df, date_col, value_col, time_granularity
        )
        
        df_hierarchy = df_rolled.merge(
            hierarchy_df[['sku_code', 'product_name', 'category', 'sub_category', 'portfolio']].drop_duplicates(),
            on='sku_code',
            how='left'
        )
        
        level_col_map = {
            ProductLevel.SKU: 'sku_code',
            ProductLevel.PRODUCT: 'product_name',
            ProductLevel.CATEGORY: 'category',
            ProductLevel.SUB_CATEGORY: 'sub_category',
            ProductLevel.PORTFOLIO: 'portfolio',
        }
        
        groupby_cols = [date_col]
        if region_level == 'region':
            groupby_cols.append('region')
        
        groupby_col = level_col_map.get(product_level, 'sku_code')
        
        result = df_hierarchy.groupby(groupby_cols)[value_col].sum().reset_index()
        
        return result
    
    @staticmethod
    def disaggregate_forecast(
        forecast_df: pd.DataFrame,
        disagg_method: str = 'even_split',
        child_count: int = 1
    ) -> pd.DataFrame:
        if child_count <= 1:
            return forecast_df
        
        forecast_df = forecast_df.copy()
        forecast_df['date'] = pd.to_datetime(forecast_df['date'])
        
        rows = []
        for _, row in forecast_df.iterrows():
            base_value = row.get('forecast', row.get('value', 0))
            base_baseline = row.get('baseline', 0)
            
            split_value = base_value / child_count
            split_baseline = base_baseline / child_count if base_baseline else 0
            
            for i in range(child_count):
                new_row = row.copy()
                new_row['forecast'] = split_value
                new_row['baseline'] = split_baseline
                new_row['child_id'] = i + 1
                rows.append(new_row)
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def get_forecast_summary(
        aggregated_df: pd.DataFrame,
        date_col: str,
        value_col: str,
        groupby_level: str
    ) -> Dict[str, Any]:
        df = aggregated_df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        
        summary = {
            'granularity': groupby_level,
            'total_' + value_col: float(df[value_col].sum()),
            'mean_' + value_col: float(df[value_col].mean()),
            'min_' + value_col: float(df[value_col].min()),
            'max_' + value_col: float(df[value_col].max()),
            'count': len(df),
            'start_date': str(df[date_col].min().date()),
            'end_date': str(df[date_col].max().date()),
        }
        
        if groupby_level in ['category', 'sub_category', 'portfolio', 'region']:
            by_group = df.groupby(groupby_level)[value_col].agg(['sum', 'mean', 'count'])
            summary['by_' + groupby_level] = {
                idx: {'total': float(row['sum']), 'mean': float(row['mean']), 'count': int(row['count'])}
                for idx, row in by_group.iterrows()
            }
        
        return summary
