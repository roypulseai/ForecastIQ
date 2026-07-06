import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class BaseForecaster:
    def __init__(self, name: str):
        self.name = name
        self.model = None
        self.results_ = None
    
    def fit(self, df: pd.DataFrame, date_col: str, value_col: str, **kwargs) -> 'BaseForecaster':
        raise NotImplementedError
    
    def forecast(self, horizon: int, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def get_metrics(self) -> Dict[str, float]:
        return {}
