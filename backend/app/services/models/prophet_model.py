"""Facebook Prophet forecaster.

Prophet requires a DataFrame with columns 'ds' and 'y'. We internally rename
the user columns and pre-merge external regressors on 'ds'.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import BaseForecaster

logger = logging.getLogger(__name__)


def _prepare_df(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
) -> pd.DataFrame:
    out = df[[date_col, value_col]].copy()
    out.columns = ["ds", "y"]
    out["ds"] = pd.to_datetime(out["ds"], errors="coerce")
    out["y"] = pd.to_numeric(out["y"], errors="coerce")
    out = out.dropna(subset=["ds", "y"])
    out = out.sort_values("ds")
    out = out.groupby("ds", as_index=False)["y"].mean()
    return out


def _align_external(
    base: pd.DataFrame,
    exog_data: Optional[Dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    """Merge external regressors into the base df on 'ds'."""
    if not exog_data:
        return base
    out = base.copy()
    if "promotions" in exog_data and exog_data["promotions"] is not None and not exog_data["promotions"].empty:
        p = exog_data["promotions"][["date", "discount"]].copy()
        p.columns = ["date", "promo_discount"]
        p["ds"] = pd.to_datetime(p["date"], errors="coerce")
        p = p.dropna(subset=["ds"]).drop(columns=["date"])
        p["promo_discount"] = pd.to_numeric(p["promo_discount"], errors="coerce").fillna(0.0)
        p = p.groupby("ds", as_index=False)["promo_discount"].max()
        out = out.merge(p, on="ds", how="left")
    if "media_plan" in exog_data and exog_data["media_plan"] is not None and not exog_data["media_plan"].empty:
        spend_col = "media_spend" if "media_spend" in exog_data["media_plan"].columns else "spend"
        m = exog_data["media_plan"][["date", spend_col]].copy()
        m.columns = ["date", "media_spend"]
        m["ds"] = pd.to_datetime(m["date"], errors="coerce")
        m = m.dropna(subset=["ds"]).drop(columns=["date"])
        m["media_spend"] = pd.to_numeric(m["media_spend"], errors="coerce").fillna(0.0)
        m = m.groupby("ds", as_index=False)["media_spend"].sum()
        out = out.merge(m, on="ds", how="left")
    if "holidays" in exog_data and exog_data["holidays"] is not None and not exog_data["holidays"].empty:
        h = exog_data["holidays"][["date", "holiday_impact"]].copy()
        h.columns = ["date", "holiday_impact"]
        h["ds"] = pd.to_datetime(h["date"], errors="coerce")
        h = h.dropna(subset=["ds"]).drop(columns=["date"])
        h["holiday_impact"] = pd.to_numeric(h["holiday_impact"], errors="coerce").fillna(1.0)
        h = h.groupby("ds", as_index=False)["holiday_impact"].max()
        out = out.merge(h, on="ds", how="left")
    if "events" in exog_data and exog_data["events"] is not None and not exog_data["events"].empty:
        e = exog_data["events"][["date", "event_impact"]].copy()
        e.columns = ["date", "event_impact"]
        e["ds"] = pd.to_datetime(e["date"], errors="coerce")
        e = e.dropna(subset=["ds"]).drop(columns=["date"])
        e["event_impact"] = pd.to_numeric(e["event_impact"], errors="coerce").fillna(1.0)
        e = e.groupby("ds", as_index=False)["event_impact"].max()
        out = out.merge(e, on="ds", how="left")
    # Fill NAs
    for c in ("promo_discount", "media_spend", "holiday_impact", "event_impact"):
        if c in out.columns:
            out[c] = out[c].fillna(0.0)
    return out


class ProphetForecaster(BaseForecaster):
    name = "Prophet"

    def __init__(
        self,
        seasonality_mode: str = "additive",
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        country: Optional[str] = None,
    ) -> None:
        super().__init__(
            seasonality_mode=seasonality_mode,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            changepoint_prior_scale=changepoint_prior_scale,
            seasonality_prior_scale=seasonality_prior_scale,
            holidays_prior_scale=holidays_prior_scale,
            country=country,
        )
        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.country = country
        self._regressors: List[str] = []

    def fit(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        **kwargs: Any,
    ) -> "ProphetForecaster":
        from prophet import Prophet

        self._date_col = date_col
        self._value_col = value_col
        base = _prepare_df(df, date_col, value_col)
        if base.empty or len(base) < 2:
            raise ValueError("Prophet requires at least 2 data points")
        exog_data = kwargs.get("exog_data")
        prophet_df = _align_external(base, exog_data)
        self._train_df = prophet_df.copy()
        self._last_date = prophet_df["ds"].iloc[-1]
        self._frequency = self._infer_frequency(df, date_col)

        try:
            self._fitted_model = Prophet(
                seasonality_mode=self.seasonality_mode,
                yearly_seasonality=self.yearly_seasonality,
                weekly_seasonality=self.weekly_seasonality,
                daily_seasonality=self.daily_seasonality,
                changepoint_prior_scale=self.changepoint_prior_scale,
                seasonality_prior_scale=self.seasonality_prior_scale,
                holidays_prior_scale=self.holidays_prior_scale,
            )
            if self.country:
                try:
                    self._fitted_model.add_country_holidays(country_name=self.country)
                except Exception as e:
                    logger.warning("Prophet country_holidays failed: %s", e)
        except Exception as e:
            raise RuntimeError(f"Prophet init failed: {e}")

        self._regressors = []
        for reg in ("promo_discount", "media_spend", "holiday_impact", "event_impact"):
            if reg in prophet_df.columns:
                try:
                    self._fitted_model.add_regressor(reg)
                    self._regressors.append(reg)
                except Exception as e:
                    logger.warning("Prophet add_regressor %s failed: %s", reg, e)

        try:
            self._fitted_model.fit(prophet_df)
        except Exception as e:
            raise RuntimeError(f"Prophet fit failed: {e}")
        return self

    def _make_future(self, horizon: int, exog_data: Optional[Dict[str, pd.DataFrame]]) -> pd.DataFrame:
        future = self._fitted_model.make_future_dataframe(periods=horizon, freq=self._frequency or "D")
        if exog_data:
            future = _align_external(future, exog_data)
        # Ensure regressor columns exist
        for reg in self._regressors:
            if reg not in future.columns:
                future[reg] = 0.0
        return future

    def _make_future_baseline(self, horizon: int) -> pd.DataFrame:
        """Baseline: future without any exog — regressor values stay at 0."""
        future = self._fitted_model.make_future_dataframe(periods=horizon, freq=self._frequency or "D")
        for reg in self._regressors:
            future[reg] = 0.0
        return future

    def forecast(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        try:
            future = self._make_future(horizon, exog_data)
            pred = self._fitted_model.predict(future).tail(horizon)
        except Exception as e:
            logger.warning("Prophet predict failed: %s — using naive fallback", e)
            last = float(self._train_df["y"].iloc[-1]) if self._train_df is not None else 0.0
            results = []
            for i in range(horizon):
                d = self._last_date + pd.Timedelta(days=i + 1)
                results.append({
                    "date": self._format_date(d),
                    "forecast": self._safe_float(last),
                    "lower_ci": self._safe_float(last * 0.85),
                    "upper_ci": self._safe_float(last * 1.15),
                })
            return results
        return [
            {
                "date": self._format_date(row["ds"]),
                "forecast": self._safe_float(row["yhat"]),
                "lower_ci": self._safe_float(row.get("yhat_lower", row["yhat"] * 0.85)),
                "upper_ci": self._safe_float(row.get("yhat_upper", row["yhat"] * 1.15)),
            }
            for _, row in pred.iterrows()
        ]

    def get_baseline(
        self,
        horizon: int,
        exog_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if self._fitted_model is None or self._last_date is None:
            raise ValueError("Model not fitted")
        try:
            future = self._make_future_baseline(horizon)
            pred = self._fitted_model.predict(future).tail(horizon)
        except Exception as e:
            logger.warning("Prophet baseline failed: %s", e)
            return self.forecast(horizon, exog_data=None, **kwargs)
        return [
            {
                "date": self._format_date(row["ds"]),
                "forecast": self._safe_float(row["yhat"]),
                "lower_ci": self._safe_float(row.get("yhat_lower", row["yhat"] * 0.85)),
                "upper_ci": self._safe_float(row.get("yhat_upper", row["yhat"] * 1.15)),
            }
            for _, row in pred.iterrows()
        ]

    def get_components(self) -> Dict[str, Any]:
        if self._fitted_model is None or self._last_date is None:
            return {}
        try:
            future = self._fitted_model.make_future_dataframe(periods=30, freq=self._frequency or "D")
            for reg in self._regressors:
                future[reg] = 0.0
            pred = self._fitted_model.predict(future).tail(30)
            comps: Dict[str, Any] = {}
            for c in ("trend", "yearly", "weekly"):
                if c in pred.columns:
                    comps[c] = [self._safe_float(v) for v in pred[c].tolist()]
            return comps
        except Exception:
            return {}
