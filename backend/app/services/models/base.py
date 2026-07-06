"""Base forecaster interface.

All concrete forecasters must inherit from BaseForecaster and implement
`fit` and `forecast`. They MAY override `get_baseline`, `get_components`,
`get_feature_importance`, and `get_metrics`.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaseForecaster(ABC):
    """Abstract base class for all forecasting models."""

    name: str = "Base"

    def __init__(self, **params: Any) -> None:
        self.params: Dict[str, Any] = dict(params)
        self._fitted_model: Any = None
        self._last_date: Optional[pd.Timestamp] = None
        self._frequency: str = "D"
        self._feature_cols: List[str] = []
        self._date_col: Optional[str] = None
        self._value_col: Optional[str] = None
        self._train_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------ fit
    @abstractmethod
    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "BaseForecaster":
        """Fit the model to `df`. Must store `_date_col`, `_value_col`,
        `_last_date`, and `_frequency` on `self`."""

    # ---------------------------------------------------------- forecast
    @abstractmethod
    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Produce a forecast. Each returned dict has keys:
        `date` (str, YYYY-MM-DD), `forecast` (float),
        `lower_ci` (float), `upper_ci` (float)."""

    # ------------------------------------------------------------ baseline
    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Baseline forecast: identical to `forecast` but with external
        factors forced to zero. Default implementation simply calls
        `forecast` with exog_data=None; subclasses may override."""
        return self.forecast(horizon, exog_data=None, **kwargs)

    # ------------------------------------------------------------- extras
    def get_components(self) -> Dict[str, Any]:
        return {}

    def get_feature_importance(self) -> Dict[str, float]:
        return {}

    def get_metrics(self) -> Dict[str, float]:
        return {}

    # ----------------------------------------------------------- utilities
    @staticmethod
    def _format_date(d: Any) -> str:
        """Format any date / timestamp value as YYYY-MM-DD string."""
        if d is None:
            return ""
        try:
            ts = pd.Timestamp(d)
            if pd.isna(ts):
                return ""
            return ts.strftime("%Y-%m-%d")
        except Exception:
            return str(d)[:10]

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            v = float(x)
            if pd.isna(v) or v != v:  # NaN check
                return default
            if v == float("inf") or v == float("-inf"):
                return default
            return v
        except (TypeError, ValueError):
            return default
