"""Model factory + analysis helpers."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .models.arima import ARIMAForecaster, SARIMAXForecaster
from .models.base import BaseForecaster
from .models.ets_model import ETSForecaster
from .models.lightgbm_model import LightGBMForecaster
from .models.prophet_model import ProphetForecaster
from .models.stl_model import STLForecaster
from .models.theta_model import ThetaForecaster
from .models.automl_model import AutoMLForecaster
from .models.wma_model import WMAForecaster
from .models.xgboost_model import XGBoostForecaster

logger = logging.getLogger(__name__)


class ModelSelector:
    """Factory + advisor for all forecasting models."""

    MODEL_CLASSES = {
        "arima": ARIMAForecaster,
        "sarimax": SARIMAXForecaster,
        "prophet": ProphetForecaster,
        "lightgbm": LightGBMForecaster,
        "xgboost": XGBoostForecaster,
        "wma": WMAForecaster,
        "ets": ETSForecaster,
        "theta": ThetaForecaster,
        "stl": STLForecaster,
        "automl": AutoMLForecaster,
    }

    def __init__(self) -> None:
        self.last_characteristics: Dict[str, Any] = {}

    # ----------------------------------------------------------- factory
    def get_model(self, model_type: str, params: Optional[Dict[str, Any]] = None) -> BaseForecaster:
        model_type = (model_type or "").lower()
        if model_type not in self.MODEL_CLASSES:
            raise ValueError(f"Unknown model type: {model_type}. "
                             f"Available: {list(self.MODEL_CLASSES.keys())}")
        p = params or {}
        m = self.MODEL_CLASSES[model_type]

        if model_type == "arima":
            ap = p.get("arima") or {}
            return m(order=(ap.get("p", 1), ap.get("d", 1), ap.get("q", 1)))
        if model_type == "sarimax":
            sp = p.get("sarimax") or {}
            return m(
                order=(sp.get("p", 1), sp.get("d", 1), sp.get("q", 1)),
                seasonal_order=(
                    sp.get("seasonal_p", 1),
                    sp.get("seasonal_d", 1),
                    sp.get("seasonal_q", 1),
                    sp.get("seasonal_period", 7),
                ),
            )
        if model_type == "prophet":
            pp = p.get("prophet") or {}
            return m(
                seasonality_mode=pp.get("seasonality_mode", "additive"),
                yearly_seasonality=pp.get("yearly_seasonality", True),
                weekly_seasonality=pp.get("weekly_seasonality", True),
                daily_seasonality=pp.get("daily_seasonality", False),
                changepoint_prior_scale=pp.get("changepoint_prior_scale", 0.05),
                seasonality_prior_scale=pp.get("seasonality_prior_scale", 10.0),
                holidays_prior_scale=pp.get("holidays_prior_scale", 10.0),
                country=pp.get("country"),
            )
        if model_type == "lightgbm":
            lp = p.get("lightgbm") or {}
            return m(
                n_estimators=lp.get("n_estimators", 200),
                learning_rate=lp.get("learning_rate", 0.05),
                max_depth=lp.get("max_depth", 5),
                num_leaves=lp.get("num_leaves", 31),
                min_child_samples=lp.get("min_child_samples", 20),
            )
        if model_type == "xgboost":
            xp = p.get("xgboost") or {}
            return m(
                n_estimators=xp.get("n_estimators", 200),
                learning_rate=xp.get("learning_rate", 0.05),
                max_depth=xp.get("max_depth", 5),
                min_child_weight=xp.get("min_child_weight", 1),
                subsample=xp.get("subsample", 0.9),
                colsample_bytree=xp.get("colsample_bytree", 0.9),
            )
        if model_type == "wma":
            wp = p.get("wma") or {}
            return m(window=wp.get("window", 8))
        if model_type == "ets":
            ep = p.get("ets") or {}
            return m(
                trend=ep.get("trend", "add"),
                seasonal=ep.get("seasonal", "add"),
                seasonal_periods=ep.get("seasonal_periods", 7),
            )
        if model_type == "theta":
            tp = p.get("theta") or {}
            return m(period=tp.get("period", 7), deseasonalize=tp.get("deseasonalize", True))
        if model_type == "stl":
            sp = p.get("stl") or {}
            return m(period=sp.get("period", 7), robust=sp.get("robust", True))
        return m()

    # ----------------------------------------------------------- analysis
    def analyze_data(self, df: pd.DataFrame, date_col: str, value_col: str) -> Dict[str, Any]:
        if df.empty or value_col not in df.columns or date_col not in df.columns:
            return {
                "length": 0, "mean": 0.0, "std": 0.0, "cv": 0.0,
                "trend": "unknown", "seasonality": "none", "stationarity": True,
                "outliers_pct": 0.0, "missing_pct": 0.0,
                "min_date": None, "max_date": None,
                "pdq_recommendation": None, "insights": [],
            }
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col)
        ts_s = ts.set_index(date_col)[value_col]
        if ts_s.index.has_duplicates:
            ts_s = ts_s.groupby(level=0).mean()
        n = len(ts_s)
        mean = float(ts_s.mean()) if n else 0.0
        std = float(ts_s.std()) if n else 0.0
        cv = float(std / mean) if mean else 0.0
        trend = self._detect_trend(ts_s)
        season = self._detect_seasonality(ts_s)
        stationary = self._test_stationarity(ts_s)
        outliers = self._detect_outliers(ts_s)
        missing = float(df[value_col].isna().sum() / max(1, len(df)) * 100)
        chars = {
            "length": n,
            "mean": mean,
            "std": std,
            "cv": cv,
            "trend": trend,
            "seasonality": season,
            "stationarity": stationary,
            "outliers_pct": outliers,
            "missing_pct": missing,
            "min_date": ts_s.index.min().strftime("%Y-%m-%d") if n else None,
            "max_date": ts_s.index.max().strftime("%Y-%m-%d") if n else None,
        }
        chars["pdq_recommendation"] = self.compute_pdq_recommendations(ts_s)
        chars["insights"] = self.generate_insights(chars)
        self.last_characteristics = chars
        return chars

    def _detect_trend(self, ts: pd.Series) -> str:
        if len(ts) < 10:
            return "unknown"
        x = np.arange(len(ts))
        slope, _ = np.polyfit(x, ts.values, 1)
        pct = slope / ts.mean() * 100 if ts.mean() else 0
        if pct > 1:
            return "increasing"
        if pct < -1:
            return "decreasing"
        return "stable"

    def _detect_seasonality(self, ts: pd.Series) -> str:
        if len(ts) < 14:
            return "none"
        try:
            ac7 = float(ts.autocorr(lag=7)) if not pd.isna(ts.autocorr(lag=7)) else 0.0
        except Exception as e:
            logger.warning("Autocorrelation lag-7 failed: %s", e)
            ac7 = 0.0
        if abs(ac7) > 0.5:
            return "weekly"
        if len(ts) > 30:
            try:
                ac30 = float(ts.autocorr(lag=30)) if not pd.isna(ts.autocorr(lag=30)) else 0.0
            except Exception as e:
                logger.warning("Autocorrelation lag-30 failed: %s", e)
                ac30 = 0.0
            if abs(ac30) > 0.5:
                return "monthly"
        if len(ts) > 365:
            try:
                ac365 = float(ts.autocorr(lag=365)) if not pd.isna(ts.autocorr(lag=365)) else 0.0
            except Exception as e:
                logger.warning("Autocorrelation lag-365 failed: %s", e)
                ac365 = 0.0
            if abs(ac365) > 0.5:
                return "yearly"
        return "none"

    def _test_stationarity(self, ts: pd.Series) -> bool:
        if len(ts) < 30:
            return True
        try:
            from statsmodels.tsa.stattools import adfuller
            result = adfuller(ts.dropna(), autolag="AIC")
            return bool(result[1] < 0.05)
        except Exception as e:
            logger.warning("Stationarity test failed, assuming stationary: %s", e)
            return True

    def _detect_outliers(self, ts: pd.Series) -> float:
        if len(ts) < 4:
            return 0.0
        q1, q3 = ts.quantile(0.25), ts.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0.0
        n = int(((ts < (q1 - 1.5 * iqr)) | (ts > (q3 + 1.5 * iqr))).sum())
        return float(n / len(ts) * 100)

    # --------------------------------------------------------- pdq recommendations
    def compute_pdq_recommendations(self, ts: pd.Series) -> Dict[str, Any]:
        """Suggest p, d, q (and seasonal P, D, Q, S) from ACF/PACF + stationarity.

        Returns a dict like:
          {
            "order": {"p": 2, "d": 1, "q": 2},
            "seasonal_order": {"p": 1, "d": 0, "q": 1, "s": 7},
            "reason": "Series is non-stationary (d=1). ACF shows 2 significant lags.",
          }
        """
        if len(ts) < 14:
            return {"order": {"p": 1, "d": 0, "q": 1}, "seasonal_order": None,
                    "reason": "Series too short for reliable ACF/PACF analysis"}

        # Differencing order d — based on stationarity test + variance stabilization
        is_stationary = self._test_stationarity(ts)
        d = 0 if is_stationary else 1
        reasons: List[str] = []

        if is_stationary:
            reasons.append("Series is stationary (d=0)")
        else:
            reasons.append("Series is non-stationary — recommend d=1")

        # Work with differenced series for ACF/PACF if non-stationary
        ts_test = ts.diff().dropna() if d > 0 else ts

        if len(ts_test) < 14:
            return {"order": {"p": 1, "d": d, "q": 1}, "seasonal_order": None,
                    "reason": "; ".join(reasons) + ". Short series: default p=1, q=1"}

        # ACF / PACF via simple lag-based correlation
        nlags = min(20, len(ts_test) // 3)
        ts_vals = ts_test.values
        mean = ts_vals.mean()
        ts_c = ts_vals - mean
        var = (ts_c ** 2).sum()
        if var == 0:
            return {"order": {"p": 1, "d": d, "q": 1}, "seasonal_order": None,
                    "reason": "; ".join(reasons) + ". Constant series"}

        n = len(ts_c)
        acf = np.ones(nlags + 1)
        for lag in range(1, nlags + 1):
            acf[lag] = (ts_c[:-lag] * ts_c[lag:]).sum() / var if var != 0 else 0.0

        # PACF via Yule-Walker (Durbin-Levinson)
        pacf = np.ones(nlags + 1)
        if n > nlags * 2:
            r = acf[1:nlags+1]
            phi = np.zeros((nlags, nlags))
            phi[0, 0] = r[0]
            pacf[1] = r[0]
            for k in range(1, nlags):
                num = r[k]
                den = 1.0
                for j in range(k):
                    num -= phi[k-1, j] * r[k-1-j]
                    den -= phi[k-1, j] * r[j]
                phi[k, k] = num / den if abs(den) > 1e-10 else 0.0
                pacf[k+1] = phi[k, k]
                for j in range(k):
                    phi[k, j] = phi[k-1, j] - phi[k, k] * phi[k-1, k-1-j]

        # Threshold: 2 / sqrt(n)
        threshold = 2.0 / np.sqrt(n)

        # Count significant PACF lags for p
        sig_pacf = [i+1 for i in range(1, nlags) if abs(pacf[i]) > threshold]
        p = (sig_pacf[-1] if sig_pacf else 0) if d == 0 else max(sig_pacf[-1] if sig_pacf else 0, 1)

        # Count significant ACF lags for q
        sig_acf = [i+1 for i in range(1, nlags) if abs(acf[i]) > threshold]
        # For q, look at the last significant lag with alternating sign pattern
        if sig_acf:
            # Find the last significant lag that's not trailing off
            q = sig_acf[-1]
            # Cap at reasonable values
            q = min(q, 5)
        else:
            q = 0 if d > 0 else 1

        p = min(max(p, 0), 5)
        q = min(max(q, 0), 5)

        reasons.append(f"ACF: {len(sig_acf)} significant lags → q={q}")
        reasons.append(f"PACF: {len(sig_pacf)} significant lags → p={p}")

        # Seasonal detection
        season_str = self._detect_seasonality(ts)
        seasonal: Optional[Dict[str, int]] = None
        if season_str != "none" and len(ts) >= 30:
            s_map = {"weekly": 7, "monthly": 30, "yearly": 365}
            sp = s_map.get(season_str, 7)
            seasonal = {"p": 1, "d": 0 if is_stationary else 1, "q": 1, "s": sp}

        return {
            "order": {"p": p, "d": d, "q": q},
            "seasonal_order": seasonal,
            "reason": "; ".join(reasons),
        }

    # --------------------------------------------------------- lag analysis
    def compute_lag_analysis(
        self,
        sales_df: pd.DataFrame,
        date_col: str,
        value_col: str,
        exog_df: pd.DataFrame,
        exog_name: str,
        max_lag: int = 30,
    ) -> Dict[str, Any]:
        """Cross-correlation between sales and an external factor up to max_lag.

        Returns optimal lag and correlation strength.
        """
        try:
            merged = sales_df[[date_col, value_col]].merge(
                exog_df, on=date_col, how="inner"
            )
            if len(merged) < max_lag + 5:
                return {"lag": 0, "correlation": None,
                        "message": f"Not enough overlapping data for {exog_name}"}

            target = pd.to_numeric(merged[value_col], errors="coerce").values
            # Pick the first numeric external column
            exog_cols = [c for c in merged.columns
                         if c not in (date_col, value_col) and pd.api.types.is_numeric_dtype(merged[c])]
            if not exog_cols:
                return {"lag": 0, "correlation": None,
                        "message": f"No numeric columns in {exog_name}"}

            exog = pd.to_numeric(merged[exog_cols[0]], errors="coerce").values

            if len(target) < 10 or len(exog) < 10:
                return {"lag": 0, "correlation": None, "message": "Too few data points"}

            best_corr = -1.0
            best_lag = 0
            for lag in range(0, min(max_lag + 1, len(target) // 2)):
                if lag == 0:
                    corr = np.corrcoef(target, exog)[0, 1]
                else:
                    corr = np.corrcoef(target[lag:], exog[:-lag])[0, 1]
                corr = abs(corr) if not np.isnan(corr) else 0.0
                if corr > best_corr:
                    best_corr = corr
                    best_lag = lag

            strength = "strong" if best_corr > 0.5 else ("moderate" if best_corr > 0.3 else "weak")
            return {
                "lag": int(best_lag),
                "correlation": round(float(best_corr), 3),
                "strength": strength,
                "message": f"Best lag={best_lag}, correlation={best_corr:.3f} ({strength})",
            }
        except Exception as e:
            return {"lag": 0, "correlation": None, "message": str(e)}

    # --------------------------------------------------------- insights
    def generate_insights(self, chars: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate human-readable narrative insights from data characteristics."""
        insights: List[Dict[str, str]] = []
        n = chars.get("length", 0)
        mean = chars.get("mean", 0.0)
        cv = chars.get("cv", 0.0)
        trend = chars.get("trend", "unknown")
        season = chars.get("seasonality", "none")
        outliers = chars.get("outliers_pct", 0.0)
        missing = chars.get("missing_pct", 0.0)
        min_d = chars.get("min_date")
        max_d = chars.get("max_date")

        if n == 0:
            insights.append({"type": "warning", "text": "No data available for analysis."})
            return insights

        # Date range
        if min_d and max_d:
            insights.append({
                "type": "info",
                "text": f"Data spans {min_d} to {max_d} ({n} observations)."
            })

        # Trend
        if trend == "increasing":
            insights.append({
                "type": "info",
                "text": "Upward trend detected — consider models with trend components (Prophet, ARIMA)."
            })
        elif trend == "decreasing":
            insights.append({
                "type": "warning",
                "text": "Downward trend detected — investigate root causes. Damped trend models may help."
            })
        else:
            insights.append({
                "type": "info",
                "text": "No strong trend detected — stable series suitable for simpler models."
            })

        # Seasonality
        if season != "none":
            insights.append({
                "type": "info",
                "text": f"Clear {season} seasonality detected — seasonal models (SARIMAX, Prophet, STL) recommended."
            })
        else:
            insights.append({
                "type": "info",
                "text": "No strong seasonality detected — non-seasonal models (ARIMA, ETS) may suffice."
            })

        # Volatility
        if cv > 0.5:
            insights.append({
                "type": "warning",
                "text": f"High volatility (CV={cv:.1%}) — ML models (LightGBM, XGBoost) handle variance better."
            })
        elif cv < 0.2:
            insights.append({
                "type": "info",
                "text": f"Low volatility (CV={cv:.1%}) — simple methods (WMA, ETS) work well."
            })

        # Outliers
        if outliers > 5:
            insights.append({
                "type": "warning",
                "text": f"{outliers:.1f}% outliers detected — consider robust models (Prophet, STL) or data cleaning."
            })

        # Missing
        if missing > 0:
            insights.append({
                "type": "warning",
                "text": f"{missing:.1f}% values missing — filled with 0. Consider data quality review."
            })

        return insights

    def recommend_models(
        self, data_chars: Dict[str, Any], has_external: bool = False,
        business_type: Optional[str] = None, business_stage: Optional[str] = None,
        cv_results: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []
        n = data_chars.get("length", 0)
        cv = data_chars.get("cv", 0.0)
        season = data_chars.get("seasonality", "none")
        stationary = data_chars.get("stationarity", True)
        outliers = data_chars.get("outliers_pct", 0.0)

        # --- CV-based scoring (most reliable) ---
        if cv_results:
            seen: set = set()
            for m, scores in sorted(
                cv_results.items(),
                key=lambda kv: kv[1].get("mae") or float("inf"),
            ):
                mae = scores.get("mae")
                if mae is None or mae <= 0:
                    continue
                # Score: inverse of normalized MAE, mapped to [0.5, 0.98]
                score = max(0.5, min(0.98, 1.0 - mae / (data_chars.get("mean", 1.0) or 1.0)))
                recs.append({
                    "model": m,
                    "score": round(score, 4),
                    "reason": f"CV MAE={mae:.2f}  RMSE={scores.get('rmse', 0):.2f} over {scores.get('n_folds', '?')} folds",
                })
                seen.add(m)
            recs.sort(key=lambda x: x["score"], reverse=True)
            return recs[:8]

        # --- Heuristic scoring (when CV not available) ---
        # --- Business context adjustments ---
        boost_ml = business_stage in ("hyper_growth", "volatile")
        boost_seasonal = business_stage == "seasonal"
        boost_stable = business_stage in ("mature", "growth")
        boost_decline = business_stage == "declining"

        if n < 14:
            recs.append({"model": "wma", "score": 0.9, "reason": "Short series, simple methods preferred"})
            recs.append({"model": "theta", "score": 0.85, "reason": "Effective for short series"})
            recs.append({"model": "ets", "score": 0.8, "reason": "Adaptive smoothing"})
            return recs[:5]
        if cv > 0.5 or boost_ml:
            score = 0.90 if boost_ml else 0.88
            recs.append({"model": "lightgbm", "score": score, "reason": "High variance — ML captures patterns"})
            recs.append({"model": "xgboost", "score": score - 0.03, "reason": "Robust boosting for complex patterns"})
        elif cv < 0.2:
            recs.append({"model": "wma", "score": 0.82, "reason": "Low variance — moving average sufficient"})
            recs.append({"model": "ets", "score": 0.80, "reason": "Exponential smoothing for stable demand"})
        if season != "none" or boost_seasonal:
            reason = f"Detected {season} seasonality" if season != "none" else "Seasonal stage selected"
            recs.append({"model": "prophet", "score": 0.92, "reason": reason})
            recs.append({"model": "sarimax", "score": 0.85, "reason": "Captures seasonal patterns"})
            recs.append({"model": "stl", "score": 0.82, "reason": "STL decomposition"})
            recs.append({"model": "theta", "score": 0.78, "reason": "Seasonal decomposition"})
        if stationary and not boost_decline:
            recs.append({"model": "arima", "score": 0.78, "reason": "Series is stationary"})
        if boost_decline:
            recs.append({"model": "arima", "score": 0.82, "reason": "ARIMA handles declining trends well"})
        if has_external:
            recs.append({"model": "prophet", "score": 0.9, "reason": "Native support for external regressors"})
            recs.append({"model": "lightgbm", "score": 0.87, "reason": "Handles multiple features well"})
            recs.append({"model": "xgboost", "score": 0.85, "reason": "Robust to feature interactions"})
        if boost_ml:
            recs.append({"model": "prophet", "score": 0.88, "reason": "Prophet handles growth curves & changepoints"})
        if boost_stable:
            recs.append({"model": "ets", "score": 0.85, "reason": "ETS works well for stable, mature demand"})
        if outliers > 5:
            recs.append({"model": "prophet", "score": 0.83, "reason": "Robust to outliers"})
            recs.append({"model": "stl", "score": 0.80, "reason": "STL handles outliers via robust decomposition"})
        # Always include theta as a robust baseline
        recs.append({"model": "theta", "score": 0.7, "reason": "Strong general-purpose baseline"})
        recs.sort(key=lambda x: x["score"], reverse=True)
        seen_set, unique = set(), []
        for r in recs:
            if r["model"] in seen_set:
                continue
            seen_set.add(r["model"])
            unique.append(r)
        return unique[:5]

    # --------------------------------------------------------- validation
    def cross_validate(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        model_type: str,
        params: Optional[Dict[str, Any]] = None,
        horizon: int = 7,
        n_folds: int = 5,
        frequency: str = "D",
    ) -> Dict[str, Any]:
        """Expanding-window time-series cross-validation.

        Runs up to `n_folds` folds with a growing training window and a
        fixed-size test window.  Returns mean + std of MAE / RMSE / MAPE
        across folds, plus per-fold details.
        """
        if df.empty or value_col not in df.columns or date_col not in df.columns:
            return {"mae": None, "rmse": None, "mape": None}
        ts = df[[date_col, value_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts[value_col] = pd.to_numeric(ts[value_col], errors="coerce")
        ts = ts.dropna().sort_values(date_col).reset_index(drop=True)
        ts = ts.groupby(date_col, as_index=False)[value_col].mean()
        n = len(ts)
        if n < max(horizon * 2, 14):
            return {"mae": None, "rmse": None, "mape": None, "note": "insufficient_data"}

        min_train = max(horizon * 2, 14)
        test_size = min(horizon, max(1, (n - min_train) // (n_folds + 1)))
        if test_size < 1:
            test_size = horizon

        fold_results: List[Dict[str, float]] = []
        for i in range(n_folds):
            train_end = min_train + i * test_size
            test_start = train_end
            test_end = test_start + test_size
            if test_end > n:
                break
            train = ts.iloc[:train_end]
            test = ts.iloc[test_start:test_end]
            if len(train) < min_train or len(test) < 1:
                continue
            try:
                model = self.get_model(model_type, params)
                model.fit(train, date_col, value_col, frequency=frequency)
                preds = model.forecast(len(test))
                pred_values = np.array([self._safe_float(p.get("forecast", 0.0)) for p in preds])
                actuals = test[value_col].astype(float).values
                m = min(len(pred_values), len(actuals))
                if m == 0:
                    continue
                pv, av = pred_values[:m], actuals[:m]
                diff = pv - av
                mae = float(np.mean(np.abs(diff)))
                rmse = float(np.sqrt(np.mean(diff ** 2)))
                denom = np.where(np.abs(av) < 1e-9, 1e-9, np.abs(av))
                mape = float(np.mean(np.abs(diff / denom)) * 100)
                fold_results.append({
                    "mae": mae, "rmse": rmse, "mape": mape,
                    "r2": 1 - float(np.sum(diff ** 2)) / float(np.sum((av - np.mean(av)) ** 2)) if len(av) > 0 and np.std(av) != 0 else None,
                    "fold": i, "train_size": len(train), "test_size": len(test)
                })
            except Exception as e:
                logger.debug("CV fold %d failed for %s: %s", i, model_type, e)

        if len(fold_results) < 2:
            logger.warning("CV for %s: only %d fold(s) succeeded — insufficient", model_type, len(fold_results))
            return {"mae": None, "rmse": None, "mape": None, "note": "insufficient_folds"}

        mae_vals = [f["mae"] for f in fold_results]
        rmse_vals = [f["rmse"] for f in fold_results]
        mape_vals = [f["mape"] for f in fold_results]
        r2_vals = [f["r2"] for f in fold_results if f.get("r2") is not None]

        return {
            "mae": float(np.mean(mae_vals)),
            "rmse": float(np.mean(rmse_vals)),
            "mape": float(np.mean(mape_vals)),
            "mae_std": float(np.std(mae_vals)),
            "rmse_std": float(np.std(rmse_vals)),
            "mape_std": float(np.std(mape_vals)),
            "r2": float(np.mean(r2_vals)) if r2_vals else None,
            "r2_std": float(np.std(r2_vals)) if r2_vals else None,
            "n_folds": len(fold_results),
            "fold_details": fold_results,
        }

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            v = float(x)
            if np.isnan(v) or np.isinf(v):
                return default
            return v
        except (TypeError, ValueError) as e:
            logger.warning("Safe float conversion failed for %r: %s", x, e)
            return default
